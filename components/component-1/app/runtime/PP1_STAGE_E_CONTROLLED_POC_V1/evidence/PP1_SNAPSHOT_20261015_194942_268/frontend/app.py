import copy
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as PolygonPatch
import streamlit as st

POC = Path(__file__).resolve().parents[1]
PROJECT = POC.parent
sys.path.insert(0, str(POC / "backend"))

from permission_validator import (
    load_json,
    validate_config,
    check_action,
)

SOURCE = (
    PROJECT / "02_GENERATED_RESEARCH_DATA"
    / "STAGE_C_OBJECTS"
    / "C3_17_RENDERER_V3_MASTER_180"
    / "SB_0005_OUTDOOR_GARDEN_L_SHAPE.json"
)
CONFIG = POC / "config" / "planner_permissions_v2.json"

st.set_page_config(
    page_title="PP1 Planner Verification",
    page_icon="📐",
    layout="wide",
)

@st.cache_data
def load_baseline():
    return load_json(SOURCE), load_json(CONFIG)


def draw_scene(scene, selected_id):
    fig, ax = plt.subplots(figsize=(10, 6))

    boundary = scene.get("site_polygon_m", [])
    if len(boundary) >= 3:
        ax.add_patch(
            PolygonPatch(
                boundary,
                closed=True,
                fill=False,
                edgecolor="black",
                linewidth=2.5,
            )
        )

    for structure in scene["structural_geometry"]:
        for ring in structure.get("polygons_m", []):
            if len(ring) >= 3:
                ax.add_patch(
                    PolygonPatch(
                        ring,
                        closed=True,
                        facecolor="lightskyblue",
                        edgecolor="steelblue",
                        alpha=0.15,
                        linewidth=0.7,
                    )
                )

    for obj in scene["event_instances"]:
        oid = int(obj["instance_id"])
        selected = oid == selected_id
        color = (
            "tomato" if selected
            else "dimgray" if obj.get("fixed") is True
            else "mediumseagreen"
        )

        for ring in obj.get("polygons_m", []):
            if len(ring) < 3:
                continue
            ax.add_patch(
                PolygonPatch(
                    ring,
                    closed=True,
                    facecolor=color,
                    edgecolor=color,
                    alpha=0.75 if selected else 0.35,
                    linewidth=2 if selected else 0.8,
                )
            )

    ax.set_aspect("equal", adjustable="box")
    ax.autoscale_view()
    ax.set_xlabel("Synthetic generator metres: X")
    ax.set_ylabel("Synthetic generator metres: Y")
    ax.set_title("SB_0005 — Generator source geometry")
    ax.grid(alpha=0.2)
    return fig


st.title("PP1 — Planner Verification Gate v2")
st.caption(
    "Controlled synthetic demonstration only. "
    "Not real venue authorization or safety certification."
)

if not SOURCE.is_file() or not CONFIG.is_file():
    st.error("Required source or configuration file missing.")
    st.stop()

scene, baseline = load_baseline()
baseline_errors = validate_config(scene, baseline)

if baseline_errors:
    st.error("Baseline permission configuration invalid.")
    st.code("\n".join(baseline_errors))
    st.stop()

if "planner_v2" not in st.session_state:
    st.session_state.planner_v2 = copy.deepcopy(baseline)

current = st.session_state.planner_v2
current_errors = validate_config(scene, current)

left, right = st.columns([1.6, 1])

