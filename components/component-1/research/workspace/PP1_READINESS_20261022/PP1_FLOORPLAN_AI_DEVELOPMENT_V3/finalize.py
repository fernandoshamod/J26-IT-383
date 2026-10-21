"""Close actual experiments, source preservation, commands and precise acceptance."""
import csv,collections,ast,subprocess,time,importlib.metadata,shutil
from common import *
def md(name,text):
 with (H/name).open("x",encoding="utf-8") as f:f.write(text)
ut=read(H/"unet/TRAINING_RESULT.json");st=read(H/"symbols/TRAINING_RESULT.json")
ev=read(H/"unet/EVALUATION.json");sv=read(H/"symbols/EVALUATION.json")
native=read(H/"unet/ELIGIBLE_NATIVE_SPLITS.json");qa=read(H/"unet/NATIVE_QUALIFICATION_RESULT.json")
tests=read(H/"uploads/TEST_RESULTS.json");symind=read(H/"symbols/INDEPENDENT_EVALUATION.json")
assert tests["status"]=="PASS" and read(H/"unet/INDEPENDENT_METRIC_REPLAY.json")["status"]=="PASS" and read(H/"INDEPENDENT_NATIVE_EXPORT_REPLAY.json")["status"]=="PASS"
# Actual fresh CLI demonstration and expected-negative metric review CLI.
source=tests["runs"][0]["source"]
argv=[sys.executable,"-B",str(H/"upload_inference.py"),"--source",source,"--route","indoor","--out",str(H/"cli/INDOOR_FINAL")]
with (H/"CLI.stdout.log").open("x",encoding="utf-8") as out,(H/"CLI.stderr.log").open("x",encoding="utf-8") as err:p=subprocess.run(argv,cwd=ROOT,stdout=out,stderr=err)
save("CLI_EXECUTION.json",{"argv":argv,"cwd":str(ROOT),"exit_code":p.returncode})
assert p.returncode==0
negative=[sys.executable,"-B",str(H/"review_cli.py"),"--page",str(H/"uploads/INDOOR_NATIVE/page_001/RESULT.json"),"--review",str(H/"upload_test_fixtures/MISSING_REVIEW.json"),"--mode","metric","--out",str(H/"REVIEW_CLI_NEGATIVE_VERIFIED.json")]
with (H/"REVIEW_CLI.stdout.log").open("x",encoding="utf-8") as out,(H/"REVIEW_CLI.stderr.log").open("x",encoding="utf-8") as err:p=subprocess.run(negative,cwd=ROOT,stdout=out,stderr=err)
save("REVIEW_CLI_EXECUTION.json",{"argv":negative,"exit_code":p.returncode,"expected_rejection_exit":2})
assert p.returncode==2 and read(H/"REVIEW_CLI_NEGATIVE_VERIFIED.json")["status"]=="rejected"
for f in H.glob("*.py"):ast.parse(f.read_text(encoding="utf-8"))
protected=read(ROOT/"PP1_READINESS_20261022/PP1_MODEL_DEVELOPMENT_V2/PROTECTED_SOURCE_HASHES.json")
protected.update(read(H/"PROTECTED_NATIVE_HASHES.json"))
for r in tests["runs"]:
 path=Path(r["source"])
 if not path.is_relative_to(H):protected[path.relative_to(ROOT).as_posix()]=r["source_sha256"]
