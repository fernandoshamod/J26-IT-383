"""Additive local bridge to the existing Event Scene compiler and frozen search adapter.

This service is deliberately limited to explicit CONTROLLED synthetic Wedding
fixtures. It creates visibly simulated input evidence, calls the existing
compiler/oracle/bridge modules, and writes all new artifacts into this release.
It does not register a real Twin or alter the frozen API/backend.
"""
from __future__ import annotations
import argparse, importlib, sys, uuid
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from PIL import Image
from shapely.geometry import box
import uvicorn

PACKAGE_ROOT = Path(__file__).resolve().parents[3]
ROOT = PACKAGE_ROOT / "runtime"
SCENE = ROOT / "PP1_READINESS_20261022" / "PP1_EVENT_SCENE_INTELLIGENCE_V1"
STATE_ROOT = Path(__import__("os").environ.get("PP1_RUN_STATE", Path(__import__("os").environ.get("PP1_RUNTIME_STATE", PACKAGE_ROOT / "runtime-state")) / "runs" / "manual")).resolve()
RELEASE = STATE_ROOT / "scene"
OUTPUT = RELEASE / "scene_compiler_runs"
KNOX_SOURCE = Path(__import__("os").environ.get("PP1_KNOX_IMAGE", PACKAGE_ROOT / "private-assets" / "venue" / "KNOX_HALL.jpg")).resolve()
KNOX_ANALYSIS = Path(__import__("os").environ.get("PP1_KNOX_ANALYSIS", PACKAGE_ROOT / "private-assets" / "venue" / "KNOX_HALL.jpg-analysis.json")).resolve()
sys.path.insert(0, str(SCENE))
common = importlib.import_module("common")
fixtures = importlib.import_module("fixtures")
# The frozen compiler confines source/evidence paths to common.ROOT. Portable
# fixtures are deliberately generated under this run's ignored state directory,
# so bind that allowlist before importing modules that snapshot it.
common.ROOT = STATE_ROOT
compiler = importlib.import_module("compiler")
oracle = importlib.import_module("oracle")
baseline = importlib.import_module("baseline")
bridge = importlib.import_module("bridge")
policy = common.read(SCENE / "profiles.json")

# Rebind only the isolated fixture writer and bridge output root. Frozen engine
# location, compiler code, policy and validators remain the originals.
common.HERE = RELEASE
fixtures.HERE = SCENE
bridge.HERE = RELEASE
OUTPUT.mkdir(parents=True, exist_ok=True)

class SceneRun(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    event_type: Literal["wedding"] = "wedding"
    guest_count: int = Field(default=160, ge=8, le=240)
    scene_state: Literal["empty", "partially_furnished"] = "empty"

    @model_validator(mode="after")
    def capacity_contract(self):
        if self.guest_count % 8:
            raise ValueError("SUPPORTED_WEDDING_GUEST_COUNT_MUST_BE_A_MULTIPLE_OF_8")
        return self

class KnoxPlanRun(BaseModel):
    """Explicit plan-derived controlled interpretation; never a real Twin admission."""
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    event_type: Literal["wedding"] = "wedding"
    guest_count: int = Field(default=80, ge=8, le=240)

    @model_validator(mode="after")
    def capacity_contract(self):
        if self.guest_count % 8:
            raise ValueError("SUPPORTED_WEDDING_GUEST_COUNT_MUST_BE_A_MULTIPLE_OF_8")
        return self

app = FastAPI(title="Component 1 isolated Event Scene bridge", version="1.0.0")

@app.get("/health")
def health():
    return {"status":"ok", "service":"isolated-scene-bridge", "scope":"controlled Wedding only", "uses_existing_compiler":True, "uses_frozen_local_engine":True}

@app.post("/scene/compile-and-optimize")
def compile_and_optimize(q: SceneRun):
    run_id = uuid.uuid4().hex
    case = OUTPUT / ("INPUT_" + run_id)
    result_dir = OUTPUT / run_id
    try:
        request = fixtures.fixture(
            case,
            event="wedding",
            guests=q.guest_count,
            partial=(q.scene_state == "partially_furnished"),
            width=32,
            height=24,
        )
        common.save(case / "REQUEST.json", request)
        spec = compiler.compile_scene(request, policy)
        common.save(case / "SPEC.json", spec)
        independent_spec = oracle.validate_spec(request, spec, policy)
        common.save(case / "INDEPENDENT_SPEC_CHECK.json", independent_spec)
        if spec.get("status") != "accepted" or not independent_spec.get("valid"):
            raise HTTPException(status_code=422, detail={"reason":"SCENE_SPECIFICATION_NOT_ACCEPTED", "issues":spec.get("issues", []), "independent":independent_spec})
        result = bridge.execute(request, spec, result_dir, seed=20261017, policy=policy)
        if result.get("status") != "success":
            return {"schema":"SCENE_COMPILER_HANDOFF_V1", "status":"non_success", "reason":result.get("reason"), "request":request, "spec":spec, "independent_spec":independent_spec, "result":result, "artifact_path":str(result_dir)}
        return {"schema":"SCENE_COMPILER_HANDOFF_V1", "status":"success", "scope":"CONTROLLED_SYNTHETIC_SIMULATED_AUTHORITY_NOT_REAL_VENUE", "request":request, "spec":spec, "independent_spec":independent_spec, "result":result, "artifact_path":str(result_dir)}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"reason":"SCENE_BRIDGE_EXECUTION_FAILED", "type":type(exc).__name__, "message":str(exc)}) from exc

