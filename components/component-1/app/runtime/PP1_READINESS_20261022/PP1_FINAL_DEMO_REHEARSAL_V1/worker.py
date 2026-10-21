"""One bounded controlled lifecycle, using existing algorithms and checkers."""
import copy, hashlib, importlib.metadata, json, os, platform, sqlite3, sys, time, traceback
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / sys.argv[1]
assert OUT.is_dir() and OUT.parent == HERE
sys.dont_write_bytecode = True
flags = dict(PYTHONDONTWRITEBYTECODE="1", MPLBACKEND="Agg",
    MPLCONFIGDIR=str(OUT/"matplotlib_config"), TEMP=str(OUT/"tmp"),
    TMP=str(OUT/"tmp"), TMPDIR=str(OUT/"tmp"), YOLO_OFFLINE="true",
    YOLO_AUTOINSTALL="false", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
    HF_HUB_DISABLE_TELEMETRY="1", WANDB_MODE="offline", WANDB_DISABLED="true",
    PIP_NO_INDEX="1", PIP_DISABLE_PIP_VERSION_CHECK="1",
    YOLO_CONFIG_DIR=str(OUT/"ultralytics_config"), TORCH_HOME=str(OUT/"torch_cache"),
    HF_HOME=str(OUT/"hf_cache"))
os.environ.update(flags)
(OUT/"tmp").mkdir()
# Windows platform discovery may run the read-only cmd /c "ver" command.
# Resolve standard-library platform metadata before installing the no-child guard.
# Research imports and all search execute after the guard is installed.
platform_metadata = platform.uname()._asdict()

def save(name, value):
    p = OUT / name
    assert p.resolve().is_relative_to(OUT)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("x", encoding="utf-8") as f:
        json.dump(value, f, indent=2, allow_nan=False)

network = []; denied = []; subprocesses = []
null_device = str(Path(os.devnull).resolve()).casefold()

def check_write(path, event):
    if isinstance(path, (str, bytes, os.PathLike)):
        p = Path(os.fsdecode(path)).resolve()
        if str(p).casefold() != null_device and not p.is_relative_to(OUT):
            denied.append(dict(event=event, path=str(p)))
            raise RuntimeError("WRITE_OUTSIDE_REHEARSAL:" + str(p))

