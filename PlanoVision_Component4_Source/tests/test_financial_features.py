import sys, unittest
from pathlib import Path
import pandas as pd
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/research_pipeline'))
from features import engineer

def record(**kwargs):
    fields=['Actual_Total_Cost','Actual_Revenue','Initial_Budget','Guest_Count','Forecasted_Total_Cost','Required_Min_Profit_Margin','Usable_Area_m2']
    return pd.DataFrame([{c:kwargs.get(c,np.nan) for c in fields}])

class Arithmetic(unittest.TestCase):
    def test_arithmetic(self):
        d=engineer(record(Actual_Total_Cost=120,Actual_Revenue=150,Initial_Budget=100,Guest_Count=10,Forecasted_Total_Cost=110,Required_Min_Profit_Margin=25)).iloc[0]
        self.assertEqual(d.Profit,30);self.assertEqual(d.Profit_Margin,20)
        self.assertEqual(d.Budget_Utilization,1.2);self.assertEqual(d.Cost_Per_Guest,12)
        self.assertEqual(d.Cost_Variance,10);self.assertEqual(d.Budget_Overrun,1);self.assertEqual(d.Profit_Margin_Risk,1)
    def test_missing_outcomes_not_zero_labels(self):
        d=engineer(record(Initial_Budget=100,Required_Min_Profit_Margin=20)).iloc[0]
        self.assertTrue(pd.isna(d.Budget_Overrun));self.assertTrue(pd.isna(d.Profit_Margin_Risk))
    def test_zero_denominators(self):
        d=engineer(record(Actual_Total_Cost=120,Actual_Revenue=0,Initial_Budget=0,Guest_Count=0)).iloc[0]
        for f in ['Profit_Margin','Budget_Utilization','Cost_Per_Guest','Profit_Margin_Risk']:self.assertTrue(pd.isna(d[f]))
    def test_margin_boundary(self):
        d=engineer(record(Actual_Total_Cost=80,Actual_Revenue=100,Initial_Budget=80,Required_Min_Profit_Margin=20)).iloc[0]
        self.assertEqual(d.Budget_Overrun,0);self.assertEqual(d.Profit_Margin_Risk,0)
    def test_no_implied_geometry(self):
        self.assertTrue(pd.isna(engineer(record(Usable_Area_m2=100)).iloc[0].Space_Utilization))
        self.assertEqual(engineer(record(Usable_Area_m2=100),pd.Series([50])).iloc[0].Space_Utilization,.5)
    def test_no_unvalidated_anomaly_or_health_score(self):
        d=engineer(record()).iloc[0]
        self.assertTrue(pd.isna(d.Vendor_Cost_Anomaly));self.assertTrue(pd.isna(d.Financial_Health_Score))
if __name__=='__main__':unittest.main()
