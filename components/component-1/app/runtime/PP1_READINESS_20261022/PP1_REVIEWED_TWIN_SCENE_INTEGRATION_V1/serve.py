from common import *
import argparse,platform
p=argparse.ArgumentParser();p.add_argument('--db',required=True);p.add_argument('--port',type=int,default=8765);a=p.parse_args()
platform.uname();sys.path.append(str(H.parent/'PP1_FINAL_MODEL_INTEGRATION_V1'))
from integrated_api import create_app
app=create_app(a.db)
import uvicorn
uvicorn.run(app,host='127.0.0.1',port=a.port,log_level='warning')
