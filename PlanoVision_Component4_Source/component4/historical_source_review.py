"""Field-specific source review. Never rewrites observations or approves market validity."""
from collections import Counter,defaultdict
import csv
from datetime import datetime,timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
MONTHS=('January February March April May June July August September October November December').split()
SNAPSHOT='outputs/experiments/v1.2/future_prices_20261018_v0_1/source_snapshot.csv'
LINEAGE='data/refined/historical.v0.1-20261012/observation_provenance.csv'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read_csv(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as stream:return list(csv.DictReader(stream))
def compact(value):return re.sub(r'\s+','',value).casefold()

def index_values(text,index_type):
    if compact('MOVEMENTS OF THE '+index_type) not in compact(text) or '2021' not in text:
        raise ValueError('index_table_heading_or_base_not_identified')
    current_year=None;rows={}
    pattern=r'^\s*(?:(20\d{2})\s+)?('+ '|'.join(MONTHS)+r')\s+(\d+(?:\.\d+)?)(?:\s|$)'
    for number,line in enumerate(text.splitlines(),1):
        match=re.match(pattern,line,re.I)
        if not match:continue
        year,month,value=match.groups()
        if year:current_year=int(year)
        if current_year is None:raise ValueError('index_year_not_identified')
        month_number=next(i for i,v in enumerate(MONTHS,1) if v.casefold()==month.casefold())
        key=f'{current_year:04d}-{month_number:02d}-01'
        if key in rows:raise ValueError('duplicate_index_month')
        rows[key]={'value':float(value),'text':line.strip(),'line':number}
    return rows

def retail_value(text,source):
    week=source['reported_week'];year,month,number=re.fullmatch(r'(\d{4})-(\d{2})-W(\d)',week).groups()
    title=r'\b'+number+r'(?:st|nd|rd|th)\s+Week\s+of\s+'+MONTHS[int(month)-1]+r'\s+'+year+r'\b'
    period_note='title_period_matches'
    if not re.search(title,text,re.I):
        # A publisher title can conflict with its current-price columns. Resolve only
        # the documented January 2024 W4 snapshot, with both column and comparison
        # headings present. Preserve the conflict, never rewrite the publisher PDF.
        known=(week=='2024-01-W4' and source['source_file']=='DCSB-WRP-2024-01-W4.pdf'
               and re.search(r'4th\s+Week\s+of\s+January\s+2023\b',text,re.I)
               and len(re.findall(r'Jan\.\s+2024\b',text,re.I))>=3
               and re.search(r'4th\s+week\s+of\s*Jan\.\s+2024\s+compared\s+to',text,re.I))
        if not known:return None,'publisher_week_or_geographic_heading_not_matched'
        period_note='publisher_title_2023_conflict_retained; current_price_columns_and_comparison_header_2024_match_filename'
    if 'colombo' not in text.casefold():
        return None,'publisher_week_or_geographic_heading_not_matched'
    if not ('Avg.Price' in text or 'Avg. Price' in text or 'Average Price' in text):
        return None,'publisher_price_column_heading_not_matched'
    prefix=compact(source['item_raw']+source['unit_raw'])
    pattern=r'^\s*'+r'\s*'.join(re.escape(c) for c in prefix)+r'(?=\s|[+\-]?\d)'
    candidates=[]
    for line_number,line in enumerate(text.splitlines(),1):
        match=re.match(pattern,line,re.I)
        if match:
            tokens=re.findall(r'n\.a\.?|[+\-]?\d+(?:,\d{3})*(?:\.\d+)?',line[match.end():],re.I)
            if len(tokens)>=3:
                value=tokens[2]
                if value.casefold().startswith('n.a'):continue
                candidates.append({'value':float(value.replace(',','')),'text':line.strip(),'line':line_number})
    if len(candidates)!=1:return None,'missing_or_ambiguous_item_unit_current_price_column'
    return {**candidates[0],'period_resolution':period_note},''

def build_review(root,pdf_page_text):
    root=Path(root);observations=read_csv(root/SNAPSHOT)
    ids={r['observation_id'] for r in observations}
    links=[r for r in read_csv(root/LINEAGE) if r['observation_id'] in ids]
    inflation={r['source_record_id']:r for r in read_csv(root/'data/processed/inflation.csv')}
    retail={r['source_record_id']:r for r in read_csv(root/'data/processed/retail_prices.csv')}
    by_observation=defaultdict(list);decisions=[];publishers={};indices={}
    for link in links:
        sid=link['source_id'];filename=link['publisher_filename']
        if Path(filename).name!=filename or sid not in {'S001','S002','S003'}:raise ValueError('unsafe_publisher_identity')
        publisher=root/'data/raw/publishers'/sid/filename
        key=str(publisher.relative_to(root)).replace('\\','/')
        if key not in publishers:
            digest=sha(publisher)
            if digest!=link['publisher_sha256']:raise ValueError('publisher_checksum_mismatch')
            publishers[key]=digest
        elif publishers[key]!=link['publisher_sha256']:raise ValueError('conflicting_publisher_hash')
        page=int(link['publisher_page'] or '1')
        text=pdf_page_text(publisher,page)
        source=inflation.get(link['source_record_id']) if sid!='S003' else retail.get(link['source_record_id'])
        if source is None:raise ValueError('missing_linked_source_row')
        expected=float(source['index_value'] if sid!='S003' else source['current_price_lkr'])
        if expected!=float(link['source_observed_value']):raise ValueError('source_lineage_value_mismatch')
        if sid=='S003':found,reason=retail_value(text,source)
        else:
            if sid not in indices:indices[sid]=index_values(text,source['index_type'])
            found=indices[sid].get(source['month']);reason='' if found else 'index_month_not_found'
        status='source_value_confirmed_keep' if found and abs(found['value']-expected)<1e-9 else 'confirmed_value_mismatch' if found else 'unresolved_source_mapping'
        decision={'observation_id':link['observation_id'],'source_record_id':link['source_record_id'],
                  'original_value':expected,'publisher_value':found['value'] if found else None,
                  'status':status,'reason':reason,'original_quality_flags':source['quality_flag'],
                  'modelled_field':'current_price_lkr' if sid=='S003' else 'index_value',
                  'publisher_file':key,'publisher_sha256':publishers[key],'publisher_page':page,
                  'publisher_text_line':found['line'] if found else None,'publisher_row_text':found['text'] if found else '',
                  'period_resolution':found.get('period_resolution','index_month_and_year_column') if found else 'unresolved',
                  'unit':link['source_unit'],'period':source['reported_week'] if sid=='S003' else source['month']}
        decisions.append(decision);by_observation[link['observation_id']].append(decision)
    reviewed=[]
    for row in observations:
        contributors=by_observation[row['observation_id']]
        if len(contributors)!=int(row['source_record_count']):raise ValueError('monthly_contributor_count_mismatch')
        expected=sum(Decimal(str(c['original_value'])) for c in contributors)/Decimal(len(contributors))
        if abs(float(expected)-float(row['y']))>1e-8:raise ValueError('monthly_aggregation_mismatch')
        resolved=all(c['status']=='source_value_confirmed_keep' and c['unit']==row['unit'] for c in contributors)
        reviewed.append({**row,'model_value_review_status':'retained_publisher_value_confirmed' if resolved else 'unresolved',
                         'unresolved_source_values':sum(c['status']!='source_value_confirmed_keep' or c['unit']!=row['unit'] for c in contributors),
                         'reviewed_value':float(row['y']),'source_contributor_ids':[c['source_record_id'] for c in contributors],
                         'original_flags_preserved':True,'publication_date_verified':False})
    if len(ids)!=len(observations) or len({c['source_record_id'] for c in decisions})!=len(decisions):raise ValueError('duplicate_review_identity')
    summaries=[]
    for sid in sorted({r['series_id'] for r in reviewed}):
        part=[r for r in reviewed if r['series_id']==sid]
        summaries.append({'series_id':sid,'records':len(part),'original_flagged_observations':sum(bool(r['quality_flag']) for r in part),
                          'unresolved_model_value_observations':sum(r['model_value_review_status']=='unresolved' for r in part),
                          'numerical_values_changed':0})
    return {'version':'historical-source-review.0.3','review_method':'Automated item/unit/period/current-column matching against checksum-verified retained publisher PDFs; not independent market or domain validation. One named publisher title conflict uses its explicit 2024 current-price/comparison headers and remains recorded.',
            'observations':reviewed,'source_decisions':decisions,'series':summaries,'publisher_hashes':publishers,
            'source_hashes':{p:sha(root/p) for p in (SNAPSHOT,LINEAGE,'data/processed/inflation.csv','data/processed/retail_prices.csv')},
            'source_status_counts':dict(Counter(r['status'] for r in decisions)),
            'original_values_changed':0,'original_flags_removed':0,'real_event_outcomes_added':0,
            'publication_timestamps_verified':False,'complete_publisher_coverage_verified':False,
            'created_utc':datetime.now(timezone.utc).isoformat()}
