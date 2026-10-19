# Component 3 — Event Planning and Dynamic Resource Optimization

Scheduling engine for the proposal (J26-IT-383). Covers:

- Objective 1 — constraint formulation and schedule generation (planning phase, Section 4.2.1)
- Objective 2 — resource allocation and conflict detection (planning phase, Section 4.2.1)
- Objective 3 — Real-Time Operational Digital Twin + divergence detection (execution phase, Section 4.2.2)
- Objective 4 — discrete-event disruption simulation (execution phase, Section 4.2.2)
- Objective 5 — adaptive re-optimisation + cost signalling (execution phase, Section 4.2.2)
- Duration and vendor-lateness prediction (gradient boosting, planning phase, Section 4.2.1)

All six specific objectives named in Section 2.2 now have a corresponding
module, and so does the duration/lateness prediction model of Section
4.2.1 — see "Duration and lateness prediction" below. Objective 6's
disruption-handling half (the 200-scenario comparison against the three
baselines) is also done — see "Disruption-handling evaluation" below.

## Layout

```
scheduling_engine/
  models.py             Plain dataclasses: Activity, Resource, Event,
                         Schedule. No OR-Tools dependency — this is the
                         data both the solver and the twin consume.
  solver.py              Builds the CP-SAT model and solves it.
                         solve_planning_phase() is the public entry point.
  conflict_detection.py  Independent, solver-free verification of a
                         schedule (Section 3.6 "Correctness validation";
                         FR-03, FR-06). Also usable on a hand-edited
                         schedule that never touched the solver.
  psplib.py               Parses PSPLIB .sm benchmark instances and
                         converts them into the above types, for
                         validating the solver against the standard
                         literature benchmark (Objective 6).
  twin.py                Real-Time Operational Digital Twin: live
                         per-activity state from check-ins, and
                         divergence detection — including detecting a
                         *missing* check-in as a disruption signal on its
                         own, with no sensor involved (Section 1.4).
  simulation.py          Discrete-event (SimPy) simulation of a
                         disruption's downstream cascade across both
                         precedence and shared resources, run forward
                         from the twin's live state — without committing
                         any change. simulate_cascade() is the entry point.
  reoptimization.py      Adaptive re-optimisation: re-solves only the
                         not-yet-started remainder of the schedule as a
                         fresh, warm-started CP-SAT model, minimising the
                         WORST (max) lateness among terminal/client-facing
                         activities first and total lateness everywhere
                         else second, while honouring locked activities
                         and all resource constraints, and packages the
                         operational facts Component 4 needs into a
                         CostSignal. reoptimize() is the entry point.
  scenario_generation.py Synthetic event + disruption generator for the
                         200-scenario evaluation (Objective 6). Declared,
                         not elicited — see its module docstring and
                         "Disruption-handling evaluation" below.
  baselines.py            The two Table 5 baselines not already covered
                         by an existing module: no_reschedule and
                         naive_forward_shift. The third, "greedy", is
                         simulate_cascade reused directly — see its
                         module docstring for why.
  history_generation.py  Synthetic historical event records (declared
                         data-generating process) for training the
                         prediction models. See data/historical/README.md.
  data_preparation.py    Auditable cleaning: activity-name aliases,
                         impossible durations, missing values.
  public_data.py         Kaggle Food Delivery Dataset: download, cleaning,
                         and log-linear calibration of traffic/weather/
                         distance effects (external validation).
  public_datasets.py     Sri Lanka rain gauges, Olist and SiP: loading,
                         cleaning, leakage-safe "known-so-far" history
                         features (seller_history).
  duration_prediction.py XGBoost duration (regression) and late-vendor
                         (classification) models: tuning, baselines,
                         SHAP explanation, save/load, and the functions
                         that feed predictions into the solver.

tests/
  test_solver.py          One test per constraint type.
  test_psplib.py           Parser correctness + a solved/verified instance.
  test_twin.py            One test per divergence type the twin detects.
  test_simulation.py       Precedence cascade, resource-contention
                         cascade between activities with no precedence
                         relationship to each other, and two regression
                         tests (fixed-time floor, resource turnaround)
                         for bugs caught during development — see below.
  test_reoptimization.py   Delay absorption + cost signal; a locked
                         activity protected by RESOURCE reassignment
                         rather than being delayed; and the case where
                         that's genuinely impossible, reported by name.
  test_scenario_generation.py  Generated scenarios are feasible and
                         conflict-free under every configuration (plain,
                         buffered, generous-resources); a buffered
                         schedule really does run later on average than
                         its unbuffered twin, and generous-resources
                         really does double singleton-role capacity (not
                         a no-op in either case); disruption injection
                         produces exactly the divergence it claims to.
  test_baselines.py        Each baseline does what Table 5 says —
                         including that naive_forward_shift's blindness
                         to locks shows up as a real, detectable conflict.
  test_prediction.py       No leakage (vendor history, split, feature
                         lists), cleaning rules, models beat today's
                         practice, SHAP sums to the prediction, save/load.

examples/
  run_example.py           The proposal's own eleven-activity wedding,
                         solved concurrently with a second event
                         competing for the same florist.
  run_twin_example.py      Continues that schedule into the execution
                         phase: some activities check in on time, one
                         reports a known 40-minute delay (Section 1.1's
                         own example), one check-in goes missing — shows
                         the twin telling the two apart.
  run_simulation_example.py  The full chain: solve, detect divergence,
                         predict the cascade. One disruption (catering,
                         40 min late) happens before the fixed ceremony
                         time and is fully absorbed by its slack; a
                         second (photos' completion never confirmed)
                         happens after it, where there's no slack left,
                         and visibly cascades through to the event's end.
  run_reoptimization_example.py  Closes the loop on the same scenario:
                         re-optimises the remainder of the schedule and
                         prints the revised times plus the CostSignal
                         that would go to Component 4. Solves in ~3ms —
                         comfortably inside the 5-second target.
  validate_psplib.py       Batch harness: solves all 480 vendored PSPLIB
                         j30 instances, independently re-verifies each
                         result, and reports feasibility/conflict-free
                         rate and solve-time distribution.
  evaluate_disruption_handling.py  The 200-scenario x 4-strategy
                         disruption-handling comparison — see below.
```

