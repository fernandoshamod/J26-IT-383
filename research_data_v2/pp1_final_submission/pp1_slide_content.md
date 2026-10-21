# PP1 slide-ready content — 11 sections

Use these as slide text and brief speaker notes. Every numeric claim points to existing evidence. The active model is the saved Random Forest; this pack does not claim a second trained model or real-world booking validation.

## 1. Title and PP1 scope

**Slide:** PlanoVision — Vendor Intelligence & Smart Package Recommendation Engine. PP1 result: one saved Random Forest model in the dynamic package flow.

**Speaker notes:** This is an academic research simulation. The scope is vendor options, recommendations, review-rule risk, comparison and simulated feasibility. Venue suitability is a separate evidence gap. [Model status](../pp1_final_model_verification/model_status.md); [architecture](../pp1_task6_presentation/architecture_explanation.md).

## 2. Problem and research question

**Slide:** An event needs multiple service categories under budget, date, location and guest constraints. Which examined package is transparent about evidence and uncertainty?

**Speaker notes:** A candidate package can pass internal checks while real availability, quotation and collaboration remain unknown. Present uncertainty alongside the recommendation. [Feasibility audit](../yelp_lineage_gap_audit/compatibility_evidence_audit.md).

## 3. Data sources and provenance

**Slide:** 18,430 vendor profiles; 57,549 synthetic service options. Yelp-derived public/review fields support vendor context; option prices, capacities and operating assumptions are simulated.

**Speaker notes:** Do not call a synthetic option a vendor offer. Business identity and review fields have stronger source lineage than event service capabilities. [Lineage summary](../yelp_lineage_gap_audit/audit_summary.md); [lineage details](../yelp_lineage_gap_audit/data_lineage.md).

## 4. Random Forest target and features

**Slide:** Five ordered inputs: stars, review_count, collected_review_count, mean_review_rating, rating_std. Target: Low / Medium / High review-derived rule label.

**Speaker notes:** The label rule directly uses three input features. The model reproduces the rule classification; it was not trained on observed cancellations or failures. [Runtime metadata](../pp1_final_model_verification/model_runtime_metadata.json); [model summary](./pp1_model_summary.md).

## 5. Saved model and reproducibility

**Slide:** Existing 100-tree artifact loads with SHA-256 `4eed156c…aea3e6a`; three output classes; direct prediction samples saved.

**Speaker notes:** This PP1 task did not retrain. The backend checks the full artifact hash and feature order before inference. Show [prediction samples](../pp1_final_model_verification/prediction_samples.csv) or [model status](../pp1_final_model_verification/model_status.md).

## 6. Evaluation: what 100% means

**Slide:** Reconstructed holdout: 3,686 rows; accuracy = macro F1 = 100% **against deterministic review-rule labels**. Confusion matrix: High 576, Low 408, Medium 2,702 correct; zero off-diagonal.

**Speaker notes:** Original held-out IDs were not separately archived. No independent real-world failure outcomes were available. This is rule-label agreement, not failure-risk accuracy. Visual: [confusion matrix](../pp1_final_model_verification/confusion_matrix.png). Table: [classification report](../pp1_final_model_verification/classification_report.csv).

## 7. What the model uses most

**Slide:** Impurity feature importance: mean_review_rating 0.4371, rating_std 0.2087, stars 0.1921, collected_review_count 0.0897, review_count 0.0724.

**Speaker notes:** Feature importance describes splits in this saved forest, not causal vendor reliability. The high weight for review mean is consistent with the target rule. Visual: [feature importance](../pp1_final_model_verification/feature_importance.png); numbers: [CSV](../pp1_final_model_verification/feature_importance.csv).

## 8. Integration with recommendation engine

**Slide:** Create Event → FastAPI dynamic route → eligible service options → saved RF predictions → bounded package search → React result.

**Speaker notes:** Current package and Vendor Intelligence views show model classes. Numeric package risk ranking uses rule-derived favorability, with model/rule disagreement gating score availability. The AI Model dashboard metrics are a saved snapshot. [Integration trace](../pp1_final_model_verification/model_integration_trace.md); [live response](./pp1_demo_inputs_and_outputs.json).

## 9. Reproducible live event and packages

**Slide:** Wedding, 16 Nov 2026, 10:00–18:00, Philadelphia PA, 50 guests, Photography + Decoration, LKR 1m, top 3. Focused check: HTTP 200; 3 packages; top cost LKR 305,535.41; score 84.7786.

**Speaker notes:** The USER ID is new per request and the example's ID is not a promised presentation-day value. The run hit a candidate cap, so top rank is within examined options. Show [recommendation capture](../pp1_task6_presentation/screenshots/recommendations.png) and [exact current response](./pp1_demo_inputs_and_outputs.json).

## 10. Comparison and simulated feasibility

**Slide:** PKG-0001 LKR 305,535.41 versus PKG-0002 LKR 328,001.78; different second options. Top package: 10 simulation passes, 8 pending checks, 0 failures; final status `VERIFICATION_REQUIRED`.

**Speaker notes:** Comparison is within one current request. Pending checks include availability, scheduling, capacity, collaboration and venue. The category compatibility heuristic is not verified vendor-pair collaboration. Visuals: [comparison](../pp1_task6_presentation/screenshots/comparison.png), [feasibility](../pp1_task6_presentation/screenshots/feasibility.png); current [feasibility rerun](./pp1_demo_inputs_and_outputs.json).

## 11. PP1 conclusion and next evidence

**Slide:** Working saved model + active dynamic API integration + reproducible simulation demo. Remaining: verified service classification, independent operational outcomes, actual quotations/availability/collaboration, presentation-day smoke check.

**Speaker notes:** Frame the deliverable as a controlled prototype. Model accuracy for real-world failures is **NOT_VERIFIED**. The 500-guest Bensalem case remains internally budget-infeasible in V1; it is not a model failure. [Remaining risks](./pp1_remaining_risks.md); [500-guest analysis](../yelp_lineage_gap_audit/guest_capacity_pricing_analysis.md).
