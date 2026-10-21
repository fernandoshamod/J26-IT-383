from common import *
import urllib.request
urls={
 "NPS_PINES_SITE_PLAN.jpg":"https://www.nps.gov/yose/planyourvisit/images/pinescombined.jpg",
 "NPS_CAMPGROUND_MAP.pdf":"https://www.nps.gov/yose/planyourvisit/upload/yosemitecampgroundmap2013.pdf",
 "NPS_MAP_RIGHTS.html":"https://www.nps.gov/subjects/gisandmapping/data-sources-and-accuracy.htm",
 "CVC_SOURCE.html":"https://dag.cvc.uab.es/dataset/cvc-fp-database-for-structural-floor-plan-analysis/"}
rows=[]
for name,url in urls.items():
 p=H/"acquired"/name
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"PP1-academic-plan-processing"}),timeout=45) as r,p.open("xb") as f:f.write(r.read())
  rows.append({"url":url,"file":str(p),"status":"DOWNLOADED","bytes":p.stat().st_size,"sha256":sha(p)})
 except Exception as e:rows.append({"url":url,"status":"FAILED","reason":repr(e)})
save("SITE_ACQUISITION.json",rows)
print(rows)
