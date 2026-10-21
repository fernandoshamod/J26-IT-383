"""Read-only Step2 adapter, explicitly bound to this consolidated output root."""
from pathlib import Path
_source=Path(__file__).resolve().parent.parent/'PP1_REVIEWED_TWIN_SCENE_INTEGRATION_V1/adapter.py'
exec(compile(_source.read_text(encoding='utf-8'),str(_source),'exec'),globals())