with right:
    st.subheader("Object review")

    objects = scene["event_instances"]
    ids = [int(x["instance_id"]) for x in objects]
    names = {
        int(x["instance_id"]): f"#{x['instance_id']} — {x['class']}"
        for x in objects
    }

    selected = st.selectbox(
        "Choose an object",
        ids,
        format_func=lambda oid: names[oid],
    )

    source_obj = next(
        x for x in objects
        if int(x["instance_id"]) == selected
    )
    existing = next(
        x for x in current["objects"]
        if int(x["instance_id"]) == selected
    )

    source_fixed = source_obj.get("fixed") is True

    st.write(
        "Source indication:",
        "**FIXED**" if source_fixed else "**NOT FIXED**",
    )
    st.write("Current review:", existing["planner_status"])

    statuses = [
        "unconfirmed", "fixed", "movable", "removable"
    ]

    with st.form(key=f"review_{selected}"):
        status = st.selectbox(
            "Planner-confirmed status",
            statuses,
            index=statuses.index(existing["planner_status"]),
        )
        reviewer = st.text_input(
            "Reviewer identifier (demo)",
            value=existing.get("approved_by") or "",
            disabled=(status == "unconfirmed"),
        )
        note = st.text_area(
            "Reason / review note",
            value=existing.get("approval_note") or "",
            disabled=(status == "unconfirmed"),
        )

        discrepancy = source_fixed and status in {
            "movable", "removable"
        }

        if discrepancy:
            st.warning(
                "Source marks this object fixed. "
                "Explicit discrepancy review is required."
            )

        reviewed = st.checkbox(
            "I reviewed the source-status discrepancy",
            value=bool(
                existing.get("source_conflict_reviewed")
            ) if discrepancy else False,
            disabled=not discrepancy,
        )

        submitted = st.form_submit_button(
            "Apply simulated planner decision"
        )

    if submitted:
        candidate = copy.deepcopy(current)
        entry = next(
            x for x in candidate["objects"]
            if int(x["instance_id"]) == selected
        )

        entry["planner_status"] = status
        entry["move_allowed"] = status == "movable"
        entry["remove_allowed"] = status == "removable"
        entry["approved_by"] = (
            reviewer.strip() if status != "unconfirmed" else None
        )
        entry["approval_note"] = (
            note.strip() if status != "unconfirmed" else None
        )
        entry["approval_scope"] = (
            "SYNTHETIC_DEMO_ONLY"
            if status != "unconfirmed" else None
        )
        entry["source_conflict_reviewed"] = (
            bool(reviewed) if discrepancy else False
        )

        errors = validate_config(scene, candidate)

        if errors:
            st.error("Decision rejected by backend:")
            st.code("\n".join(errors))
        else:
            st.session_state.planner_v2 = candidate
            current = candidate
            st.success("Simulated review accepted.")

    st.subheader("Backend permission decisions")

    for action in ("move", "remove"):
        result = check_action(
            scene, current, selected, action
        )
        st.write(
            f"**{action.upper()}:** "
            f"{'ALLOWED' if result['allowed'] else 'DENIED'} "
            f"— {result['reason']}"
        )

    if st.button("Reset all simulated reviews"):
        st.session_state.planner_v2 = copy.deepcopy(baseline)
        st.rerun()

with left:
    st.subheader("Synthetic venue")
    fig = draw_scene(scene, selected)
    st.pyplot(fig)
    plt.close(fig)

    st.caption(
        "Blue: generator-source structural polygons. "
        "Green: event footprints. Gray: source-fixed. "
        "Red: selected object. No geometry safety certification."
    )

st.divider()

a, b, c = st.columns(3)
a.metric("Structures", len(scene["structural_geometry"]))
b.metric("Event objects", len(scene["event_instances"]))
c.metric(
    "Simulated move approvals",
    sum(
        x["move_allowed"]
        for x in st.session_state.planner_v2["objects"]
    ),
)

if validate_config(scene, st.session_state.planner_v2):
    st.error("Current simulated permissions are invalid.")
else:
    st.success("Current permission configuration valid.")

st.info(
    "Demo approvals exist only in this Streamlit session. "
    "Source files and saved permission configuration remain unchanged. "
    "Geometry constraints and optimization are not implemented here."
)
# PP1_CLIENT_PLANNER_REQUIREMENTS_UI_V1
from requirements_v1 import validate_requirements

