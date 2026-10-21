"""Practical prediction-blind local polygon/box review queue; no fake approvals."""
from common import *
import base64,subprocess
from PIL import Image
from annotation_contract import EVENT,OUTDOOR
tasks=[]
def add(path,kind,rights,note,prefill=None,original=None,annotation_reference=False):
 p=Path(path);im=Image.open(p).convert('RGB');w,h=im.size
 tasks.append({'task_id':'TASK_%03d'%(len(tasks)+1),'source_path':str(p),'source_sha256':sha(p),'width':w,'height':h,'classes':EVENT if kind=='objects' else OUTDOOR,
  'training_rights':rights,'raster_training_allowed':not annotation_reference,'source_kind':kind,'notes':note,'prefill':prefill or [],'original_document':original,
  'image_data_url':'data:image/'+('jpeg' if p.suffix.lower() in ['.jpg','.jpeg'] else 'png')+';base64,'+base64.b64encode(p.read_bytes()).decode()})
qa=read(H/'objects_v2/PREDICTION_BLIND_QA_RECORDS.json');records={r['id']:r for r in read(H/'objects_v2/SOURCE_RECORDS.json')}
for q in qa[:8]:
 r=records[q['id']];pre=[]
 for j,b in enumerate(r['annotations']):
  x,y,a,z=b['bbox_pixels'];pre.append({'id':'PUBLISHED_CHAIR_%03d'%j,'class':'chair','geometry':{'type':'Polygon','coordinates':[[[x,y],[a,y],[a,z],[x,z],[x,y]]]},'status':'PUBLISHED_NOT_HUMAN_REVIEWED'})
 add(r['source'],'objects','DECLARED_RESEARCH_USE','Check EVERY visible chair including dining chairs. Published labels are incomplete. Mark exact rectangular/round tables only if unambiguous; event equipment purpose cannot be inferred from generic tables. Physical stock/proposed design unknown.',pre)
V=H.parent/'PP1_FLOORPLAN_AI_DEVELOPMENT_V3'
add(V/'acquired/NPS_PINES_SITE_PLAN.jpg','outdoor','DECLARED_RESEARCH_USE','Public-domain NPS orientation map. Distinguish legend boxes and site/legal/event-usable boundary. Mark UNKNOWN in notes if no supported boundary; do not enclose the page. Do not infer roof/restrictions/access from appearance alone.')
for r in read(H/'outdoor/SOURCE_REGISTRY.json')[:4]:
 add(r['layout'],'outdoor','DECLARED_RESEARCH_USE','SCUT semantic TARGET, not raw drawing. Entrance yellow per publisher Fig2. Site-range boundary annotation is separate reference; no legal/usable equivalence. This is annotation QA only; it cannot qualify raw-site-plan training.',annotation_reference=True)
