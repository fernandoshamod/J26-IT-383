import copy
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as PolygonPatch
import streamlit as st

POC = Path(__file__).resolve().parents[1]
PROJECT = POC.parent
sys.path.insert(0, str(POC / "backend"))

from permission_validator import load_json, validate_config, check_action

SOURCE = (
    PROJECT / "02_GENERATED_RESEARCH_DATA"
    / "STAGE_C_OBJECTS"
    / "C3_17_RENDERER_V3_MASTER_180"
    / "SB_0005_OUTDOOR_GARDEN_L_SHAPE.json"
)
CONFIG = POC / "config" / "planner_permissions_v1.json"

st.set_page_config(
    page_title="PP1 Event Layout POC",
    page_icon="📐",
    layout="wide"
)

@st.cache_data
def load_data():
    return load_json(SOURCE), load_json(CONFIG)

def rings(item):
    return item.get("polygons_m", [])

def draw_scene(scene, selected_id):
    fig, ax = plt.subplots(figsize=(10, 6))

    boundary = scene.get("site_polygon_m", [])
    if boundary:
        ax.add_patch(PolygonPatch(
            boundary, closed=True, fill=False,
            edgecolor="black", linewidth=2.5
        ))

    for structure in scene["structural_geometry"]:
        for ring in rings(structure):
            if len(ring) >= 3:
                ax.add_patch(PolygonPatch(
                    ring, closed=True,
                    facecolor="lightskyblue",
                    edgecolor="steelblue",
                    alpha=0.15, linewidth=0.7
                ))

    for obj in scene["event_instances"]:
        oid = int(obj["instance_id"])
        selected = oid == selected_id
        color = (
            "tomato" if selected
            else "dimgray" if obj.get("fixed") is True
            else "mediumseagreen"
        )
        for ring in rings(obj):
            if len(ring) >= 3:
                ax.add_patch(PolygonPatch(
                    ring, closed=True,
                    facecolor=color,
                    edgecolor=color,
                    alpha=0.70 if selected else 0.35,
                    linewidth=2 if selected else 0.7
                ))
                if selected:
                    xs = [pt[0] for pt in ring]
                    ys = [pt[1] for pt in ring]
                    ax.text(
                        sum(xs) / len(xs),
                        sum(ys) / len(ys),
                        str(oid),
                        ha="center", va="center",
                        fontsize=10, fontweight="bold"
                    )

    ax.set_aspect("equal", adjustable="box")
    ax.autoscale_view()
    ax.set_xlabel("Synthetic generator metres — X")
    ax.set_ylabel("Synthetic generator metres — Y")
    ax.set_title("SB_0005: Source geometry (not AI-predicted structures)")
    ax.grid(alpha=0.2)
    return fig

st.title("PP1 — Venue Verification Prototype")
st.caption(
    "Controlled synthetic research POC. "
    "Not a real-venue safety or planner approval system."
)

if not SOURCE.is_file() or not CONFIG.is_file():
    st.error("Required source or permission configuration not found.")
    st.stop()

scene, baseline = load_data()
issues = validate_config(scene, baseline)
if issues:
    st.error("Permission configuration invalid.")
    st.code("\n".join(issues))
    st.stop()

if "simulated_permissions" not in st.session_state:
    st.session_state.simulated_permissions = copy.deepcopy(baseline)

current = st.session_state.simulated_permissions

left, right = st.columns([1.7, 1])

with right:
    st.subheader("Planner verification")
    objects = scene["event_instances"]
    ids = [int(o["instance_id"]) for o in objects]
    labels = {
        int(o["instance_id"]): (
            f"#{o['instance_id']} — {o['class']}"
        )
        for o in objects
    }

    selected_id = st.selectbox(
        "Choose event object",
        ids,
        format_func=lambda x: labels[x]
    )

    source_obj = next(
        o for o in objects
        if int(o["instance_id"]) == selected_id
    )
    entry = next(
        o for o in current["objects"]
        if int(o["instance_id"]) == selected_id
    )

    st.write("Source-fixed:", bool(source_obj.get("fixed")))
    st.write("Current status:", entry["planner_status"])

    if source_obj.get("fixed") is True:
        st.warning("Source-fixed object: relocation/removal locked.")
    else:
        action = st.radio(
            "Simulated planner decision",
            ["unconfirmed", "movable", "removable"],
            index=["unconfirmed", "movable", "removable"].index(
                entry["planner_status"]
                if entry["planner_status"] in
                ["unconfirmed", "movable", "removable"]
                else "unconfirmed"
            )
        )

        if st.button("Apply simulated decision"):
            entry["planner_status"] = action
            entry["move_allowed"] = action == "movable"
            entry["remove_allowed"] = action == "removable"
            entry["approved_by"] = (
                "SYNTHETIC_DEMO_PLANNER"
                if action != "unconfirmed" else None
            )
            entry["approval_note"] = (
                "In-session research simulation only"
                if action != "unconfirmed" else None
            )
            st.success("In-session simulation updated.")

    st.subheader("Backend action checks")
    for operation in ["move", "remove"]:
        result = check_action(
            scene, current, selected_id, operation
        )
        st.write(
            f"**{operation.upper()}:** "
            f"{'ALLOWED' if result['allowed'] else 'DENIED'} "
            f"— {result['reason']}"
        )

    if st.button("Reset all simulated decisions"):
        st.session_state.simulated_permissions = copy.deepcopy(baseline)
        st.rerun()

    current_issues = validate_config(scene, current)
    if current_issues:
        st.error("Validation errors:")
        st.code("\n".join(current_issues))
    else:
        st.success("Backend permission configuration valid")

with left:
    st.subheader("Synthetic venue source map")
    figure = draw_scene(scene, selected_id)
    st.pyplot(figure)
    plt.close(figure)
    st.caption(
        "Blue = source structural polygons; "
        "green = source event footprints; "
        "gray = source-fixed; red = selected. "
        "Polygon overlap and accessibility are not certified."
    )

st.divider()
a, b, c = st.columns(3)
a.metric("Structural entities", len(scene["structural_geometry"]))
b.metric("Event objects", len(scene["event_instances"]))
c.metric(
    "Simulated move authorizations",
    sum(bool(o["move_allowed"]) for o in current["objects"])
)

st.info(
    "This screen tests object identity and permissions only. "
    "It does not perform geometric safety checks or optimization. "
    "Decisions are stored only in the current UI session."
)