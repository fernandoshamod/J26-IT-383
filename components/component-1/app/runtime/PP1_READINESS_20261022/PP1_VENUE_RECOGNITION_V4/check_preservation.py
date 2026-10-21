"""Reuse authoritative manifests, no broad filesystem audit or source mutation."""
from common import *
V=H.parent/'PP1_FLOORPLAN_AI_DEVELOPMENT_V3';B=H.parent/'PP1_EXECUTABLE_V1';F=H.parent/'PP1_FRONTEND_V1'
sets={
 'original_research_and_data':{ROOT/p:s for p,s in read(H.parent/'PP1_MODEL_DEVELOPMENT_V2/PROTECTED_SOURCE_HASHES.json').items()},
 'native_cubicasa':{ROOT/p:s for p,s in read(V/'PROTECTED_NATIVE_HASHES.json').items()},
 'V3_delivery':{V/p:s for p,s in read(V/'DELIVERY_SHA256.json').items()},
 'backend_freeze':{ROOT/p:s for p,s in read(B/'BACKEND_FREEZE_V1.json')['runtime_sha256'].items()},
}
frontend=read(F/'FRONTEND_ARTIFACT_SHA256_V1.json')
# Inspect format explicitly rather than silently claiming unverifiable coverage.
if isinstance(frontend,dict) and all(isinstance(v,str) and len(v)==64 for v in frontend.values()):
 sets['frontend_artifacts']={(ROOT/p if (ROOT/p).is_file() else F/p):s for p,s in frontend.items()}
records=read(H/'objects_v2/SOURCE_RECORDS.json');sets['2DPlan_inputs']={Path(r[k]):r[k+'_sha256'] for r in records for k in ['source','annotation']}
outdoor=read(H/'outdoor/SOURCE_REGISTRY.json');sets['SCUT_inputs']={Path(r[k]):r[v] for r in outdoor for k,v in [('layout','layout_sha256'),('boundary_annotation','boundary_sha256')]}
result={};changed=[]
for name,entries in sets.items():
 bad=[str(p) for p,digest in entries.items() if not p.is_file() or sha(p)!=digest]
 result[name]={'entries':len(entries),'matches':len(entries)-len(bad),'changed_or_missing':bad};changed+=bad
 print(name,len(entries),'changed',len(bad),flush=True)
save('PRESERVATION.json',{'status':'PASS' if not changed else 'FAIL','manifests':result,'claim_limit':'Hash coverage is limited to these authoritative prior manifests and newly consumed inputs, not all project bytes. No previous model is replaced.','frontend_manifest_format':type(frontend).__name__})
assert not changed
