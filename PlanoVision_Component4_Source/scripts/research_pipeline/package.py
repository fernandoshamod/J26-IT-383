from pathlib import Path
import zipfile
from common import ROOT,COLLECTION
target=COLLECTION/'Component4_Engineering_Stage1.zip'
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for folder in ['scripts/research_pipeline','tests','reports','data/processed','data/final']:
        for p in sorted((ROOT/folder).rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith('.inspect.ndjson'):
                z.write(p,p.relative_to(ROOT))
    z.write(ROOT/'README_dataset_pipeline.md','README_dataset_pipeline.md')
    z.write(ROOT/'work/original_schema.json','work/original_schema.json')
print('PACKAGE',target,target.stat().st_size)
