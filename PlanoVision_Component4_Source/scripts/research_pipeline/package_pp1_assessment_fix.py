"""Package rubric-aligned current docs and genuine evidence without personal records."""
from pathlib import Path
import hashlib
import html
import json
import shutil
import zipfile
from html.parser import HTMLParser
import mistune

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'outputs/PlanoVision_PP1_Assessment_Fixed_20261021'


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUT.exists(): raise ValueError('refuse_existing_assessment_package')
    OUT.mkdir()
    source=ROOT/'reports/PP1_ASSESSMENT_FIXED_20261021'
    docs=sorted(source.glob('*.md'))
    renderer=mistune.create_markdown(plugins=['table'])
    sections=[]
    for index,path in enumerate(docs):
        shutil.copy2(path,OUT/path.name)
        sections.append('<section id="part'+str(index)+'">'+renderer(path.read_text(encoding='utf-8'))+'</section>')
    for path in source.glob('*.json'): shutil.copy2(path,OUT/path.name)
    originals=OUT/'supporting_evidence'
    originals.mkdir()
    support=['reports/RESEARCH_GAP_AND_RELATED_WORK_20261021.md','reports/RESEARCH_GAP_SEARCH_AUDIT_20261021.md','reports/PP1_COMPONENT_COMPLETE_DOSSIER_20261021.md','reports/UI_REFRESH_FINAL_VERIFICATION_20261021.json','reports/CRUD_CONNECTED_VERIFICATION_20261020.md','outputs/PlanoVision_Viva_Dataset_Evidence_20261021/FRESH_VERIFICATION.json']
    for relative in support: shutil.copy2(ROOT/relative,originals/Path(relative).name)
    criteria=Path('C:/Users/User/AppData/Local/Packages/5319275A.WhatsAppDesktop_cv1g1gvanyjgm/LocalState/sessions/286B147D0B3896BD3A9BFF6668C047494C9C27A2/transfers/2026-42/PP1 Assessment Criteria.pdf')
    shutil.copy2(criteria,OUT/'PP1_Assessment_Criteria.pdf')
    shutil.copy2(ROOT/'outputs/PlanoVision_Viva_Jupyter_Evidence_20261021.zip',OUT/'PlanoVision_Viva_Jupyter_Evidence_20261021.zip')
    shutil.copy2(ROOT/'outputs/PlanoVision_Viva_Dataset_Evidence_20261021/notebook_figures/02_confusion_matrices.png',originals/'synthetic_test_confusion_matrices.png')
    proof=json.loads((OUT/'CURRENT_WORKFLOW_PROOF.json').read_text())
    assert proof['status']=='PASS_CURRENT_WORKFLOW_AND_ISOLATED_SQLITE'
    assert proof['preview_cost_increase_lkr']==100000 and proof['margin_change_percentage_points']==-4
    assert all(proof['sqlite'][k]=='PASS' for k in ['create','reopen_and_read','preview_does_not_write','explicit_update','soft_delete'])
    assert proof['sqlite']['personal_database_opened'] is False
    slides=(OUT/'05_FINAL_SIX_SLIDE_TEXT_AND_NOTES.md').read_text(encoding='utf-8')
    assert sum(line.startswith('## Slide ') for line in slides.splitlines())==6
    css='body{font:17px/1.65 Segoe UI,Arial,sans-serif;color:#183943;background:#f3f7f8;max-width:1180px;margin:0 auto;padding:30px}h1{font-size:31px}h2{font-size:25px}h3{font-size:20px}section{background:#fff;border:1px solid #dce7e9;border-radius:12px;padding:28px;margin:24px 0;overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:10px;border-bottom:1px solid #dce7e9;text-align:left;vertical-align:top}th{background:#edf5f4}pre{background:#edf3f5;padding:18px;overflow:auto}a{color:#087284;overflow-wrap:anywhere}nav{display:flex;gap:15px;flex-wrap:wrap}blockquote{border-left:4px solid #218c83;margin-left:0;padding-left:15px}li{margin:7px 0}@media print{body{background:white;padding:0;font-size:12px}nav{display:none}section{padding:12px;break-before:page}table{font-size:10px}}'
    nav='<nav>'+''.join('<a href="#part'+str(i)+'">'+html.escape(p.stem.replace('_',' '))+'</a>' for i,p in enumerate(docs))+'</nav>'
    intro='<h1>PlanoVision: PP1 Assessment Evidence</h1><p>Current requirements, progress, project risks, commercialization and six-slide speaking notes.</p><p><a href="PP1_Assessment_Criteria.pdf">Original assessment criteria</a> | <a href="05_FINAL_SIX_SLIDE_TEXT_AND_NOTES.md">Six-slide text and Sinhala notes</a> | <a href="CURRENT_WORKFLOW_PROOF.json">Fresh workflow proof</a> | <a href="PlanoVision_Viva_Jupyter_Evidence_20261021.zip">Executed Jupyter evidence ZIP</a></p>'
    document='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PlanoVision PP1 Assessment</title><style>'+css+'</style>'+intro+nav+''.join(sections)+'</html>'
    (OUT/'OPEN_PP1_ASSESSMENT.html').write_text(document,encoding='utf-8')
    # Check only actual linked files in the document; external citations and fragments are separate.
    links=[]
    class Parser(HTMLParser):
        def handle_starttag(self,tag,attrs):
            links.extend(v for k,v in attrs if tag=='a' and k=='href')
    Parser().feed(document)
    missing=[link for link in links if not link.startswith(('http:','https:','#','mailto:')) and not (OUT/link).is_file()]
    assert not missing,missing
    verification=dict(status='PASS_ASSESSMENT_PACK',markdown_documents=len(docs),slides=6,allocated_seconds=240,local_links_checked=sum(not x.startswith(('http:','https:','#','mailto:')) for x in links),fresh_workflow_proof=proof['status'],focused_CRUD_tests=11,app_changed=False,models_refitted=False,remaining_external_evidence=['approved original timeline','genuine planner feedback','observed completed-event outcomes','actual laptop rehearsal and backup video'])
    (OUT/'PACK_VERIFICATION.json').write_text(json.dumps(verification,indent=2),encoding='utf-8')
    hashes={p.relative_to(OUT).as_posix():digest(p) for p in OUT.rglob('*') if p.is_file()}
    (OUT/'PACK_MANIFEST.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
    archive=OUT.with_suffix('.zip')
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
        for p in OUT.rglob('*'):
            if p.is_file(): z.write(p,OUT.name+'/'+p.relative_to(OUT).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for relative,expected in hashes.items():
            assert hashlib.sha256(z.read(OUT.name+'/'+relative)).hexdigest()==expected
    archive.with_suffix('.zip.sha256').write_text(digest(archive)+'  '+archive.name+'\n',encoding='ascii')
    print(json.dumps(dict(**verification,archive=str(archive),bytes=archive.stat().st_size,sha256=digest(archive),viewer=str(OUT/'OPEN_PP1_ASSESSMENT.html')),indent=2))


if __name__=='__main__': main()