st.divider()
st.header("Event Requirements — Client & Planner")
st.caption(
    "Structured requirements for a controlled synthetic POC. "
    "Submitting does not run spatial optimization."
)

with st.form("event_requirements_v1"):
    client_col, planner_col = st.columns(2)

    with client_col:
        st.subheader("Client requirements")

        event_type = st.selectbox(
            "Event type",
            [
                "conference", "wedding", "concert",
                "exhibition", "corporate_event", "other"
            ]
        )

        guest_count = st.number_input(
            "Guest count",
            min_value=1,
            max_value=10000,
            value=80,
            step=1
        )

        required_chairs = st.number_input(
            "Required chairs",
            min_value=0,
            max_value=10000,
            value=28,
            step=1
        )

        required_tables = st.number_input(
            "Required round tables",
            min_value=0,
            max_value=10000,
            value=4,
            step=1
        )

        client_preference = st.text_area(
            "Client spatial preferences",
            value="Clear view of the stage"
        )

    with planner_col:
        st.subheader("Planner priorities")

        circulation = st.selectbox(
            "Circulation priority",
            ["low", "medium", "high"],
            index=2
        )

        visibility = st.selectbox(
            "Stage visibility priority",
            ["low", "medium", "high"],
            index=2
        )

        utilization = st.selectbox(
            "Space utilization priority",
            ["low", "medium", "high"],
            index=1
        )

        minimum_change = st.selectbox(
            "Minimum-change priority",
            ["low", "medium", "high"],
            index=2
        )

    submitted_requirements = st.form_submit_button(
        "Validate requirements"
    )

if submitted_requirements:
    client_input = {
        "event_type": event_type,
        "guest_count": int(guest_count),
        "required_objects": {
            "chair": int(required_chairs),
            "round_table": int(required_tables)
        },
        "preference": client_preference
    }

    planner_input = {
        "circulation_priority": circulation,
        "visibility_priority": visibility,
        "utilization_priority": utilization,
        "minimum_change_priority": minimum_change
    }

    result = validate_requirements(
        scene, client_input, planner_input
    )

    st.session_state["requirements_v1_result"] = result

if "requirements_v1_result" in st.session_state:
    result = st.session_state["requirements_v1_result"]

    if result["valid"]:
        st.success("Structured requirements validated by backend.")
    else:
        st.error("Requirements validation failed.")

    for error in result["errors"]:
        st.error(error)

    for warning in result["warnings"]:
        st.warning(warning)

    st.subheader("Structured backend output")
    st.json({
        "client": result.get("client"),
        "planner": result.get("planner"),
        "valid": result["valid"],
        "warnings": result["warnings"],
        "spatial_feasibility_checked": result.get(
            "spatial_feasibility_checked"
        ),
        "optimization_executed": result.get(
            "optimization_executed"
        )
    })

    st.info(
        "Backend input validation is not venue-capacity approval. "
        "Geometric feasibility, route safety and optimization "
        "are separate pending milestones."
    )

# PP1_NSGA2_RESULTS_UI_V1
st.divider()
st.header("NSGA-II — Computed Layout Alternatives")
st.caption(
    "Saved constrained NSGA-II results for one round table. "
    "Synthetic generator-local geometry, not a certified venue plan."
)

result_path = POC / "outputs" / "nsga2_round_table_v1.json"

if not result_path.is_file():
    st.warning("No saved optimization report available.")
