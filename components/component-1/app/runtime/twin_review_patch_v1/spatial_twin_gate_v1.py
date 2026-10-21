"""Stage D planner-reviewed metric twin contract gate.

This module NEVER interprets U-Net segmentation masks as approved geometry.
It creates a verified geometric *candidate* for Stage E, not safety approval.
Requires Shapely 2+. Use as a library: validate_and_normalize(review).
"""
import json
import math
import hashlib
import sys
from pathlib import Path
from shapely.geometry import Polygon, Point

CONTRACT = 'STAGE_D_REVIEWED_TWIN_V1'
SUPPORTED_STATUS = {'fixed', 'movable', 'uncertain'}


def _error(code):
    raise ValueError(code)


def _xy(value):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        _error('INVALID_POINT')
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in value):
        _error('INVALID_POINT')
    return [float(value[0]), float(value[1])]


def _ring(data, width, height):
    if not isinstance(data, list) or len(data) < 3:
        _error('INVALID_POLYGON')
    points = [_xy(p) for p in data]
    if any(x < 0 or y < 0 or x > width or y > height for x, y in points):
        _error('POLYGON_OUTSIDE_IMAGE')
    if points[0] == points[-1]:
        points = points[:-1]
    if len(points) < 3:
        _error('INVALID_POLYGON')
    shape = Polygon(points)
    if not shape.is_valid or shape.area <= 0:
        _error('INVALID_POLYGON')
    return shape


def validate_and_normalize(review, image_path=None):
    if not isinstance(review, dict) or review.get('contract_id') != CONTRACT:
        _error('INVALID_TWIN_CONTRACT')
    img = review.get('image')
    if not isinstance(img, dict):
        _error('IMAGE_METADATA_REQUIRED')
    w, h = img.get('width_pixels'), img.get('height_pixels')
    if any(type(z) is not int or z <= 0 for z in [w, h]):
        _error('INVALID_IMAGE_SIZE')
    if type(img.get('sha256')) is not str or len(img['sha256']) != 64:
        _error('IMAGE_HASH_REQUIRED')
    try:
        int(img['sha256'], 16)
    except ValueError:
        _error('IMAGE_HASH_INVALID')
    if image_path is not None:
        path = Path(image_path)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest().lower() != img['sha256'].lower():
            _error('IMAGE_HASH_MISMATCH')

    calibration = review.get('scale_calibration')
    if not isinstance(calibration, dict) or calibration.get('method') != 'two_point_known_distance':
        _error('SCALE_CALIBRATION_REQUIRED')
    a, b = _xy(calibration.get('point_a_px')), _xy(calibration.get('point_b_px'))
    if not all(0 <= p[0] <= w and 0 <= p[1] <= h for p in [a, b]):
        _error('CALIBRATION_OUTSIDE_IMAGE')
    pixels = math.dist(a, b)
    known = calibration.get('known_distance_m')
    if pixels <= 1 or isinstance(known, bool) or not isinstance(known, (int, float)) or not math.isfinite(known) or known <= 0:
        _error('INVALID_CALIBRATION_DISTANCE')
    metres_per_pixel = float(known) / pixels
    if metres_per_pixel < 0.0001 or metres_per_pixel > 100:
        _error('IMPLAUSIBLE_CALIBRATION_SCALE')

    if review.get('planner_review', {}).get('confirmed') is not True:
        _error('PLANNER_CONFIRMATION_REQUIRED')
    reviewer = review['planner_review'].get('reviewer_id')
    if not isinstance(reviewer, str) or not reviewer.strip():
        _error('REVIEWER_ID_REQUIRED')
    if review['planner_review'].get('metric_dimensions_reviewed') is not True:
        _error('METRIC_DIMENSIONS_REVIEW_REQUIRED')
    boundary = _ring(review.get('usable_boundary_px'), w, h)
    obstacles = review.get('objects', [])
    if not isinstance(obstacles, list):
        _error('INVALID_OBJECTS')
    ids = set()
    fixed_shapes = []
    normalized = []
    for ob in obstacles:
        if not isinstance(ob, dict) or not isinstance(ob.get('id'), str) or not ob['id'].strip():
            _error('INVALID_OBJECT_ID')
        oid = ob['id']
        if oid in ids:
            _error('DUPLICATE_OBJECT_ID')
        ids.add(oid)
        status = ob.get('status')
        if status not in SUPPORTED_STATUS:
            _error('INVALID_OBJECT_STATUS')
        footprint = _ring(ob.get('polygon_px'), w, h)
        if not boundary.covers(footprint):
            _error('OBJECT_OUTSIDE_USABLE_BOUNDARY')
        if status == 'uncertain':
            _error('UNRESOLVED_UNCERTAIN_GEOMETRY')
        if status == 'fixed':
            fixed_shapes.append((oid, footprint))
        normalized.append({'object_id': oid, 'class': str(ob.get('class', 'obstacle')),
                           'status': status,
                           'footprint_coordinates_m': [[round(x*metres_per_pixel, 8), round(y*metres_per_pixel, 8)] for x,y in footprint.exterior.coords]})
    for i in range(len(fixed_shapes)):
        for j in range(i+1,len(fixed_shapes)):
            if fixed_shapes[i][1].intersection(fixed_shapes[j][1]).area > 1e-8:
                _error('FIXED_OBJECTS_OVERLAP')

    # Provenance and experimental readiness must not be confused with real-world safety.
    result = {
        'contract_id': 'STAGE_D_METRIC_TWIN_V1',
        'venue_id': str(review.get('venue_id', '')),
        'image_sha256': img['sha256'].lower(),
        'metres_per_pixel': metres_per_pixel,
        'boundary_polygon_m': [[round(x*metres_per_pixel, 8), round(y*metres_per_pixel, 8)] for x,y in boundary.exterior.coords],
        'objects': normalized,
        'planner_review': {'confirmed': True, 'reviewer_id': reviewer.strip(), 'approval_origin': 'LOCAL_RESEARCH_INPUT_UNAUTHENTICATED'},
        'verification_flags': {
            'geometry_reviewed': True,
            'metric_scale_calibrated': True,
            'safety_certified': False,
            'route_connectivity_verified': False,
            'structural_ai_accuracy_verified': False,
            'stage_e_current_engine_accepts_real_twin': False
        }
    }
    return result


def main():
    if len(sys.argv) not in (3,4):
        raise SystemExit('Usage: python spatial_twin_gate_v1.py review.json output.json [image.png]')
    request, dest = Path(sys.argv[1]), Path(sys.argv[2])
    if dest.exists():
        raise FileExistsError(f'No overwrite: {dest}')
    review = json.loads(request.read_text(encoding='utf-8'))
    result = validate_and_normalize(review, sys.argv[3] if len(sys.argv) == 4 else None)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print('STAGE D METRIC TWIN GATE: PASS')
    print('Scale m/px:', result['metres_per_pixel'])
    print('Objects:', len(result['objects']))
    print('Stage E real twin acceptance: NO — adapter and generalization pending')
    print('Output:', dest)

if __name__ == '__main__':
    main()