changed=[p for p,h in protected.items() if sha(ROOT/p)!=h]
freeze=read(ROOT/"PP1_READINESS_20261022/PP1_EXECUTABLE_V1/BACKEND_FREEZE_V1.json")
drift=[p for p,h in freeze["runtime_sha256"].items() if sha(ROOT/p)!=h]
save("PRESERVATION.json",{"status":"PASS" if not changed and not drift else "FAIL","tracked_original_files":len(protected),"changed":changed,"backend_freeze_entries":len(freeze["runtime_sha256"]),"backend_freeze_drift":drift,"hashes":protected,"scope":"Tracked source/checkpoint/history and source-image pairs, not a new full-project bytewise audit."})
assert not changed and not drift
oldnative=ev["incumbent"]["native"]["pooled_metrics"];newnative=ev["native_v3"]["native"]["pooled_metrics"]
oldcvc=ev["incumbent"]["observed_cvc"]["pooled_metrics"];newcvc=ev["native_v3"]["observed_cvc"]["pooled_metrics"]
historical=read(ROOT/"02_GENERATED_RESEARCH_DATA/STAGE_B_PP1_BASELINE/provisional_splits.json")
oldparts={r["id"]:s for s,rows in historical.items() for r in rows}
baseline_exposure=dict(collections.Counter(oldparts[r["id"]] for r in native["diagnostic_test"]))
save("SOURCE_EXPOSURE_LIMITS.json",{"v3_native_test_original_incumbent_partition":baseline_exposure,"historical_svg_test_scores_previously_observed":True,"native_raster_test_model_predictions_before_this_mission":False,"complete_physical_source_ancestry_certified":False,"known_group_overlap_excluded":True,"cvc_ten_observed_diagnostics_not_untouched":True,"uninspected_112_cvc_inferred":False})
capabilities=[
 ("Indoor native raster structural inference","IMPLEMENTED_AND_TESTED","448publisher-native technical pairs;320train64val64heldout; class-IoU bounded to this subset; no human certification"),
 ("Walls/room/door/window quality","PARTIAL","Native pooled0.79046; CVCdoor0.10432; no background output and margin false positives"),
 ("PNG/JPG decoding","IMPLEMENTED_AND_TESTED","Original hashes, actual inference/candidates, source coordinates"),
 ("PDF multipage raster handling","IMPLEMENTED_AND_TESTED","Actual4page user PDF plus public PDF; raster decode only, no venue metric units inferred"),
 ("SVG vector/semantic regions","PARTIAL","Strict safe subset; affine polygon source-coordinate extraction; typed source regions/fixed furniture, not generic learned semantics"),
 ("CAD/DXF/DWG","NOT_IMPLEMENTED","No verified converter installed; explicit refusal"),
 ("Native door/window symbol YOLO","IMPLEMENTED_AND_TESTED","New2class16epochmodel; 618door517window testGT; not twelve-event-object model"),
 ("Twelve event-object recognition on new real floorplans","DATA_BLOCKED","Native source labels do not support the twelve classes; localFloorPlanCAD version/taxonomy mismatch and drawing-rights caveat held"),
 ("Outdoor algorithmic polygon proposals/editing","IMPLEMENTED_AND_TESTED","Actual2unclassified contours on NPS plan plus structured edit function; zero on public PDF; no boundary semantic success"),
 ("Outdoor true boundary recognition","FAILED","Inspected NPS proposals include map legend/frame, not verified usable/site boundary"),
 ("Outdoor entrance/obstacle/covered/open/restricted understanding","DATA_BLOCKED","No eligible annotation targets or trained recognizer; never infer from indoor labels"),
 ("Hybrid source-annotated SVG region handling","PARTIAL","Real native sourceRoom/Outdoor regions, affine transforms and overlap refusal; not general raster mixed-region learning"),
 ("Automatic hybrid raster region understanding","DATA_BLOCKED","Requires source region annotation/review; no trained mixed-zone classifier"),
 ("Mask-to-polygon geometry","IMPLEMENTED_AND_TESTED","Actual reused cell-union function, independent native export and numerical/source-frame checks; not semantic/physical geometry accuracy"),
 ("Metric calibration/planner verification","PARTIAL","Structured editing and unchanged gate delegation; negative missing evidence test; genuine measurements and reviewer not supplied"),
 ("Approved real metric Twin handoff","DATA_BLOCKED","No genuine positive approval, two measured controls, reviewed boundary/fixed objects or required reviewed stage provided")]
save("CAPABILITY_ACCEPTANCE.json",{"capabilities":[dict(capability=c,status=s,evidence=e) for c,s,e in capabilities],"whole_system_complete":False,"new_unet_trained":True,"new_yolo_opening_model_trained":True,"existing_12class_model_retrained_on_new_floorplans":False,"genuine_positive_real_twin":False})
with (H/"CAPABILITY_ACCEPTANCE.csv").open("x",encoding="utf-8",newline="") as f:
 w=csv.writer(f);w.writerow(["capability","status","evidence"]);w.writerows(capabilities)