else:
    optimization = load_json(result_path)
    alternatives = optimization.get("selected_alternatives", [])

    if optimization.get("scene_id") != scene.get("id"):
        st.error("Optimization report scene does not match venue.")
    elif not alternatives:
        st.warning("No feasible alternatives recorded.")
    else:
        st.write(
            "Algorithm:", optimization.get("algorithm"),
            "| Evaluations:", optimization.get("evaluations"),
            "| Returned solutions:",
            optimization.get("returned_feasible_nondominated_count")
        )

        labels = {
            "minimum_change": "A — Minimum change",
            "balanced": "B — Balanced trade-off",
            "maximum_clearance": "C — Maximum clearance",
        }

        options = list(range(len(alternatives)))
        choice = st.selectbox(
            "Select computed alternative",
            options,
            format_func=lambda i: labels.get(
                alternatives[i]["selection_label"],
                alternatives[i]["selection_label"]
            ),
        )

        selected_solution = alternatives[choice]
        oid = optimization["object_id"]
        original_object = next(
            (o for o in scene["event_instances"]
             if o["instance_id"] == oid),
            None
        )

        metric1, metric2, metric3 = st.columns(3)
        metric1.metric(
            "Relocation (synthetic m)",
            f"{selected_solution['relocation_synthetic_m']:.2f}"
        )
        metric2.metric(
            "Nearest protected clearance (synthetic m)",
            f"{selected_solution['nearest_protected_synthetic_m']:.2f}"
        )
        metric3.metric(
            "Selected alternative",
            f"{choice + 1} of {len(alternatives)}"
        )

        checks = selected_solution["checks"]
        failed_checks = [
            name for name, item in checks.items()
            if item.get("passed") is not True
        ]

        if len(checks) != 5 or failed_checks:
            st.error(
                "Recorded constraint checks are incomplete or failed. "
                "Do not treat this result as feasible."
            )
        else:
            st.success(
                "All five recorded candidate checks PASS. "
                "Route connectivity remains unverified."
            )

        if original_object is not None:
            fig, ax = plt.subplots(figsize=(10, 6))

            for ring in scene["site_polygon_m"]:
                if len(ring) >= 3:
                    ax.add_patch(PolygonPatch(
                        ring, fill=False,
                        edgecolor="black", linewidth=2
                    ))

            for structure in scene["structural_geometry"]:
                for ring in structure.get("polygons_m", []):
                    if len(ring) >= 3:
                        ax.add_patch(PolygonPatch(
                            ring, facecolor="lightskyblue",
                            edgecolor="steelblue", alpha=0.12
                        ))

            for obj_item in scene["event_instances"]:
                if obj_item["instance_id"] == oid:
                    continue
                for ring in obj_item["polygons_m"]:
                    ax.add_patch(PolygonPatch(
                        ring, facecolor="gray",
                        edgecolor="gray", alpha=0.30
                    ))

            for ring in original_object["polygons_m"]:
                ax.add_patch(PolygonPatch(
                    ring, facecolor="orange",
                    edgecolor="darkorange",
                    alpha=0.65, linewidth=2,
                    label="Original position"
                ))

            for ring in selected_solution["footprints_m"]:
                ax.add_patch(PolygonPatch(
                    ring, facecolor="mediumseagreen",
                    edgecolor="darkgreen",
                    alpha=0.75, linewidth=2,
                    label="Optimized position"
                ))

            ax.set_aspect("equal", adjustable="box")
            ax.autoscale_view()
            ax.grid(alpha=0.2)
            ax.set_xlabel("Synthetic generator metres — X")
            ax.set_ylabel("Synthetic generator metres — Y")
            ax.set_title(
                "Round Table #2 — Original vs NSGA-II proposal"
            )
            ax.legend(loc="best")

            st.pyplot(fig)
            plt.close(fig)

            st.caption(
                "Orange: original round table. "
                "Green: selected NSGA-II proposal. "
                "Gray: unchanged event objects. "
                "Blue: source structural polygons."
            )

        with st.expander("Detailed constraint evidence"):
            st.json(checks)

        st.subheader("Alternative comparison")
        rows = [
            {
                "Alternative": labels.get(
                    s["selection_label"],
                    s["selection_label"]
                ),
                "Relocation (synthetic m)":
                    s["relocation_synthetic_m"],
                "Clearance (synthetic m)":
                    s["nearest_protected_synthetic_m"],
                "Failed checks": sum(
                    check.get("passed") is not True
                    for check in s["checks"].values()
                ),
            }
            for s in alternatives
        ]
        st.dataframe(rows, hide_index=True)

        st.warning(
            "Only Round Table #2 was optimized, using simulated "
            "planner permission. Other 34 event objects stay unchanged. "
            "No real-world safety, topology or whole-layout "
            "certification is claimed."
        )

