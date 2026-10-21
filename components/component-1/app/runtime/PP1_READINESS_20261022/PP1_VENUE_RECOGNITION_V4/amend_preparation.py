from pathlib import Path
import shutil
H=Path(__file__).resolve().parent
shutil.copyfile(H/'prepare_objects.py',H/'objects/PREPARE_AT_FIRST_ATTEMPT.py')
p=H/'prepare_objects.py';s=p.read_text(encoding='utf-8')
s=s.replace("H/'data'","H/'data_v2'").replace("'objects/","'objects_v2/").replace("H/'objects'","H/'objects_v2'")
s=s.replace("save('ONTOLOGY_FREEZE.json',", "save('ONTOLOGY_AMENDMENT_V2.json',")
s=s.replace("cid,x,y,bw,bh=map(float,line.split());assert cid.is_integer() and 0<=cid<40", "values=list(map(float,line.split()));cid=values[0];assert cid.is_integer() and 0<=cid<40\n    if len(values)==5:x,y,bw,bh=values[1:]\n    else:\n     assert len(values)>=7 and len(values)%2==1\n     pts=np.array(values[1:]).reshape(-1,2);lo=pts.min(0);hi=pts.max(0);x,y=(lo+hi)/2;bw,bh=hi-lo")
p.write_text(s,encoding='utf-8')
