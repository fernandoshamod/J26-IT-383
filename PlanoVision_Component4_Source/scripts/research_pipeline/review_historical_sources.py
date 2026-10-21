"""Read retained publisher PDFs and create a separate field-specific review derivative."""
from functools import lru_cache
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from component4.historical_source_review import build_review,sha

def main():
    from pypdf import PdfReader
    @lru_cache(maxsize=256)
    def reader(path):return PdfReader(path)
    @lru_cache(maxsize=512)
    def page_text(path,page):
        return reader(path).pages[page-1].extract_text()
    out=ROOT/'data/reviewed/historical_quality_v0_3_20261021'
    if out.exists():raise ValueError('refuse_existing_review_derivative')
    review=build_review(ROOT,page_text)
    summary={k:v for k,v in review.items() if k not in {'source_decisions','observations','publisher_hashes'}}
    summary.update(observation_count=len(review['observations']),source_records=len(review['source_decisions']),publisher_files=len(review['publisher_hashes']))
    out.mkdir(parents=True)
    (out/'review.json').write_text(json.dumps(review,indent=2,allow_nan=False),encoding='utf-8')
    (out/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False),encoding='utf-8')
    manifest={'version':review['version'],'files':{name:sha(out/name) for name in ('review.json','summary.json')},
              'review_code_sha256':sha(ROOT/'component4/historical_source_review.py'),
              'builder_sha256':sha(Path(__file__)),
              'source_hashes':review['source_hashes'],'source_snapshot_sha256':review['source_hashes']['outputs/experiments/v1.2/future_prices_20261018_v0_1/source_snapshot.csv'],
              'original_values_changed':0,'original_flags_removed':0,'model_refit_performed':False}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps({**summary,'manifest_sha256':sha(out/'manifest.json')},indent=2))

if __name__=='__main__':main()
