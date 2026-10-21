"""Financial arithmetic. Missing prerequisites remain missing, including labels."""
import numpy as np
import pandas as pd

POST_EVENT={'Actual_Total_Cost','Actual_Revenue','Budget_Utilization','Profit','Profit_Margin',
            'Cost_Per_Guest','Cost_Variance','Budget_Overrun','Profit_Margin_Risk','Vendor_Cost_Anomaly','Financial_Health_Score'}
def safe_ratio(a,b):
    return a.div(b.where(b>0)).replace([np.inf,-np.inf],np.nan)

def engineer(frame,used_area=None):
    d=frame.copy()
    for c in ['Actual_Total_Cost','Actual_Revenue','Initial_Budget','Guest_Count','Forecasted_Total_Cost','Required_Min_Profit_Margin','Usable_Area_m2']:
        d[c]=pd.to_numeric(d[c],errors='coerce')
    cost,revenue=d.Actual_Total_Cost,d.Actual_Revenue
    d['Budget_Utilization']=safe_ratio(cost,d.Initial_Budget)
    d['Profit']=revenue-cost
    d['Profit_Margin']=safe_ratio(d.Profit,revenue)*100
    d['Cost_Per_Guest']=safe_ratio(cost,d.Guest_Count)
    d['Cost_Variance']=cost-d.Forecasted_Total_Cost
    d['Space_Utilization']=np.nan if used_area is None else safe_ratio(used_area,d.Usable_Area_m2)
    for target,left,right in [('Budget_Overrun',cost,d.Initial_Budget),('Profit_Margin_Risk',d.Required_Min_Profit_Margin,d.Profit_Margin)]:
        valid=left.notna()&right.notna()
        if target=='Profit_Margin_Risk':valid&=revenue.gt(0)
        d[target]=pd.Series(pd.NA,index=d.index,dtype='Int64')
        d.loc[valid,target]=(left[valid]>right[valid]).astype(int)
    d['Vendor_Cost_Anomaly']=pd.Series(pd.NA,index=d.index,dtype='Int64')
    d['Financial_Health_Score']=np.nan
    return d
