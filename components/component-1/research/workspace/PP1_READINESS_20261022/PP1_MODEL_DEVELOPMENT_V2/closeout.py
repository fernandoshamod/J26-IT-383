"""Summarize actual results and verify preservation; no model execution."""
import ast,csv,collections,datetime,importlib.metadata,shutil
from common import *
def write(name,s):
 with (H/name).open("x",encoding="utf-8") as f:f.write(s)
trained=read(H/"yolo/TRAINING_RESULT.json");compare=read(H/"yolo/COMPARISON.json")
selection=read(H/"yolo/MODEL_SELECTION.json")
groups=read(H/"unet/GROUP_REPORT.json");export=read(H/"yolo/DATASET_EXPORT.json")
independent=read(H/"yolo/INDEPENDENT_DETECTION_VERIFICATION.json")
adapter=read(H/"adapter_outputs/TEST_RESULTS.json")
hybrid=read(H/"adapter_outputs/HYBRID_CROP_TEST.json")
assert independent["status"]==adapter["status"]==hybrid["status"]=="PASS"
protected=read(H/"PROTECTED_SOURCE_HASHES.json")
changed=[p for p,h in protected.items() if sha(ROOT/p)!=h]
freeze=read(ROOT/"PP1_READINESS_20261022/PP1_EXECUTABLE_V1/BACKEND_FREEZE_V1.json")
drift=[p for p,h in freeze["runtime_sha256"].items() if sha(ROOT/p)!=h]
save("PRESERVATION_RESULT.json",{"tracked_existing_files":len(protected),"changed_files":changed,
 "frozen_backend_manifest_entries":len(freeze["runtime_sha256"]),"frozen_backend_manifest_drift":drift,
 "status":"PASS" if not changed and not drift else "FAIL","scope":"Directly used original datasets/checkpoints and preserved backend runtime freeze. No whole-project bytewise baseline claimed."})
assert not changed and not drift
libs={n:importlib.metadata.version(n) for n in ["torch","torchvision","ultralytics","segmentation-models-pytorch","numpy","Pillow","opencv-python","shapely","pydantic"]}
save("ENVIRONMENT.json",{"python":sys.version,"executable":sys.executable,"packages":libs,"disk_bytes":dict(zip(["total","used","free"],shutil.disk_usage(ROOT))),
 "resource_evidence":"Completed training 12 epochs, batch4/960/float32; GPU memory about 2.3GB per log. Resource capacity was established by preparation copy success and actual run; explicit disk measurement recorded at closeout, not a fabricated preflight measurement.",
 "environment_modified":False,"new_packages_installed":False,"new_data_downloaded":False,"network_scope":"Offline flags and Python audit denial, not OS-level isolation. Successful training/evaluation logged and blocked localhost socket binds and github.com DNS probes. They must not be reported as zero network attempts."})
