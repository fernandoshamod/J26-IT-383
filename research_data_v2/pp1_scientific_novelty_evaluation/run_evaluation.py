"""Isolated PP1 experiments. Run: venv/Scripts/python.exe -B research_data_v2/pp1_scientific_novelty_evaluation/run_evaluation.py"""
import csv, hashlib, itertools, json, math, random, statistics, sys, time
from collections import Counter, defaultdict
from pathlib import Path
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT / "research_data_v2/pp1_task2_conflict_engine")]
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from backend.engine import bounded_package_generator as gen
from backend.engine.candidate_selection import select_candidates_for_event
from backend.engine.dynamic_feasibility import validate_dynamic_package
from backend.engine.package_data_loader import load_service_options
from backend.engine.risk_signals import FEATURES, load_risk_signals, verified_model
from backend.engine.service_compatibility import load_compatibility_rules, service_compatibility
from backend.engine.validation_helpers import validate_service_option_lkr
from conflict_engine import evaluate_case
from research_evaluation.metrics import rank_pool
from research_evaluation.model_audit import evaluate_model

SEED = 42
SERVICES = ["Photography", "Decoration"]
CITIES = [("Blackwood","NJ"),("Alton","IL"),("Abington","PA"),("Goleta","CA"),
          ("Belleville","IL"),("Brandon","FL"),("Lansdale","PA"),("West Chester","PA")]
INPUTS = ["hybrid_simulation_v1/synthetic_service_options.csv",
          "hybrid_simulation_v1/real_vendor_profiles.csv","vendor_compatibility_matrix.csv",
          "models/vendor_risk_random_forest.pkl","data/cleaned/vendor_profiles_missingness_checked.csv",
          "research_data_v2/pp1_task2_conflict_engine/fixtures.json",
          "research_data_v2/pp1_task2_conflict_engine/conflict_engine.py"]

def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""): h.update(block)
    return h.hexdigest()
def csvout(name,rows):
    with (OUT/name).open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,list(rows[0]));w.writeheader();w.writerows(rows)
def stats(xs):
    return {"n":len(xs),"mean":statistics.mean(xs) if xs else None,
            "median":statistics.median(xs) if xs else None}
def ci(xs):
    if len(xs)<2:return None
    rng=random.Random(SEED)
    estimates=sorted(statistics.mean(rng.choices(xs,k=len(xs))) for _ in range(10000))
    return [estimates[249],estimates[9749]]
def event(city,state):
    return {"event_id":"EVAL-"+city.upper().replace(" ","-"),"event_type":"Wedding",
            "event_date":"2026-11-16","start_time":"10:00","end_time":"18:00",
            "city":city,"state":state,"guest_count":50,"budget_lkr":1000000.0,
            "duration_hours":8.0,"required_services":";".join(SERVICES),"currency":"LKR"}
def snapshot(p):
    return {"option_ids":tuple(p["option_ids"]),"vendor_ids":tuple(p["vendor_ids"]),
            "service_coverage":tuple(p["service_coverage"]),"total_cost_lkr":p["total_cost_lkr"],"budget_lkr":round(p["total_cost_lkr"]+p["remaining_budget_lkr"],2),
            "risk":p["risk"],"compatibility":p["compatibility"],
            "feasibility_status":p["feasibility"]["final_status"]}
def diversity(items):
    ids=[v for p in items for v in p["vendor_ids"]]
    return len(set(ids))/len(ids) if ids else None
def eligible(group,e):
    result=[]
    for o in group.to_dict("records"):
        v=validate_service_option_lkr(o,guest_count=e["guest_count"],duration_hours=e["duration_hours"],budget_lkr=e["budget_lkr"])
        c=v.get("estimated_cost_lkr")
        if c is None or not math.isfinite(float(c)) or v.get("capacity_status")=="Fail":continue
        o["estimated_cost_lkr"]=round(float(c),2);result.append(o)
    return result
