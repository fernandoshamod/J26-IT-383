"""Transport-independent dashboard adapter; no HTTP server or trained model."""
from .engine import evaluate, what_if

def dashboard_request(config, payload, *, operation='calculate'):
    if not isinstance(payload, dict):
        raise ValueError('request_must_be_an_object')
    allowed = {'event_type', 'changes'} if operation == 'what-if' else {'event_type', 'overrides'}
    if set(payload) - allowed:
        raise ValueError('unsupported_request_fields:client_cannot_set_mode_approvals_or_outcomes')
    event = payload.get('event_type')
    if event not in {'Wedding', 'Corporate'}:
        raise ValueError('unsupported_event_type')
    changes = payload.get('changes' if operation == 'what-if' else 'overrides', {})
    if not isinstance(changes, dict):
        raise ValueError('changes_must_be_an_object')
    if operation == 'calculate':
        return evaluate(config, event, changes, mode='live')
    if operation == 'what-if':
        return what_if(config, event, changes, mode='live')
    raise ValueError('unsupported_operation')
