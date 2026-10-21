"""Restart comparisons only from pre-existing frozen input manifest."""
from lab import *
import copy,csv,time,sqlite3,importlib.metadata,collections
events=guard();runtime,adapter=boot()
from repair import run as eag_run
from constraint_graph import build
from independent import verify_envelope
from conventional import run_standard
config=read(H/'EXPERIMENT_CONFIGURATION.json');METHODS=config['methods'];SEEDS=config['seeds'];EXPECTED=config['expectations']
manifest=read(H/'FROZEN_BENCHMARK_MANIFEST.json');units=manifest['units'];before=read(H/'PRESERVATION_BEFORE.json');receipt=read(H/'HTTP/TWIN_RECEIPT.json');binding=read(H/'REGISTERED_BASE_BINDING.json')
save('PROTOCOL_AMENDMENT_1.json',dict(reason='Independent conventional wrapper omitted result reasons in its envelope. First comparison stopped with KeyError; frozen inputs/setup unchanged. Add reasons and restart all comparisons in raw_final; preserve raw/failed logs. No policy, objectives, budget, scenario or label change.',old_source_freeze_sha256=sha(H/'PROTOCOL_SOURCE_FREEZE.json'),current_code={p.name:sha(p) for p in H.glob('*.py')},failed_search_evaluations=1200,failed_search_excluded_from_final_statistics=True,setup_evaluations_reused=4800))
source=(H/'benchmark.py').read_text(encoding='utf-8');source=source[source.index('records=[];failures=[];calltrace='):]
source=source.replace("H/'raw'","H/'raw_final'").replace("Path('raw')","Path('raw_final')")
exec(compile(source,str(H/'benchmark.py'),'exec'),globals())
