"""Analytical coordinate checks, kept separate from real-plan performance claims."""
from common import *
from outdoor_geometry import vector_regions,affine
from shapely.geometry import shape
import numpy as np
p=H/"upload_test_fixtures/AFFINE.svg"
p.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><g transform="translate(10 20) scale(2)" class="Space Bedroom"><polygon points="0,0 10,0 10,10 0,10"/></g></svg>',encoding="utf-8")
r=vector_regions(p,1000,1000);g=shape(r["regions"][0]["geometry"])
assert np.allclose(g.bounds,[100,200,300,400]) and abs(g.area-40000)<1e-9
assert np.allclose(affine("rotate(90 10 10)")@np.array([20,10,1]),[10,20,1])
save("REGION_AFFINE_VERIFICATION.json",{"status":"PASS","expected_bounds":[100,200,300,400],"actual_bounds":list(g.bounds),"area":g.area,"rotation_about_pivot":True,"scope":"Explicit analytic synthetic transform test, not actual venue annotation/performance."})
