"""Start the project-owned official CPU runtime; never pull models implicitly."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from .local_llm_report import ROOT,local_request,LLMUnavailable,status

RUNTIME=ROOT/'work/ollama_cpu_0_40_5'


def verified_executable():
    manifest=json.loads((RUNTIME/'DOWNLOAD_MANIFEST.json').read_text())
    if manifest['version']!='0.40.5' or manifest['url']!='https://github.com/ollama/ollama/releases/download/v0.40.5/ollama-windows-amd64.zip':raise ValueError('unrecognized_local_runtime_provenance')
    for name,info in manifest['files'].items():
        file=(RUNTIME/name).resolve()
        if not file.is_relative_to(RUNTIME.resolve()) or hashlib.sha256(file.read_bytes()).hexdigest()!=info['sha256']:raise ValueError('local_runtime_file_hash_mismatch')
    exe=RUNTIME/'ollama.exe'
    if not {'ollama.exe','lib/ollama/llama-server.exe'}<=set(manifest['files']):raise ValueError('missing_verified_executable_or_cpu_runner')
    return exe


def ensure_runtime():
    try:local_request('GET','/api/tags');return status()
    except LLMUnavailable:pass
    exe=verified_executable();env=dict(os.environ)
    env.update(OLLAMA_HOST='127.0.0.1:11434',OLLAMA_MODELS=str(ROOT/'work/ollama_models'),OLLAMA_NO_CLOUD='1',OLLAMA_VULKAN='false')
    flags=getattr(subprocess,'CREATE_NO_WINDOW',0)
    with (RUNTIME/'server.stdout.log').open('ab') as out,(RUNTIME/'server.stderr.log').open('ab') as err:
        process=subprocess.Popen([str(exe),'serve'],cwd=RUNTIME,env=env,stdout=out,stderr=err,creationflags=flags)
    for _ in range(20):
        if process.poll() is not None:raise RuntimeError('local_ollama_exited_check_runtime_logs')
        try:local_request('GET','/api/tags',timeout=1);return status()
        except LLMUnavailable:time.sleep(.25)
    raise RuntimeError('local_ollama_start_timeout')
