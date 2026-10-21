from common import *
sys.path.append(str(H.parent/'PP1_FINAL_MODEL_INTEGRATION_V1'))
source=H.parent/'PP1_FINAL_MODEL_INTEGRATION_V1/run_regression.py'
exec(compile(source.read_text(encoding='utf-8'),str(source),'exec'),dict(__file__=str(source),__name__='__main__'))