datasets=[
 {"name":"CubiCasa5K","source":"https://github.com/CubiCasa/CubiCasa5k","license_source":"https://github.com/CubiCasa/CubiCasa5k/blob/master/LICENSE","license":"CC BY-NC 4.0; noncommercial academic use with attribution","local":"01_DATASET_DOWNLOADS/CubiCasa5K","used_for":"4990 source/reference hashes, conservative source grouping, review queue and original frozen inference only","new_training":False,"status":"HOLD_FOR_TRAINING","reason":"Semantic review and full family ancestry unresolved; original raster registration not qualified. Original zero remains unassigned; no background label invented.","download_url_verified_in_this_mission":False},
 {"name":"CVC-FP","source":"https://portalrecerca.uab.cat/en/publications/cvc-fp-and-sgt-a-new-database-for-structural-floor-plan-analysis-/","license":"Primary publication supports research-community benchmark use; no blanket commercial/redistribution grant inferred","local":"01_DATASET_DOWNLOADS/06_CVC_FP_OFFICIAL","used_for":"Previously saved frozen ten-sheet external result and its hash only","new_training":False,"status":"TEN_OBSERVED_DIAGNOSTIC_RECORDS;112_HELD","reason":"No newly qualified human-reviewed unused subset; native door/window semantics differ; do not tune or call ten sheets untouched.","download_url_verified_in_this_mission":False},
 {"name":"Existing C3.17 procedural event diagrams","source":"Local C3.17/C3.8 procedural generator lineage; existing DATASET_LINEAGE_REVIEW.md and source-group manifest","license":"Project procedural research assets; no external-photo license inferred","local":"02_GENERATED_RESEARCH_DATA/STAGE_C_OBJECTS/C3_17_V3_CLEAN_YOLO_CANDIDATE_157","used_for":"New isolated copy, train-only rare-scene resampling and GPU YOLO fine-tuning, validation and observed synthetic diagnostic test","new_training":True,"status":"ELIGIBLE_CONTROLLED_ONLY","counts":{"train_original":107,"train_with_repetitions":185,"val":20,"test":30},"original_boxes":6529,"classes":12,"groups":11,"reason":"Procedural annotations, not human-labelled venue evidence. Buffet has zero val/test support. No indoor source group in val or test."},
 {"name":"FloorPlanCAD","source":"https://floorplancad.github.io/","download_landing":"https://floorplancad.github.io/","license":"Publisher annotations CC BY-NC 4.0; drawing copyright not owned by authors; explicit use responsibility terms","local":"01_DATASET_DOWNLOADS/FloorPlanCAD","status":"HOLD","new_training":False,"reason":"Vector primitive ontology and underlying drawing rights require record-level qualification; not automatically twelve event classes. No package downloaded or converted."},
 {"name":"ResPlan","source":"https://github.com/m-agour/ResPlan","license_source":"https://github.com/m-agour/ResPlan/blob/main/LICENSE","download_landing":"https://github.com/m-agour/ResPlan","license":"CC BY4.0 over released derived geometry; code MIT; does not provide rights to absent original listings/images","local":"01_DATASET_DOWNLOADS/08_ResPlan_VECTOR_GRAPH_OFFICIAL","status":"HOLD","new_training":False,"reason":"CV-derived geometry, not an independently human-labelled original-raster benchmark; no source-image pairing qualification for this mission."},
 {"name":"Local 2DPlan Roboflow export","source":"Local README.roboflow.txt; original publisher/license chain not established in this mission","local":"01_DATASET_DOWNLOADS/02_2DPlan_Objects","status":"REJECT_FOR_DIRECT_12_CLASS_TRAINING","new_training":False,"reason":"door/window/sofa/sliding_door ontology mismatch; three augmentation variants and unresolved rights/ancestry/label adjudication."},
 {"name":"SCUT AutoALP/outdoor source registry","local":"01_DATASET_DOWNLOADS/09_SCUT_AUTOALP_OFFICIAL","status":"HOLD","new_training":False,"reason":"No newly qualified licensed outdoor boundary/entrance/obstacle ontology and independent annotations; no forced indoor label mapping."}]
save("DATASET_SOURCE_AND_LICENSE_MANIFEST.json",datasets)
best=compare["diagnostic_test"]["candidate"]["metrics"];old=compare["diagnostic_test"]["incumbent"]["metrics"]
ut=read(ROOT/"PP1_READINESS_20261022/PP1_UNET_CVC_EXTERNAL_EVALUATION_V1/CONFUSION_MATRICES.json")
checks={"checkpoint_production_yolo":"PASS","checkpoint_production_new_unet":"NOT_EVALUATED","data_source_split_integrity":"PARTIAL","segmentation_class_quality_external":"FAIL","detection_class_quality":"PARTIAL","segmentation_cross_domain":"FAIL","detection_real_domain":"NOT_EVALUATED","indoor_structural_applicability":"PARTIAL","indoor_heldout_object_accuracy":"NOT_EVALUATED","outdoor_boundary_understanding":"NOT_EVALUATED","hybrid_semantic_understanding":"NOT_EVALUATED","controlled_routing":"PASS","existing_real_object_recognition":"NOT_EVALUATED","image_space_geometry_replay":"PASS","physical_geometry_reliability":"NOT_EVALUATED","metric_twin_handoff":"PARTIAL"}
save("MODEL_ACCEPTANCE.json",{"status":"PARTIAL;HUMAN_DATA_GATE_REQUIRED","acceptance_dimensions":checks,"new_unet_trained":False,"new_yolo_trained":True,"new_yolo":trained,
 "unet_checkpoint":{"path":"02_GENERATED_RESEARCH_DATA/STAGE_B_PP1_BASELINE/best_unet_resnet18.pt","sha256":"480f15179818f63b1bdcfc5f72eef62cfdb0db092f27459f274fc72268888a5a"},"selected_yolo":selection["selected_checkpoint"],"selected_yolo_sha256":selection["selected_sha256"],
 "whole_real_venue_system_complete":False,"frozen_sources_preserved":True,"phase_status":{"A":"PARTIAL;UNET/REAL_DATA_HUMAN_GATE_BLOCKED","B":"PASS_EXISTING_YOLO_REPRODUCED;UNET_PRIOR_EVIDENCE_REUSED","C":"PARTIAL_YOLO_RARE_SCENE_RESAMPLING_AND_NEW_ROUTING","D":"YOLO_COMPLETED;UNET_NOT_COMPLETED","E":"PARTIAL_CONTROLLED_DIAGNOSTICS;NEW_EXTERNAL_NOT_COMPLETED","F":"YOLO_VALIDATION_SELECTION_COMPLETED;NEW_UNET_NOT_COMPLETED","G":"CANDIDATE_ONLY_ADAPTER;NO_APPROVED_REAL_TWIN","H":"LOCAL_CONTROLLED_MODEL_DEMO;FULL_REAL_VENUE_NOT_COMPLETED"}})