# PP1_CONFLICT_DIAGNOSIS_UI_V1
from requirement_conflicts_v1 import diagnose

st.divider()
st.header("Requirement & Permission Conflict Diagnosis")
st.caption(
    "Uses currently submitted client/planner requirements "
    "and simulated planner permissions."
)

requirements_result = st.session_state.get(
    "requirements_v1_result"
)

if requirements_result is None:
    st.info(
        "Submit the Client & Planner Requirements form first."
    )
else:
    if st.button("Diagnose submitted requirements"):
        diagnosis = diagnose(
            scene,
            st.session_state.planner_v2,
            requirements_result["client"],
            requirements_result["planner"],
        )
        st.session_state["conflict_diagnosis_v1"] = diagnosis

    if "conflict_diagnosis_v1" in st.session_state:
        diagnosis = st.session_state["conflict_diagnosis_v1"]

        if diagnosis["blocking_errors"]:
            st.error("Input or permission configuration errors detected.")
            for error in diagnosis["blocking_errors"]:
                st.error(error)

        if diagnosis["unresolved_requirements"]:
            st.warning(
                "Unresolved requirements found. "
                "Full requirement fulfillment cannot be claimed."
            )
            for issue in diagnosis["unresolved_requirements"]:
                st.write(
                    f"**{issue['class']}** — requested "
                    f"{issue['requested']}, existing "
                    f"{issue['existing']}, shortfall "
                    f"{issue['shortfall']}"
                )
        elif not diagnosis["blocking_errors"]:
            st.success(
                "No inventory shortfall detected in the "
                "submitted object counts."
            )

        st.write(
            "Currently authorized movable object IDs:",
            diagnosis["approved_movable_ids"]
        )

        st.json(diagnosis)

        st.info(
            "This diagnosis is not a spatial-feasibility "
            "or whole-layout optimization result. "
            "Resubmit and diagnose again after changing "
            "requirements or permissions."
        )

# PP1_RUN_PLANNING_UI_V1
from planning_workflow_v1 import run_planning

st.divider()
st.header("Run Planning — Controlled Synthetic POC")
st.caption(
    "Execute the backend using submitted Client/Planner "
    "requirements and current in-session permissions."
)

requirements = st.session_state.get("requirements_v1_result")

if requirements is None:
    st.info("Validate Client & Planner Requirements first.")
