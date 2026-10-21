"""Validate native XGBoost binary TreeSHAP explanations, without model fitting."""
import numpy as np


def validate_additivity(contributions, margins, probabilities, feature_count):
    phi = np.asarray(contributions, dtype=np.float64)
    margin = np.asarray(margins, dtype=np.float64)
    probability = np.asarray(probabilities, dtype=np.float64)
    if phi.ndim != 2 or phi.shape[1] != feature_count + 1 or phi.shape[0] == 0:
        raise ValueError('invalid_contribution_dimensions')
    if margin.shape != (len(phi),) or probability.shape != margin.shape:
        raise ValueError('invalid_prediction_dimensions')
    if not all(np.isfinite(x).all() for x in (phi, margin, probability)):
        raise ValueError('nonfinite_explanation')
    if ((probability < 0) | (probability > 1)).any():
        raise ValueError('invalid_probability')
    errors = np.abs(phi.sum(axis=1) - margin)
    if not np.allclose(phi.sum(axis=1), margin, rtol=1e-5, atol=5e-5):
        raise ValueError('shap_margin_reconciliation_failed')
    sigmoid = np.exp(-np.logaddexp(0., -margin))
    probability_errors = np.abs(sigmoid - probability)
    if not np.allclose(sigmoid, probability, rtol=1e-5, atol=2e-6):
        raise ValueError('margin_probability_reconciliation_failed')
    return {'status': 'PASS', 'rows': len(phi), 'maximum_margin_error': float(errors.max()),
            'maximum_probability_error': float(probability_errors.max()),
            'scale': 'raw_binary_log_odds_not_probability_points',
            'last_column': 'model_bias_term'}


def summarize_features(contributions, predictors, weights):
    phi = np.asarray(contributions, dtype=np.float64)
    w = np.asarray(weights, dtype=np.float64)
    if phi.ndim != 2 or phi.shape[1] != len(predictors) + 1 or w.shape != (len(phi),) or len(phi) == 0:
        raise ValueError('invalid_summary_dimensions')
    if not np.isfinite(phi).all() or not np.isfinite(w).all() or (w <= 0).any():
        raise ValueError('invalid_summary_weights_or_values')
    absolute = np.abs(phi[:, :-1])
    row_mean = absolute.mean(axis=0)
    grouped = np.average(absolute, weights=w, axis=0)
    return sorted([{'feature': name, 'mean_absolute_shap_row_weighted': float(row_mean[i]),
                    'mean_absolute_shap_group_equal': float(grouped[i])}
                   for i, name in enumerate(predictors)],
                  key=lambda r: (-r['mean_absolute_shap_group_equal'], r['feature']))
