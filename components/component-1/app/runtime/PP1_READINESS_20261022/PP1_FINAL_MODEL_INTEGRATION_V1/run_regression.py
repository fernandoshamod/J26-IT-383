"""Original 49-case suite, unchanged test source, output relocated and new analysis evidence."""
from common import *
import platform
platform.uname();events=guard(allow_loopback=True)
from perception import backend_modules
backend_modules()
import support,api
from integrated_api import create_app
support.PACKAGE=H;api.create_app=create_app
original=H.parent/'PP1_EXECUTABLE_V1/tests_execution.py'
save('REGRESSION_SOURCE_BINDING.json',{'test_source':str(original),'sha256':sha(original),'output_PACKAGE_binding':str(H),'api_factory':'integrated_api.create_app','pending_model_evidence':'outputs/PATH_A_REAL_MODEL from newly executed updated models','source_edits':0})
sys.argv=[str(original),'--output-name','REGRESSION_49_001']
try:exec(compile(original.read_text(encoding='utf-8'),str(original),'exec'),{'__file__':str(original),'__name__':'__main__'})
finally:save('REGRESSION_GUARD.json',events)