sources=[
 {"dataset":"CubiCasa5K","local":"01_DATASET_DOWNLOADS/CubiCasa5K","official":"https://github.com/CubiCasa/CubiCasa5k","package_url":"https://zenodo.org/records/2613548/files/cubicasa5k.zip?download=1","publisher_zip_md5":"0ce0b203d1e3c125b51087b219bd23b9","original_archive_available_for_recheck":False,"downloaded_this_mission":False,"used":"Publisher F1_scaled rasters and native source polygons, NOT prior SVG-render image/mask export","license":"CC BY-NC4.0 with attribution; Kalervo et al., CubiCasa5K,2019","native_contract":"https://raw.githubusercontent.com/CubiCasa/CubiCasa5k/master/floortrans/loaders/svg_loader.py","accepted_technical_pairs":448,"excluded_by_predeclared_gate":len(qa["rejected"]),"remaining_unexported":4990-448-len(qa["rejected"]),"approval":"No independent human sign-off claimed; original A2/export review statuses untouched"},
 {"dataset":"CVC-FP","local":"01_DATASET_DOWNLOADS/06_CVC_FP_OFFICIAL","official":"https://dag.cvc.uab.es/dataset/cvc-fp-database-for-structural-floor-plan-analysis/","downloaded_this_mission":False,"used":"10previouslyobservednative-labeldiagnostics; other112notinferred or trained","license":"Publication supports research benchmark release; no commercial/redistribution grant inferred","new_acquisition_failure":"Local HTTPS certificate verification failed; not disabled or bypassed","training":False},
 {"dataset":"FloorPlanCAD","official":"https://floorplancad.github.io/","downloaded_this_mission":False,"local":"01_DATASET_DOWNLOADS/FloorPlanCAD","status":"HOLD_NOT_USED_FOR_TRAINING","reason":"Local hyphenatedannotation IDs/schema not reconciled with fetched author taxonomy; visual examples warn against guessing classIDs. Publisher releases annotations CC BYNC, does not own underlying drawings.","primary_taxonomy":"https://raw.githubusercontent.com/VITA-Group/CADTransformer/main/config/anno_config.py"},
 {"dataset":"NPS campground/site plans","downloaded_this_mission":True,"official":"https://www.nps.gov/yose/planyourvisit/pinescampgrounds.htm","jpeg":"https://www.nps.gov/yose/planyourvisit/images/pinescombined.jpg","pdf":"https://www.nps.gov/yose/planyourvisit/upload/yosemitecampgroundmap2013.pdf","rights":"https://www.nps.gov/subjects/gisandmapping/data-sources-and-accuracy.htm","license":"NPS maps public domain; generalized orientation maps, explicitly not legal boundary documents","used":"Outdoor and document-decoding functional tests only; NO trained boundary or zone ground truth"},
 {"dataset":"Existing user venue PDF","local":"03_REAL_VENUE_REFERENCES/00_INBOX/PDF_ORIGINALS/feb-2025-floor-plan.pdf","downloaded_this_mission":False,"used":"User-authorized4page local inference demonstration only","rights":"Training/public-redistribution rights unverified; not included as training ground truth"},
 {"dataset":"ResPlan/SCUT/localRoboflow candidates","downloaded_this_mission":False,"used":"None for new training","status":"HOLD","reason":"No new source-bound, ontology-compatible raster/furniture/site annotation qualification; no satellite/photo substitute used"}]