@app.post("/scene/knox-plan/compile-and-optimize")
def compile_knox_plan(q: KnoxPlanRun):
    """Run the existing scene compiler/search on a declared plan interpretation.

    Geometry is transcribed from the KNOX architectural drawing and its printed
    overall dimensions. The simulated review is deliberate: the result is a
    plan-derived demonstration, not an approved/as-built venue Twin.
    """
    if not KNOX_SOURCE.is_file() or not KNOX_ANALYSIS.is_file():
        raise HTTPException(status_code=503, detail={"reason":"KNOX_SOURCE_OR_MODEL_EVIDENCE_MISSING"})
    from shapely.geometry import Polygon
    import copy, json, math
    run_id = "KNOX_PLAN_" + uuid.uuid4().hex
    case = OUTPUT / ("INPUT_" + run_id)
    result_dir = OUTPUT / run_id
    try:
        # The published drawing labels the overall plan 96 ft x 64 ft. These
        # pixel endpoints are an analyst transcription of the dimension lines;
        # they support a controlled plan illustration only.
        source_sha = common.filehash(KNOX_SOURCE)
        with Image.open(KNOX_SOURCE) as im:
            width_px, height_px = im.size
        scale_x = (96.0 * 0.3048) / 521.0
        scale_y = (64.0 * 0.3048) / 347.0
        scale = (scale_x + scale_y) / 2.0
        origin_px = [87.0, 51.0]
        boundary_px = fixtures.ring(87.0, 51.0, 389.0, 347.0)
        def to_m(pt):
            return [(float(pt[0])-origin_px[0])*scale, (float(pt[1])-origin_px[1])*scale]
        boundary_m = [to_m(pt) for pt in boundary_px]

        request = fixtures.fixture(case, event="wedding", guests=q.guest_count, partial=False, width=32, height=24)
        # fixture() is reused only for its declared synthetic actor/policy
        # scaffold. Remove that scaffold's generated bitmap/evidence before
        # resealing the request against the actual KNOX source hash below.
        for generated_name in ["CONTROLLED_SOURCE.png", "venue_SIMULATED_RECORD.json", "client_SIMULATED_RECORD.json", "planner_SIMULATED_RECORD.json"]:
            (case/generated_name).unlink(missing_ok=True)
        request["event_id"] = "KNOX_PLAN_WEDDING_" + str(q.guest_count)
        v = request["venue"]
        v["venue_id"] = "KNOX_PLAN_INTERPRETATION_CONTROLLED"
        v["source"] = dict(path=str(KNOX_SOURCE.resolve()), sha256=source_sha, width_px=width_px, height_px=height_px,
                           domain="plan_derived_controlled", origin="PLAN_DRAWING_INTERPRETATION")
        v["review"]["scope"] = "PLAN_DERIVED_SIMULATED"
        v["review"]["reviewer_id"] = "SIMULATED_KNOX_PLAN_INTERPRETATION"
        request["client"]["scope"] = "PLAN_DERIVED_SIMULATED"
        request["planner"]["scope"] = "PLAN_DERIVED_SIMULATED"
        # Keep the shared/frozen catalogue unchanged. For this KNOX-only
        # vertical stage interpretation, express its local axes as 2.5 x 8 m
        # in a request-scoped policy snapshot.
        knox_policy = copy.deepcopy(policy)
        knox_policy["catalog"]["stage"]["width_m"] = 2.5
        knox_policy["catalog"]["stage"]["depth_m"] = 8.0
        knox_policy_sha = common.digest(knox_policy)
        request["client"]["policy_sha256"] = knox_policy_sha
        request["planner"]["policy_sha256"] = knox_policy_sha
        v["boundary_px"] = boundary_px
        v["origin_px"] = origin_px
        v["controls"] = [
            dict(a_px=[86.0,35.0], b_px=[607.0,35.0], distance_m=96.0*0.3048),
            dict(a_px=[622.0,51.0], b_px=[622.0,398.0], distance_m=64.0*0.3048),
        ]
        v["boundary_m"] = boundary_m
        # The ten small square symbols in the Event Space are transcribed as
        # fixed plan obstacles. Their size is approximate and explicitly
        # covered by simulated, not external, review evidence.
        columns=[]
        for row, cy in enumerate([116.0,332.0], start=1):
            for col, cx in enumerate([152.0,217.0,282.0,347.0,412.0], start=1):
                ring_px=fixtures.ring(cx-2.5,cy-2.5,5.0,5.0)
                columns.append(dict(instance_id=f"KNOX_PLAN_COLUMN_R{row}C{col}", class_name="column",
                    footprint_m=[to_m(pt) for pt in ring_px], status="fixed", review_status="approved",
                    protected=True, candidate_ref="PLAN_SYMBOL_TRANSCRIPTION_NOT_MODEL_CONFIRMED"))
        v["existing"] = columns
        # Designed equipment is new event supply; it is not misrepresented as
        # venue stock. Coordinates are in the plan-derived 72 ft x 64 ft hall.
        def metric_box(x,y,w,h):
            return [list(pt) for pt in box(x,y,x+w,y+h).exterior.coords]
        hall_w, hall_h = Polygon(boundary_m).bounds[2:4]
        placements=[
            # Vertical along the east/right side of the event hall. The
            # placement leaves at least 0.5 m to the buffet access reservation.
            dict(class_name="stage", ordinal=1, footprint_m=metric_box(hall_w-2.7, 2.5, 2.5, 8.0)),
            dict(class_name="buffet_counter", ordinal=1, footprint_m=metric_box(hall_w-2.9, 12.0, 2.5, 1.2)),
        ]
        request["placements"] = placements
        request = fixtures.seal(request, case)
        common.save(case/"REQUEST.json", request)
        spec = compiler.compile_scene(request, knox_policy)
        common.save(case/"SPEC.json", spec)
        independent_spec = oracle.validate_spec(request, spec, knox_policy)
        common.save(case/"INDEPENDENT_SPEC_CHECK.json", independent_spec)
        if spec.get("status") != "accepted" or not independent_spec.get("valid"):
            raise HTTPException(status_code=422, detail={"reason":"KNOX_PLAN_SPECIFICATION_NOT_ACCEPTED", "issues":spec.get("issues", []), "independent":independent_spec})
        result = bridge.execute(request, spec, result_dir, seed=20261017, policy=knox_policy)
        if result.get("status") != "success":
            return {"schema":"SCENE_COMPILER_HANDOFF_V1", "status":"non_success", "scope":"CONTROLLED_KNOX_PLAN_INTERPRETATION_SIMULATED_REVIEW_NOT_REAL_VENUE", "reason":result.get("reason"), "request":request, "spec":spec, "independent_spec":independent_spec, "result":result, "artifact_path":str(result_dir)}
        analysis=json.loads(KNOX_ANALYSIS.read_text(encoding="utf-8"))
        projection=dict(image_url="/knox-demo/KNOX_HALL.jpg", width_px=width_px, height_px=height_px,
            source_sha256=source_sha, decoded_model_source_sha256=analysis["candidate_bundle"]["source"]["sha256"],
            analysis_id=analysis["analysis_id"], scale_m_per_pixel=scale, origin_px=origin_px,
            boundary_px=boundary_px, pixel_controls=v["controls"], assumptions=[
                "96 ft x 64 ft overall printed drawing dimensions used as plan controls",
                "event-space boundary transcribed from drawing; not independently reviewed",
                "ten square symbols treated as fixed columns with approximate 5 px footprints",
                "stage shown vertically along the east/right side as a 2.5 m x 8 m request-scoped catalogue orientation; its position is a controlled design assumption",
                "doors/routes are not constraints in this optimizer; no access/safety validation",
                "simulated review and authority; not an as-built or approved venue Twin",
            ])
        common.save(result_dir/"SOURCE_PROJECTION.json", projection)
        return {"schema":"SCENE_COMPILER_HANDOFF_V1", "status":"success", "scope":"CONTROLLED_KNOX_PLAN_INTERPRETATION_SIMULATED_REVIEW_NOT_REAL_VENUE", "plan_projection":projection, "request":request, "spec":spec, "independent_spec":independent_spec, "result":result, "artifact_path":str(result_dir)}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"reason":"KNOX_PLAN_BRIDGE_EXECUTION_FAILED", "type":type(exc).__name__, "message":str(exc)}) from exc

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=8769)
    a=p.parse_args()
    uvicorn.run(app, host="127.0.0.1", port=a.port, log_level="info")

if __name__ == "__main__":
    main()