def exhaustive(e,groups,lookup,compat):
    lists=[eligible(groups[s],e) for s in SERVICES]
    start=time.perf_counter();valid=[]
    for pair in itertools.product(*lists):
        if len({str(o["business_id"]) for o in pair})!=len(pair):continue
        cost=sum(o["estimated_cost_lkr"] for o in pair)
        if cost>e["budget_lkr"]:continue
        status=validate_dynamic_package(e,list(pair),SERVICES)["final_status"]
        if status=="FAIL":continue
        risk=gen._package_risk(list(pair),lookup)
        score,_=gen._ranking(cost,e["budget_lkr"],risk,compat,gen._ranking_weights())
        valid.append((0 if status=="PASS_IN_SIMULATION" else 1,-score,round(cost,2),
                      tuple(str(o["service_option_id"]) for o in pair)))
    valid.sort()
    return {"eligible":[len(x) for x in lists],"cartesian":math.prod(len(x) for x in lists),
            "count":len(valid),"top":valid[:3],"ms":(time.perf_counter()-start)*1000}
def chart(name,rows,key,title):
    values=[float(r[key] or 0) for r in rows];scale=max([abs(x) for x in values]+[1])
    height=80+32*len(rows)
    lines=[f'<svg xmlns="http://www.w3.org/2000/svg" width="820" height="{height}">',
           f'<rect width="820" height="{height}" fill="white"/>',
           f'<text x="15" y="27" font-family="sans-serif" font-size="17">{title}</text>',
           '<line x1="490" x2="490" y1="40" y2="'+str(height-12)+'" stroke="#333"/>']
    for i,(r,v) in enumerate(zip(rows,values)):
        y=50+32*i;width=250*abs(v)/scale;x=490 if v>=0 else 490-width
        lines.extend([f'<text x="15" y="{y+14}" font-family="sans-serif" font-size="12">{r["scenario_id"]}</text>',
                      f'<rect x="{x:.2f}" y="{y}" width="{width:.2f}" height="17" fill="#4755aa"/>',
                      f'<text x="750" y="{y+14}" font-family="sans-serif" font-size="12">{v:.2f}</text>'])
    (OUT/name).write_text("\n".join(lines+["</svg>",""]),encoding="utf-8")

