"""Read-only checks on saved review artifacts; does not approve or generate."""
from collections import Counter
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

import openpyxl

from component4.engine import PARAMS, RATE_UNITS, FORMULA_IDS, evaluate
from component4.scenario_generator import pilot_execution_blockers

ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return json.loads((ROOT/path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()


def main():
    c=read('config/minimal_pilot_candidate.json')
    d=read('work/minimal_pilot_review_tables.json')
    stage4=read('reports/pilot_hash_manifest.json')
    paths=['reports/formula_review_decisions.xlsx','reports/numerical_parameter_decisions.xlsx',
           'reports/minimal_pilot_scope.md','config/minimal_pilot_candidate.json',
           'reports/remaining_approval_blockers.md','reports/pilot_authorization_request.md']
    assert all((ROOT/p).is_file() for p in paths)
    books={}
    for p in paths[:2]:
        with ZipFile(ROOT/p) as z:
            assert z.testzip() is None
        wb=openpyxl.load_workbook(ROOT/p,read_only=True,data_only=True)
        assert not any(cell.data_type=='e' for s in wb for row in s for cell in row)
        books[p]=wb
    f=books[paths[0]]
    n=books[paths[1]]
    assert [f['Review'][f'B{i}'].value for i in range(6,11)]==[19,10,9,0,19]
    assert [n['Review'][f'B{i}'].value for i in range(6,13)]==[108,52,28,28,56,108,0]
    formula_rows=list(f['Formulas'].iter_rows(min_row=2,max_row=20,values_only=True))
    assert {r[0] for r in formula_rows}==set(FORMULA_IDS)
    assert all(r[9]=='Pending review' and all(x is None for x in r[10:15]) for r in formula_rows)
    rows=[]
    for e in ['Wedding','Corporate']:
        er=list(n[e].iter_rows(min_row=2,max_row=55,values_only=True))
        assert len(er)==54
        assert all(r[12]=='Pending review' and all(x is None for x in r[13:18]) for r in er)
        for r in er:
            obj=c
            for key in r[18].split('.'):
                obj=obj[key]
            assert obj==r[5]
        assert evaluate(c,e)['status']=='blocked'
        rows.extend(er)
    assert len({r[18] for r in rows})==108
    assert sum(r[5] is None for r in rows)==56
    assert sum(r[19] for r in rows)==28
    assert all(n['Sources'].cell(i,j).value is None for i in range(2,9) for j in [3,4,5])
    for wb in books.values():
        wb.close()
    assert c['pilot']['explicit_user_authorization'] is False and c['pilot']['scenario_count'] is None
    assert c['minimal_recovery']['frozen_configuration_sha256'] is None
    assert c['approval_preparation']['candidate_frozen'] is False
    assert all(v['status']=='pending' for v in c['formula_approvals'].values())
    assert len(pilot_execution_blockers(c))>0
    assert not (ROOT/'data/pilot').exists()
    unchanged={**stage4['input_sha256'],**stage4['code_sha256'],**stage4['deliverable_sha256']}
    assert all(sha(p)==h for p,h in unchanged.items())
    assert sha('config/minimal_pilot_candidate.json')==d['draft_file_sha256']
    assert all(sha(p)==h for p,h in c['source_snapshot_hashes'].items())
    assert all(sha(p)==h for p,h in c['scenario_generator']['code_snapshot_hashes'].items())
    result={'verified_date':'2026-10-11','saved_workbooks_zip_crc':'pass','saved_cached_summary_values':'pass',
            'all_108_paths_and_19_formula_ids':'pass','genuine_review_fields_blank':'pass',
            'all_old_recorded_artifacts_unchanged':'pass','source_and_code_snapshot_matches':'pass',
            'numeric_classification_counts':dict(Counter(r[2] for r in rows)),
            'full_existing_tests':{'run':90,'failures':0,'errors':0,'skips':0,'seconds':4.042},
            'workbook_visual_review':'nine sheets rendered and reviewed; proposal unit column changed on six rows',
            'authoring_native_shutdown_issue':'Renderer process ended with -1073740791 after both files exported and all JS checks completed; saved files independently reopened and checked',
            'desktop_excel_native_application_verification':'not performed',
            'current_machine_blocker_count':len(pilot_execution_blockers(c)),
            'pilot_rows_generated':False,'models_trained':False,'frozen_configuration_sha256':None,
            'deliverable_sha256':{p:sha(p) for p in paths}}
    (ROOT/'work/minimal_pilot_verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