save("DATA_SOURCES_AND_LICENSES.json",sources)
traininfo=read(H/"unet/TRAINING_CONFIG.json")
md("README.md",f"""# Floorplan AI development V3

**Executed: new native-raster U-Net training, a separate native door/window YOLO training run, matched/independent evaluation and local PNG/JPG/PDF/SVG processing. The full twelve-class event-stock/outdoor/approved-Twin system remains incomplete.**

All work is isolated here. Original U-Net/YOLO checkpoints, datasets, prior metrics, A-F/eight-logics, backend/frontend/EAG/NSGA-II remain unchanged. No dependency installation/upgrades.

## Measured results

- New U-Net:16GPUepochs on320publisher-native raster plans; validation64; heldout64. Known source/render/native duplicate and near-family checks; unresolved physical ancestry remains disclosed. New checkpoint: unet/best_native_unet.pt; SHA{ut['sha256']}.
- Common native-raster letterbox protocol: incumbent mIoU **{oldnative['miou']:.8f}**, V3 **{newnative['miou']:.8f}**. Four classes include no verified background.
- Ten previously observed CVC diagnostics under the same new letterbox protocol: **{oldcvc['miou']:.8f} -> {newcvc['miou']:.8f}**. Do not compare these directly to historical square-resize0.28178 or SVG-render0.90277. No untouched external test claim.
- New auxiliary YOLO:16GPUepochs, **door/window only**. Test mAP50 **{sv['metrics']['metrics/mAP50(B)']:.8f}**, mAP50-95 **{sv['metrics']['metrics/mAP50-95(B)']:.8f}**. This is not the preserved twelve-event-object model.
- Independent target/box export replay448records, saved-mask metric replay148model/domainrecords, separate scalar detection matching/AP, source-coordinate and refusal tests retained.
- Upload tests:8document cases ({len(tests['checks'])}assertions within one suite), plus invalidJPEG/CAD refusals and actual reviewCLI missing-evidence rejection. Counts are not independent scientific studies or model-accuracy acceptance.

## Read first

TRAINING_AND_RESULTS.md explains exact targets/metrics; DATASET_QUALIFICATION.md explains native pairing and limitations; CAPABILITY_ACCEPTANCE.csv/JSON distinguishes operational success from scientific gaps. FAILURE_CASES.md preserves outdoor legend/margin errors and document shift. RUNBOOK.md has actual commands and a fresh-output CLI example.

Sources/download hashes are in DATA_SOURCES_AND_LICENSES.json and acquisition manifests. Actual overlays under unet/predictions/, symbols/predictions_conf025/ and uploads/. The public-domain NPS map is development input with no target labels. The private user PDF is not licensed training material.

**PP1 can show an actual uploaded floorplan being decoded, segmented, detected and converted to provisional source-bound geometry. It cannot honestly show automatic true boundaries, twelve-class real-plan stock recognition or a genuinely approved metric Twin without the missing evidence.**
""")
md("DATASET_QUALIFICATION.md",f"""# Native floorplan data qualification

## What changed from V2

The official [CubiCasa loader](https://github.com/CubiCasa/CubiCasa5k/blob/master/floortrans/loaders/svg_loader.py) reads F1_scaled.png and builds annotations at that image height/width. Its native polygon coordinates are not the earlier SVG-viewBox-render path. V3 implements a NEW native pixel projection from publisher polygons; it does not relabel the prior masks or sign any old human-review record.

F1_scaled is a publisher-supplied raster derived from an original drawing; it is not our annotation-SVG render, and not a claim of unprocessed F1_original scan pixels. Native masks were newly generated in this isolated workspace. Raw Space polygons (except Outdoor/Undefined) become room0; native Wall1/Door2/Window3 overwrite by declared precedence. All other/unassigned pixels and letterboxpadding remain255ignored. Room is a source region, not event-usable area or proof of indoor enclosure. No background truth was invented.

Before any inference, fixed technical gates required all4classes on512grid, >=100wallpixels, >=0.60fraction of nativewallpixels darker than180gray, and >=0.98nativevertices inside source raster. Group-ranked selection took one record per observed conservative family. Nine source-only qualification previews were inspected prediction-blind, spanning all partitions. This is technical/publisher-native experimental qualification plus agent-assisted sample review, NOT independent human certification.

Accepted/exported:320train64validation64heldout =448pairs. **{len(qa['rejected'])}** inspected candidates failed technical gates; the remaining {4990-448-len(qa['rejected'])} records were not exported/qualified here (including unexamined/skipped group members). Every exclusion and exact source/mask path is saved. Darkness gates can exclude correct faint labels, biasing this bounded subset; the results do not represent all5000plans or generic scans.

Known groups reuse V2 conservative SVG/render/image/mask unions and near-variant edges, then check native RGB hashes and63-bitDCT Hamming<=6 across selected partitions. No observed cross-partition match remained. Full physical venue ancestry is still unresolved; don't call this exhaustively certified venue-disjoint data.

All64 V3heldout IDs belong to the incumbent's historical test partition: {baseline_exposure}. Historical SVG-domain test outcomes have already been seen. The new native predictions were not used for choices before checkpoint selection, but this is not a pristine untouched external family benchmark. All10CVCsheets are observed diagnostics; the other112remain unused.

Independent export replay uses a separate DOM parser/explicit rules to rebuild all448native masks and opening boxes and compare exact outputs. It shares Pillow rasterization and the declared source ontology; it is not independent annotation truth.

## Acquisition and rights

[CubiCasa official licence](https://github.com/CubiCasa/CubiCasa5k/blob/master/LICENSE): CC BY-NC4.0, attribution/noncommercial research. Existing source corpus reused rather than redundantly downloading5.5GB. Official package link/MD5 recorded; the original archive was absent, so its complete byte identity was NOT reverified. Every used original raster/SVG has recorded hashes.

Downloaded official ResNet18 ImageNet initialization and publisher loader/licence files; fullSHA recorded, published filename-hash prefix verified. No trained task checkpoint initialized V3U-Net. [NPS map source](https://www.nps.gov/yose/planyourvisit/pinescampgrounds.htm) and [rights/accuracy statement](https://www.nps.gov/subjects/gisandmapping/data-sources-and-accuracy.htm) support public-domain development examples, not legal boundaries or training annotations.

FloorPlanCAD's local annotation-version/schema/class mapping did not meet qualification. No classID was guessed from visual appearance. All twelve event-stock classes remain unsupported on new real plans. A separate two-class structural-opening resource uses explicit native Door/Window polygons; do not call it furniture detection.

No external venue scraping, satellite substitute, new human label, planner approval or invented physical measurement was used. CVC HTTPS acquisition failed certificate validation and was retained; security verification was not disabled. Known essential full-export/human review limitations remain open.
""")
classrows="| Class | Old native IoU | V3 native IoU | Old observed-CVC IoU | V3 observed-CVC IoU |\n|---|---:|---:|---:|---:|\n"
for i,c in enumerate(["room_region","wall","door","window"]):classrows+=f"| {c} | {oldnative['class_iou'][i]:.8f} | {newnative['class_iou'][i]:.8f} | {oldcvc['class_iou'][i]:.8f} | {newcvc['class_iou'][i]:.8f} |\n"
symbolrows="| Class | Test GT | Precision bestF1 | Recall bestF1 | AP50 | AP50-95 |\n|---|---:|---:|---:|---:|---:|\n"
for i,c in enumerate(["door","window"]):symbolrows+=f"| {c} | {sv['support'][str(i)]} | {sv['precision_best_f1'][i]:.8f} | {sv['recall_best_f1'][i]:.8f} | {sv['ap50'][i]:.8f} | {sv['ap50_95'][i]:.8f} |\n"
md("TRAINING_AND_RESULTS.md",f"""# Actual training and held-out results

## U-Net/ResNet18 nativeV3

New local ImageNet encoder initialization (downloaded official PyTorch weight), random decoder,4classes,320train/64val,16epochs,batch4,512aspect-preservingletterbox. RGB/ImageNetnormalization; unknown/padding255. AdamW lr0.0003 weightdecay0.0001, cosine scheduler; capped inverse-square-root training-frequency weightedcrossentropy +0.5valid-pixelmacrosoftDice. Flip/90degreerotation and mildcontrast/brightness/blur augment TRAIN ONLY. Train mixedprecision, validation/testFP32; best pooled validationmIoU selection frozen before test.

Best validationmIoU {ut['best_val_miou']:.10f}; train seconds {ut['seconds']:.3f}; GPU {ut['gpu']}. Exact config/history/checkpoint metadata and train class weights are saved. GPU training started and completed; not a mocked substitute. No silent pretrained task-weight reuse.

{classrows}

Native pooled means: old {oldnative['miou']:.10f}, new {newnative['miou']:.10f}. ObservedCVC means: old {oldcvc['miou']:.10f}, new {newcvc['miou']:.10f}. Both models use IDENTICAL new letterbox images/targets and FP32argmax, so this is a matched diagnostic protocol. OldSVG0.9027725281 and nativeCVCsquare0.2817846732 remain separate historical artifacts. Allfourpositive-support classes contribute; ignoredpixels excluded from all denominators. Outside/background performance is not measured and remains poor.

Saved per-record4x4confusions, IoUs, support and overlays: unet/EVALUATION.json, unet/PER_RECORD_METRICS.csv, unet/predictions/. Independent scalarCounter mask replay exactly matched all148record matrices and pooled IoUs; model was not run again for the replay. No superiority, significance or new-architecture claim; data/preprocessing/training/loss changes are confounded.

## Auxiliary native floorplan opening YOLOv8n

Preserves the twelve-event-object models separately. New2classmodel maps native Door->0/Window->1, not event-stock classIDs.320train64val64test,16epochs,960,batch4,FP32,localCOCOyolov8n initialization, AdamW0.0003/cosine, mildspatial/brightnessaugmentation. Validationfitness selects checkpoint; test run afterward.

{symbolrows}

Pooled mAP50 {sv['metrics']['metrics/mAP50(B)']:.10f}, mAP50-95 {sv['metrics']['metrics/mAP50-95(B)']:.10f}; macro denominator2classes. Train seconds {st['seconds']:.3f}. Low localization AP50-95 and nontrivialFN/FP remain. Do not compare against the V2twelve-class synthetic0.91045 as an improvement: ontology and domain differ.

Independent scalarIoU/greedy101pointAP over saved per-image predictions: mAP50 {symind['map50']:.10f}, mAP50-95 {symind['map50_95']:.10f}; labels/support/sourcehashes checked. Library rectangular batchpadding and independent matching differ from per-image replay, so exact equality with libraryAP is NOT falsely claimed. Rawboxes/labels and fixedthresholdcounts remain.

Actual success and worst-case overlays retained. Original low-thresholdconf0.001 raw-evaluation plots are intentionally dense; readable actualpredictionsconf0.25 versions are under symbols/predictions_conf025/. Neither display threshold was tuned after viewing test outcomes.
""")
table="| Capability | Acceptance | Evidence/limit |\n|---|---|---|\n"+"\n".join("| "+c+" | "+s+" | "+e+" |" for c,s,e in capabilities)
md("FUNCTIONAL_ACCEPTANCE.md",f"""# Functional acceptance

**PARTIAL working research subsystem. Full real-venue recognition/approved-Twin completion is not claimed.**

{table}

Eight document cases and{len(tests['checks'])}assertions are a functional suite, not semantic accuracy or independent studies. Actual fresh CLI exit0; actual missing-review CLI exit2/rejected. Model checkpoints and64recordheldout metrics are real. All{len(protected)}trackedoriginal source/checkpoint/evidence files and{len(freeze['runtime_sha256'])}backendfreezeentries match.

The genuine multi-page commercialPDF processes all4pages with actual models. It has no gold annotation/physical scale/verified provenance here, and its margin/legend errors make reliable venue understanding unestablished. NPSsite map produced2unverified closed contours, including a legendbox: no valid true boundary success is claimed. NPSPDF produced0candidatecontours. These null/failed semantic results are preserved.

The hybrid SVG demonstrates more than routing: explicit sourceRoom/Outdoor regions and fixed furniture are transformed to decoded pixels, overlaps are checked, and indoor model output is masked to source-declared indoor regions. This is source-qualified vector/rule processing, not learned recognition of unannotated raster mixed regions.

All outputs remain optimization_ready=false. The unchanged metric gate still requires genuine measured calibration, reviewed boundary, fixed-object semantics, source-bound evidence and exactlyone reviewedstage. No residentialplan was relabelled as containing a stage; no new design object was fabricated as observed stock. Positive real-Twin registration/persistence was NOT executed because those inputs are absent.

Original A-F/eight research logics, S-GCN/weather/safety/feedback/XAI objectives remain untouched. No frontend, frozen backend edits, optimizer execution or source cleanup. Scientific originality status is unchanged by these application/model corrections.
""")
md("FAILURE_CASES.md","""# Preserved failures and limitations

1. Initial acquisition in sandbox failed connection access; manifest retained. Authorized explicit download succeeded outside sandbox. CVCsource HTTPS certificate failed even afterward; certificate checks were not disabled.
2. Native candidate QA rejected507inspectedrecords before any model prediction. Lowdarkness can reflect true faintwalls, so exclusions bias the subset. No heldout record was replaced after scoring. Complete source-family ancestry and independent human semantic certification remain unresolved.
3. Worst new native test: cubi_02663 mIoU0.5312238806, large/multi-plan/faintdetails. Best: cubi_00412 mIoU0.9287625837. Both source/GT/prediction overlays retained. Even best foreground score hides wrong predictions in unassigned margins.
4. CVCnative doors stillIoU0.1043205092: native swing sectors differ from narrow CubiCasa openings. NewwindowsIoU0.4045252934 improves the matched diagnostic but remains weak. The ten records are observed, not untouched final transfer evidence.
5. New YOLOdoor/window localization mAP50-95 is0.3876450426. Fixedconf0.25 original-coordinate counts: door463TP132FP155FN; window382TP191FP135FN. These differ from librarybestF1precision/recall definitions.
6. Twelve event-stock classes lack qualified newfloorplan annotations. FloorPlanCAD schema/version/rawID mismatch was NOT solved by appearance-based guessing. No real floorplan buffet, chair, stage or temporarypartition claim.
7. RealNPSoutdoor site-map proposals include a legendbox/frame, not a verified site/usable boundary. The other publicPDF returned0contours. Classical contour extraction is operational but failed semantic boundary qualification. The map itself is generalized/notto-scale in places, not a legal boundary source. Entrances/obstacles/covered/restricted semantics remain unsupported.
8. Actual four-page commercialfloorplan PDF decoder/model calls succeeded, but sourceprovenance/annotation/metrictruth are unverified. Page1overlay visibly labels margins and legend as structural classes. Functional processing is not correct venue understanding.
9. Hybrid source-labelled SVG region parsing/affineconflict detection works in tested scope. Source labels, not trained mixed-region perception, supply region types. Some sourceclasses remain unclassified; invalid/outofframepolygons are held. Generic hybridraster understanding remains data-blocked.
10. Source PNG/JPG/PDF/SVG coordinates are decoded pixel frames; no automatic metres/true usablefloor. PDFpoint scale is document scale, not venue scale. Arbitrarily rotatedPDF raw-coordinate inversion and fullSVGgrammar are not independently validated.
11. Blankimage and overlappingregions refuse model execution; invalidJPEG/CAD converter requests refuse decoding. Controlledtest fixture geometry/edits are explicitly artificial and never called genuine planner approval.
12. Runtimewarnings (loss Tensor-to-scalar, PNGICCprofile, globalfitzdeprecation) are retained. They did not change exit success or justify package upgrades. Python network guards/logs are instrumentation, not complete OS isolation; no zeroattempt claim is made if logs show library probes.
""")
md("INPUT_ROUTING_AND_REVIEW.md","""# Local upload and review contract

New upload_inference.py version3.0.0, local Python/CLI, preserves existing server/UI/checkpoints. PNG/JPG directly decode; PDF uses already-installed globalPyMuPDF, pages<=20/max1600side; SVG uses already-installed globalCairoSVG, strictviewBox/affines and externalreference/script/DOCTYPE rejection. No package upgrade. CAD/DWG/DXF converter is absent and explicitly rejected.

Indoor PNG/JPG/PDF: actual V3U-Net and auxiliary2classopeningYOLO. User-specified route is not inferred venue truth. Pureoutdoor never runs indoor labels. Hybrid SVG can use explicit sourceRegionclasses; missing typedregions stayspending, conflictingIndoor/Outdoorpolygons refuse modelcalls. No unsupported raster mixed-zone classifier is invented.

Output preserves originaldocumentSHA and byte-identical local copy; per-page decodedPNGsourceSHA/dimensions/transform and source-imagepixelcandidates form IMAGE_SPACE_TWIN_CANDIDATE_V2. PDF/SVGoriginalidentity is a companion provenance record; frozen gate sourcepath is the actual decodedPNG. Both identities are retained. No external evidence automatically verifies physicalscale.

States are explicit: actual model candidates PREDICTED+uncertain; source-layer polygons DERIVED_FROM_VECTOR; contourregions UNVERIFIED; unsupported event-stock/entrance/zones UNSUPPORTED. No USER_CONFIRMED result is fabricated because no genuine reviewer input was supplied. Nativevectorfixedfurniture remains its source class, never relabelled one of12eventobjects by guessing.

PENDING_REVIEW.json containsnullboundary/calibration/reviewer rather than dummyvalues. review_handoff.edit_proposal accepts explicit source-bound pixelcorrections/reviewer/reason and validpolygon; returns LOCAL_UNAUTHENTICATED_EDIT with optimization_ready=false, not approvedTwin. The tested edit is explicitly CONTROLLED_UNIT_TEST_NOT_A_PLANNER.

review_cli.py --mode metric delegates actual contracts.TwinReview/reviewed_metric_twin unchanged. Submit complete genuinely supplied evidence, not the pendingtemplate, to validate the metric gate. Gate success alone is unauthenticated localinput and does not create a DBregistration; use the existing verified backend registration contract afterward. No positive external review/metric success was executed here.

Only supported fixedreviewedobjects and exactlyone reviewedstage fit the frozen metricgate. General residentialplans do not supply that stage automatically. Planned equipment must remain distinct from observedinventory. Current workflow stops before approval because legitimate inputs are missing.
""")
md("RUNBOOK.md",f"""# Reproduction and actual demonstration

From C:\\My Research Component, existing .venv. All newoutputs stay inside PP1_FLOORPLAN_AI_DEVELOPMENT_V3. Evidence stages use exclusivecreation; do not rerun them into populateddirectories.

Actual stages executed:

    .venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_FLOORPLAN_AI_DEVELOPMENT_V3/acquire.py
    .venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_FLOORPLAN_AI_DEVELOPMENT_V3/acquire_cad_metadata.py
    .venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_FLOORPLAN_AI_DEVELOPMENT_V3/acquire_site.py
    .venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_FLOORPLAN_AI_DEVELOPMENT_V3/qualify_native.py
    .venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_FLOORPLAN_AI_DEVELOPMENT_V3/check_native_split.py
    .venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_FLOORPLAN_AI_DEVELOPMENT_V3/run_stage.py train_unet
    .venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_FLOORPLAN_AI_DEVELOPMENT_V3/run_stage.py prepare_cad
    .venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_FLOORPLAN_AI_DEVELOPMENT_V3/run_stage.py train_cad
    .venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_FLOORPLAN_AI_DEVELOPMENT_V3/run_stage.py evaluate_unet
    .venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_FLOORPLAN_AI_DEVELOPMENT_V3/run_stage.py evaluate_cad
    .venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_FLOORPLAN_AI_DEVELOPMENT_V3/run_stage.py test_uploads
    .venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_FLOORPLAN_AI_DEVELOPMENT_V3/verify_native_export.py
    .venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_FLOORPLAN_AI_DEVELOPMENT_V3/region_geometry_checks.py

train_cad/prepare_cad filenames refer to the isolated nativeplan-symbol branch, NOT successful FloorPlanCAD data use. They train only two nativeopeningclasses; existing12eventclasses are unchanged. Stage COMMAND.json/stdout/stderr preserve exactargv/cwd/exit/time. Acquisition manifests preserve failed and successful downloads; acquisition was explicit network work, train/inference were locallyguarded. YOLOtrain/eval needed approved Windows pipe access outside sandbox.

Actual fresh CLI example completed at cli/INDOOR_FINAL (see CLI_EXECUTION.json). To reproduce inference, use another fresh output:

    .venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_FLOORPLAN_AI_DEVELOPMENT_V3/upload_inference.py --source "{source}" --route indoor --out PP1_READINESS_20261022/PP1_FLOORPLAN_AI_DEVELOPMENT_V3/cli/MY_NATIVE_001

Open that directory's page_001/UNET_OVERLAY.png, OPENING_YOLO_OVERLAY.png, RESULT.json, PENDING_REVIEW.json and top-levelUPLOAD_RESULT.json. No actualreviewer/calibration is filled automatically.

Saved working cases: uploads/INDOOR_NATIVE, INDEPENDENT_DRAWING_STYLE, NATIVE_HYBRID_VECTOR, USER_MULTIPAGE_PDF. Outdoorfailureexamples: NPS_OUTDOOR_SITE and PUBLIC_PDF. Refusals/controlcases remainalongside. Source/GT/prediction comparisons: unet/predictions/native/native_v3; source-symbolresults: symbols/predictions_conf025.

Structured review CLI:

    .venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_FLOORPLAN_AI_DEVELOPMENT_V3/review_cli.py --page <page_RESULT.json> --review <genuine_complete_review.json> --mode metric --out PP1_READINESS_20261022/PP1_FLOORPLAN_AI_DEVELOPMENT_V3/reviews/MY_REVIEW_001.json

Missingreview actualCLI exited2/rejected (REVIEW_CLI_EXECUTION.json). A valid external review command remains dependent on genuine suppliedinputs. Do not insert simulatedapproval or syntheticmeasurements. There is no automatic optimizer invocation.
""")
md("PP1_VERDICT_AND_NEXT_ACTION.md",f"""# PP1 verdict

Actual real floorplan processing demonstration: **YES, bounded and review-required.** Both newlocalGPUtrainingruns completed; real masks/boxes/polygons, perclassheldoutmetrics, independent export/metric checks and preservedfailurecases exist.

BestnewU-Net: unet/best_native_unet.pt, SHA{ut['sha256']}.
BestnewauxiliaryYOLO: symbols/native_openings/weights/best.pt, SHA{st['sha256']}.

Model acceptance remainsPARTIAL: native-raster U-Net is an experimental boundedsubset result; sourceancestry and independenthumanevaluation incomplete. AuxiliaryYOLOcoversdoor/window, not the12eventstocksystem. Outdoorsemanticboundaryvalidityfailed in inspected publicmap; genericmixedrasterunderstanding and mostsiteclasses are data-blocked.

No full user-plan -> genuinely approvedmetricTwin -> optimizedeventlayout was demonstrated. Actualmodelsprocessing a plan and passing arithmetic/coordinate tests do not establish semantictruth, measuredgeometry, safety or planneracceptance.

**Single highest-priority next action:** obtain genuine calibrated geometry and planner review for ONE representative venueplan using its newpending-reviewoutput, then test that source-bound record through the unchanged metricTwin/backend contract. Do not fake an existingstage, measurements or approval to make the demonstration continue.

Preserve remaining12classfloorplanannotation work and trueoutdoor/mixedregion evaluation as explicit latergaps. Originaleight-logics/A-F/S-GCN/weather/safety/feedback/XAI scope is unchanged.
""")
save("RUNTIME_DEPENDENCIES.json",{"venv_python":sys.executable,"versions":{n:importlib.metadata.version(n) for n in ["torch","torchvision","segmentation-models-pytorch","ultralytics","numpy","Pillow","shapely","opencv-python"]},"document_renderer_python":"C:/Users/User/AppData/Local/Programs/Python/Python312/python.exe","document_libraries":"Existing global PyMuPDF/CairoSVG; no install/upgrade","local_library_apis_used":True,"hosted_model_or_optimizer_used":False,"OS_network_isolation_claimed":False,"disk_usage_bytes":dict(zip(["total","used","free"],shutil.disk_usage(ROOT)))})
print("Finalized actual results and acceptance; originals",len(protected),"unchanged; frozen",len(freeze["runtime_sha256"]),"match")
