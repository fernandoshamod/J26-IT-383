# Historical event records — dataset card

Format follows *Datasheets for Datasets* (Gebru et al., 2021), shortened.

## Why this dataset exists

The duration and vendor-lateness models (proposal Section 4.2.1, WBS task
3.6) need planned-vs-actual timings from past events. **No public dataset of
event activity durations exists** (proposal Section 3.3.2), and the industry
partner's (Blooming Moments) historical records are not yet digitised. These
files are therefore **synthetic**: produced by the documented data-generating
process (DGP) in `scheduling_engine/history_generation.py`, seed 42. No result
computed from them is presented as a real-world measurement.

The pipeline is built so the real records drop in unchanged: cleaning
(`data_preparation.py`) → features → training → evaluation never look at how
the data was made. Only the generator gets swapped.

## Files

| File | Rows | One row = |
|---|---|---|
| `raw_activity_records.csv` | 8,378 | one activity performed at one past event |
| `raw_vendor_arrivals.csv` | 4,000 | one vendor booking and how late the vendor arrived |

800 events, dated 2022-01-01 to 2025-12-31, 4 event types (wedding 50%,
corporate 25%, engagement 15%, birthday 10%), 11 activity types, 40 vendors
(8 each of florist, AV vendor, caterer, photographer, band/DJ).

### `raw_activity_records.csv`

| Column | Meaning | Known at planning time? |
|---|---|---|
| `event_id`, `event_date` | event key and date | yes |
| `event_type`, `guest_count`, `venue_type` | event attributes | yes |
| `activity_name` | **raw, inconsistent** name (e.g. "Catering Load-in", "food load in") | yes |
| `planned_start_hour`, `planned_duration_minutes` | the planner's plan | yes |
| `crew_size` | crew assigned | yes |
| `vendor_id`, `vendor_prior_jobs` | vendor and its number of earlier jobs | yes |
| `actual_duration_minutes` | **target** — what really happened | no (label) |

### `raw_vendor_arrivals.csv`

| Column | Meaning | Known at planning time? |
|---|---|---|
| `event_id`, `event_date`, `activity_name` | which event/activity | yes |
| `vendor_id`, `vendor_category` | who | yes |
| `booked_arrival_hour`, `travel_distance_km` | booking details | yes |
| `vendor_prior_jobs`, `vendor_prior_mean_lateness` | vendor's record from **strictly earlier** events only | yes |
| `lateness_minutes` | **target** — minutes after the booked time (0 = on time) | no (label) |

The model target is `lateness_minutes > 10` (the digital twin's default
tolerance).

## How it was generated (the declared assumptions)

Every effect below is a constant at the top of `history_generation.py`, with
its reason written next to it.

**Actual duration** = base workload for the activity type
× planning-fallacy overrun (speeches 1.35, photos 1.25 … entertainment 1.00, a
contracted slot; Buehler, Griffin & Ross, 1994)
× guest-count effect (dinner service +30% per +100 guests, sound check 0%)
× outdoor-in-rainy-month slowdown (+15%, rain-sensitive activities only;
rainy months = May, Jun, Sep, Oct, Nov, **calibrated** from Sri Lanka
Department of Meteorology rain gauges as months with rain on more than
half their days; the original guess missed September)
× crew-size effect (more crew helps setup/catering/strike, with diminishing returns)
× novice-vendor slowdown (+10% for a vendor with fewer than 10 past jobs)
× random noise (lognormal, σ = 0.12, which no model can predict).

**Planned duration** is the planner's estimate of the same thing. It scales
with guests at only *half* the true rate and has its own noise, so planners
underestimate, and they underestimate most for big events.

**Vendor lateness**: each vendor has a hidden "typical lateness" (some are
chronically late). The chance of being on time falls with that, rush hour
(07–08, 16–18) and rainy months. If late, the minutes scale with rush hour
(×1.30), rain (×1.16) and travel distance (doubling every 55 km), times a
right-skewed random factor.

Those three factors are **calibrated from public data**, not guessed. They
were estimated from 45,593 deliveries in the Kaggle Food Delivery Dataset,
holding other factors fixed (see the README section "Public data: external
validation and calibration"). The original guesses were ×1.6, ×1.4 and 40 km.

**Features with no planted effect**: `is_weekend` (both models),
`event_type` beyond whether there's a ceremony, and `vendor_category` for
lateness. A correct model should rank these near zero, and it does
(see `results/ml/*_feature_importance.png`). That's a built-in sanity check.

## Deliberate data-quality defects (and how cleaning handles them)

| Defect | Rate | Cleaning rule | Result (seed 42) |
|---|---|---|---|
| Inconsistent activity names | 25% of rows | explicit alias table; unknown names dropped, never guessed | 2,090 + 991 renamed, 0 unknown |
| Impossible durations (0, negative, ×10 typo) | 0.5% | drop if ≤ 0 or > 4× planned | 29 dropped |
| Missing guest count | 3% of events | **kept as missing**: XGBoost learns where missing values go | 285 rows |
| Missing travel distance | 4% | kept as missing | 161 rows |
| No vendor history (first-ever job) | by design | kept as missing | 40 rows |

## Leakage controls

- Features use only planning-time information (see the tables above).
- Vendor history features are computed from strictly earlier events. This is
  tested in `tests/test_prediction.py::test_vendor_history_features_only_use_earlier_events`.
- Chronological split: train = 2022–2024 (594 events), test = 2025 (206 events).
- Tuning uses GroupKFold by event, so no event is split across folds.
- The `oracle_*` columns (the best possible prediction, from hidden DGP values)
  exist only in memory for measuring the noise ceiling. They are not in these
  CSVs and are never used as features.

## Limitations

- Apart from the four factors calibrated from public data (three travel
  factors and the rainy months), the
  **effect sizes are assumptions**, so the accuracy numbers show the
  *pipeline works and recovers known effects*. They do not show how accurate
  the model will be on real events.
- Real data will contain effects we didn't think of (and won't contain some
  we assumed). The learning curve suggests about 100–200 real events are
  enough to beat planner estimates clearly.
- Planned next step: collect Blooming Moments' records, re-fit the DGP
  constants from them (or skip the generator entirely), and re-run
  `python -m examples.train_prediction_models` unchanged.

## Regenerate

```
python -m examples.train_prediction_models
```