write("README.md",f"""# Two-model development V2

**Actual implementation and GPU training completed for a bounded YOLO correction. Overall mission remains PARTIAL, blocked on genuine U-Net data review and qualified real-domain annotations.**

New workspace only; frozen backend/frontend/checkpoints/datasets remain unchanged. No package installation, upgrades or new dataset downloads. New model does not replace the frozen backend's checkpoint.

## Measured outcome

- New YOLO: 12 completed epochs of local fine-tuning, train-only rare-scene resampling, 185 training presentations per epoch from 107 unique training scenes. Validation20; previously observed test30. All twelve class names retained.
- Validation mAP50-95: incumbent {selection['validation_results']['incumbent']['metrics']['metrics/mAP50-95(B)']:.8f}; candidate {selection['validation_results']['candidate']['metrics']['metrics/mAP50-95(B)']:.8f}. Candidate selected before this mission's test evaluation.
- Diagnostic synthetic test mAP50 **{old['metrics/mAP50(B)']:.8f} -> {best['metrics/mAP50(B)']:.8f}**; mAP50-95 **{old['metrics/mAP50-95(B)']:.8f} -> {best['metrics/mAP50-95(B)']:.8f}**. Precision falls; recall rises. This is extra-training/resampling evidence, not a controlled causal or new-architecture superiority claim.
- Temporary partition test AP50=0.065 (5 GT), still poor. Buffet has zero val/test GT: NOT_VALIDATED. Reported macro AP denominator11, not12.
- New U-Net training: **NOT_COMPLETED**. 4990 records conservatively grouped into {groups['observed_groups']} observed groups, partitions {groups['partition_counts']}. Unknown ancestry and missing human semantic review prevent certification. Original raster registration remains unqualified; unknown zero is not background.
- Frozen U-Net external native-CVC mIoU remains {ut['pooled_metrics']['miou']:.10f}, unchanged. No new segmentation improvement is claimed.
- New local adapter runs actual selected models, returns source-bound pixel candidates and keeps metric Twin readiness false. Real controlled indoor functional test uses a TRAINING scene, never claimed held-out accuracy. Outdoor bypasses indoor segmentation. Hybrid crop test covers routing/coordinates only.

## Start here

Read MODEL_ACCEPTANCE.md, TRAINING_AND_EVALUATION.md, DATASET_READINESS.md and RUNBOOK.md. Raw reports/checkpoints are under yolo/; U-Net candidate groups and human-review queue under unet/; actual candidate artifacts under adapter_outputs/. Failures remain under failures/.

Independent detection replay: {independent['status']}, {len(independent['checks'])} assertions within one replay. Adapter: {len(adapter['checks'])} assertions; hybrid coordinate test: {len(hybrid['checks'])}. These do not establish real-domain validity or independent expert ground truth.

**Single next action:** resolve the source-bound human semantic/ancestry/registration review queue before authorizing a U-Net training dataset. This task stops at that essential human gate, as requested; it does not mark both models complete.
""")
write("TRAINING_AND_EVALUATION.md",f"""# Actual training and evaluation

YOLO architecture remains YOLOv8n/12 classes. Original initialization checkpoint SHA613428387a2d2d01680f264b075cc8437cda4da86e7d58f8d4d139555fa9e3cd. Corrected run verified exact equality of all355 state tensors before first epoch. No pretrained network download.

Explicit local initialization, AdamW lr0=0.0001, cosine schedule lrf0.1, seed261018, 12epochs, batch4, imgsz960, workers0, float32/AMPfalse, mosaic/mixup0, translate0.05, scale0.15, fliplr0.5, brightness0.1, patience12. Full actual settings including framework defaults: yolo/rare_resample_finetune/args.yaml; frozen requested config: yolo/TRAINING_PROTOCOL.json.

Training completed in {trained['seconds']:.3f} seconds. History: yolo/rare_resample_finetune/results.csv; best/last/periodic checkpoints under weights/. New best checkpoint SHA **{trained['sha256']}**. Historical incumbent had25epochs and this run adds12 with resampling, so this is not compute-matched or isolated-effect experimentation. No extra variant was tried after the diagnostic test results.

## Matched diagnostic comparison

Both checkpoints use the same unmodified validation/test images and labels, image960, batch4, FP32, NMS0.7/conf0.001/maxdet300 and installed Ultralytics version. Candidate selected by validation mAP50-95 before test. The test is already historically observed; it is not a new untouched external generalization test.

| Metric | Incumbent | Candidate |
|---|---:|---:|
| Synthetic test mAP50 | {old['metrics/mAP50(B)']:.10f} | {best['metrics/mAP50(B)']:.10f} |
| Synthetic test mAP50-95 | {old['metrics/mAP50-95(B)']:.10f} | {best['metrics/mAP50-95(B)']:.10f} |
| Library best-F1 precision | {old['metrics/precision(B)']:.10f} | {best['metrics/precision(B)']:.10f} |
| Library best-F1 recall | {old['metrics/recall(B)']:.10f} | {best['metrics/recall(B)']:.10f} |

Full class AP/P/R arrays: yolo/evaluations/*_test.json. Class indices are explicit; class1buffet omitted from macro AP because support0, not assigned an invented score.

## Independent saved-box replay

Raw per-image predictions at conf0.001, original-image coordinates and original label hashes are under yolo/predictions/*_RAW.json. Independent scalar one-to-one IoU matching verifies fixed conf0.25/IoU0.5 TP/FP/FN and source GT supports. Independent 101-point AP uses saved per-image predictions, confidence ordering, precision envelope and IoU0.50:0.05:0.95, with null AP for unsupported classes. See yolo/INDEPENDENT_DETECTION_VERIFICATION.json and INDEPENDENT_CLASS_METRICS.csv.

Independent AP50 incumbent {independent['results']['incumbent']['map50']:.10f}, candidate {independent['results']['candidate']['map50']:.10f}; AP50-95 incumbent {independent['results']['incumbent']['map50_95']:.10f}, candidate {independent['results']['candidate']['map50_95']:.10f}. These are not exact replays of library rectangular-batch val: per-image padding and independent matching differ. Neither is a real-domain test. Fixed-threshold precision is separate from the library best-F1 metric. Unsupported class and empty-prediction conventions must not be hidden.

Candidate temporary partition fixed-threshold outcome: 1TP,2FP,4FN on5GT. That remains a material failure. Extra copies did not create independent scenes, annotations or buffet evaluation support.

## Preserved failures and correction

1. ATTEMPT_001: obsolete settings key neptune raised KeyError before training. Fixed by filtering installed setting keys.
2. ATTEMPT_002: Windows sandbox denied multiprocessing named pipe; no epoch completed. Localhost probes were blocked and recorded. Successful run used approved execution outside sandbox, preserving software network/write guards.
3. ATTEMPT_003: pretrained=False discarded checkpoint weights in this installed trainer. Stopped after3recorded epochs; never used for test/selection. Interrupted guard summary was not flushed. Explicit local checkpoint plus355-tensor equality check fixed initialization.
4. ADAPTER_FIXTURE_001: a sorted OUTDOOR source was incorrectly declared indoor in the first test. Its initial PASS was withdrawn as indoor evidence. Preserved outputs show why source-aware tests matter. Corrected test uses actual indoor training fixture and adds source-group route conflict rejection.

Runtime network instrumentation recorded blocked localhost bind and github.com DNS probes in successful training/evaluation. No successful hosted inference/optimization or data download is evidenced. Do not say zero attempted network operations. Python audit instrumentation is not full OS isolation. No security protection was disabled.
""")
write("DATASET_READINESS.md",f"""# Dataset readiness and human gate

Machine source/license manifest: DATASET_SOURCE_AND_LICENSE_MANIFEST.json. Official rights checked against [CubiCasa licence](https://github.com/CubiCasa/CubiCasa5k/blob/master/LICENSE), [CVC publication](https://portalrecerca.uab.cat/en/publications/cvc-fp-and-sgt-a-new-database-for-structural-floor-plan-analysis-/), [ResPlan licence](https://github.com/m-agour/ResPlan/blob/main/LICENSE), and [FloorPlanCAD terms](https://floorplancad.github.io/). No new dataset was obtained. Download links for held resources were not tested as binary downloads; source landing pages are not mislabeled verified package URLs.

## U-Net

Current4990 exact consumed records, existing images/masks/sourceSVG hashes recorded. Union-find groups exact source/image/mask equality, conservative63-bit DCT Hamming<=6 candidates and the two prior visually identified near pairs. {len(groups['near_screen_edges'])} perceptual edges; {groups['observed_groups']} observed groups; partition sizes {groups['partition_counts']}. Conservative grouping may merge unrelated drawings. Exact known groups are kept together, but unknown/shared physical ancestry remains unresolved; do not label the candidate split certified leakage-free.

Groups crossing original partitions go wholly to old test first, otherwise validation; new training records never share an observed group with proposed val/diagnostic_test. Original incumbent trained on some moved records, so these regrouped partitions cannot be called independent tests of that checkpoint.

No sources/masks moved. CANDIDATE_SPLITS.json is reference-only, not a qualified raster training export. Existing 4990 source renders remain review-only at the authoritative semantic registry. HUMAN_REVIEW_QUEUE.json contains24deterministically selected source-bound cases (8per proposed partition), with six exact source-only preview examples. Previews show original rasters separately and explicitly UNREGISTERED, not dimension-based approval.

Required decisions: validate native class semantics/coverage, verify annotation/raster registration before raster use, adjudicate possible source families and retain documented group decisions. Sample sign-off alone does not magically certify all4990. No approval/measurement/annotation was fabricated. Original unassigned0 remainsignore255; background and outdoor boundary labels cannot be invented. No revised U-Net was trained; aspect-preserving/tiling/background/loss experiments remain NOT_COMPLETED behind data readiness.

The ten CVC sheets have already been observed; their results were reused unchanged, not re-inferred/tuned. The other112remain held pending annotation qualification. Different dataset names do not prove ancestry independence.

## YOLO

107unique training/20val/30test scenes,6529original boxes,11procedural groups with no cross-split group or image-hash overlap. Export has185train images because buffet/temporary-partition scenes are repeated3times in TRAIN ONLY. Copies/labels and all identities recorded in yolo/DATASET_EXPORT.json; no new human annotation.

Crucial applicability limit: the sole INDOOR_BANQUET_RECTANGLE group belongs to train. Validation/test groups are outdoor/hybrid procedural templates. Therefore no held-out indoor detector accuracy is established even though indoor functional inference executes. Labels are diagram objects, not proof of observed physical venue stock. Buffet train16instances, val0/test0. Other exact class supports are exported; no 12-class validation claim.

Real twelve-class object photos, outdoor boundary annotations and mixed-region semantics are NOT_READY. Local Roboflow data have incompatible classes and unresolved rights/augmentation families. ResPlan derived geometry and FloorPlanCAD vector primitives are useful candidates, not an automatically compatible gold raster/furniture set.
""")
write("MODEL_ACCEPTANCE.md","""# Acceptance and stop condition

Machine verdict: MODEL_ACCEPTANCE.json. The whole real-venue detection system is **NOT COMPLETE**.

| Dimension | Verdict | Evidence / limit |
|---|---|---|
| Actual new YOLO training/checkpoint | PASS | 12epochs, localGPU, verified initialization, real weights/history |
| New U-Net training | NOT_EVALUATED | NOT_COMPLETED behind semantic/ancestry/registration gate |
| Source/split integrity | PARTIAL | Observed-group separation; unknown ancestry and real-domain data remain unresolved |
| Existing U-Net external quality | FAIL | Preserved native-CVC pooledmIoU0.2817846732; door/window/low-contrast wall failures |
| YOLO per-class quality | PARTIAL | Synthetic comparison improves aggregate; partition weak, buffet unvalidated |
| Independent real-domain detection | NOT_EVALUATED | No new qualified real twelve-class test |
| Indoor applicability | PARTIAL | Structural render scope only; no held-out indoor detection group |
| Outdoor boundary understanding | NOT_EVALUATED | Pure outdoor bypasses indoor model and remains pending |
| Hybrid semantic understanding | NOT_EVALUATED | Explicit crop coordinate test only; no transition/topology inference |
| Image-space extraction | PASS | Saved actual outputs, independent raster flood-fill versus polygon area |
| Physical geometry reliability | NOT_EVALUATED | Pixel overlap is not measured geometry or safe usable area |
| Metric Twin handoff | PARTIAL | Existing candidate schema, source identities and missing-review rejection; no genuine approval/scale |

Both models remain incomplete for the full declared indoor/outdoor/hybrid research scope. The selected YOLO is a bounded controlled-diagram candidate, not a production detector. U-Net remains frozen and acceptable only for a truthful limited demonstration. Training completion is not model/domain acceptance.

All eight logics and A-F scope remain unchanged. HistoricalS-GCN, weather/safety, event compiler, NSGA-II, EAG-APR and XAI were not retrained/redesigned. No frontend or frozen backend routes were changed. New adapter outputs are provisional and require the same genuine review/evidence/calibration gates.

Single critical next task: complete the source-bound semantic/ancestry/raster-registration human review for a bounded U-Net candidate subset and independent evaluation policy. Do not authorize a large run by accepting a fabricated review record or by using already observed CVC examples as an untouched final test.
""")
write("ADAPTER_AND_APPLICABILITY.md","""# Local inference adapter2.0.0

adapter.py / infer.py expose local Python functions and a CLI, not a new backend HTTP route. Request JSON schema is adapter_outputs/REQUEST_SCHEMA.json. Existing IMAGE_SPACE_TWIN_CANDIDATE_V2 source/bundle fields are preserved; no metric scale or review approval is inferred. The frozen backend still uses its original checkpoint; only this isolated adapter selects the new controlled candidate.

Indoor floorplan raster: actual original U-Net and validation-selected YOLO; argmax masks and threshold0.7 structural pixel-cell candidates, detectionconf0.25/NMS0.7/maxdet300. Thresholds were inherited, not tuned here. Softmax/scores are uncalibrated. No invented background class or physical footprint conversion.

Pure outdoor/site-plan input: zero model calls, pending planner boundary/entrance/obstacle evidence. Hybrid: requires explicit indoor pixel rectangles; coordinate-tested crop inference maps candidates into source coordinates, but cannot identify indoor zones or transitions. The supplemental crop is an arbitrary LAB window, explicitly not a qualified indoor-region annotation.

PDF/CAD originals and venue photos: unsupported. A separately qualified raster conversion may use the raster contract, but no CAD/PDF parser or photo-domain model was implemented. Caller-declared real-source venue type remains an assertion requiring review. Known controlled files are checked against hashed generator source groups and reject conflicting indoor/outdoor/hybrid declarations.

Output carries source path/hash/dimensions/domain, checkpoint identities, pixel-coordinate mask/box/polygon geometry, class/identity/score or explicit confidence limitation, uncertain semantics, planner_confirmed=false, relocation_allowed=false, boundary=null, metres_per_pixel=null, optimization_ready=false. Existing structural geometry extraction pure function is loaded by AST from its unchanged authoritative source; its hash is returned. No optimizer, calibration or registration call is made.

Tests: actual controlled indoor source is a TRAIN scene (functional only); independent saved-grid flood fill verifies polygon area; pending actual frozen TwinReview schema/gate rejects empty measurements/review. Hybrid test independently checks shifted geometry bounds. This is not proof of successful positive external Twin registration or approved metric handoff. Original frozen approval/evidence contracts remain authoritative.
""")
write("TECHNICAL_VIVA.md","""# Technical viva

Why segmentation and detection? Structural segmentation assigns room/wall/door/window labels per pixel; YOLO predicts boxes for twelve event-diagram object classes. They are different tasks; a design requirement for a new stage is not an observed stage.

U-Net: ResNet18 encoder and U-Net decoder, four logits per512-squarepixel. RGB/255/ImageNetnormalization, bilinear image resize, nearest GT, raw1..4->model0..3, zeroignore255. Frozen historical training used crossentropy/AdamW and validation-best checkpoint. Four classes do not include background, so outside room predictions are not usable floor area. NativeCVC door swing sectors differ from training narrow openings. External score0.28178 is real and retained; high historicalSVG score0.90277 does not establish real transfer.

Why not immediately retrain U-Net? Existing raster registration, semantic review and full source-family truth are unresolved. Added background would turn unknown into false truth. We built candidate grouping and review evidence instead of manufacturing approval.

What changed in YOLO? No new detector architecture: explicit local incumbent initialization, verified355tensors, 12extra epochs and rare-scene train-only repetitions with mild geometric/photometric augmentation. No labels or test scenes were manufactured. Extra compute and repetition are confounded, so no novel algorithm or isolated improvement claim.

What metrics? Library AP uses validation/test evaluation; eleven supported classes enter macro AP because buffet haszeroGT. Precision/recall shown by library use a best-F1 operating point. Separate fixed0.25confidence/0.5IoU counts and independent101-point AP from raw saved boxes disclose different per-imagepadding/matching.

What failed? Temporary partition still1TP/2FP/4FN on5GT at fixed thresholds. Window externalIoUzero. Low-contrast walls collapse. Synthetic tests have no held-out indoor group. No genuine venue-photo object or outdoor boundary evaluation.

How is authority enforced? Adapter outputs remain uncertain and pixel-space, never optimization-ready. Actual frozen schema/gate rejects absent calibration/review. Source hashes and known controlled type conflicts are checked, but software cannot certify truthful external measurements or human identity.

Local execution? Actual installed PyTorch/SMP/Ultralytics libraries and GPU training/inference; Python/library APIs still exist. Blocked localhost/githubDNS probes are recorded. This is not literal noAPI or OS-level isolation. No hosted model or optimization service was substituted.
""")
request=read(H/"adapter_outputs/INDOOR_CONTROLLED/RESULT.json")["request"]
save("INDOOR_REQUEST.json",request)
save("OUTDOOR_REQUEST.json",read(H/"adapter_outputs/OUTDOOR_PENDING/RESULT.json")["request"])
write("RUNBOOK.md","""# Executable commands

Run from C:\\My Research Component with existing .venv. All outputs must stay in this isolated workspace. Prior evidence uses exclusive writes; do not rerun stages into populated directories.

Actual successful commands:

    .venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_MODEL_DEVELOPMENT_V2/prepare.py
    .venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_MODEL_DEVELOPMENT_V2/run_stage.py train_yolo
    .venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_MODEL_DEVELOPMENT_V2/run_stage.py evaluate_yolo
    .venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_MODEL_DEVELOPMENT_V2/verify_detection.py
    .venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_MODEL_DEVELOPMENT_V2/run_stage.py test_adapter
    .venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_MODEL_DEVELOPMENT_V2/run_stage.py qualify_unet
    .venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_MODEL_DEVELOPMENT_V2/routing_supplement.py

train_yolo/evaluate_yolo ran with approved sandbox escalation for Windows multiprocessing pipe access, retaining Python offline/write guards. Each stage COMMAND.json captures actualargv/cwd/exit/time; stdout/stderr and failed attempts preserved. Direct prepare/verify/routing tool invocations completed exit0; they were not retrospectively assigned subprocess logs.

New inference invocation (fresh output path):

    .venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_MODEL_DEVELOPMENT_V2/infer.py --request PP1_READINESS_20261022/PP1_MODEL_DEVELOPMENT_V2/INDOOR_REQUEST.json --out PP1_READINESS_20261022/PP1_MODEL_DEVELOPMENT_V2/demos/MY_INDOOR_001

This exact CLI command is tested in CLI_EXECUTION.json. Inspect RESULT.json and overlays; optimization_ready staysfalse. OUTDOOR_REQUEST.json selects the pending path; it does not invent boundary detection. No server/frontend or optimizer startup is needed.

New U-Net training command: NONE. Its essential human data-readiness gate is not satisfied. Do not invoke the frozen legacy trainer to bypass the gate or overwrite history.
""")
save("FINAL_SOURCE_CHECKPOINT_IDENTITIES.json",{"unet":sha(ROOT/"02_GENERATED_RESEARCH_DATA/STAGE_B_PP1_BASELINE/best_unet_resnet18.pt"),"old_yolo":sha(compare["diagnostic_test"]["incumbent"]["checkpoint"]),"new_yolo":sha(trained["best_checkpoint"])})
print("Closeout reports written; preservation",len(protected),"original files and",len(freeze["runtime_sha256"]),"freeze entries PASS")
