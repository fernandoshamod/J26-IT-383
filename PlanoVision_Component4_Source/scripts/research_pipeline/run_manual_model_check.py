"""Interactive terminal runner using existing checksum-verified models."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from component4.manual_model_check import main

if __name__=='__main__':main()
