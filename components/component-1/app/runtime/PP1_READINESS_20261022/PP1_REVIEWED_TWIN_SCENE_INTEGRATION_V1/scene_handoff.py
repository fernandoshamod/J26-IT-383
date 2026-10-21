"""Reusable controlled reviewed-Twin admission, with no optimizer invocation."""
import sys,argparse
from pathlib import Path
H=Path(__file__).resolve().parent
sys.path.insert(0,str(H.parent/'PP1_EAG_APR_IMPLEMENTATION_V1'))
import runtime
runtime.common.HERE=H;runtime.bridge.HERE=H
from adapter import read,convert
p=argparse.ArgumentParser();p.add_argument('--receipt',required=True);p.add_argument('--db',required=True);p.add_argument('--brief',required=True);p.add_argument('--out',required=True);a=p.parse_args()
convert(read(a.receipt),a.db,read(a.brief),Path(a.out))
print('Controlled registered HTTP Twin converted; no optimizer invoked')