else:
    st.write(
        "Submitted event:",
        requirements["client"]["event_type"],
        "| Guests:",
        requirements["client"]["guest_count"]
    )
    st.write(
        "Submitted object requirements:",
        requirements["client"]["required_objects"]
    )

    if st.button("Run Planning", key="run_joint_planning"):
        with st.spinner("Evaluating authorized placements..."):
            planning_result = run_planning(
                scene,
                st.session_state.planner_v2,
                requirements["client"],
                requirements["planner"],
                max_objects=2
            )
            st.session_state["planning_result_v1"] = planning_result

    if "planning_result_v1" in st.session_state:
        result = st.session_state["planning_result_v1"]
        status = result["status"]

        st.subheader("Backend planning decision")

        if status == "CONTROLLED_PLACEMENTS_FOUND":
            st.success("Controlled joint placements found.")
        elif status == "BLOCKED_UNRESOLVED_REQUIREMENTS":
            st.warning(
                "Planning blocked: unresolved required objects."
            )
        else:
            st.warning(f"Planning status: {status}")

        for issue in result["diagnosis"].get(
            "unresolved_requirements", []
        ):
            st.write(
                f"{issue['class']}: "
                f"requested {issue['requested']}, "
                f"existing {issue['existing']}, "
                f"shortfall {issue['shortfall']}"
            )

        placements = result.get("placements", [])

        if status == "CONTROLLED_PLACEMENTS_FOUND":
            st.subheader("Computed joint layout")

            fig, ax = plt.subplots(figsize=(10, 6))

            for ring in scene["site_polygon_m"]:
                ax.add_patch(PolygonPatch(
                    ring, fill=False,
                    edgecolor="black", linewidth=2
                ))

            for structure in scene["structural_geometry"]:
                for ring in structure.get("polygons_m", []):
                    ax.add_patch(PolygonPatch(
                        ring,
                        facecolor="lightskyblue",
                        edgecolor="steelblue",
                        alpha=0.13
                    ))

            moved_ids = {
                p["instance_id"] for p in placements
            }

            for item in scene["event_instances"]:
                if item["instance_id"] in moved_ids:
                    color = "orange"
                else:
                    color = "gray"

                for ring in item["polygons_m"]:
                    ax.add_patch(PolygonPatch(
                        ring,
                        facecolor=color,
                        edgecolor=color,
                        alpha=0.32 if color == "gray" else 0.65
                    ))

            for placement in placements:
                for ring in placement["footprints_m"]:
                    ax.add_patch(PolygonPatch(
                        ring,
                        facecolor="mediumseagreen",
                        edgecolor="darkgreen",
                        linewidth=2,
                        alpha=0.8
                    ))

            ax.set_aspect("equal", adjustable="box")
            ax.autoscale_view()
            ax.grid(alpha=0.2)
            ax.set_xlabel("Synthetic generator metres — X")
            ax.set_ylabel("Synthetic generator metres — Y")
            ax.set_title(
                "Orange: original | Green: proposed | "
                "Gray: unchanged"
            )

            st.pyplot(fig)
            plt.close(fig)

            rows = []
            for p in placements:
                rows.append({
                    "Object ID": p["instance_id"],
                    "Class": p["class"],
                    "X offset": p["dx"],
                    "Y offset": p["dy"],
                    "Positions evaluated": p["candidates_tested"],
                    "Failed recorded checks": sum(
                        check.get("passed") is not True
                        for check in p["checks"].values()
                    ),
                })

            st.dataframe(rows, hide_index=True)

            st.info(
                "This is a deterministic joint placement POC, "
                "not multi-object NSGA-II. "
                "Full event fulfillment and route connectivity "
                "are not verified."
            )

        with st.expander("Planning diagnosis and result metadata"):
            st.json({
                "status": status,
                "diagnosis": result["diagnosis"],
                "placement_count": len(placements),
                "full_requested_plan_generated": result.get(
                    "full_requested_plan_generated"
                ),
                "route_connectivity_verified": result.get(
                    "route_connectivity_verified"
                ),
                "multi_object_nsga2_executed": result.get(
                    "multi_object_nsga2_executed"
                ),
            })

        st.caption(
            "Results are from the most recent Run Planning click. "
            "After changing planner approvals or requirements, "
            "validate requirements and run planning again."
        )

# PP1_MULTI_OBJECT_NSGA2_UI_V1
st.divider()
st.header("Multi-Object NSGA-II — Computed Alternatives")
st.caption(
    "Two-object synthetic optimization from a saved research run. "
    "Not the result of the current Run Planning button."
)

multi_path = POC / "outputs" / "multi_object_nsga2_v1.json"

