# Results and Discussion

## 1. Experimental Setup

The PlanoVision prototype was evaluated using 30 synthetic event
requirements and a hybrid vendor-service dataset. The evaluation
focused on package feasibility, recommendation coverage, ranking,
explanation consistency, and ranking sensitivity.

Vendor prices, availability, and collaboration scenarios used in
the prototype were simulated and should not be interpreted as
vendor-confirmed real-world information.

## 2. Package Feasibility Evaluation

A total of 5,037 packages were evaluated.

Of these, 2,818 packages were not
classified as failures, representing a non-failed package rate
of 55.95%.

The simulation-pass rate was
1.47%.

A simulation pass indicates that the implemented checks were
satisfied using the available synthetic evidence. It does not
confirm real-world vendor availability or feasibility.

## 3. Recommendation Coverage

The system identified at least one non-failed package for
18 out of
30 events.

The resulting event coverage was
60.00%.

Events without non-failed candidates demonstrate the system's
ability to report cases where its current constraints and
simulated evidence do not support a recommendation.

## 4. Package Ranking

A total of 2,818 non-failed packages
were ranked using a weighted scoring method.

The provisional ranking assigned 60% weight to cost efficiency
and 40% weight to evidence completeness.

These weights were predefined research assumptions rather than
empirically optimized user preferences.

## 5. Explanation Consistency

Explanations were evaluated for
18 top-ranked packages.

All 18 tested recommendations
passed the implemented explanation-consistency checks.

These checks compared validation status, check counts, and
synthetic-evidence disclosure with the generated explanations.

The results do not establish explanation faithfulness under all
perturbations or human interpretability.

## 6. Ranking Sensitivity

The ranking was compared under three weight configurations:
50/50, 60/40, and 70/30.

The top-ranked package remained unchanged for
16 events, giving a
top-1 stability rate of
88.89%.

Detailed global ranking analysis identified weight-dependent
recommendation changes for two events.

## 7. Limitations

The evaluation relied partly on synthetic service options,
pricing, availability, and collaboration scenarios.

No independent vendor-confirmed ground truth was available for
real-world recommendation accuracy or feasibility evaluation.

The reported metrics therefore demonstrate prototype behaviour,
constraint consistency, and sensitivity under the simulated
evaluation conditions rather than real-world predictive validity.

## 8. Discussion

The results indicate that PlanoVision can generate candidate
packages, apply feasibility constraints, rank non-failed
alternatives, and provide validation-based explanations.

However, recommendation coverage was incomplete, and many
packages required additional verification.

Future evaluation should include vendor-confirmed information,
real user preferences, independent recommendation-quality
benchmarks, and user-centred explanation assessments.