def audit(event, args):
    if event in {"socket.connect","socket.connect_ex","socket.getaddrinfo",
                 "socket.gethostbyname","socket.gethostbyaddr","socket.sendto",
                 "socket.sendmsg","socket.bind"}:
        network.append(dict(event=event, args=repr(args)[:500]))
        raise RuntimeError("PYTHON_NETWORK_ATTEMPT_DENIED:" + event)
    if event == "subprocess.Popen":
        subprocesses.append(repr(args)[:500])
        raise RuntimeError("UNEXPECTED_CHILD_PROCESS")
    if event in {"os.mkdir","os.remove","os.rmdir"}:
        check_write(args[0], event)
    if event == "os.rename":
        check_write(args[0], event); check_write(args[1], event)
    if event == "open":
        p, mode, bits = args
        writing = (isinstance(mode,str) and any(x in mode for x in "wax+")) or (
            isinstance(bits,int) and bits & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
        if writing: check_write(p, event)
    if event == "sqlite3.connect": check_write(args[0], event)

sys.addaudithook(audit)
save("ENVIRONMENT.json", dict(argv=sys.argv, cwd=str(Path.cwd()), python=sys.version,
     executable=sys.executable, flags=flags, platform_metadata=platform_metadata,
     platform_discovery_before_guard=True, shared_kernels=["Shapely","SciPy"],
     network_limit="Python audit-hook enforcement, not complete OS/native network isolation."))
save("LIBRARY_VERSIONS.json", {p:importlib.metadata.version(p) for p in
     ["numpy","scipy","shapely","pymoo","pydantic","matplotlib","Pillow"]})

trace = Counter()
watched = [str(HERE.parent/x).casefold() for x in
           ["PP1_EAG_APR_IMPLEMENTATION_V1","PP1_EVENT_SCENE_INTELLIGENCE_V1","PP1_EXECUTABLE_V1"]]
def profile(frame, event, arg):
    if event != "call": return
    filename = frame.f_code.co_filename
    key = filename.casefold()
    if any(key.startswith(p) for p in watched) or ("pymoo" in key and frame.f_code.co_name=="minimize"):
        trace[(filename, frame.f_code.co_name)] += 1

branches = []; responses = {}; approved_ref = None
start = time.perf_counter()
try:
    sys.path.insert(0, str(HERE.parent/"PP1_EAG_APR_IMPLEMENTATION_V1"))
    sys.setprofile(profile)
    import runtime
    from repair import run, make_reference
    from scenarios import initial, change
    from independent import verify_candidate, verify_envelope
    # Existing common/bridge guards remain enabled but now enforce this run root.
    # POLICY, source module paths, compiler, gates and optimizer functions stay unchanged.
    runtime.HERE = OUT
    runtime.common.HERE = OUT
    runtime.bridge.HERE = OUT
    save("OUTPUT_RELOCATION.json", dict(
         technique="Existing in-memory runtime/common/bridge HERE relocation",
         new_output_root=str(OUT), original_scene_policy=str(runtime.SCENE/"profiles.json"),
         original_backend=str(runtime.BACKEND), file_edits=False,
         authorization_source_validity_and_permission_checks_changed=False))

    def branch(name, packet, reference, expected, operation, evaluations, reason=None):
        folder = OUT / name
        t = time.perf_counter()
        rec = dict(branch=name, verdict="NOT_RUN", input_source="Fresh existing controlled fixture/change functions",
                   expected_status=expected, expected_operation=operation)
        branches.append(rec)
        try:
            response, graph = run(packet, folder, "EAG", 20261017, reference)
            responses[name] = response
            assert response["status"] == expected, (name, response["status"])
            assert response["operation"] == operation
            assert response["optimizer_evaluations"] == evaluations
            if reason: assert reason in [r["code"] for r in response["reasons"]]
            envelope = verify_envelope(packet, response, reference)
            assert envelope["valid"], envelope
            replay = {}
            if expected == "eligible":
                assert response["candidate_layouts"]
                for layout in response["candidate_layouts"]:
                    v = verify_candidate(packet, response["spec"], layout,
                        response["initialization_centers_m"], reference,
                        packet["context"]["requested_group"] if operation=="SELECTIVE_SINGLETON" else None)
                    assert v["valid"] and v == response["validation"][layout["layout_id"]]
                    replay[layout["layout_id"]] = v
            else:
                assert not response["candidate_layouts"] and not response["selected_ids"]
                assert response["optimizer_calls"] == 0 and evaluations == 0
            # Read the actual persisted database row, not a generated summary.
            dbpath = folder / "assurance.sqlite3"
            assert dbpath.is_file()
            with sqlite3.connect(dbpath) as db:
                rows = db.execute("SELECT input_json,response_json,sha256 FROM records").fetchall()
            assert len(rows) == 1
            stored_packet, stored_response = map(json.loads, rows[0][:2])
            assert stored_packet == packet and stored_response == response
            assert rows[0][2] == runtime.digest(response)
            native = None
            native_db = folder/"ACTUAL_SEARCH/scene.sqlite3"
            if native_db.is_file():
                with sqlite3.connect(native_db) as db:
                    rr = db.execute("SELECT request,spec,response,sha FROM results").fetchall()
                assert len(rr)==1
                nr, ns, nresponse = map(json.loads, rr[0][:3])
                assert nr == packet["scene"] and ns == response["spec"]
                assert rr[0][3] == runtime.digest(nresponse)
                nv = runtime.oracle.validate_result(nr,ns,nresponse)
                assert nv["valid"], nv
                native = dict(valid=True, sha256=rr[0][3], independent_result=nv)
            save(name+"/POST_READBACK_VERIFICATION.json", dict(valid=True,
                envelope=envelope, raw_candidate_replay=replay,
                sqlite=dict(valid=True, rows=1, exact_input=True, exact_response=True,
                            sha256=rows[0][2], native_scene_sqlite=native),
                reference_sha256=runtime.digest(reference["layout"]) if reference else None))
            rec.update(verdict="PASS" if expected=="eligible" else
                       "EXPECTED_PENDING" if expected=="pending" else "EXPECTED_REFUSAL",
                       status=response["status"], operation=response["operation"],
                       optimizer_evaluations=response["optimizer_evaluations"],
                       optimizer_calls=response["optimizer_calls"],
                       optimizer_seconds=response["optimizer_seconds"],
                       candidate_count=len(response["candidate_layouts"]),
                       material_menu_count=len(response["selected_ids"]),
                       selected_ids=response["selected_ids"], reasons=response["reasons"],
                       independent_validation=True, exact_sqlite_readback=True,
                       xai_valid=True, fallback=response["fallback"])
            print(name, rec["verdict"], evaluations, "evaluations", flush=True)
            return response, graph
        except BaseException as exc:
            rec.update(verdict="FAIL", exception=type(exc).__name__, message=str(exc))
            save(name+"_FAILURE.json", dict(**rec, traceback=traceback.format_exc()))
            raise
        finally:
            rec["wall_seconds_including_replay"] = time.perf_counter()-t

    base = initial(OUT/"BASE_INPUT",32,24)
    response, graph = branch("A_INITIAL", base, None,"eligible","FULL_RECOMPUTATION",1200)
    ref = make_reference(base["scene"],response,graph,OUT/"A_INITIAL")
    save("INITIAL_REFERENCE.json",ref)
    context = copy.deepcopy(base["context"])
    context.update(version=2, reference_sha256=runtime.digest(ref["layout"]),
                   allowed_groups=sorted(ref["layout"]["group_centers_m"]))
    approved = runtime.seal_packet(base["scene"], context, OUT/"SIMULATED_LAYOUT_APPROVAL")
    response, graph = branch("B_SIMULATED_APPROVAL", approved,ref,"eligible","REVALIDATE_EXISTING_POOL",0)
    ref.update(certificate=response["certificate"],graph=graph,pool=response["candidate_layouts"])
    approved_ref = ref
    save("APPROVED_REFERENCE.json",ref)
    save("APPROVAL_BINDING.json",dict(
         scope="SIMULATED_FIXTURE_NOT_AUTHENTICATED_AUTHORITY", real_consent=False,
         selected_layout_id=ref["layout"]["layout_id"], layout_sha256=runtime.digest(ref["layout"]),
         scene_sha256=runtime.digest(approved["scene"]), context=approved["context"],
         authority=approved["authority"], certificate_sha256=response["certificate"]["certificate_sha256"],
         note="One explicit fresh fixture authority record. Full permissions are recorded; singleton runtime locks all non-target groups."))
    for name,case,expected,operation,ev,reason in [
        ("C_UNCHANGED_REUSE","unchanged","eligible","REVALIDATE_EXISTING_POOL",0,None),
        ("D_AUTHORIZED_SINGLETON","authorized_singleton_repair","eligible","SELECTIVE_SINGLETON",1680,None),
        ("E_MANDATORY_DANCE","mandatory_dance_added","eligible","FULL_RECOMPUTATION",1200,None),
        ("F_UNAUTHORIZED_STAGE","unauthorized_stage_relocation","refused","REFUSE",0,"PROTECTED_OR_UNAUTHORIZED_STOCK_MOVE"),
        ("G_MISSING_METRIC","missing_metric_verification","pending","REFUSE",0,"VENUE_REVIEW_REQUIRED")]:
        packet = change(case, approved, ref, OUT/"CHANGES"/case)
        branch(name,packet,ref,expected,operation,ev,reason)
    assert responses["E_MANDATORY_DANCE"]["fallback"]
    assert "dancing" in responses["E_MANDATORY_DANCE"]["spec"]["functions"]
    assert sum(r["optimizer_evaluations"] for r in branches)==4080
    assert sum(r["optimizer_calls"] for r in branches)==3
    sys.setprofile(None)

    # Scientific plots: exact returned object polygons and separate zone records.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as Patch
    figures = OUT/"figures"; figures.mkdir()
    singleton = responses["D_AUTHORIZED_SINGLETON"]
    chosen = max(singleton["candidate_layouts"], key=lambda l:singleton["validation"][l["layout_id"]]["stable_group_relocation_m"])
    packet = runtime.read(OUT/"D_AUTHORIZED_SINGLETON/INPUT.json")
    target = packet["context"]["requested_group"]
    def draw(ax, layout, title):
        boundary = approved["scene"]["venue"]["boundary_m"]
        x,y = zip(*boundary); ax.plot(x,y,color="#1d2830")
        for ob in layout["objects"]:
            color = "#1b9e91" if ob["group_id"]==target else {
                "stage":"#9869b0","buffet_counter":"#d3943b","round_table":"#477b9e",
                "chair":"#a8bbc9"}.get(ob["class"],"#a8bbc9")
            ax.add_patch(Patch(ob["footprint_coordinates_m"],facecolor=color,edgecolor="white",linewidth=.35))
        for z in layout["zones"]:
            if z["exclusive"]:
                ax.add_patch(Patch(z["footprint_m"],facecolor="none",edgecolor="#ce4660",hatch="//"))
                xy=z["footprint_m"][0]; ax.text(xy[0],xy[1],z["zone_id"],fontsize=6)
        ax.set_aspect("equal");ax.set_xlim(-.5,32.5);ax.set_ylim(-.5,24.5)
        ax.set_title(title,fontsize=10);ax.set_xlabel("x (m)");ax.set_ylabel("y (m)")
    fig,axes=plt.subplots(1,2,figsize=(12,5.5))
    draw(axes[0],ref["layout"],"Fresh simulated approved reference")
    draw(axes[1],chosen,"Actual singleton alternative "+chosen["layout_id"])
    fig.suptitle("Supported singleton adaptation: unchanged non-target individual polygons")
    fig.text(.5,.02,"Controlled 32 x 24 m, 80 guests; 1680 evaluations. Largest-relocation returned option shown. No transport-path claim.",ha="center",fontsize=8)
    fig.tight_layout(rect=(0,.05,1,.94));fig.savefig(figures/"SINGLETON_BEFORE_AFTER.png",dpi=160);plt.close(fig)
    dance=responses["E_MANDATORY_DANCE"]
    dl=next(l for l in dance["candidate_layouts"] if l["layout_id"]==dance["selected_ids"][0])
    fig,axes=plt.subplots(1,2,figsize=(12,5.5))
    draw(axes[0],ref["layout"],"Same approved reference, before independent change")
    draw(axes[1],dl,"Mandatory dance: actual full-recomputation option")
    fig.suptitle("Mandatory dance zone: full recomputation, not selective multi-group repair")
    fig.text(.5,.02,"Hatched geometry represents declared exclusive zones, not physical equipment. All returned candidates checked; 1200 evaluations.",ha="center",fontsize=8)
    fig.tight_layout(rect=(0,.05,1,.94));fig.savefig(figures/"DANCE_FULL_RECOMPUTATION.png",dpi=160);plt.close(fig)
    save("FIGURE_BINDINGS.json",dict(
         singleton=dict(reference_sha256=runtime.digest(ref["layout"]),layout_id=chosen["layout_id"],layout_sha256=runtime.digest(chosen),target=target),
         dance=dict(reference_sha256=runtime.digest(ref["layout"]),layout_id=dl["layout_id"],layout_sha256=runtime.digest(dl)),
         files=["figures/SINGLETON_BEFORE_AFTER.png","figures/DANCE_FULL_RECOMPUTATION.png"]))
    verdict = all(b["verdict"] in ("PASS","EXPECTED_REFUSAL","EXPECTED_PENDING") for b in branches)
    save("LIFECYCLE_RESULT.json",dict(passed=verdict,branches=branches,
         total_optimizer_evaluations=sum(b["optimizer_evaluations"] for b in branches),
         actual_search_calls=sum(b["optimizer_calls"] for b in branches),
         successful_candidate_occurrences=sum(b["candidate_count"] for b in branches if b["verdict"]=="PASS"),
         elapsed_seconds=time.perf_counter()-start, new_perception_execution=False,
         repeat_occurrences_are_not_independent_experiments=True,
         real_approval=False, originality="UNRESOLVED"))
except BaseException:
    sys.setprofile(None)
    save("UNHANDLED_FAILURE.json",dict(traceback=traceback.format_exc(),branches=branches))
    traceback.print_exc()
    raise
finally:
    sys.setprofile(None)
    save("GUARD_EVENTS.json",dict(network_attempts=network,denied_writes=denied,
         child_process_attempts=subprocesses,
         limitation="Python instrumentation cannot prove absence of native/OS-level network or filesystem activity."))
    save("LOCAL_CALL_TRACE.json",[dict(path=p,function=f,calls=n) for (p,f),n in sorted(trace.items())])