## Why CP-SAT (not a genetic algorithm or MIP)

This follows Table 3 of the proposal directly. A genetic algorithm or
simulated annealing handles constraints as penalty terms in the
objective, so it can return a schedule that violates a constraint if the
penalty is outweighed elsewhere — unacceptable here, because a violated
resource constraint means a real staff member is double-booked on the
event day. CP-SAT instead either returns a schedule that satisfies every
constraint, or *proves* none exists. Mixed-integer programming gives the
same feasibility guarantee but its solve time grows too fast for the
sub-5-second re-optimisation target (that target belongs to the
execution phase, not this planning-phase build, but the method choice is
shared across both phases so it's made once, here).

## How each constraint is modelled

| Proposal concept | CP-SAT mechanism |
|---|---|
| Precedence | `start[successor] >= end[predecessor] + lag` |
| Fixed / locked times | start pinned via an **assumption literal**, not a plain hard constraint (see below) |
| Resource exclusivity | one boolean "is this candidate resource assigned" variable per (activity, candidate resource) pair, exactly `count` of them true, feeding an optional interval into `add_no_overlap` (capacity 1) or `add_cumulative` (capacity > 1) per resource |
| Minimum turnaround | the optional interval used for the exclusivity check is padded by `resource.min_turnaround_minutes` *after* the activity's real end — so the resource stays "blocked" during turnaround without changing when precedence treats the activity as finished |
| Resource duration | **not a decision variable** — taken as input, produced by the duration-prediction model (`duration_prediction.py`) |

### Why fixed/locked times use assumptions, not a plain `model.add(...)`

A plain hard constraint would make an infeasible model just say
"INFEASIBLE" with no further information. Wrapping each pinned start in
an `only_enforce_if` literal and passing those literals to
`model.add_assumptions(...)` gets the same enforcement when the model is
feasible, but when it's not, `solver.sufficient_assumptions_for_infeasibility()`
returns exactly which pinned activities are jointly responsible. That is
what `Schedule.conflicting_pinned_activity_ids` reports — a direct,
scoped answer to FR-03's "report infeasibility with the conflicting
constraints identified," for the specific case Section 3.6.1 names as the
likely real-world cause (a planner locking two things that can't both
hold).

A solver timeout (`status_name == "UNKNOWN"`) is reported distinctly from
a proven infeasibility (`status_name == "INFEASIBLE"`) — the former means
no proof either way yet, and must never be presented to a user as "no
schedule exists."

## PSPLIB validation (Objective 6)

`psplib.py` converts each generic PSPLIB resource pool (e.g. "12 units of
R1, no names attached") into 12 interchangeable named `Resource` objects,
so the already-tested solver can be reused unmodified. Running the full
480-instance j30 benchmark set (`python -m examples.validate_psplib`):
100% feasible, 100% independently-verified conflict-free, mean solve time
0.28s.

That unit-per-capacity decomposition introduces symmetry (many
interchangeable ways to pick "which unit"), which makes *proving a
minimal makespan* far slower than finding a feasible one — for no
planner-visible benefit, since feasibility is what Objective 6 actually
asks this benchmark to validate. `solve_planning_phase(..., minimize_makespan=False)`
(the harness's default) skips that search; pass `--optimize-makespan` to
the harness to re-enable it and see the difference.

## The digital twin (Objective 3)

`twin.py` picks up where the solver leaves off: it holds live
per-activity state (`ActivityTwinState`) driven only by `CheckIn` events,
and `detect_divergence(now_minutes)` compares that state against the
`Schedule` it was built from. Because a venue has no sensors (Section
1.3.3's stated obstacle to transferring manufacturing digital-twin
methods here), the twin distinguishes two different kinds of divergence,
not one:

- an explicit check-in arrived, but at a time that misses the plan
  (`START_TIME_DEVIATION` / `END_TIME_DEVIATION`) — a known, reported delay;
- no check-in arrived at all, even though the plan says one was due
  (`MISSING_START_CONFIRMATION` / `MISSING_COMPLETION_CONFIRMATION`) — the
  absence itself is the signal, which is Section 1.4's actual novelty
  claim, not a detail.

Both are governed by a per-activity tolerance (`tolerance_minutes_by_activity`,
falling back to `default_tolerance_minutes`) — Objective 3's "tolerance
thresholds at which divergence constitutes a disruption" — so ordinary
timing noise doesn't get reported as a disruption.

What's deliberately NOT here yet: nothing reacts to a `Divergence`. That's
the simulation below, and ultimately re-optimisation (Objective 5, not
built) — this module only detects and reports.

## The disruption simulation (Objective 4)

`simulate_cascade()` takes the twin's current state plus a quantified
disruption (how much extra duration an overrunning activity is predicted
to need) and runs the rest of the plan forward as SimPy processes: each
not-yet-started activity waits for its predecessors, then separately
queues for its assigned resources, exactly as the solver's own model
does. Table 4 is explicit about why discrete-event simulation is the
right tool here over Monte Carlo: it "naturally represents dependency
propagation and resource contention" — i.e. it tells you *which*
activities are affected and in what order, not just a probability over
outcomes.

Two real bugs surfaced while building this, both now locked in as
regression tests, and both worth being able to explain:

- **Symmetric resources need to hold their resource too.** A completed or
  in-progress activity doesn't call into the solver's model at all, so it
  was easy to forget that it still needs to *occupy* its assigned
  resource for the simulation's resource-contention logic to see it as
  busy. Without that, a not-yet-started activity sharing the same
  resource would wrongly see it as free immediately.
- **Fixed/locked times and resource turnaround are solver concepts that
  the simulation has to replicate, not just the shape of the DAG.** The
  first version computed each activity's readiness from precedence alone,
  ignoring `fixed_start_minutes`/`locked_start_minutes` entirely, and
  released resources immediately instead of holding them for
  `min_turnaround_minutes` afterward. Both bugs showed up the same way:
  predicted times for a *completely undisturbed* schedule didn't match
  the original plan — a good sanity check to run whenever extending this
  module (`test_resource_turnaround_matches_the_plan_with_no_disruption`
  is exactly that check, pinned down as a test).

`run_simulation_example.py` demonstrates the resulting distinction
directly: a disruption before the fixed ceremony time gets absorbed by
its slack and produces no visible cascade at all; a disruption after it
(nothing to re-anchor against) visibly delays everything downstream by
exactly the overrun amount.

## Adaptive re-optimisation (Objective 5)

`reoptimize()` builds a FRESH, smaller CP-SAT model covering only the
not-yet-started activities — completed/in-progress ones enter as fixed
facts (same anchoring idea as simulation.py, now feeding a solver instead
of a SimPy clock), including their own resource occupancy, so a
not-yet-started activity correctly queues behind them. Three choices
worth being able to defend on their own:

- **Objective minimises the worst terminal lateness first, total lateness
  second — not makespan, and not a plain summed lateness either.**
  Objective 5's job is to claw back as much of an injected disruption as
  possible — directly the proposal's own "proportion of injected delay
  absorbed" metric (Table 6, framed around what's "passed downstream to
  the client") — not to find the physically shortest event. A plain
  equally-weighted SUM of every remaining activity's lateness was tried
  first, and the 200-scenario evaluation caught a real failure mode in
  it: minimising a sum can make the event's actual ending LATER than
  doing nothing, if that frees up slack for several intermediate
  activities to each avoid a little lateness. The objective now minimises
  the worst lateness among activities nobody else depends on (the
  client-facing ends of the schedule) as the dominant term, with total
  lateness elsewhere as a secondary tie-break — see the module docstring
  for the full account, including why even a heavily-weighted SUM over
  multiple terminal activities (rather than their MAX) wasn't quite
  enough when a schedule has more than one such activity.
- **Locking an activity's TIME doesn't lock its resource.** FR-07 lets a
  planner lock an activity so re-optimisation can't move it — it says
  nothing about which resource serves it. `test_reoptimize_protects_a_locked_activity_by_reassigning_its_resource`
  constructs a case where an overrunning activity would otherwise force a
  locked one to slip, and checks that the solver instead moves the locked
  activity onto a second, identical, idle resource — keeping its time
  exactly as planned. That is itself a legitimate way to absorb a
  disruption, distinct from just shifting time, and a CP solver finds it
  automatically because resource choice is already a decision variable,
  not something bolted on afterward.
- **Warm-started from the original plan** (`model.add_hint`, seeding both
  start times and the original resource assignments) — CP-SAT doesn't
  have to honour a hint, but starting from "keep everything where it was"
  is usually close to optimal when only one activity has slipped, which
  is part of why the full wedding scenario re-solves in ~3ms, well under
  the 5-second target (`run_reoptimization_example.py`).

Scope boundary with Component 4: this module reports a `CostSignal` —
total delay, which activities were delayed, and per-resource overtime
minutes — not a currency amount. Table 8 (Individual Responsibility
Boundary) assigns "financial forecasting and what-if simulation" to
Component 4; this module's job stops at handing over the operational
facts a cost model needs, not guessing at rates and penalty clauses that
belong to a different component's domain.

## Disruption-handling evaluation (Objective 6)

`scenario_generation.py` generates randomised, plausible events (11–15
activities, matching Section 1.1's own stated typical range) and injects
one disruption of known type, magnitude and timing per scenario — all
declared placeholders, not elicited data, per Section 3.3.2's own
disclosure requirement. `evaluate_disruption_handling.py` runs four
strategies against each generated scenario: `no_reschedule` and
`naive_forward_shift` (Table 5, newly implemented in `baselines.py`),
`greedy` (Table 5's "absorb into slack, respect locks" — reused directly
from `simulate_cascade`, see `baselines.py`'s module docstring for why a
second implementation of the same idea wasn't written), and
`cp_reoptimize` (this project's own Objective 5).

**Results, 200 scenarios, three generator configurations:**

| Configuration | cp_reoptimize conflict-free | Infeasible (correct refusal) | cp delay absorbed* | cp overtime(min)* |
|---|---|---|---|---|
| Tight (original, no slack at all) | 62.0% | 76 (38.0%) | 35.2% (n=124) | 110.1 |
| Buffered (+precedence slack) | 46.4% | 105 (52.5%) | 33.3% (n=91) | 107.3 |
| Generous (+resource slack) | 64.0% | 72 (36.0%) | 59.6% (n=128) | 67.4 |
| **Slack (consumable buffer, no early starts)** | **66.3%** | **66 (33.7%)** | **84.5% (n=130)** | **41.0** |

*computed only over conflict-free outcomes — a schedule with a conflict
isn't physically realizable, so comparing its nominal end time to the
plan would be meaningless, not merely optimistic (this gating is itself
the fix for a real bug caught during development — see below). Baseline
(naive_forward_shift / greedy) numbers for all three configurations are
in the script's own output; the table above focuses on cp_reoptimize
since the three-way comparison is specifically about ITS delay-absorbed
figure.

**The headline finding, true in all three configurations:**
cp_reoptimize's conflict-free rate plus its correctly-proven-infeasible
rate always sum to **100%** — it never once produces a schedule with an
undetected conflict, regardless of how much slack exists. The baselines
cannot make that claim in any configuration: naive_forward_shift and
greedy are each broken somewhere between a third and half the time, with
no warning to the planner. This is the proposal's central thesis (Table
3's feasibility guarantee), measured directly rather than argued for, and
it holds up no matter which generator assumption is varied.

**Chasing the ≥60% delay-absorbed target — two hypotheses tested, one
first wrongly ruled out, then corrected; both confirmed:**

The tight generator's 35.2% delay-absorbed figure clearly beats both
baselines but sits below the proposal's own ≥60% target. Two different
explanations were tested empirically rather than assumed:

1. *Hypothesis: the schedule has no precedence-level slack.*
   `generate_scenario(..., include_buffer=True)` adds a declared,
   randomised contingency gap after each precedence edge — the kind of
   slack a real planner typically builds into a timeline. First result:
   apparently **ruled out**. Every metric got slightly worse
   (conflict-free 46.4%, down from 62.0%), not better.

   **Correction (re-examined later).** That test was operationalised
   wrongly. The buffer was added as `min_lag_minutes`, which the solver,
   the simulation and the re-optimiser all *enforce*: a compulsory gap
   that can never absorb anything. It tested "make every gap mandatory",
   not slack. A planner's contingency buffer is padding in the plan that
   can be used up. The corrected configuration
   (`consumable_buffer=True`) uses the same buffer to shape the plan,
   then leaves the gap free to be consumed. It also adds a realism guard:
   nothing may start before its planned time, so delay can only be
   absorbed by using up spare time, never by pulling later activities
   forward. Result: **confirmed, strongly**. CP re-optimisation absorbs
   **84.5%** of injected delay (n=130), well above the 60% target,
   with overtime down to 41 min. Without the realism guard the figure
   was 85.1%, so the gain is not an artefact of unrealistic early starts.
2. *Hypothesis: the schedule has no resource-level slack* — three of the
   five declared roles have only one unit each (deliberately realistic:
   a single wedding only needs one officiant). `generate_scenario(...,
   generous_resources=True)` gives every role 2 units instead. Result:
   **confirmed**. Delay-absorbed jumps to 59.6% — essentially at the
   target — while the conflict-free/infeasible split stays roughly the
   same (if anything, marginally better), and overtime drops by nearly
   40% (110.1 → 67.4 minutes) as a bonus side effect.

Corrected conclusion: delay absorption depends on **both** kinds of
slack, spare time in the plan *and* spare resources. A plan with neither
(the tight generator) can only absorb about 35%. That is a property of
the plan, not a limit of the re-optimiser, and it is a practical
recommendation for planners: build consumable contingency time into the
running order.

Once slack exists, even the greedy baseline absorbs a lot (81.5%). Under
slack, CP re-optimisation's added value is that it is the only strategy
that never returns a schedule with a hidden conflict (greedy: 62.8%
conflict-free, with no warning for the rest), it absorbs the most, and it
needs the least overtime (41 vs 47 min). The earlier "precedence slack
doesn't help" reading was wrong, and is kept above, corrected, rather
than deleted. All three result sets are kept and reported here rather
than one superseding another (four configurations now), per Section
3.6.1's own "threats to validity" framing — the tight generator remains the honest baseline;
the gap it shows is a property of a resource-scarce synthetic world, not
a flaw in the re-optimisation method. (Run-to-run figures can drift by a
point or two even for the same configuration — CP-SAT's parallel search
across `num_search_workers=8` isn't perfectly deterministic when the
model has tied-optimal solutions. The differences reported above, several
percentage points to tens of points, are well outside that noise.)

**Three real bugs were caught building this evaluation, each worth being
able to explain:**

1. Comparing a strategy's revised schedule to the original plan is
   meaningless when the revised schedule has a conflict — `no_reschedule`
   initially showed "100% delay absorbed" simply because it never updates
   any OTHER activity's recorded time at all, not because it handled
   anything. Fixed by computing delay-absorbed and overtime only over
   conflict-free outcomes (shown as `n=` in the tables above).
2. `inject_disruption` originally decided which activities were
   "downstream of the disruption" (and so must stay NOT_STARTED) using a
   start-time sort. Two activities can share the exact same planned start
   (parallel branches), which a sort can't distinguish — an unrelated
   parallel activity was left out of the "mark everyone else on-time"
   loop entirely, making it look disrupted too and producing artificially
   inflated cascades. Fixed by using actual precedence reachability
   instead of start-time ordering.
3. The fix for #2 was then applied too broadly: every non-descendant
   activity was marked "completed on time" purely because it finished
   before `now_minutes` by the clock — including true descendants of the
   disruption whose planned end happened to fall before `now_minutes` in
   a tightly-packed chain, which is a causality violation (a descendant
   cannot have completed before its real, overrunning predecessor did).
   The correct rule needs BOTH conditions together: a true descendant
   stays NOT_STARTED regardless of its own planned time; everything else
   is decided by comparing its own planned time to `now_minutes`. Neither
   condition alone is sufficient — both were tried separately and each
   was wrong in its own way, caught by manually tracing specific seeds
   where a re-optimised schedule's final delay exceeded the raw injected
   disruption, which should be structurally impossible unless something
   upstream of the measurement itself was wrong.

## Duration and lateness prediction (Section 4.2.1)

Files: `scheduling_engine/history_generation.py` (synthetic history),
`scheduling_engine/data_preparation.py` (cleaning),
`scheduling_engine/duration_prediction.py` (features, training,
evaluation, use), `examples/train_prediction_models.py` (the full
pipeline), `examples/run_prediction_example.py` (models feeding the
solver). Dataset card: `data/historical/README.md`.

**Data.** No public event-duration dataset exists (Section 3.3.2), so the
models train on 800 synthetic past events (8,378 activity rows, 4,000
vendor arrivals, 2022–2025). They come from a declared data-generating
process whose every effect is a named constant with a stated reason. The
raw files are deliberately dirty (inconsistent names, missing values,
impossible durations), and `data_preparation.py` cleans them with
auditable rules. Since we know the true process, we can also compute an
**oracle ceiling**: the best score any model could reach.

**Two models, both XGBoost** (gradient boosting is the proposal's locked
choice: tabular, heterogeneous, scarce data):

- *Duration* (regression, MAE objective): actual minutes for an activity.
- *Late vendor* (classification): P(vendor arrives > 10 min late, the
  twin's tolerance). A first attempt regressed exact minutes late and
  barely beat "assume on time" (MAE 10.6 vs 10.8). About 60% of arrivals
  are exactly on time and the rest are a noisy tail, so the question was
  reframed as the yes/no one the twin actually needs.

**Evaluation protocol**: chronological split (train 2022–2024, test 2025),
5-fold GroupKFold by event for tuning an 8-point grid with early stopping,
the test set used once, and three baselines including today's practice.

Results on the 206 held-out 2025 events (synthetic, so they show the
pipeline works and recovers known effects; they are *not* a real-world
accuracy claim):

| Duration model | MAE (min) | R² | within ±10 min |
|---|---|---|---|
| B0 planner estimate (today) | 11.23 | 0.68 | 60.0% |
| B1 per-activity overrun ratio | 8.90 | 0.80 | 66.7% |
| B2 linear regression | 8.11 | 0.84 | 70.2% |
| **XGBoost** | **6.41** | **0.90** | **79.5%** |
| Oracle ceiling | 5.94 | 0.91 | 81.8% |

| Late-vendor model | ROC-AUC | Avg precision | Brier |
|---|---|---|---|
| B0 no information (today) | 0.500 | 0.273 | 0.200 |
| B1 vendor's past late-rate | 0.753 | 0.508 | 0.168 |
| B2 logistic regression | 0.735 | 0.523 | 0.176 |
| **XGBoost** | **0.762** | **0.538** | **0.167** |
| Oracle ceiling | 0.775 | 0.547 | 0.162 |

- Duration error is cut by 43% against planner estimates. XGBoost closes
  91% of the gap between today's practice and the theoretical best; for
  lateness AUC it closes 95%.
- Explanation (exact TreeSHAP from XGBoost): the features with no planted
  effect (`is_weekend`, `event_type`, `vendor_category`) come out near the
  bottom. That's a sanity check real data can't offer.
- Learning curve: 25 past events already beat the planner (MAE about 8 vs
  11), and gains flatten after about 400 events.
- Used in the scheduler: for a 250-guest outdoor October wedding, predicted
  durations move the realistic end time from 19:45 to 21:30, still
  conflict-free and still holding the client's fixed 14:00 arrival. The
  lateness model flags the caterer (64%) for a confirmation call.

Figures are in `results/ml/` and every number is in `results/ml/metrics.json`.

### Public data: external validation and calibration

`scheduling_engine/public_data.py`, `examples/validate_on_public_data.py`,
results in `results/public/`.

There is still no public *event* dataset, so the **Kaggle Food Delivery
Dataset** (gauravmalik26/food-delivery-dataset, 45,593 labelled deliveries
in Indian cities, Feb–Apr 2022) is used as the closest public analogue of
one part of the problem: a vendor travelling to a site through South Asian
traffic and weather. Its rows are **never mixed into the event training
data**. It is used for two things:

**A. External validation.** The same pipeline runs on data we didn't
generate. Cleaning handles 9,131 text "NaN" values, 431 sign-flipped
coordinates, 53 impossible ratings and 3,640 unknown locations. The
evaluation uses a chronological split (last 10 days held out), GroupKFold
by day, and the same grid.

| Delivery time (held-out 10 days) | MAE (min) | R² |
|---|---|---|
| B0 overall median | 7.55 | 0.00 |
| B1 median by traffic × weather | 6.22 | 0.27 |
| B2 linear regression | 4.79 | 0.59 |
| **XGBoost** | **3.19** | **0.81** |

**B. Calibration.** A log-linear model with bootstrap 95% CIs estimates
the multiplicative effects, holding the other factors fixed. They replaced
three vendor-lateness constants in `history_generation.py` that had been
guesses:

| Effect | Public estimate (95% CI) | Assumed before | Now |
|---|---|---|---|
| traffic Jam vs Low → rush hour | ×1.30 (1.30–1.31) | ×1.6 | ×1.30 |
| weather Stormy vs Sunny → rainy month | ×1.16 (1.15–1.17) | ×1.4 | ×1.16 |
| +10 km distance | ×1.13 (1.13–1.14) | ×1.19 (doubling/40 km) | doubling/55 km |

The raw Jam/Low median ratio is ×1.55. The adjusted ×1.30 is lower because
jams coincide with other slowing factors, which is why a model that holds
them fixed is used rather than a raw ratio.

*Provenance caveat:* the uploader doesn't document collection, and some
properties suggest the data is partly simulated (near-uniform weather
categories, times bounded to 10–54 min, fixed coordinate offsets). It is
reported as a widely used public benchmark, not as field measurement.

### More public data: three more assumptions tested

`scheduling_engine/public_datasets.py`, `examples/validate_on_more_public_data.py`,
results in `results/public_more/`. Each dataset tests or calibrates one
specific assumption, and none is mixed into the event training data.

**1. Sri Lanka rainfall → which months are rainy (calibrated).** Data:
Department of Meteorology rain gauges at Dehiwala, Ratmalana and Homagama,
2012–2018, 7,638 station-days (Kaggle ivantha/sri-lanka-weather-dataset).
The rule is that a month counts as rainy if it rains (≥ 1 mm) on more than
half its days. The data says {May, Jun, **Sep**, Oct, Nov}; the original
guess {May, Jun, Oct, Nov} missed September, which gets 264 mm a month
against June's 210. `RAINY_MONTHS` now uses the data. A model-based
weather dataset (rasulmah, Open-Meteo-style) has the same seasonal shape
(r = 0.89) but reports rain on 77% of days against 40% at the gauges, so
it serves only as a cross-check. Measured gauges beat model output.

**2. Olist → real supplier lateness against a promise (tests the
late-vendor classifier).** Data: 95,195 delivered single-seller orders
from the Brazilian e-commerce marketplace Olist (Kaggle
olistbr/brazilian-ecommerce), 6.9% delivered after the promised date.
Seller history uses only outcomes *known* at purchase time: an earlier
order counts only once it has been delivered.

| Late delivery (held-out Jun–Aug 2018) | ROC-AUC | Avg precision |
|---|---|---|
| B0 base rate | 0.500 | 0.069 |
| B1 seller's past late-rate | 0.539 | 0.078 |
| B2 logistic regression | 0.704 | 0.161 |
| **XGBoost** | **0.794** | **0.280** |

The method transfers to real data. But this result **challenges an event
generator assumption**: the seller's own history ranks only 8th of 15
features. Season, promised lead time and destination dominate. The event
generator assumes vendor history is the strongest signal. That's plausible
for event vendors, who travel themselves, while Olist sellers hand parcels
to a carrier, but it is unverified until partner data arrives. It is
reported as an open question, not explained away.

**3. SiP → real estimated vs actual durations (tests the duration model
and the planning fallacy).** Data: 8,175 completed commercial software
tasks, 2004–2014 (Jones & Cullum, github.com/Derek-Jones/SiP_dataset, CC
BY-NC-ND 4.0, downloaded at run time and not redistributed). Columns
computed from actual hours are excluded as leakage. The cleaned data
reproduces the authors' published split exactly: **30% overrun, 37% exact,
33% underrun**. That's independent evidence the cleaning is right. The
mean actual/estimate ratio is 1.29 against a median of 1.00: a right-skewed
overrun tail, the same shape the event generator assumes.

| Actual hours (held-out 2012–2014) | MAE (h) | R² |
|---|---|---|
| B0 developer's estimate (today) | 4.99 | −1.27 |
| B1 estimate × category median ratio | 4.99 | −1.27 |
| B2 linear regression | 5.17 | 0.23 |
| **XGBoost** | **4.24** | **0.42** |

XGBoost cuts error 15% against the people's own estimates on real data. B1
equals B0 because every category's median ratio is exactly 1.0. Software
tasks are not event activities, so this tests the method and the shape of
the assumption, not event-specific overrun sizes.

## Live operations service and API (FR-07 to FR-16)

`scheduling_engine/integration.py`, `scheduling_engine/operations.py`,
`api/app.py`, `api/scenario.py`; tests in `tests/test_operations.py`.

`EventOperations` runs the execution-phase loop of Section 4.2.2 as one
service:

check-in (FR-08) → digital twin (FR-09) → divergence (FR-10) → simulate
the do-nothing cascade (FR-11) → re-optimise (FR-12, locks respected) →
**proposal shown to the planner** (FR-13) → on confirmation: revised plan
written back into the twin, cost signal published (FR-14), affected staff
and vendors notified (FR-15). Every step goes into an append-only,
timestamped audit log (FR-16), which is also written to `logs/audit.jsonl`.

Integration follows Section 4.3: Component 3 publishes on an event bus
(`schedule.planned`, `disruption.detected`, `proposal.created`,
`schedule.changed`, `cost_signal.issued`, …). It never calls other
components directly. `Component4Stub` subscribes to `cost_signal.issued`,
and the real Component 4 replaces it by subscribing to the same topic.

Design rules, each one found by a failing test or a live run:

- **Nothing changes without the planner** (FR-13). The system proposes;
  a person accountable to the client decides.
- **Absorbed disruptions don't interrupt.** If the simulation shows slack
  absorbs a delay (e.g. catering 40 min late before the fixed 14:00 guest
  arrival), it is logged as `disruption.absorbed` and no proposal is
  raised.
- **Stale proposals are superseded.** A proposal is valid only for the
  state it was computed from. Any new check-in supersedes it and the
  system recomputes, because confirming an outdated plan could undo what
  just happened.
- **Rejections are remembered by size.** A rejected "dinner 20 min late"
  is not re-raised at 21 minutes, but is raised again once it grows past
  the tolerance (e.g. 80 minutes).
- **Confirmed plans become the new reference.** The twin is rebuilt from
  the revised schedule and every check-in is replayed, so no observed fact
  is lost (NFR-03). Acknowledgements reset, so overrunning even the
  *revised* plan triggers again.
- **Only what's still ahead is a "change".** Completed activities are
  recorded facts and are not re-notified.

Demo story on the proposal's wedding plus a concurrent corporate launch:
catering is 40 min late (absorbed, no interruption); the photographer
never confirms completion and is detected at 16:05 from silence alone;
the system re-optimises in about 0.01 s against the 5 s target, moving 5
activities; the planner confirms; Component 4 receives 80 delay-minutes
and 6 crews on overtime; 7 staff and vendor notifications go out.

**Planner dashboard** (`api/static/index.html`): the original
`EventOps_Component3_Prototype.html` design with its hard-coded figures
replaced by live engine data. All seven screens (ops board, running
order, resources, conflicts, disruption console, re-optimisation, event
log) render from `GET /api/state`, and every button calls the engine.
Three one-click demo scenarios:

- **A: catering 40 min late.** A known delay. The simulation shows slack
  absorbs it before the fixed 14:00 guest arrival, so it is logged and
  the planner is not interrupted.
- **B: setup crew overruns.** At 15 min overdue it is absorbed. At 30
  min, doing nothing would start the *other client's* fixed 10:30
  corporate launch at 10:40, because the AV crew is shared.
  Re-optimisation keeps the launch at 10:30 and moves the wedding sound
  check to 12:40, still before 14:00.
- **ML forecasts screen.** It switches planning between the planner's
  estimates and the duration model's predictions, so the solver re-plans
  either way: the realistic day ends 21:30, not 19:45. Each prediction
  shows its TreeSHAP reasons and the model's test accuracy, and each
  vendor booking shows a late-arrival risk (caterer 64%: confirm the day
  before). In ML mode, scenario B needs no decision, because the
  realistic plan already allows enough setup time. Code:
  `api/forecast.py`, with declared demo booking inputs.
- **C: photographer goes silent.** Detected from the missing completion
  check-in alone. The cascade pushes dinner, speeches, entertainment and
  strike back by 20 min.

**Vendor and staff check-in page** (`api/static/checkin.html`, at
`/checkin`; FR-08, NFR-05, NFR-07). It is phone-first:

- Each person opens their own link (`/checkin?r=photographer-1`) and sees
  only their tasks. A check-in is **one tap** on a big button ("I've
  started" or "Done"), within NFR-05's two-interaction limit.
- **Weak signal (NFR-07).** Each check-in is saved on the phone *first*,
  with the time it was tapped, then sent. With no signal it waits in a
  local queue and is sent automatically, in tap order, when signal
  returns. The audit log marks it "queued offline, delivered at …".
- **Safe retries.** Every check-in carries a unique `client_id`. If a send
  arrived but the reply was lost, the retry is recognised and ignored, so
  it is never double-counted and never errors.
- A "Simulate no signal" switch demonstrates the queue live.
- The queue logic is pure functions, tested in Node
  (`node tests/js/test_checkin_queue.mjs`). It covers offline, a dropped
  connection mid-send, ordering, server rejection, and corrupt storage.

```
python -m uvicorn api.app:app --host 0.0.0.0   # dashboard http://127.0.0.1:8000 · phones: http://<laptop-ip>:8000/checkin
```

To check in from a real phone, put the laptop and phone on the same
network (e.g. the phone's hotspot) and allow Python through the Windows
firewall for private networks when prompted.

## Scalability (NFR-04)

`scheduling_engine/scale_generation.py`, `examples/scalability_test.py`,
results in `results/scalability/`.

NFR-04 requires at least five concurrent events, each with up to 30
activities and 40 resources, within NFR-01's 5-second limit for detection
plus re-optimisation. Each generated event has 30 of its own resources and
competes with every other event for a shared pool of 10 (AV crews,
florists, photographers, bands). Events overlap on one day. Each disruption
is a random activity overrunning by 15–60 minutes with no completion
check-in. It goes through the live `EventOperations` service, and the
timed clock tick includes detection, the do-nothing simulation and the
CP-SAT re-optimisation. Every revised plan is verified independently.

| Concurrent events | Activities | Resources | Plan (s) | Disruptions | Median (s) | Worst (s) | Within 5 s | Conflicts |
|---|---|---|---|---|---|---|---|---|
| 1 | 30 | 40 | 0.09 | 20 | 0.015 | 0.047 | 100% | 0 |
| 3 | 90 | 100 | 0.24 | 20 | 0.058 | 0.093 | 100% | 0 |
| **5 (NFR-04)** | **150** | **160** | **0.43** | **60** | **0.101** | **0.215** | **100%** | **0** |
| 6 | 180 | 190 | 0.52 | 20 | 0.120 | 0.292 | 100% | 0 |
| 8 | 240 | 250 | 1.25 | 20 | 0.148 | 3.510 | 100% | 0 |

**Verdict: PASS.** At the NFR-04 size, all 60 disruptions were fully
re-planned (no locks), the worst in 0.215 s, about 23× under the limit,
with 0 conflicts. With one planner-locked activity per event, 52 of 60
disruptions had no valid re-plan that keeps the lock, because the plans
are packed with no slack. CP-SAT proved this in under 0.09 s and named the
lock rather than returning a broken plan. Latency rises sharply only at 8
events (worst 3.5 s), which marks the practical ceiling of this
configuration.

The test also exposed a bug in the demo replay helper (`play_on_time`).
It checked in the next job of a crew that was still busy on an overrunning
activity, telling the engine one crew was in two places at once, and the
engine correctly answered "infeasible". The helper now holds back any
activity waiting for a busy resource, as well as its successors. A
regression test covers it.

```
python -m examples.scalability_test     # ~1-2 min; --quick for a smoke run
```

## Checking the ML yourself

`notebooks/ml_walkthrough.ipynb` walks through the ML step by step on the
real data files. Open it in VS Code and run the cells in order. Cells marked
✅ stop with an error if anything is wrong. It checks:

- cleaning removed exactly the bad rows counted by hand;
- vendor history uses only earlier events;
- the train and test sets don't overlap;
- retraining reproduces the saved model;
- MAE and AUC computed by hand equal the official results;
- each SHAP explanation adds up to its prediction;
- the data regenerates identically from seed 42.

It also has "what if" predictions and a warning-threshold comparison: at 0.3
the late-vendor model catches 53% of late vendors, against 20% at 0.5.

## Checking the other parts yourself

`notebooks/engine_walkthrough.ipynb` does the same for everything except the
ML, with 21 checks. It verifies every planning rule by hand on the wedding,
shows impossible fixed times refused and named, and catches a hand-broken
schedule. It also covers the twin's late and missing check-ins, the
simulation cascade, re-optimisation (including the shared AV crew and an
impossible lock), 30 evaluation scenarios with delay absorbed computed by
hand, the live service's proposal flow, and a 5-event scalability run.

The notebook found a gap in `verify_schedule`: a hand-edited schedule giving
the speeches to the photographer (the wrong role) passed, because only timing
and double-booking were checked. It now also checks that each requirement
gets the right number of resources of the right role (`WRONG_ASSIGNMENT`).
The PSPLIB and evaluation results are unchanged.

## Running it on another computer or in Google Colab

The repository is public, so the ML walkthrough runs anywhere:

- **Google Colab:** upload `notebooks/ml_walkthrough.ipynb` at
  colab.research.google.com (File → Upload notebook) and run the Setup cell.
  It clones this branch, installs the libraries (with the XGBoost and
  scikit-learn versions the models were trained with) and restarts once.
  Run Setup again, then Runtime → Run all.
- **Another computer** (Python 3.11+ and Git):

```
git clone -b event-planning-dynamic-resource-optimization/dinuja https://github.com/fernandoshamod/J26-IT-383.git
cd J26-IT-383
python -m venv venv
venv\Scripts\activate          # Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
```

  Then open `notebooks/ml_walkthrough.ipynb` in VS Code (Python and Jupyter
  extensions, kernel = venv), or run `pip install notebook` and `jupyter notebook`.

## Running it

```
pip install -r requirements.txt
python -m pytest tests/ -v
python -m examples.run_example
python -m examples.run_twin_example
python -m examples.run_simulation_example
python -m examples.run_reoptimization_example
python -m examples.validate_psplib --limit 30   # drop --limit for the full 480
python -m examples.evaluate_disruption_handling --count 20   # drop --count for the full 200 x 3 configurations
python -m examples.train_prediction_models    # ~20 s: data -> clean -> tune -> train -> evaluate -> figures
python -m examples.run_prediction_example     # needs the models saved by the line above
python -m examples.validate_on_public_data    # downloads the Kaggle data (~2 MB, no login), ~1 min
python -m examples.validate_on_more_public_data  # rainfall + Olist + SiP (~45 MB first run), ~3 min
```
