"""Compatibility test runner delegates to the one final entrypoint."""
import sys
from backend import main
sys.argv.insert(1,'serve')
main()
