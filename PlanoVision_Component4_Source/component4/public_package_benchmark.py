"""Advertised package benchmarks, separate from the approved full-event engine.

This estimates a published per-person component, never a complete event budget
or a financial risk target. It does not enable the live financial engine.
"""
from datetime import date, timedelta
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from component4.engine import money, number


def load_evidence(config_path):
    config = json.loads(Path(config_path).read_text(encoding='utf-8'))
    project = Path(__file__).resolve().parents[1]
    evidence_path = (project / config['evidence_file']).resolve()
    if not evidence_path.is_relative_to(project):
        raise ValueError('evidence_outside_project')
    contents = evidence_path.read_bytes()
    if hashlib.sha256(contents).hexdigest() != config['evidence_sha256']:
        raise ValueError('evidence_hash_mismatch')
    evidence = json.loads(contents)
    if config.get('mode') != 'public_advertised_package_benchmark':
        raise ValueError('unsupported_benchmark_mode')
    if config.get('acceptance_scope') != 'working_evidence_only':
        raise ValueError('working_evidence_scope_required')
    return config, evidence


def estimate_package(evidence, evidence_id, guests, event_type, event_date=None):
    if isinstance(guests, bool) or not isinstance(guests, int) or guests <= 0:
        raise ValueError('guests_must_be_positive_integer')
    if event_type not in {'Wedding', 'Corporate'}:
        raise ValueError('unsupported_event_type')
    matches = [row for row in evidence['rates'] if row['Evidence_ID'] == evidence_id]
    if len(matches) != 1:
        raise ValueError('unknown_or_duplicate_evidence_id')
    row = matches[0]
    if row['Event_Scope'] != event_type:
        raise ValueError('package_event_scope_mismatch')
    if row['Currency'] != 'LKR' or row['Rate_Unit'] != 'person':
        raise ValueError('unsupported_rate_unit')
    if not number(row['Rate_LKR']) or row['Rate_LKR'] < 0:
        raise ValueError('invalid_published_rate')
    when = date.fromisoformat(event_date) if event_date is not None else None
    if when and row.get('Valid_Until') is not None:
        expires = date(1899, 12, 30) + timedelta(days=row['Valid_Until'])
        if when > expires:
            raise ValueError('event_after_published_expiry')
    if when and row.get('Valid_From') is not None:
        starts = date(1899, 12, 30) + timedelta(days=row['Valid_From'])
        if when < starts:
            raise ValueError('event_before_published_validity')
    if row.get('Minimum_Guests') is not None and guests < row['Minimum_Guests']:
        raise ValueError('below_published_guest_minimum')
    # This particular offer supports Sundays AND Poya days. Do not infer a
    # Poya calendar or silently apply its rate to arbitrary weekdays.
    if evidence_id == 'HOTEL-PUB-R005' and when and when.weekday() != 6:
        raise ValueError('non_sunday_offer_requires_separate_poya_confirmation')
    amount = money(Decimal(guests) * Decimal(str(row['Rate_LKR'])))
    service = row.get('Service_Charge_Points')
    unspecified = row.get('Unspecified_Surcharge_Points')
    for charge in (service, unspecified):
        if charge is not None and (not number(charge) or not 0 <= charge <= 100):
            raise ValueError('invalid_published_charge')
    if service is not None and unspecified is not None:
        raise ValueError('overlapping_charge_scope_requires_review')
    charge = service if service is not None else unspecified
    surcharge = None if charge is None else money(amount * Decimal(str(charge)) / 100)
    known = amount if surcharge is None else amount + surcharge
    warnings = [
        'Advertised package component only; not a full-event budget or observed outcome.',
        'Guest minimum, service coverage and event-date availability are not confirmed.',
        'Do not add bundled stage, furniture, venue or AV charges without a scope review.',
    ]
    if row['Price_Kind'] == 'Starting price':
        warnings.append('Starting price: exact event quotation may be higher.')
    if row.get('Tax_Rate_Points') is None:
        warnings.append('Tax breakdown unknown; do not interpret missing tax as zero.')
    if row.get('Valid_Until') is None:
        warnings.append('No published expiry captured; access date is not a validity date.')
    if unspecified is not None:
        warnings.append('Published +10% charge type is unspecified; it is not classified as tax or service charge.')
    if evidence_id == 'HOTEL-PUB-R005' and when is None:
        warnings.append('Sunday/Poya eligibility must be confirmed before using this offer.')
    return {
        'result_kind': 'public_advertised_package_benchmark',
        'is_trained_model_prediction': False,
        'is_observed_event_outcome': False,
        'eligible_as_financial_risk_training_record': False,
        'currency': 'LKR', 'evidence_id': evidence_id,
        'provider': row['Provider'], 'package': row['Package'],
        'event_type': event_type, 'planned_guests': guests, 'event_date': event_date,
        'published_rate_lkr_per_person': row['Rate_LKR'],
        'published_price_kind': row['Price_Kind'],
        'advertised_package_amount_lkr': float(amount),
        'published_charge_amount_lkr': None if surcharge is None else float(surcharge),
        'published_charge_kind': 'service_charge' if service is not None else 'unspecified_surcharge' if unspecified is not None else 'unresolved',
        'known_components_subtotal_lkr': float(known),
        'charge_calculation_assumption': None if surcharge is None else 'Published percentage applied once to the advertised base; tax-on-service rules remain unknown.',
        'confirmed_all_in_package_total_lkr': None,
        'complete_event_total_lkr': None,
        'actual_cost_lkr': None, 'profit_lkr': None, 'risk_labels': None,
        'source_url': row['Source_URL'], 'source_access_date': evidence['access_date'],
        'warnings': warnings,
    }