pdf=ROOT/'03_REAL_VENUE_REFERENCES/00_INBOX/PDF_ORIGINALS/feb-2025-floor-plan.pdf';out=H/'annotations/pdf_decode'
if not out.exists():
 argv=['C:/Users/User/AppData/Local/Programs/Python/Python312/python.exe','-B',str(H/'decode_document.py'),str(pdf),str(out)]
 p=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True)
 save('annotations/PDF_DECODE_COMMAND.json',{'argv':argv,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
if (out/'DECODE.json').exists():
 for page in read(out/'DECODE.json')['pages']:
  add(page['image'],'objects','UNVERIFIED_REVIEW_ONLY','User-supplied plan: review drawing symbols, legends and proposed/existing distinction. Training blocked until original drawing permission supplied.',original={'path':str(pdf),'sha256':sha(pdf),'page':page['page'],'decode':page})
save('annotations/TASKS_V2.json',[{k:v for k,v in t.items() if k!='image_data_url'} for t in tasks])
html='''<!doctype html><meta charset="utf-8"><title>Source-bound venue annotation review</title>
<style>body{font:15px system-ui;margin:24px;background:#f5f5f3;color:#222}header{max-width:1100px}button,select,input{padding:8px;margin:4px}#canvas{background:white;border:1px solid #999;max-width:100%;cursor:crosshair}aside{max-width:1100px;line-height:1.5}#meta{white-space:pre-wrap;font:12px monospace;overflow-wrap:anywhere}#warn{color:#8a3300}button{cursor:pointer}#items{max-height:150px;overflow:auto}</style>
<header><h1>Venue drawing annotation review</h1><p>Annotation input only. This tool does not approve a Spatial Twin, certify physical stock, infer scale, or authenticate a planner. No model predictions are used to prefill this queue.</p></header>
<select id="task"></select><button id="prev">Previous</button><button id="next">Next</button><aside id="note"></aside><pre id="meta"></pre>
<select id="klass"></select><select id="mode"><option value="polygon">Polygon: click vertices, finish</option><option value="box">Box: click two opposite corners</option></select><button id="finish">Finish polygon</button><button id="undo">Undo point</button><button id="clear">Clear current points</button>
<p id="warn">Published prefill is unreviewed. Check completeness and every geometry. Unknown semantics must remain UNKNOWN; they are never negative training examples.</p><div id="classStates"></div>
<canvas id="canvas"></canvas><div id="items"></div>
<p>Reviewer name/ID <input id="reviewer" placeholder="Required, never auto-filled"><br><textarea id="notes" rows="4" cols="100" placeholder="Required: unknowns, exclusions, source evidence, target completeness and reasons"></textarea><br>
<label><input type="checkbox" id="attest">I personally reviewed all listed target classes and annotations on this source, including their absence where applicable.</label></p>
<button id="export">Export explicit annotation JSON</button><span id="status"></span>
<script>const TASKS=__TASKS__;let current=0,points=[],anns=[],image=new Image(),drafts={};const $=x=>document.getElementById(x),ctx=$('canvas').getContext('2d');
TASKS.forEach((t,i)=>{let o=document.createElement('option');o.value=i;o.textContent=t.task_id+' '+t.source_kind+' '+t.source_path.split(/[\\\\/]/).pop();$('task').append(o)});
function states(){let s={};document.querySelectorAll('[data-class-state]').forEach(e=>s[e.dataset.classState]=e.value);return s}
function remember(){drafts[current]={anns:JSON.parse(JSON.stringify(anns)),notes:$('notes').value,reviewer:$('reviewer').value,attest:$('attest').checked,states:states()}}
function load(i){current=Math.max(0,Math.min(TASKS.length-1,i));let t=TASKS[current];$('task').value=current;points=[];let d=drafts[current];anns=d?d.anns:JSON.parse(JSON.stringify(t.prefill));$('notes').value=d?d.notes:'';$('reviewer').value=d?d.reviewer:'';$('attest').checked=d?d.attest:false;$('klass').innerHTML='';t.classes.forEach(k=>{let o=document.createElement('option');o.textContent=k;$('klass').append(o)});$('note').textContent=t.notes;$('meta').textContent=t.source_path+'\\nSHA256 '+t.source_sha256+' | '+t.width+' x '+t.height+' pixels | rights '+t.training_rights;image.onload=()=>{let s=Math.min(1,1100/t.width,850/t.height);$('canvas').width=Math.round(t.width*s);$('canvas').height=Math.round(t.height*s);draw()};image.src=t.image_data_url;render()}
function draw(){let t=TASKS[current],sx=$('canvas').width/t.width,sy=$('canvas').height/t.height;ctx.clearRect(0,0,$('canvas').width,$('canvas').height);ctx.drawImage(image,0,0,$('canvas').width,$('canvas').height);ctx.lineWidth=2;anns.forEach(a=>{ctx.strokeStyle='#c0392b';ctx.beginPath();a.geometry.coordinates[0].forEach((p,i)=>i?ctx.lineTo(p[0]*sx,p[1]*sy):ctx.moveTo(p[0]*sx,p[1]*sy));ctx.closePath();ctx.stroke();let p=a.geometry.coordinates[0][0];ctx.fillStyle='#a02520';ctx.fillText(a.class,p[0]*sx,p[1]*sy)});ctx.strokeStyle='#005fa8';ctx.beginPath();points.forEach((p,i)=>{if(i)ctx.lineTo(p[0]*sx,p[1]*sy);else ctx.moveTo(p[0]*sx,p[1]*sy)});ctx.stroke();points.forEach(p=>{ctx.fillStyle='#005fa8';ctx.fillRect(p[0]*sx-3,p[1]*sy-3,6,6)})}
function render(){$('items').replaceChildren();anns.forEach((a,i)=>{let b=document.createElement('button');b.textContent='Delete '+a.id+' '+a.class;b.onclick=()=>{anns.splice(i,1);$('attest').checked=false;render();draw()};$('items').append(b)})}
function finish(){if(points.length<3){$('status').textContent='Need at least three points';return}anns.push({id:'LOCAL_'+Date.now()+'_'+anns.length,class:$('klass').value,geometry:{type:'Polygon',coordinates:[[...points,points[0]]]},origin:'HUMAN_DRAWN_OR_HUMAN_REVIEWED_PUBLISHED_LABEL'});points=[];$('attest').checked=false;render();draw()}
$('canvas').onclick=e=>{let r=$('canvas').getBoundingClientRect(),t=TASKS[current];points.push([Math.max(0,Math.min(t.width,(e.clientX-r.left)*t.width/r.width)),Math.max(0,Math.min(t.height,(e.clientY-r.top)*t.height/r.height))]);if($('mode').value==='box'&&points.length===2){let a=points[0],b=points[1],x=Math.min(a[0],b[0]),y=Math.min(a[1],b[1]),z=Math.max(a[0],b[0]),w=Math.max(a[1],b[1]);points=[[x,y],[z,y],[z,w],[x,w]];finish()}draw()};$('finish').onclick=finish;$('undo').onclick=()=>{points.pop();draw()};$('clear').onclick=()=>{points=[];draw()};$('task').onchange=()=>{let n=+$('task').value;remember();load(n)};$('next').onclick=()=>{remember();load(current+1)};$('prev').onclick=()=>{remember();load(current-1)};
$('export').onclick=()=>{let t=TASKS[current];if(!$('attest').checked||!$('reviewer').value.trim()||!$('notes').value.trim()||points.length){$('status').textContent='Finish geometry and supply explicit review, identity and notes.';return}let result={schema:'SOURCE_BOUND_HUMAN_ANNOTATION_V1',task_id:t.task_id,source_sha256:t.source_sha256,source_width:t.width,source_height:t.height,reviewer:$('reviewer').value.trim(),attested_human_review:true,notes:$('notes').value,reviewed_classes:t.classes,inventory_authority:'UNKNOWN_NOT_PHYSICAL_STOCK',annotations:anns.map(a=>({...a,origin:'HUMAN_DRAWN_OR_HUMAN_REVIEWED_PUBLISHED_LABEL'})),planner_approved:false,optimization_ready:false};let blob=new Blob([JSON.stringify(result,null,2)],{type:'application/json'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=t.task_id+'_human_annotation.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);$('status').textContent='Exported local unauthenticated annotation. Validate in Python; no metric or planner approval issued.'};load(0);</script>'''
html=html.replace("image.src=t.image_data_url;render()", "$('classStates').replaceChildren();t.classes.forEach(k=>{let label=document.createElement('label');label.textContent=k+' ';let sel=document.createElement('select');sel.dataset.classState=k;['UNKNOWN','PRESENT_ANNOTATED','ABSENT_CONFIRMED','NOT_APPLICABLE'].forEach(v=>{let o=document.createElement('option');o.value=v;o.textContent=v;sel.append(o)});if(d&&d.states)sel.value=d.states[k]||'UNKNOWN';sel.onchange=()=>{$('attest').checked=false};label.append(sel);$('classStates').append(label)});image.src=t.image_data_url;render()")
html=html.replace('reviewed_classes:t.classes,inventory_authority:', 'reviewed_classes:t.classes,class_review_status:states(),inventory_authority:')
(H/'annotations/REVIEW_V2.html').write_text(html.replace('__TASKS__',json.dumps(tasks).replace('</','<\\/')),encoding='utf-8')
print(len(tasks),'source-bound review tasks; no reviews fabricated')