def main():
    before={p:sha(ROOT/p) for p in INPUTS}
    assert gen._positive_limit("PLANOVISION_MAX_CANDIDATES_PER_SERVICE",12)==12
    assert gen._positive_limit("PLANOVISION_MAX_SEARCH_NODES",5000)==5000
    assert gen._ranking_weights()=={"cost":0.4,"risk":0.4,"compatibility":0.2}
    options=load_service_options();rules=load_compatibility_rules()
    compat=service_compatibility(SERVICES,rules);ranking=[];search=[]
    for city,state in CITIES:
        e=event(city,state);groups=select_candidates_for_event(e,SERVICES,options)
        ids={str(v) for group in groups.values() for v in group["business_id"]}
        lookup,_=load_risk_signals(ids);pool=[];original=gen.explain_package
        def capture(p):
            pool.append(snapshot(p));return original(p)
        begin=time.perf_counter()
        with patch.object(gen,"explain_package",side_effect=capture):
            bounded=gen.generate_bounded_packages(e,SERVICES,groups,3,risk_lookup=lookup,compatibility=compat)
        bounded_ms=(time.perf_counter()-begin)*1000
        assert len(pool)==bounded["feasible_combinations_seen"]
        begin=time.perf_counter();base=rank_pool(pool,"cost_only",3);base_ms=(time.perf_counter()-begin)*1000
        begin=time.perf_counter();prop=rank_pool(pool,"multi_factor",3,gen._ranking_weights());prop_ms=(time.perf_counter()-begin)*1000
        assert [p["option_ids"] for p in prop]==[tuple(p["option_ids"]) for p in bounded["packages"]]
        a=base[0] if base else None;b=prop[0] if prop else None
        def risk(p):return p["risk"]["mean_rule_risk_score"] if p else None
        ranking.append({"scenario_id":city+"_"+state,"budget_lkr":e["budget_lkr"],
          "required_services":";".join(SERVICES),"shared_examined_pool":len(pool),
          "candidate_truncated":bounded["search"]["candidate_limit_reached"],
          "baseline_option_ids":";".join(a["option_ids"]) if a else "",
          "proposed_option_ids":";".join(b["option_ids"]) if b else "",
          "baseline_cost_lkr":a["total_cost_lkr"] if a else None,
          "proposed_cost_lkr":b["total_cost_lkr"] if b else None,
          "paired_cost_difference_lkr":b["total_cost_lkr"]-a["total_cost_lkr"] if a and b else None,
          "baseline_risk_favorability":risk(a),"proposed_risk_favorability":risk(b),
          "paired_risk_difference":risk(b)-risk(a) if risk(a)!=None and risk(b)!=None else None,
          "baseline_category_compatibility":a["compatibility"]["score"] if a else None,
          "proposed_category_compatibility":b["compatibility"]["score"] if b else None,
          "baseline_budget_compliant":a["total_cost_lkr"]<=e["budget_lkr"] if a else None,
          "proposed_budget_compliant":b["total_cost_lkr"]<=e["budget_lkr"] if b else None,
          "baseline_coverage":set(a["service_coverage"])==set(SERVICES) if a else None,
          "proposed_coverage":set(b["service_coverage"])==set(SERVICES) if b else None,
          "baseline_top3_diversity":diversity(base),"proposed_top3_diversity":diversity(prop),
          "baseline_ranking_ms":round(base_ms,6),"proposed_ranking_ms":round(prop_ms,6),
          "shared_generation_ms":round(bounded_ms,4)})
        full=exhaustive(e,groups,lookup,compat)
        best=bounded["packages"][0] if bounded["packages"] else None
        optimum=full["top"][0] if full["top"] else None
        regret=max(0,-optimum[1]-best["ranking_score"]) if best and optimum else None
        search.append({"scenario_id":city+"_"+state,
          "full_eligible_photography":full["eligible"][0],"full_eligible_decoration":full["eligible"][1],
          "full_cartesian_size":full["cartesian"],
          "bounded_selected_photography":bounded["selected_candidate_counts"]["Photography"],
          "bounded_selected_decoration":bounded["selected_candidate_counts"]["Decoration"],
          "candidate_truncated":bounded["search"]["candidate_limit_reached"],
          "node_truncated":bounded["search"]["node_limit_reached"],
          "bounded_feasible_count":bounded["feasible_combinations_seen"],
          "exhaustive_feasible_count":full["count"],
          "missed_feasible_combinations":full["count"]-bounded["feasible_combinations_seen"],
          "bounded_best_score":best["ranking_score"] if best else None,
          "exhaustive_best_score":round(-optimum[1],4) if optimum else None,
          "best_score_regret":round(regret,4) if regret!=None else None,
          "bounded_best_option_ids":";".join(best["option_ids"]) if best else "",
          "exhaustive_best_option_ids":";".join(optimum[3]) if optimum else "",
          "bounded_ms":round(bounded_ms,4),"exhaustive_ms":round(full["ms"],4)})
        print(city,state,"examined",len(pool),"full",full["count"],flush=True)
    csvout("baseline_comparison.csv",ranking);csvout("search_quality_comparison.csv",search)
    chart("paired_cost_differences.svg",ranking,"paired_cost_difference_lkr","Proposed minus cheapest cost (LKR)")
    chart("search_regret.svg",search,"best_score_regret","Bounded best-score regret (points)")
    data=pd.read_csv(ROOT/"data/cleaned/vendor_profiles_missingness_checked.csv",usecols=[*FEATURES,"risk_level"])
    _,x,_,y=train_test_split(data[list(FEATURES)],data["risk_level"],test_size=.2,random_state=SEED,stratify=data["risk_level"])
    pred=verified_model().predict(x)
    rule=["Low" if m>=4 and s<1 and c>=20 else "Medium" if m>=3 else "High"
          for m,s,c in zip(x["mean_review_rating"],x["rating_std"],x["collected_review_count"])]
    audit=evaluate_model()
    risk_result={"holdout_n":len(y),"seed":SEED,"audit_status":audit["status"],
      "model_accuracy_vs_rule_labels":accuracy_score(y,pred),
      "model_macro_f1_vs_rule_labels":f1_score(y,pred,average="macro"),
      "rules_only_accuracy_vs_rule_labels":accuracy_score(y,rule),
      "rules_only_macro_f1_vs_rule_labels":f1_score(y,rule,average="macro"),
      "model_rule_disagreements":sum(a!=b for a,b in zip(pred,rule)),
      "independent_real_world_validation":False}
    (OUT/"risk_model_baseline.json").write_text(json.dumps(risk_result,indent=2)+"\n",encoding="utf-8")
    fixtures=json.loads((ROOT/"research_data_v2/pp1_task2_conflict_engine/fixtures.json").read_text())
    assert fixtures["evidence_class"]=="SYNTHETIC_TEST";conflicts=[]
    for case in fixtures["cases"]:
        services=[a["service_category"] for a in case["assignments"]]
        category=service_compatibility(services,rules);actual=evaluate_case(case)
        conflicts.append({"case_id":case["case_id"],"evidence_type":"SYNTHETIC_TEST",
          "category_pair":";".join(services),"category_score":category["score"],
          "category_status":category["status"],"expected_status":case["expected_status"],
          "observed_status":actual["status"],"correct":actual["status"]==case["expected_status"],
          "conflict_checks":actual["conflict_count"],"pending_checks":actual["pending_count"]})
    csvout("conflict_comparison.csv",conflicts)
    groups=defaultdict(set)
    for r in conflicts:groups[(r["category_pair"],r["category_score"])].add(r["observed_status"])
    costs=[float(r["paired_cost_difference_lkr"]) for r in ranking if r["paired_cost_difference_lkr"]!=None]
    risks=[float(r["paired_risk_difference"]) for r in ranking if r["paired_risk_difference"]!=None]
    regrets=[float(r["best_score_regret"]) for r in search if r["best_score_regret"]!=None]
    result={"design":"eight purposively selected synthetic two-service cities; fixed seed 42; paired by scenario",
      "ranking":{"events":len(ranking),"paired_nonempty":len(costs),"cost_difference":stats(costs),
        "cost_difference_descriptive_bootstrap_95pct":ci(costs),
        "risk_difference":stats(risks),"risk_difference_descriptive_bootstrap_95pct":ci(risks),
        "same_top1_count":sum(r["baseline_option_ids"]==r["proposed_option_ids"] and bool(r["baseline_option_ids"]) for r in ranking),
        "baseline_ranking_ms":stats([r["baseline_ranking_ms"] for r in ranking]),
        "proposed_ranking_ms":stats([r["proposed_ranking_ms"] for r in ranking])},
      "search":{"events":len(search),"candidate_truncated_events":sum(r["candidate_truncated"] for r in search),
        "node_truncated_events":sum(r["node_truncated"] for r in search),
        "total_exhaustive_feasible":sum(r["exhaustive_feasible_count"] for r in search),
        "total_bounded_feasible":sum(r["bounded_feasible_count"] for r in search),
        "total_missed_feasible":sum(r["missed_feasible_combinations"] for r in search),
        "best_score_regret":stats(regrets),
        "bounded_ms":stats([r["bounded_ms"] for r in search]),
        "exhaustive_ms":stats([r["exhaustive_ms"] for r in search])},
      "risk":risk_result,
      "conflict":{"fixture_count":len(conflicts),"correct_statuses":sum(r["correct"] for r in conflicts),
        "status_counts":dict(Counter(r["observed_status"] for r in conflicts)),
        "same_category_groups_with_multiple_operational_statuses":sum(len(v)>1 for v in groups.values())},
      "seed":SEED,"input_sha256":before}
    assert before=={p:sha(ROOT/p) for p in INPUTS},"An input hash changed"
    (OUT/"summary.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k!="input_sha256"},indent=2))
if __name__=="__main__":main()


