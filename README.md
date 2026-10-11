# Component 3 — Event Planning and Dynamic Resource Optimization

Scheduling engine for the proposal (J26-IT-383). Covers:

- Objective 1 — constraint formulation and schedule generation (planning phase, Section 4.2.1)
- Objective 2 — resource allocation and conflict detection (planning phase, Section 4.2.1)
- Objective 3 — Real-Time Operational Digital Twin + divergence detection (execution phase, Section 4.2.2)
- Objective 4 — discrete-event disruption simulation (execution phase, Section 4.2.2)
- Objective 5 — adaptive re-optimisation + cost signalling (execution phase, Section 4.2.2)

All six specific objectives named in Section 2.2 now have a corresponding
module except the duration/lateness prediction model mentioned alongside
the planning phase in Section 4.2.1. Objective 6's disruption-handling
half (the 200-scenario comparison against the three baselines) is also
done — see "Disruption-handling evaluation" below.

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
| Resource duration | **not a decision variable** — taken as input, standing in for the (separate) duration-prediction model's output |

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
| **Generous (+resource slack)** | **64.0%** | **72 (36.0%)** | **59.6% (n=128)** | **67.4** |

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
ruled out, one confirmed:**

The tight generator's 35.2% delay-absorbed figure clearly beats both
baselines but sits below the proposal's own ≥60% target. Two different
explanations were tested empirically rather than assumed:

1. *Hypothesis: the schedule has no precedence-level slack.*
   `generate_scenario(..., include_buffer=True)` adds a declared,
   randomised contingency gap after each precedence edge — the kind of
   slack a real planner typically builds into a timeline. Result: **ruled
   out**. Every metric got slightly worse (conflict-free 46.4%, down from
   62.0%), not better.
2. *Hypothesis: the schedule has no resource-level slack* — three of the
   five declared roles have only one unit each (deliberately realistic:
   a single wedding only needs one officiant). `generate_scenario(...,
   generous_resources=True)` gives every role 2 units instead. Result:
   **confirmed**. Delay-absorbed jumps to 59.6% — essentially at the
   target — while the conflict-free/infeasible split stays roughly the
   same (if anything, marginally better), and overtime drops by nearly
   40% (110.1 → 67.4 minutes) as a bonus side effect.

This is a clean result precisely because the two experiments point in
different directions: precedence slack doesn't help, resource slack does,
isolating resource contention (not schedule tightness in general) as the
actual lever. All three result sets are kept and reported here rather
than one superseding another, per Section 3.6.1's own "threats to
validity" framing — the tight generator remains the honest baseline;
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
```
