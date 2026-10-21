"""Step 3 interactive review for the EXISTING V2 Streamlit app.

Review coordinates refer to the original image pixels, not the preview size.
No automatic Stage E request is issued.
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw
import streamlit as st

try:
    from streamlit_image_coordinates import streamlit_image_coordinates
except ImportError:
    streamlit_image_coordinates = None


def _preview(image, state, scale):
    canvas = image.copy().convert('RGB')
    draw = ImageDraw.Draw(canvas)
    boundary = state['boundary']
    if len(boundary) >= 2:
        draw.line([tuple(p) for p in boundary], fill='#1878f4', width=5)
    if len(boundary) >= 3:
        draw.line([tuple(boundary[-1]), tuple(boundary[0])], fill='#1878f4', width=2)
    for p in boundary:
        x, y = p
        draw.ellipse((x-6,y-6,x+6,y+6), fill='#1878f4')
    for obj in state['objects']:
        pts = [tuple(p) for p in obj['polygon_px']]
        draw.polygon(pts, outline='#f59e0b', width=4)
    pending = state['pending']
    if len(pending) >= 2:
        draw.line([tuple(p) for p in pending], fill='#e11d48', width=4)
    for x,y in pending:
        draw.ellipse((x-5,y-5,x+5,y+5), fill='#e11d48')
    if len(state['calibration']) == 2:
        draw.line([tuple(p) for p in state['calibration']], fill='#16a34a', width=5)
    for x,y in state['calibration']:
        draw.ellipse((x-7,y-7,x+7,y+7), fill='#16a34a')
    if scale != 1:
        canvas = canvas.resize((round(canvas.width*scale),round(canvas.height*scale)))
    return canvas


def _blank():
    return {'boundary': [], 'calibration': [], 'pending': [], 'objects': [], 'last_click': None}


def render(root: Path):
    st.divider()
    st.header('Step 3 — Planner-Reviewed Metric Spatial Twin')
    st.caption('Manual geometry review over an AI-assisted floorplan. Not an automatic segmentation-to-geometry approval.')
    if streamlit_image_coordinates is None:
        st.error('Missing dependency: pip install streamlit-image-coordinates')
        return

    uploads = root / 'assets' / 'uploads'
    images = sorted(p for p in uploads.glob('venue_*') if p.suffix.lower() in ('.png','.jpg','.jpeg','.webp'))
    if not images:
        st.info('Save a floorplan in Step 1 first.')
        return
    selection = st.selectbox('Floorplan for planner review', options=images,
                             format_func=lambda p:p.name, key='twin_review_selected_image')
    raw = selection.read_bytes()
    image_hash = hashlib.sha256(raw).hexdigest()
    image = Image.open(selection).convert('RGB')
    prefix = f'twin_review_{image_hash[:16]}'
    if prefix not in st.session_state:
        st.session_state[prefix] = _blank()
    state = st.session_state[prefix]

    st.warning('U-Net segmentation is an unverified suggestion. Mark the actual usable boundary and scale from a trusted dimension. Reject ambiguous or unverified geometry.')
    mode = st.radio('Click action', ['Usable boundary','Known-distance points','Fixed/movable object'], horizontal=True, key=prefix+'_mode')
    max_w = 900
    scale = min(1.0, max_w / image.width)
    view = _preview(image, state, scale)
    st.caption(f'Original image: {image.width} × {image.height} pixels. Blue=boundary, green=calibration, red=pending object, orange=saved objects.')
    click = streamlit_image_coordinates(view, key=prefix+'_canvas')
    if click is not None:
        # Streamlit widget retains its last response on unrelated reruns.
        token = (int(click['x']), int(click['y']), mode)
        if token != state['last_click']:
            p = [min(image.width, max(0,round(int(click['x'])/scale))),
                 min(image.height,max(0,round(int(click['y'])/scale)))]
            if mode == 'Usable boundary':
                state['boundary'].append(p)
            elif mode == 'Known-distance points':
                if len(state['calibration']) < 2:
                    state['calibration'].append(p)
            else:
                state['pending'].append(p)
            state['last_click'] = token
            st.rerun()

    cols = st.columns(3)
    with cols[0]:
        st.write('Boundary vertices:', len(state['boundary']))
        if st.button('Undo boundary vertex',key=prefix+'_undo_boundary') and state['boundary']:
            state['boundary'].pop(); state['last_click'] = None; st.rerun()
    with cols[1]:
        st.write('Calibration points:',len(state['calibration']))
        if st.button('Reset calibration',key=prefix+'_reset_cal'):
            state['calibration'] = []; state['last_click'] = None; st.rerun()
    with cols[2]:
        st.write('Pending object vertices:',len(state['pending']))
        if st.button('Clear pending object',key=prefix+'_clear_object'):
            state['pending'] = []; state['last_click'] = None; st.rerun()

    distance = st.number_input('Known distance between green points (metres)',min_value=0.0,value=0.0,step=0.5,key=prefix+'_known_m')
    reviewer = st.text_input('Reviewer reference (local research only)',key=prefix+'_reviewer')
    st.caption('Review identity entered here is NOT authenticated planner approval.')
    obj_name = st.text_input('Object ID',value=f'OB_{len(state["objects"])+1:03d}',key=prefix+'_obj_id')
    obj_class = st.selectbox('Object class',['pillar','wall','stage','permanent_fixture','obstacle','other'],key=prefix+'_obj_class')
    obj_status = st.selectbox('Object status',['fixed','movable','uncertain'],key=prefix+'_obj_status')
    if st.button('Add marked object polygon',key=prefix+'_add_obj'):
        if len(state['pending']) < 3:
            st.error('Mark at least three object polygon vertices.')
        elif any(o['id'] == obj_name for o in state['objects']):
            st.error('Duplicate object ID.')
        else:
            state['objects'].append({'id':obj_name,'class':obj_class,'status':obj_status,'polygon_px':state['pending'].copy()})
            state['pending'] = []; state['last_click'] = None; st.rerun()
    if state['objects']:
        st.dataframe([{'id':o['id'],'class':o['class'],'status':o['status'],'vertices':len(o['polygon_px'])} for o in state['objects']],hide_index=True)
        if st.button('Remove last object',key=prefix+'_remove_last'):
            state['objects'].pop(); state['last_click'] = None; st.rerun()

    st.subheader('Validate and save reviewed geometry')
    dimensions_reviewed = st.checkbox('I checked the scale and venue boundary against a trustworthy dimension/source',value=False,key=prefix+'_dimension_review')
    confirmed = st.checkbox('I explicitly confirm the geometry review (not a safety or AI-accuracy certification)',value=False,key=prefix+'_confirmed')

    review = {
        'contract_id': 'STAGE_D_REVIEWED_TWIN_V1',
        'venue_id': selection.stem,
        'image': {'width_pixels': image.width, 'height_pixels': image.height, 'sha256': image_hash},
        'scale_calibration': {'method':'two_point_known_distance','point_a_px':state['calibration'][0] if len(state['calibration'])>0 else None,
                              'point_b_px':state['calibration'][1] if len(state['calibration'])>1 else None,
                              'known_distance_m': float(distance)},
        'usable_boundary_px': state['boundary'],
        'objects': state['objects'],
        'planner_review': {'confirmed':confirmed,'reviewer_id':reviewer,'metric_dimensions_reviewed':dimensions_reviewed}
    }
    if st.button('Validate and save metric Twin',type='primary',key=prefix+'_save'):
        backend = root / 'backend'
        sys.path.insert(0,str(backend))
        from spatial_twin_gate_v1 import validate_and_normalize
        try:
            result = validate_and_normalize(review, image_path=selection)
        except ValueError as exc:
            st.error('Geometry NOT accepted: '+str(exc))
        else:
            destination = root / 'outputs' / 'planner_reviewed_twins'
            destination.mkdir(parents=True,exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            review_file = destination / f'{selection.stem}_{stamp}_review.json'
            twin_file = destination / f'{selection.stem}_{stamp}_metric_twin.json'
            review_file.write_text(json.dumps(review,indent=2),encoding='utf-8')
            twin_file.write_text(json.dumps(result,indent=2),encoding='utf-8')
            st.success('Metric Spatial Twin saved; Stage E real-venue support remains blocked pending geometry generalization and route analysis.')
            st.json({'metric_twin_file':str(twin_file),'metres_per_pixel':result['metres_per_pixel'],
                     'geometry_reviewed':True,'real_world_safety_certified':False})

    with st.expander('Review payload preview'):
        st.json(review)
