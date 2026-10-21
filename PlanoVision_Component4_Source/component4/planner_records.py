"""Local SQLite persistence. Financial inputs only, never model outputs or datasets."""
from contextlib import contextmanager
from datetime import date, datetime, timezone
import json
from pathlib import Path
import sqlite3
import uuid


class RecordError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def exact(value, fields):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise RecordError('Unexpected or missing record fields.')


def text(value, required=False):
    if not isinstance(value, str) or len(value) > 100 or (required and not value.strip()):
        raise RecordError('Text fields must be at most 100 characters; required fields cannot be blank.')
    return value.strip()


def valid_day(value, future=True):
    try:
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value or (future and parsed <= date.today()):
            raise ValueError()
    except (ValueError, TypeError):
        raise RecordError('Choose a valid future event date.') from None


class PlannerRecords:
    def __init__(self, path):
        self.path = Path(path)

    @contextmanager
    def connection(self, write=False):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            db.execute('CREATE TABLE IF NOT EXISTS records (id TEXT PRIMARY KEY, kind TEXT NOT NULL, data TEXT NOT NULL, revision INTEGER NOT NULL, active_date TEXT, deleted INTEGER NOT NULL DEFAULT 0)')
            db.execute('CREATE UNIQUE INDEX IF NOT EXISTS one_active_booking_per_day ON records(active_date) WHERE kind="booking" AND active_date IS NOT NULL')
            if write:
                db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except sqlite3.IntegrityError:
            db.rollback()
            raise RecordError('Already booked: another event occupies this date.', 409) from None
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def listing(self, kind):
        with self.connection() as db:
            rows = db.execute('SELECT * FROM records WHERE kind=? AND deleted=0 ORDER BY id', (kind,)).fetchall()
        return {'storage': 'sqlite', 'records': [json.loads(r['data']) for r in rows], 'revisions': {r['id']: r['revision'] for r in rows}}

    def write(self, kind, payload, identifier=None, revision=None, delete=False):
        with self.connection(write=True) as db:
            old = None
            if identifier:
                row = db.execute('SELECT * FROM records WHERE id=? AND kind=? AND deleted=0', (identifier, kind)).fetchone()
                if row is None:
                    raise RecordError('Record not found. Reload saved records.', 404)
                if type(revision) is not int or revision != row['revision']:
                    raise RecordError('Record changed in another session. Reload before editing.', 409)
                old = json.loads(row['data'])
            identifier = identifier or str(uuid.uuid4())
            now = datetime.now(timezone.utc).isoformat()
            if kind == 'booking':
                if delete:
                    data = {**old, 'status': 'cancelled'}
                else:
                    exact(payload, ('resource', 'date', 'label', 'event_type', 'client_name', 'client_contact', 'event_category', 'status'))
                    data = {k: text(v, k in ('resource', 'label')) for k, v in payload.items() if k != 'date'}
                    if data['event_type'] not in ('Wedding', 'Corporate', 'Unspecified') or data['status'] not in ('reserved', 'cancelled'):
                        raise RecordError('Invalid booking type or status.')
                    if old and data['resource'] != old['resource']:
                        raise RecordError('Venue changes require a new booking.')
                    valid_day(payload['date'], future=data['status'] == 'reserved')
                    data.update(date=payload['date'], id=identifier, created_at=old['created_at'] if old else now)
                active_day = data['date'] if data['status'] == 'reserved' else None
                removed = 0
            else:
                if delete:
                    data = old
                else:
                    exact(payload, ('name', 'client_name', 'plan'))
                    data = {'id': identifier, 'name': text(payload['name'], True), 'client_name': text(payload['client_name']),
                            'plan': payload['plan'], 'created_at': old['created_at'] if old else now, 'updated_at': now}
                active_day, removed = None, int(delete)
            encoded = json.dumps(data, allow_nan=False)
            if len(encoded.encode()) > 131072:
                raise RecordError('Record is too large.')
            if old:
                db.execute('UPDATE records SET data=?, revision=revision+1, active_date=?, deleted=? WHERE id=?', (encoded, active_day, removed, identifier))
            else:
                if delete:
                    raise RecordError('Missing record ID.')
                db.execute('INSERT INTO records VALUES (?,?,?,?,?,0)', (identifier, kind, encoded, 1, active_day))
        return {**self.listing(kind), 'saved_id': identifier}

    def import_bookings(self, rows):
        if not isinstance(rows, list) or len(rows) > 200:
            raise RecordError('Import at most 200 browser records at a time.')
        result = []
        for row in rows:
            try:
                required = {'id', 'resource', 'date', 'label', 'event_type', 'status', 'created_at'}
                if not isinstance(row, dict) or not required <= row.keys() or set(row) - required - {'client_name', 'client_contact', 'event_category'}:
                    raise RecordError('Invalid legacy booking fields.')
                text(row['id'], True)
                valid_day(row['date'], future=False)
                datetime.fromisoformat(row['created_at'].replace('Z', '+00:00'))
                with self.connection(write=True) as db:
                    old = db.execute('SELECT data FROM records WHERE id=?', (row['id'],)).fetchone()
                    if old:
                        if json.loads(old['data']) != row:
                            raise RecordError('ID already exists with different details; browser copy retained.', 409)
                        result.append({'id': row['id'], 'status': 'already_imported'})
                        continue
                    if row['event_type'] not in ('Wedding', 'Corporate', 'Unspecified') or row['status'] not in ('reserved', 'cancelled'):
                        raise RecordError('Invalid legacy booking status/type.')
                    for key in ('resource', 'label', 'client_name', 'client_contact', 'event_category'):
                        if key in row:
                            text(row[key], key in ('resource', 'label'))
                    db.execute('INSERT INTO records VALUES (?,?,?,?,?,0)', (row['id'], 'booking', json.dumps(row), 1, row['date'] if row['status'] == 'reserved' else None))
                result.append({'id': row['id'], 'status': 'imported'})
            except (ValueError, TypeError, KeyError) as exc:
                result.append({'id': row.get('id', '') if isinstance(row, dict) else '', 'status': 'not_imported', 'reason': str(exc)})
        return {**self.listing('booking'), 'import_results': result}
