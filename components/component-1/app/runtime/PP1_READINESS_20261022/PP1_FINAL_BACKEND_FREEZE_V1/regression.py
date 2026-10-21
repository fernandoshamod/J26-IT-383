"""Original 49-case test source, final application factory, isolated outputs."""
from common import *
import platform
platform.uname();events=guard(allow_loopback=True)
sys.path.append(str(H.parent/'PP1_FINAL_MODEL_INTEGRATION_V1'))
from perception import backend_modules
backend_modules()
import support,api
from application import create_app
support.PACKAGE=H;api.create_app=create_app
source=H.parent/'PP1_EXECUTABLE_V1/tests_execution.py'
save('REGRESSION_SOURCE_BINDING.json',dict(source=str(source),sha256=sha(source),source_edits=0,factory='application.create_app',output_root=str(H)))
sys.argv=[str(source),'--output-name','REGRESSION_49_001']
try:exec(compile(source.read_text(encoding='utf-8'),str(source),'exec'),dict(__file__=str(source),__name__='__main__'))
finally:save('REGRESSION_GUARD.json',events)
