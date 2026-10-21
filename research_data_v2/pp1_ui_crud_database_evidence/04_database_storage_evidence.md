# 04 Database storage evidence

## Database

- Technology: SQLite 3, Python standard-library `sqlite3`.
- File: `D:\Vendor-Intelligence-System\backend\planovision.db`.
- Connection code: `backend/db.py`, using `DATABASE_PATH` and `_connect()`.
- Table: `events`.
- User-entered fields are stored as columns; `required_services` is stored as JSON text and decoded on API read.

## Observed lifecycle

A temporary test event was created, updated, used for recommendation generation, then deleted. Observed output:

```json
{"created_id":"USER-33E229C78EBE","read_guest_count":50,"updated_guest_count":60,"recommendation_event_id":"USER-33E229C78EBE","packages":2,"deleted":true}
```

A second temporary event was created, the backend was stopped and started, and the record was read successfully:

```json
{"event_id":"USER-6708CFCD7323","survived_restart":true,"list_count":1,"db_path":"D:\\Vendor-Intelligence-System\\backend\\planovision.db"}
```

The test records were removed after verification. The SQLite file remains because it contains the schema and is the demonstration database.

## Inspect directly

```powershell
cd D:\Vendor-Intelligence-System
& .\venv\Scripts\python.exe -c "import sqlite3; c=sqlite3.connect('backend/planovision.db'); print(c.execute(\"select name, sql from sqlite_master where type='table'\").fetchall()); print(c.execute('select * from events').fetchall())"
```

No secrets or personal information were used. This database has no authentication or ownership boundary.
