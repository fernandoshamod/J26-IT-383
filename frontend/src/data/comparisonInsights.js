const known = (value) => typeof value === 'number' && Number.isFinite(value);
const lkr = (value) => 'LKR ' + value.toLocaleString('en-LK', {
  minimumFractionDigits: 2, maximumFractionDigits: 2,
});
const points = (value) => value.toFixed(1) + '/100';

/** Deterministic observations only; no inferred vendor reliability or collaboration. */
export function comparisonInsights(packages) {
  if (packages.length < 2) return [];
  const insights = [];
  const ordered = [...packages].sort((a, b) => a.rank - b.rank || a.package_id.localeCompare(b.package_id));
  const cost = ordered.filter((pkg) => known(pkg.total_cost_lkr));
  if (cost.length !== ordered.length) {
    insights.push('Estimated cost is unavailable for one or more selected packages.');
  } else {
    const lowest = [...cost].sort((a, b) => a.total_cost_lkr - b.total_cost_lkr || a.rank - b.rank)[0];
    const highest = Math.max(...cost.map((pkg) => pkg.total_cost_lkr));
    insights.push(highest === lowest.total_cost_lkr
      ? 'All selected packages have the same estimated total cost.'
      : lowest.package_id + ' has the lowest estimated cost (' + lkr(lowest.total_cost_lkr) +
        '), ' + lkr(highest - lowest.total_cost_lkr) + ' below the highest.');
  }
  const risk = ordered.map((pkg) => pkg.risk?.mean_rule_risk_score);
  if (risk.some((value) => !known(value))) {
    insights.push('Review-derived risk favorability is unknown for one or more selected packages.');
  } else if (risk.every((value) => value === risk[0])) {
    insights.push('Review-derived risk favorability is identical across these packages (' + points(risk[0]) + ').');
  } else {
    const highest = Math.max(...risk);
    insights.push('Highest recorded review-derived risk favorability: ' + points(highest) + ' for ' +
      ordered.filter((pkg) => pkg.risk.mean_rule_risk_score === highest).map((pkg) => pkg.package_id).join(', ') + '.');
  }
  const compatibility = ordered.map((pkg) => pkg.compatibility?.score);
  if (compatibility.some((value) => !known(value))) {
    insights.push('Category compatibility is unknown or not applicable for one or more selected packages.');
  } else if (compatibility.every((value) => value === compatibility[0])) {
    insights.push('Category compatibility is identical across these packages (' + points(compatibility[0]) + ').');
  } else {
    const highest = Math.max(...compatibility);
    insights.push('Highest recorded category compatibility: ' + points(highest) + ' for ' +
      ordered.filter((pkg) => pkg.compatibility.score === highest).map((pkg) => pkg.package_id).join(', ') + '.');
  }
  const services = [...new Set(ordered.flatMap((pkg) => (pkg.service_breakdown || []).map((item) => item.service)))].sort();
  if (services.length) {
    const vendorIds = services.map((service) =>
      ordered.map((pkg) => (pkg.service_breakdown || []).find((item) => item.service === service)?.vendor_id));
    const differentVendors = services.filter((_, index) => new Set(vendorIds[index]).size > 1);
    insights.push(vendorIds.some((ids) => ids.some((id) => !id))
      ? 'Vendor comparison is incomplete because one or more service vendor IDs are missing.'
      : differentVendors.length
        ? 'Selected vendors differ for ' + differentVendors.join(', ') + '.'
        : 'Selected vendor IDs are identical for all recorded services.');
  }
  const pending = ordered.map((pkg) => pkg.feasibility?.pending_checks?.length);
  if (pending.every(known)) {
    insights.push(pending.every((count) => count === pending[0])
      ? 'Each package has ' + pending[0] + ' pending external checks.'
      : 'Pending external check counts differ: ' + ordered.map((pkg, index) =>
        pkg.package_id + ' has ' + pending[index]).join('; ') + '.');
  } else {
    insights.push('Pending external check counts are unavailable for one or more selected packages.');
  }
  const statuses = [...new Set(ordered.map((pkg) => pkg.feasibility?.final_status || 'Unknown'))];
  insights.push(statuses.length === 1
    ? 'All selected packages have the same feasibility status: ' + statuses[0].replaceAll('_', ' ') + '.'
    : 'Feasibility statuses differ; inspect each package’s pending checks before contacting vendors.');
  return insights;
}


