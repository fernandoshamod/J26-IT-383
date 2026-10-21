# Ten challenging PP1 viva questions and concise answers

1. **What is new if The Knot and Zola already recommend vendors?**  
   The individual algorithms are not new. The proposed contribution is a transparent, event-specific integration of constraint filtering, bounded multi-vendor package construction, declared ranking factors, explanations and explicit unknown evidence. I have not shown superiority to either commercial system, whose private algorithms are not publicly documented.

2. **Does 100% Random Forest accuracy mean vendors are reliable?**  
   No. The measured target is a deterministic review-derived label. Accuracy measures rule-label agreement on a reconstructed holdout, not actual delivery failures or future booking outcomes. Independent outcome labels and external validation are needed.

3. **Is the model probability used as the ranking risk score?**  
   No. The model supplies a class and a model-rule agreement check. The numeric risk favorability used in ranking is the existing rule-derived score; it is not a calibrated failure probability. See [inference](../../backend/engine/risk_signals.py) and [ranking](../../backend/engine/bounded_package_generator.py).

4. **Are your generated packages optimal?**  
   Only within the examined bounded candidate pool. The default per-service candidate cap is 12 and the node cap is 5,000. A reached limit is disclosed. Exhaustive comparison on tractable subsets is needed to estimate ranking regret.

5. **How do you know a vendor actually offers the displayed service?**  
   I do not. Historical Yelp-derived names, categories and review fields are distinct from synthetic service-option assignments. Those assignments and prices are simulation inputs, not verified offerings or quotes.

6. **Can the compatibility score distinguish two pairs of vendors in the same categories?**  
   The production score cannot; it comes from a category matrix. The separate synthetic conflict fixture page shows how two named pairs can have different scoped operational outcomes, but no real collaboration history is verified.

7. **What does VERIFICATION_REQUIRED mean when ten checks pass?**  
   The passed checks are within recorded simulation data. Eight other checks can still require capacity, availability, setup/travel, collaboration or venue confirmation. Missing evidence is not converted into a pass.

8. **What is your strongest evidence that your ranking is better than cost-only?**  
   I do not yet have independent evidence of improved real-world decisions. A saved synthetic comparison exists, but its cost-only baseline uses an already selected candidate pool. A fairer ablation on the same untruncated options and user/outcome evaluation remains future work.

9. **Why not deploy the Sri Lankan pilot in the recommendation engine now?**  
   The pilot is separate and lacks the review features, verified service offerings, prices, capacities and availability needed for the current workflow. Inserting guessed values to make it run would undermine validity. Permission-based enrichment and schema validation are needed first.

10. **How would you test the claimed research gap scientifically?**  
    Pre-register event scenarios and outcomes; compare constrained ranking with cost-only, greedy and relevant package baselines on identical data; assess coverage, budget/capacity violations, runtime, truncation and top-K regret against exhaustive search where feasible. Then use independent operational labels and a blinded explanation-utility study. Current PP1 evidence verifies implementation and synthetic behavior, not this full comparative claim.

See [claim–evidence matrix](./claim_evidence_matrix.md) for the exact validation status of each contribution.
