"""Build review metadata and observed summaries only. Never generate scenarios."""
import json, hashlib
import pandas as pd
from common import ROOT,REPORTS,PROCESSED,FINAL,sha

HEADERS=['Assumption_ID','Category','Related_Master_Columns','Assumption_Description','Proposed_Formula_or_Range',
         'Supporting_Data_Source','Unit_or_Currency','Scientific_Justification','Confidence_Level',
         'Uncertainty_Description','Validation_Required','Approval_Status']

def run():
    rows=[]
    def add(category,cols,description,formula,source,unit,why,confidence,uncertainty,validation):
        rows.append([f'A{len(rows)+1:03d}',category,cols,description,formula,source,unit,why,confidence,uncertainty,validation,'Pending review'])
    add('Accounting','All cost/revenue columns','One organiser/project boundary; mutually exclusive service ledgers.',
        'Total cost = sum(disjoint expense lines); reserve excluded from expenses.','No observed event ledger; financial_dependency_rules.md','LKR after rate approval',
        'Dimensional/accounting reconciliation prevents bundle and reserve double counting.','Arithmetic identity / scope assumed','Tax, packages and income retention unspecified.','Approve boundary, tax and bundle exclusions.')
    add('Rates','Quoted_*_Cost; Transport_Cost; Misc_Cost','No absolute LKR default rate is established by the collected sources.',
        'Each rate_j > 0 with approved LKR/unit, date, quantity, tax and bundle scope; numeric values UNSET.','S003 ingredient proxies only; no local service rate cards','LKR/unit',
        'Preserves monetary meaning without treating foreign contracts or retail prices as event quotations.','Unvalidated assumption','All local service levels/rates unresolved.','Supply or explicitly approve simulator-only rate cards before generation.')
    add('Event archetypes','Event_Type','Six requested design strata; weights are experimental, not observed prevalence.',
        'Wedding, Corporate, Conference, Exhibition, Birthday, Outdoor Festival; weights supplied in approved config.','User-defined experiment; S015 names not a population sample','category / probability weights',
        'Coverage supports controlled comparisons without making a population-frequency claim.','Unvalidated assumption','No local archetype frequency distribution.','Approve allocations and names; preserve Corporate/Outdoor Festival explicitly.')
    add('Capacity benchmark','Guest_Count; Seating_Count','Use source room capacities only as indoor-scale benchmark observations.',
        'S013 capacities: n=149, min=4, Q25=12, median=25, Q75=50, max=299; sample within approved seating-style stratum.','S013 data/processed/venues.csv; Observed_Evidence sheet','persons',
        'Uses an actual empirical distribution while explicitly limiting geographic/arrangement transfer.','Observed description; transfer unvalidated','California rooms are not Sri Lankan/festival venues or representative venues.','Review strata, usage restrictions and indoor applicability; no area/rent inference.')
    add('Planned guests','Guest_Count','Occupancy fractions are proposed bounded experimental controls.',
        'Wedding .50–1.00C; Corporate .30–.90C; Conference .40–1.00C; Birthday .20–.75C; round to positive integer and enforce geometry.','S013 benchmark C; fractions are designer assumptions','persons / ratio',
        'Conditioning on capacity avoids independent impossible counts.','Unvalidated assumption','Fractions are not measured attendance distributions.','Approve occupancy ranges and arrangements; do not call them real guest statistics.')
    add('Outdoor/exhibition capacity','Guest_Count; Venue_Area_m2','Separate synthetic occupancy/area specifications required for non-room archetypes.',
        'Exhibition .20–.80C; Outdoor Festival .40–1.00C; C and V bounds UNSET; never substitute seated-room C as standing capacity.','No observed festival/exhibition geometry','persons / m2',
        'Avoids extrapolating conference-room data to unsupported large outdoor layouts.','Unvalidated assumption','No justified absolute capacity/area bounds.','Expert supplies or approves synthetic archetype bounds.')
    add('Duration','Event_Duration_Hours; Labor_Hours','Event hours, setup and clearance are separate paid-time drivers.',
        'H>0; Hsetup,Hclear>=0; archetype-specific bounds UNSET. Date span is not event hours.','S015 date ranges only; no duration measurements','hours',
        'Separates scheduled span from measured/paid hours.','Unvalidated assumption','No duration or labour-hour distribution.','Approve hour bounds and overtime/paid-break policy.')
    add('Seating','Seating_Count','Seat share and table occupancy depend on archetype.',
        'N=ceil(seated_share*G); 0<=seated_share<=1; 0<=NVIP<=N<=G; seats_per_table positive approved integer.','S013 arrangement labels; quantities assumed','persons / seats/table',
        'Preserves integer resource requirements and dependent quantities.','Unvalidated assumption','Shares/table layout are not observed.','Review each archetype, standing permission and VIP allocation.')
    add('Geometry','Venue_Area_m2; Usable_Area_m2','Venue area must be supplied, not inferred as observed from capacity.',
        'U=V-excluded_area; 0<U<=V; V and excluded-area bounds UNSET.','S013 has no floor areas','m2',
        'Avoids substituting capacity for physical measurement.','Unvalidated assumption','Unknown usable areas and exclusion/circulation rules.','Approve synthetic area ranges; external floor plans needed for reality claims.')
    add('Area density','Seating_Count; VIP_Area_m2; Space_Utilization','Standard/VIP seat area coefficients are synthetic layout parameters.',
        'Seating_area=(N-NVIP)*a_seat; VIP_area=NVIP*a_VIP; a_seat,a_VIP>0, numeric bounds UNSET.','No observed seating density/layouts','m2/person',
        'Dimensionally consistent allocation without inventing venue standards.','Unvalidated assumption','Density is not fire-code compliance.','Venue expert approves arrangement-specific densities and circulation accounting.')
    add('Stage','Stage_Area_m2; Quoted_AV_Cost; Quoted_Lighting_Cost','Stage is a synthetic rectangle linked to resource demand.',
        'S=width*length; positive approved dimension bounds UNSET; kit count=base+ceil(S/area_per_kit).','No measured stages or AV area-cost pairs','m2; LKR/kit',
        'Models possible stepwise resource changes rather than an unobserved fitted correlation.','Unvalidated assumption','Kit thresholds, fixed/minimum charges and dimensions unknown.','Expert review of steps, bundles and bounds.')
    add('Feasibility','Space_Utilization; Usable_Area_m2','Explicit non-overlapping area ledger and arrangement capacity constrain sampling.',
        'Used_area=standard_seats+VIP+stage+booths+service+circulation; Used_area<=U; G<=approved arrangement C.','Designed conservation constraints; S013 capacity context','m2 / ratio',
        'Prevents physically impossible combinations.','Arithmetic identity / layout assumed','No real adjacency, egress or regulatory validation.','Independent geometry check; no safety certification claim.')
    add('Catering','Quoted_Catering_Cost','Select BOM or per-guest package, never charge both.',
        'BOM: sum(G*portion_j*(1+waste_j)*price_j)+fixed_service; package: G*package_rate+extras. Quantities/rates UNSET.','S003 selected ingredient prices; no observed meal recipes/quotes','kg or explicit source unit; LKR',
        'Resource accounting makes guest-to-food dependency transparent.','Proxy limited','Retail-to-catering, menu, waste and service margins unknown.','Review menu/unit conversions and package inclusions.')
    add('Furniture','Quoted_Equipment_Rental_Cost','Furniture is a disjoint subledger within equipment rental.',
        'chair_qty*chair_rate+table_qty*table_rate+explicit delivery; bundled items charged zero only when inclusion is established.','S013 furniture/AV availability, not hire prices','LKR/item',
        'Connects seating demand to quantities and avoids bundle duplication.','Unvalidated assumption','Existing furniture and rental contracts unknown.','Approve bill-of-items and inclusion flags.')
    add('Staffing','Staff_Count; Labor_Hours; Quoted_Labor_Cost','Role-specific guest/stage/time demand sets general labour.',
        'Staff=base+ceil(G/guests_per_staff)+approved extras; labour=sum(role_count*paid_hours*role_rate)+overtime. Parameters UNSET.','S017 cell-level wage context not yet interpreted; no event allocations','persons; person-hours; LKR/hour',
        'Maintains dependencies and units; avoids random independent staff/cost columns.','Unvalidated assumption','Role ratios, wages and overtime uncalibrated.','Approve staffing requirements; exclude package/security staff already charged elsewhere.')
    add('Source price paths','Quoted_Catering_Cost','Review item/unit paths before any empirical monthly fluctuation reuse.',
        'Approved consecutive complete-month p_t>0; r_t=log(p_t/p_previous). Reject gaps/ambiguous item identities; train/prior window only.','S003 data/final/prophet_cost_timeseries.csv; Observed_Evidence','LKR/source unit; log ratio',
        'Preserves observed time order and prevents interpreting gaps as monthly shocks.','Derived proxy; transfer unvalidated','Revised sources, incomplete months, retail coverage and trend regimes.','Whitelist items; inspect flags and source vintages; approve cutoff and residual method.')
    add('Escalation','Quoted_*_Cost','Optional generic price-index pass-through is assumed, not estimated.',
        'p(t)=p(base)*(I(t)/I(base))^beta; beta stress scope [0,1], not an estimated elasticity.','S001 CCPI 57 months; S002 NCPI 56 months','index ratio; LKR/unit',
        'Keeps observed index movement separate from unknown service-price pass-through.','Proxy limited','Broad CPI may not match AV/venue/security/labour costs.','Approve index selection, beta and base date; compare against no-escalation model.')
    add('Seasonality','Quoted_*_Cost','No automatic seasonal premium is added to historical paths.',
        'Use raw path OR train-only trend/season decomposition plus residuals; never double-count seasonal/inflation terms.','S003/CCPI/NCPI histories; no event seasonal premium observations','ratio',
        'Avoids adding the same observed movement twice.','Proxy limited','Seasonal stability and event demand effects unknown.','Approve decomposition only after training-window diagnostic review.')
    add('Vendor tiers','Quoted_*_Cost','Tier multipliers represent designed service choices.',
        'tier_multiplier>0 with ordered scope/quality definitions; all numeric tier rates/multipliers UNSET.','No comparable vendor-service tiers observed','ratio / LKR',
        'Exposes policy rather than fabricating a vendor ranking or market markup.','Unvalidated assumption','Higher cost need not imply higher real quality.','Approve service definitions and non-duplicative rate model.')
    add('Venue rent','Quoted_Venue_Rental_Cost','No empirical capacity-to-rental relationship is fitted.',
        'rent=fixed_fee+billable_hours*hourly_rate+explicit extras; alternatively approved area tariff, not both without scope.','S013 capacity only; no rental values','LKR/booking; LKR/hour',
        'Supports costs while preventing a false observed capacity-price correlation.','Unvalidated assumption','All tariffs, minimums and booking inclusions unknown.','Approve venue archetype rate cards and billable hours.')
    add('Budget','Initial_Budget','Budget is determined before outcome shocks.',
        'B=approved independent budget or b*Q; proposed b stress interval [.85,1.30], not population estimate; B>=Reserve.','No observed event budgets','LKR / ratio',
        'Preserves ex-ante constraint and includes financially stressed cases.','Unvalidated assumption','Budget distribution and affordability factor arbitrary experimental controls.','Review stress interval; forbid budget derivation from realised cost.')
    add('Revenue','Expected_Revenue; Actual_Revenue','Revenue mode follows project accounting, not random income fill.',
        'Contract: approved retained fee. Ticketed: planned attendees*ticket_rate+retained booth/sponsor receipts. Values UNSET.','No observed event receipts; S015 attendance 100% missing','LKR',
        'Allows loss/profit outcomes without forcing expected revenue to match actual costs.','Unvalidated assumption','Attendance, demand, sponsor and cancellation processes unobserved.','Approve revenue modes/amounts and realised-receipt uncertainty by archetype.')
    add('Margin policy','Required_Min_Profit_Margin','Minimum margin is a configurable experiment/domain policy.',
        'Proposed stress policies 10%,20%,30%; stored as 10,20,30 percentage points. Not industry averages.','No domain-approved required margin','percentage points',
        'Labels have explicit business-policy meaning and auditable boundaries.','Unvalidated assumption','No evidence any policy is suitable for this organiser.','Reviewer approves/amends policies before labels are generated.')
    add('Contingency','Contingency_Reserve; Initial_Budget','Reserve is a funding allowance, not an expense.',
        'Reserve=c*Q; proposed c stress policies .05,.10,.15,.20; alternative pre-event quantile requires approved shock model.','No observed reserves; designed policy','LKR / ratio',
        'Avoids double counting reserve and exposes policy sensitivity.','Unvalidated assumption','No calibrated reserve probability or cost-risk distribution.','Approve rate/quantile policy and budget-includes-reserve convention.')
    add('Outcome variation','Actual_Total_Cost; Actual_Revenue','Latent quantities/rates/receipts change after planning.',
        'Proposed bounded stress widths ±5%,±10%,±20%; baseline no-shock case. Distribution family/probabilities require approval.','Price paths may inform ingredient proxies only; other residuals unobserved','ratio',
        'Separates unknown outcomes from planning inputs and explores robustness.','Unvalidated assumption','Stress widths are not estimated confidence intervals.','Approve positivity bounds, shock scope/distribution and evidence versus hypothetical settings.')
    add('Shock dependence','Actual_Total_Cost; Actual_Revenue','Shared latent shocks may create correlated service outcomes.',
        'Approved shared-factor or synchronized-history sampler versus independent baseline; coefficients/block length UNSET.','No observed event-level covariance','dimensionless factors',
        'Tests dependence instead of falsely asserting independent or observed correlated errors.','Unvalidated assumption','Dependence structure, cancellation and demand-price coupling unknown.','Approve dependence model; inspect joint feasible bounds.')
    add('Cost forecast/history','Forecasted_Total_Cost; Historical_Mean_Cost; Vendor_Price_Volatility','Forecast is pre-event; unsupported historical event/vendor fields remain missing.',
        'Forecast=approved planning-rule estimate initially; historical event mean/vendor volatility NULL without defined comparable history.','No observed event cost outcomes or vendor-specific histories','LKR; explicitly defined volatility unit',
        'Prevents replacing event history with ingredient or contract aggregates.','Unvalidated assumption','No empirical event residual calibration.','Approve forecast definition; require rolling/OOF forecasts for later models.')
    add('Budget target','Budget_Overrun','Target is simulated expenditure exceeding total ex-ante budget.',
        '1[C_sim>B], equality=0; missing when inputs invalid; label origin simulated.','Definition requested by user; simulated realised ledger only','binary',
        'Transparent financial boundary with no outcome input leakage.','Arithmetic identity / outcomes simulated','Truth reflects simulator and chosen budget rules only.','Check boundaries and budget/reserve ledger; independent real outcomes needed later.')
    add('Margin target','Profit_Margin_Risk; Profit_Margin','Positive-revenue margin shortfall under approved policy.',
        'margin=100*(R_sim-C_sim)/R_sim; target=1[margin<m_required]; R_sim<=0 or missing => target missing.','User definition; synthetic outcomes','percentage points / binary',
        'Avoids false finite margins and incorrect zero labels.','Arithmetic identity / outcomes simulated','Policy and simulated receipts determine labels.','Verify equality/zero-revenue cases and label masks.')
    add('Injected vendor regime','Vendor_Cost_Anomaly','Primary label identifies a deliberately injected abnormal charge regime.',
        'Z_event=max(Z_service); approved Z=1 rate multiplier >1; experimental prevalence and multiplier bounds UNSET.','No observed vendor anomalies; simulator intervention only','binary / ratio',
        'Provides transparent injection truth without an unvalidated historical anomaly threshold.','Unvalidated assumption','Not real abnormality/fraud; identifiability depends on severity/noise.','Approve regime and severity; restrict latent flags to diagnostics, never predictors.')
    add('Graph dependencies','Spatial context; planned expense columns','Edges encode approved functional dependencies, not real floor-plan adjacency.',
        'Typed demand/resource/area/price/aggregation edges with rule IDs; no observed-coordinate claim.','spatial_financial_graph_schema.md; no measured layouts','typed edge; coefficient-specific units',
        'Supports controlled graph ablations with transparent construction.','Unvalidated assumption','Topology and coefficients are designer supplied.','Review rules, missing masks, no post-event inputs and graph/ledger reconciliation.')
    add('Validation split','Base_Event_ID; Scenario_ID','Keep every descendant with its synthetic base before calibration/augmentation.',
        'Group split first; chronology for source-history fit; hold out families/archetypes where possible.','Dataset lineage and leakage protocol','group / date',
        'Avoids treating derivatives as independent held-out evidence.','Methodological proposal','Grouped simulator tests still lack external reality validation.','Assert zero descendant overlap; no full-data fitting or target-driven prevalence tuning.')
    add('Reproducibility','Scenario_ID; Base_Event_ID; Data_Source; Is_Augmented','Version/seed/source/approval metadata is mandatory.',
        'Stable SYN/SYNBASE IDs; Is_Augmented=1; independent recorded RNG streams; paired what-if common random draws.','Source SHA256 manifest; proposed simulator config','identifier',
        'Makes scenario construction and interventions reproducible/auditable.','Methodological proposal','Seed alone is insufficient if versions/sources change.','Verify exact replay and atomic provenance export.')
    add('Final score','Financial_Health_Score','No unapproved composite health score is invented.',
        'NULL until a separately reviewed score definition/weights is approved.','No supplied health-score definition','undefined',
        'Prevents an arbitrary composite being presented as validated decision support.','Unvalidated assumption','Weights and target interpretation unresolved.','Separate scoring-policy review; exclude from risk prediction inputs.')
    evidence=[]
    v=pd.read_csv(PROCESSED/'venues.csv')
    for style,g in [('All source arrangements',v),*list(v.groupby('seatingstylename'))]:
        s=g.capacity.dropna()
        evidence.append(['S013',str(style),'Advertised room capacity',len(s),float(s.min()),float(s.quantile(.25)),float(s.median()),float(s.quantile(.75)),float(s.max()),'persons','California arrangement-specific snapshot; not local venue population','https://catalog.data.gov/dataset/dgs-conference-rooms',sha(PROCESSED/'venues.csv')])
    ts=pd.read_csv(FINAL/'prophet_cost_timeseries.csv')
    for sid in ['S001:CCPI:base2021','S002:NCPI:base2021','S003:Ash Plantain:1 kg.','S003:Carrot:1 kg.']:
        g=ts[ts.series_id.eq(sid)]
        s=g.y
        evidence.append([sid.split(':')[0],sid,'Observed/derived monthly level',len(g),float(s.min()),float(s.quantile(.25)),float(s.median()),float(s.quantile(.75)),float(s.max()),g.unit.iloc[0],
                         f'{g.ds.min()} to {g.ds.max()}; retail means include partial latest month; not approved shock calibration',
                         'https://www.statistics.gov.lk/InflationAndPrices/StaticalInformation/'+('RetailPrices' if sid.startswith('S003') else 'Monthly'+sid.split(':')[1]),sha(FINAL/'prophet_cost_timeseries.csv')])
    evidence_headers=['Source_ID','Series_or_Arrangement','Statistic_Kind','N','Min','Q25','Median','Q75','Max','Unit','Scope_and_Limitations','Source_URL','Snapshot_SHA256']
    metadata={'Assumptions':{'headers':HEADERS,'rows':rows},'Observed_Evidence':{'headers':evidence_headers,'rows':evidence}}
    (REPORTS/'simulation_review_data.json').write_text(json.dumps(metadata,ensure_ascii=False,allow_nan=False),encoding='utf-8')
    pd.DataFrame(rows,columns=HEADERS).to_csv(REPORTS/'simulation_assumption_register.csv',index=False)
    print('REVIEW_ONLY',len(rows),'pending assumptions;',len(evidence),'observed summary rows; 0 scenarios')
if __name__=='__main__':run()
