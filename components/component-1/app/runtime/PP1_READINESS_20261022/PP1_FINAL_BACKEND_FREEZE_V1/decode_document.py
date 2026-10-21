"""Run with existing global Python (PyMuPDF/CairoSVG); no package installation."""
import sys,argparse,math,xml.etree.ElementTree as ET,re
from common import *
parser=argparse.ArgumentParser();parser.add_argument("source",type=Path);parser.add_argument("out",type=Path)
args=parser.parse_args();source=args.source.resolve();out=args.out.resolve();assert out.is_relative_to(H)
out.mkdir(parents=True,exist_ok=False);events=guard()
from PIL import Image
items=[]
ext=source.suffix.lower()
if ext in [".png",".jpg",".jpeg"]:
 with Image.open(source,formats=["PNG","JPEG"]) as im:
  if im.width*im.height>16000000:raise ValueError("IMAGE_OVER_16_MEGAPIXELS")
  im=im.convert("RGB");dest=out/"page_001.png";im.save(dest)
 items.append({"page":1,"image":str(dest),"width":im.width,"height":im.height,"transform":"Original raster pixels; no resize"})
elif ext==".pdf":
 import fitz
 doc=fitz.open(source)
 if doc.needs_pass or len(doc)>20:raise ValueError("PASSWORD_OR_PAGE_COUNT_UNSUPPORTED")
 for i,page in enumerate(doc):
  zoom=min(2.,1600/max(page.rect.width,page.rect.height))
  pix=page.get_pixmap(matrix=fitz.Matrix(zoom,zoom),alpha=False)
  dest=out/("page_%03d.png"%(i+1));pix.save(dest)
  items.append({"page":i+1,"image":str(dest),"width":pix.width,"height":pix.height,"pdf_page_rect":list(page.rect),"pdf_rotation":page.rotation,"pdf_points_to_pixels_scale":zoom,"metric_venue_scale_inferred":False})
elif ext==".svg":
 import cairosvg
 raw=source.read_bytes()
 if len(raw)>20*1024*1024 or re.search(br"<!DOCTYPE|<!ENTITY|<script|<foreignObject|@import|https?://",raw,re.I):
  # XML namespace URLs are harmless declarations; strip only those for the safety scan.
  scan=re.sub(br'xmlns(?::\w+)?=["\'][^"\']*["\']',b"",raw)
  if re.search(br"<!DOCTYPE|<!ENTITY|<script|<foreignObject|@import|https?://",scan,re.I):raise ValueError("UNSAFE_EXTERNAL_SVG")
 tree=ET.fromstring(raw)
 for e in tree.iter():
  for k,v in e.attrib.items():
   if k.rsplit("}",1)[-1]=="href" and not v.startswith("#"):raise ValueError("EXTERNAL_SVG_REFERENCE")
   if "url(" in v and not re.search(r"url\(\s*#",v):raise ValueError("EXTERNAL_SVG_CSS")
 vb=list(map(float,tree.get("viewBox","").split()))
 if len(vb)!=4 or vb[2]<=0 or vb[3]<=0:raise ValueError("SVG_VIEWBOX_REQUIRED")
 scale=min(1.,1600/max(vb[2],vb[3]));w=max(1,round(vb[2]*scale));h=max(1,round(vb[3]*scale))
 dest=out/"page_001.png";cairosvg.svg2png(bytestring=raw,write_to=str(dest),output_width=w,output_height=h,background_color="white",unsafe=False)
 items.append({"page":1,"image":str(dest),"width":w,"height":h,"svg_viewbox":vb,"svg_frame":"ViewBox preserved; child affine transforms handled during geometry extraction"})
else:raise ValueError("UNSUPPORTED_INPUT; supported PNG/JPG/PDF/SVG; no verified CAD converter")
save(out.relative_to(H)/"DECODE.json",{"source":str(source),"source_sha256":sha(source),"format":ext,"pages":items,"guard":events,"decoder_python":sys.executable})
print(len(items),"pages decoded")
