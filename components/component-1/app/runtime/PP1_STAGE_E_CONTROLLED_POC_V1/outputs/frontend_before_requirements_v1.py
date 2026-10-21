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