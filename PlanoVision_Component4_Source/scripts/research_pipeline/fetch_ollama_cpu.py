"""Read official standalone ZIP directory with HTTP ranges; fetch CPU files only.

No cloud endpoint, installer execution, registry edits or automatic startup.
Downloaded entry CRCs are verified; a local SHA-256 inventory records provenance.
"""
import argparse
import io
import json
from pathlib import Path
import struct
import urllib.request
import zipfile
import zlib
import hashlib

ROOT=Path(__file__).resolve().parents[2]
URL='https://github.com/ollama/ollama/releases/download/v0.40.5/ollama-windows-amd64.zip'


class RemoteZip(io.RawIOBase):
    def __init__(self):
        with urllib.request.urlopen(urllib.request.Request(URL,method='HEAD'),timeout=30) as r:
            self.url=r.geturl();self.size=int(r.headers['Content-Length'])
        self.pos=0
    def seekable(self):return True
    def readable(self):return True
    def tell(self):return self.pos
    def seek(self,n,whence=0):
        self.pos=n if whence==0 else self.pos+n if whence==1 else self.size+n
        return self.pos
    def read(self,n=-1):
        if n<0:n=self.size-self.pos
        n=min(n,self.size-self.pos)
        if n==0:return b''
        if n>8*1024*1024:raise ValueError('unexpected_large_directory_read')
        raw=self.range(self.pos,self.pos+n-1);self.pos+=len(raw);return raw
    def range(self,start,end):
        req=urllib.request.Request(self.url,headers={'Range':f'bytes={start}-{end}'})
        with urllib.request.urlopen(req,timeout=45) as r:
            if r.status!=206:raise ValueError('server_must_honor_bounded_range')
            raw=r.read(end-start+2)
        if len(raw)!=end-start+1:raise ValueError('invalid_range_length')
        return raw


def run(download):
    remote=RemoteZip()
    with zipfile.ZipFile(remote) as z:
        entries=z.infolist()
        # CPU-only standalone: root executable and common/CPU library DLLs.
        chosen=[i for i in entries if not i.is_dir() and (i.filename=='ollama.exe' or
                i.filename.startswith('lib/ollama/') and len(Path(i.filename).parts)==3 and i.filename.endswith(('.dll','.exe')))]
        print(json.dumps([{'path':i.filename,'compressed_bytes':i.compress_size,'bytes':i.file_size} for i in chosen],indent=2),flush=True)
        if not download:return
        if not chosen or not any(i.filename=='ollama.exe' for i in chosen):raise ValueError('expected_standalone_cpu_layout_missing')
        out=ROOT/'work/ollama_cpu_0_40_5'
        out.mkdir(parents=True,exist_ok=True);inventory={}
        for i in chosen:
            target=(out/i.filename).resolve()
            if not target.is_relative_to(out.resolve()):raise ValueError('unsafe_zip_path')
            if target.exists():
                existing=target.read_bytes()
                if len(existing)!=i.file_size or zlib.crc32(existing)!=i.CRC:raise ValueError('existing_runtime_file_differs_refuse_overwrite')
                inventory[i.filename]={'sha256':hashlib.sha256(existing).hexdigest(),'bytes':len(existing),'zip_crc32':i.CRC}
                print('Retained verified CPU runtime entry',i.filename,flush=True)
                continue
            header=remote.range(i.header_offset,i.header_offset+29)
            values=struct.unpack('<4s5H3I2H',header)
            if values[0]!=b'PK\x03\x04':raise ValueError('invalid_local_header')
            offset=i.header_offset+30+values[-2]+values[-1]
            compressed=bytearray()
            for start in range(offset,offset+i.compress_size,4*1024*1024):
                compressed.extend(remote.range(start,min(start+4*1024*1024,offset+i.compress_size)-1))
            if i.compress_type==zipfile.ZIP_DEFLATED:raw=zlib.decompress(compressed,-15)
            elif i.compress_type==zipfile.ZIP_STORED:raw=bytes(compressed)
            else:raise ValueError('unsupported_zip_compression')
            if len(raw)!=i.file_size or zlib.crc32(raw)!=i.CRC:raise ValueError('zip_entry_crc_failed')
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
            inventory[i.filename]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'zip_crc32':i.CRC}
            print('Verified CPU runtime entry',i.filename,flush=True)
        (out/'DOWNLOAD_MANIFEST.json').write_text(json.dumps({'provider':'official Ollama release','url':URL,'version':'0.40.5',
            'scope':'CPU-only entry extraction, not full GPU distribution','files':inventory},indent=2),encoding='utf-8')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--download',action='store_true');run(p.parse_args().download)
