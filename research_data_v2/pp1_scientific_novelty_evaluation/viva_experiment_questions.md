# Five viva questions on the baseline experiments

1. **Was the cost-only baseline genuinely fair?**  
   Both methods sorted the same validated package pool for each event, so ranking differences are paired and constraints are identical. However, the production candidate selector reserves slots using risk scores before either sort. This makes the comparison fair **conditional on that examined pool**, not a full-universe neutral cost baseline. A future baseline must control candidate selection too.

2. **Why claim an improvement when seven of eight top packages were identical?**  
   I claim only a measured trade-off in one synthetic case: +20 review-rule favorability points for +LKR 4,181.03. The median paired difference is zero. This does not establish user benefit or real reliability; larger, independently sampled cases and user outcomes are needed.

3. **Does zero best-score regret prove bounded DFS is optimal?**  
   No. Zero regret was observed against exhaustive enumeration in eight small two-service cases. Five cases hit the candidate cap, and three feasible combinations were missed in one case. Other inputs can have positive regret; this experiment does not bound it globally.

4. **Why does the Random Forest have 100% accuracy, and does it beat a rule-only baseline?**  
   Its target labels were generated deterministically from review-related features. On the reconstructed 3,686-row holdout, the saved model and exact rule both scored 1.000 accuracy and macro-F1, with zero disagreements. That is rule imitation, not prediction of observed vendor failures.

5. **What do the 12/12 operational conflict fixture results prove?**  
   They show the standalone engine returns the authored compatible, conflict and verification-required statuses for 12 synthetic test cases. Category scores alone cannot distinguish all those cases. The fixtures do not prove current vendor availability, actual pair collaboration, equipment inventory or venue feasibility.
