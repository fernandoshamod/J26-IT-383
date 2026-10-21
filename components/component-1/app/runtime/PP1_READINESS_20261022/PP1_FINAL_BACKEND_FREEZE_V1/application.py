"""Stable factory. One pinned registry, same verified API contracts and models."""
from common import *
import threading
from runtime_check import verify
sys.path.append(str(H.parent/'PP1_FINAL_MODEL_INTEGRATION_V1'))
from integrated_api import create_app as integrated_factory
_FACTORY_LOCK=threading.RLock()
def create_app(db_path):
 proof=verify()
 with _FACTORY_LOCK:app=integrated_factory(db_path)
 app.state.backend_baseline='PP1_FINAL_BACKEND_FREEZE_V1'
 app.state.runtime_verification=proof
 # Do not alter 1.1.0 paths or response schemas. Scene/EAG is a CLI contract,
 # not falsely advertised as a new frontend HTTP route.
 return app
