"""Artifact integrity is checkable; identity and truth of evidence are not inferred."""
from pathlib import Path
from support import ROOT,filehash,ResearchError

def verify_evidence_artifacts(record):
    source=record['source'];artifacts=record.get('evidence_artifacts',[]);by_id={}
    for artifact in artifacts:
        eid=artifact['evidence_id']
        if eid in by_id:raise ResearchError('DUPLICATE_EVIDENCE_ID')
        p=Path(artifact['path']).resolve()
        if not p.is_relative_to(ROOT.resolve()) or not p.is_file():raise ResearchError('EVIDENCE_FILE_MISSING_OR_OUTSIDE_WORKSPACE',{'evidence_id':eid})
        if p==Path(source['path']).resolve():raise ResearchError('SOURCE_IMAGE_IS_NOT_REVIEW_OR_MEASUREMENT_EVIDENCE')
        if artifact['source_sha256']!=source['sha256']:raise ResearchError('EVIDENCE_SOURCE_BINDING_MISMATCH',{'evidence_id':eid})
        if filehash(p)!=artifact['sha256']:raise ResearchError('EVIDENCE_FILE_HASH_MISMATCH',{'evidence_id':eid})
        by_id[eid]=artifact
    required=[record['review']['evidence_ref']]+[c['evidence_ref'] for c in record['calibration']['controls']]+[o['decision_evidence_ref'] for o in record['objects']]
    if source['domain']=='real_source' and any(ref not in by_id for ref in required):raise ResearchError('EXTERNAL_EVIDENCE_REFERENCE_NOT_RESOLVED',{'missing':sorted(set(required)-set(by_id))})
    return {'files_verified':len(artifacts),'external_identity_authenticated':False,'evidence_truth_independently_verified':False}
