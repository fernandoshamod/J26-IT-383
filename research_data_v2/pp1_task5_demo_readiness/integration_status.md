# Component boundaries for PP1

| Component | Current status | Evidence boundary |
|---|---|---|
| Fresh USER-event dynamic packages; cost/capacity filtering; bounded search | Production implementation | Current options are synthetic; candidate cap can truncate search. |
| Random Forest risk inference | Production implementation | Predicts rule-generated review-feature labels; not independently validated real-world failures. Higher rule-risk score means more favorable. |
| Service-category compatibility | Production implementation | 15 category-pair rules; not named-vendor collaboration evidence. |
| Feasibility, ranking and deterministic explanations | Production implementation | USER availability, scheduling, vendor collaboration and venue suitability remain pending. |
| Operational conflict detection | Task 2 standalone research prototype | Synthetic fixture agreement only; not wired into production. |
| Shadow conflict assessment | Task 3 read-only prototype | Six packages assessed, all pending; not wired into production. |
| Shared-mask candidate optimization | Task 4 isolated prototype | Regression tested on three scenarios; not wired into production. |
| Real vendor availability and verified pair evidence | Planned | No event-specific verified observations in current source. |
| Production conflict integration and true individual-vendor baseline | Planned | Needs evidence, proposal criteria and broader regression. |
| Venue suitability / Digital Twin | External team contract proposed | Not implemented by this component; live feasibility reports pending. |

Do not present Task 2's fixture metrics, Task 3's shadow status or Task 4's timing as active production capabilities.