if multi_path.is_file():
    multi = load_json(multi_path)
    choices = multi.get("selected_alternatives", [])

    if (
        multi.get("scene_id") != scene.get("id")
        or set(multi.get("object_ids", [])) != {2, 3}
    ):
        st.error("Saved optimization report identity mismatch.")
    elif not choices:
        st.warning("No optimizer alternatives available.")
    else:
        st.write(
            "Algorithm:", multi["algorithm"],
            "| Evaluations:", multi["evaluations"]
        )

        selected_index = st.selectbox(
            "Multi-object alternative",
            range(len(choices)),
            format_func=lambda i: choices[i]["label"],
            key="multi_nsga2_choice",
        )
        alternative = choices[selected_index]

        m1, m2 = st.columns(2)
        m1.metric(
            "Total relocation (synthetic m)",
            f"{alternative['total_relocation_synthetic_m']:.2f}"
        )
        m2.metric(
            "Minimum clearance (synthetic m)",
            f"{alternative['minimum_clearance_synthetic_m']:.2f}"
        )

        positions = alternative.get("positions", [])
        moved_ids = {p["instance_id"] for p in positions}
        checks = alternative.get("checks", {})

        valid_record = (
            moved_ids == {2, 3}
            and len(positions) == 2
            and all(
                checks.get(str(oid), {}).get("feasible") is True
                and len(
                    checks.get(str(oid), {}).get("checks", {})
                ) == 5
                for oid in moved_ids
            )
        )

        if not valid_record:
            st.error("Incomplete saved feasibility evidence.")
        else:
            st.success(
                "Both objects have five recorded candidate checks. "
                "Route topology is not verified."
            )

            fig, ax = plt.subplots(figsize=(10, 6))

            for ring in scene["site_polygon_m"]:
                ax.add_patch(PolygonPatch(
                    ring, fill=False,
                    edgecolor="black", linewidth=2
                ))

            for structure in scene["structural_geometry"]:
                for ring in structure["polygons_m"]:
                    ax.add_patch(PolygonPatch(
                        ring, facecolor="lightskyblue",
                        edgecolor="steelblue", alpha=0.13
                    ))

            for item in scene["event_instances"]:
                moved = item["instance_id"] in moved_ids
                for ring in item["polygons_m"]:
                    ax.add_patch(PolygonPatch(
                        ring,
                        facecolor="orange" if moved else "gray",
                        edgecolor="darkorange" if moved else "gray",
                        alpha=0.65 if moved else 0.30
                    ))

            for position in positions:
                for ring in position["footprints_m"]:
                    ax.add_patch(PolygonPatch(
                        ring, facecolor="mediumseagreen",
                        edgecolor="darkgreen",
                        alpha=0.80, linewidth=2
                    ))

            ax.set_aspect("equal", adjustable="box")
            ax.autoscale_view()
            ax.grid(alpha=0.2)
            ax.set_xlabel("Synthetic generator metres — X")
            ax.set_ylabel("Synthetic generator metres — Y")
            ax.set_title(
                "Orange: originals | Green: NSGA-II | "
                "Gray: unchanged"
            )
            st.pyplot(fig)
            plt.close(fig)

            st.dataframe([
                {
                    "Object": p["instance_id"],
                    "X offset": round(p["dx"], 3),
                    "Y offset": round(p["dy"], 3),
                }
                for p in positions
            ], hide_index=True)

        st.subheader("Baseline vs optimizer")
        comparison = [{
            "Method": "Deterministic baseline",
            "Relocation": multi["baseline"][
                "total_relocation_synthetic_m"
            ],
            "Clearance": multi["baseline"][
                "minimum_clearance_synthetic_m"
            ],
        }]
        comparison += [
            {
                "Method": x["label"],
                "Relocation": x[
                    "total_relocation_synthetic_m"
                ],
                "Clearance": x[
                    "minimum_clearance_synthetic_m"
                ],
            }
            for x in choices
        ]
        st.dataframe(comparison, hide_index=True)

        st.warning(
            "This is a separate saved NSGA-II experiment "
            "with simulated approvals for objects #2 and #3. "
            "It does not optimize the current submitted form, "
            "guest capacity, visibility or circulation priorities. "
            "No independent safety validation."
        )
else:
    st.warning("Multi-object NSGA-II report not found.")
