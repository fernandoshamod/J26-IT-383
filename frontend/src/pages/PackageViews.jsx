import React, { useState } from 'react';
import { Badge, EmptyState, Icon, Loading, Notice, PageHeader, ProgressBar, StatusBadge } from '../components/UI';
import { money, percentage, score } from '../data/catalog';
import { comparisonInsights } from '../data/comparisonInsights';
import FeasibilityDashboard from './FeasibilityDashboard';

function CheckList({ title, items, tone, formatEvidence = (text) => text }) {
  return <section className="check-list"><h4><Badge tone={tone}>{items?.length || 0}</Badge> {title}</h4>
    {items?.length ? <ul>{items.map((item, index) => <li key={item.code || index}>{formatEvidence(item.message || item)}</li>)}</ul>
      : <p>None recorded.</p>}</section>;
}
export function FeasibilityDetails({ value, formatEvidence = (text) => text }) {
  if (!value) return null;
  return <div className="feasibility-details">
    <div className="feasibility-heading"><StatusBadge status={value.final_status}/>
      <span>{value.evidence_scope || 'Synthetic simulation checks only'}</span></div>
    <div className="stat-inline"><span>Estimated cost <strong>{money(value.total_cost_lkr)}</strong></span>
      <span>Remaining budget <strong>{money(value.budget_remaining_lkr)}</strong></span></div>
    <div className="check-grid">
      <CheckList title="Passed checks" items={value.passed_checks} tone="success" formatEvidence={formatEvidence}/>
      <CheckList title="Pending verification" items={value.pending_checks} tone="warning" formatEvidence={formatEvidence}/>
      <CheckList title="Failed checks" items={value.failed_checks} tone="danger" formatEvidence={formatEvidence}/>
    </div>
    <p className="subtle">PASS IN SIMULATION confirms only the recorded simulated checks. It does not confirm real availability or suitability.</p>
  </div>;
}
export function PackageDetails({ pkg }) {
  const factors = pkg.ranking_factors || {};
  const explanation = pkg.explanation || {};
  const formatEvidence = (text) => (pkg.service_breakdown || []).reduce((value, option) =>
    option.vendor_id && option.vendor_name ? value.replaceAll(option.vendor_id, option.vendor_name) : value,
    String(text));
  return <div className="package-detail">
    <div className="detail-grid">
      <section><h4>Ranking evidence</h4>
        <div className="metric-line"><span>Cost efficiency</span><strong>{percentage(factors.cost_efficiency)}</strong></div>
        <div className="metric-line"><span>Budget used</span><strong>{percentage(factors.budget_utilization)}</strong></div>
        <div className="metric-line"><span>Low-risk favorability</span><strong>{score(pkg.risk?.mean_rule_risk_score)}</strong></div>
        <div className="metric-line"><span>Category compatibility</span><strong>{pkg.compatibility?.status === 'not_applicable' ? 'Not applicable' : score(pkg.compatibility?.score)}</strong></div>
        <p className="subtle">Effective weights: cost {percentage(factors.effective_weights?.cost || 0)}, risk {percentage(factors.effective_weights?.risk || 0)}, compatibility {percentage(factors.effective_weights?.compatibility || 0)}.</p>
        {!!factors.unknown_components?.length && <p className="subtle">Omitted unknown factors: {factors.unknown_components.join(', ')}.</p>}
      </section>
      <section><h4>Why recommended</h4><ul className="detail-list">{(explanation.reasons || []).map((value, index) =>
        <li key={index}>{value}</li>)}</ul></section>
    </div>
    <div className="detail-grid">
      <section><h4>Trade-offs</h4><ul className="detail-list">{(explanation.tradeoffs || []).map((value, index) =>
        <li key={index}>{value}</li>)}</ul></section>
      <section><h4>Verification needed</h4><ul className="detail-list">{(explanation.verification_steps || []).map((value, index) =>
        <li key={index}>{formatEvidence(value)}</li>)}</ul></section>
    </div>
    <section><h4>Service-category rules</h4>
      {pkg.compatibility?.pairs?.length ? <div className="chip-row">{pkg.compatibility.pairs.map((pair) =>
        <Badge tone={pair.score == null ? 'warning' : 'neutral'} key={pair.service_1 + pair.service_2}>
          {pair.service_1} + {pair.service_2}: {score(pair.score)}</Badge>)}</div>
        : <p className="subtle">No category pair applies to a one-service package.</p>}
      <p className="subtle">These rules do not demonstrate collaboration between selected vendors. Pair scores may be identical for all packages covering the same services.</p>
    </section>
    <FeasibilityDetails value={pkg.feasibility} formatEvidence={formatEvidence}/>
  </div>;
}
function MetricHelp({ label, children }) {
  return <details className="metric-help">
    <summary aria-label={'Explain ' + label} title={'Explain ' + label}>?</summary>
    <p>{children}</p>
  </details>;
}
function CompactMetric({ label, value, help, prominent = false }) {
  return <div className={'compact-metric' + (prominent ? ' prominent' : '')}>
    <div className="compact-metric-label"><span>{label}</span>{help && <MetricHelp label={label}>{help}</MetricHelp>}</div>
    <strong>{value}</strong>
  </div>;
}
function compatibilityText(pkg) {
  return pkg.compatibility?.status === 'not_applicable' ? 'Not applicable' : score(pkg.compatibility?.score);
}
function pendingCount(pkg) {
  return pkg.feasibility?.pending_checks?.length ?? null;
}
function CopyIdentifier({ label, value }) {
  const [message, setMessage] = useState('');
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setMessage('Copied');
    } catch {
      setMessage('Copy unavailable; select the ID to copy it.');
    }
  };
  return <div className="vendor-technical-row">
    <dt>{label}</dt>
    <dd><code>{value}</code><button className="button ghost" type="button" onClick={copy}
      aria-label={'Copy ' + label}>{message === 'Copied' ? 'Copied' : 'Copy'}</button></dd>
    {message && <span className="vendor-copy-status" role="status">{message}</span>}
  </div>;
}
function SelectedVendors({ pkg }) {
  return <section className="selected-vendors" aria-label="Selected vendors and option costs">
    <div className="selected-vendors-heading"><h4>Selected vendors and option costs</h4>
      <p>Individual option prices are synthetic estimates. Review-derived risk is an indicator, not a verified real-world failure probability.</p></div>
    <div className="selected-vendor-grid">{(pkg.service_breakdown || []).map((option) =>
      <article className="selected-vendor-card" key={option.option_id}>
        <div className="selected-vendor-header"><div><span className="selected-vendor-label">Selected vendor</span>
          <h5>{option.vendor_name || 'Vendor name unavailable'}</h5></div>
          <Badge tone="violet">{option.service}</Badge></div>
        <div className="selected-vendor-fields">
          <div><span>Selected option</span><strong>{option.option_tier ? option.option_tier + ' tier' : 'Tier not recorded'}</strong></div>
          <div><span>Estimated individual option cost</span><strong className="selected-vendor-cost">{money(option.estimated_cost_lkr)}</strong></div>
          <div><span>Review-derived risk indicator</span><strong>{option.predicted_risk_level || 'Unknown'}</strong></div>
          {option.rule_risk_score != null && <div><span>Review-rule favorability</span><strong>{score(option.rule_risk_score)}</strong></div>}
        </div>
        <details className="vendor-technical-details"><summary>Technical Details</summary>
          <dl><CopyIdentifier label="Vendor ID" value={option.vendor_id}/>
            <CopyIdentifier label="Service Option ID" value={option.option_id}/></dl>
        </details>
      </article>)}</div>
    <div className="selected-vendors-total"><span>Complete estimated package total</span>
      <strong>{money(pkg.total_cost_lkr)}</strong></div>
  </section>;
}
export function PackageCard({ pkg, selected, comparisonFull, onToggleCompare, onCheck, checking }) {
  const services = pkg.service_coverage || [];
  const pending = pendingCount(pkg);
  const utilization = pkg.ranking_factors?.budget_utilization;
  return <article className="package-card recommendation-card card" data-package-id={pkg.package_id}>
    <div className="recommendation-top">
      <div><span className="rank-label">RANK {String(pkg.rank).padStart(2, '0')} · CURRENT REQUEST</span>
        <h3>Package {pkg.rank}</h3><p className="package-id">{pkg.package_id}</p></div>
      <StatusBadge status={pkg.feasibility?.final_status}/>
    </div>
    <div className="service-chip-row" aria-label="Required services covered">
      {services.map((service) => <Badge tone="violet" key={service}>{service}</Badge>)}
    </div>
    <div className="recommendation-primary">
      <CompactMetric label="Estimated total" value={money(pkg.total_cost_lkr)} prominent/>
      <CompactMetric label="Remaining budget" value={money(pkg.remaining_budget_lkr)}/>
      <CompactMetric label="Ranking score" value={score(pkg.ranking_score)}
        help="A score for ordering examined packages under this request's ranking formula. Rank is not a real-world reliability rating."/>
    </div>
    <div className="budget-meter"><div className="metric-line"><span>Event budget used</span>
      <strong>{percentage(utilization)}</strong></div>
      {utilization != null && <ProgressBar value={utilization * 100}/>}</div>
    <div className="recommendation-evidence">
      <CompactMetric label="Review-based risk favorability" value={score(pkg.risk?.mean_rule_risk_score)}
        help="Higher means more favorable under review-feature-derived risk rules. It is not a prediction of actual vendor failure."/>
      <CompactMetric label="Category compatibility" value={compatibilityText(pkg)}
        help="A service-category rule, not evidence that the selected vendors have collaborated."/>
      <CompactMetric label="Pending external checks" value={pending == null ? 'Unknown' : String(pending)}
        help="Availability, collaboration and other facts require external confirmation when evidence is missing."/>
    </div>
    <div className="quick-reason"><h4>Why this package?</h4>
      <p>It covers {services.length ? services.join(', ') : 'the recorded services'} with a ranking score of {score(pkg.ranking_score)} in the examined pool. Estimated cost is {money(pkg.total_cost_lkr)}, leaving {money(pkg.remaining_budget_lkr)}; {pending == null ? 'pending verification count is unavailable.' : pending + ' checks still need verification.'}</p>
    </div>
    <div className="package-actions">
      <label className="compare-choice"><input type="checkbox" checked={selected}
        disabled={!selected && comparisonFull}
        aria-label={'Compare ' + pkg.package_id} onChange={() => onToggleCompare(pkg.package_id)}/>
        Compare this package</label>
      <button className="button secondary" type="button" disabled={checking}
        onClick={() => onCheck(pkg)}>{checking ? 'Checking…' : 'Check feasibility'}</button>
    </div>
    <details className="package-research-details"><summary>View Research Details</summary>
      <SelectedVendors pkg={pkg}/>
      <PackageDetails pkg={pkg}/>
    </details>
  </article>;
}
function RecoveryPanel({ result, onEdit, onCreateNew }) {
  const diagnostic = result.diagnostics;
  const generation = result.generation;
  const event = result.event || {};
  const services = result.required_services || [];
  return <section className="card recovery-panel" aria-labelledby="recovery-title">
    <div className="recovery-intro">
      <Badge tone="warning">NO PACKAGE RETURNED</Badge>
      <h2 id="recovery-title">No Matching Packages Found</h2>
      <p>The current synthetic service-option records did not produce a package for this event. No substitute vendors or locations were selected.</p>
    </div>
    <h3 className="recovery-section-title">Your event</h3>
    <div className="review-grid recovery-summary">
      <div><span>Event</span><strong>{event.event_type || 'Unknown'} · {event.event_date || 'Date unknown'}</strong></div>
      <div><span>Time</span><strong>{event.start_time?.slice(0, 5) || '?'}–{event.end_time?.slice(0, 5) || '?'}</strong></div>
      <div><span>Location</span><strong>{event.city || 'Unknown'}, {event.state || 'Unknown'}</strong></div>
      <div><span>Guests</span><strong>{event.guest_count ?? 'Unknown'}</strong></div>
      <div><span>Budget</span><strong>{money(event.budget_lkr)}</strong></div>
      <div><span>Services</span><strong>{services.join(', ') || 'Unknown'}</strong></div>
    </div>
    <div className="recovery-content">
      <section className="recovery-block" aria-labelledby="recovery-reasons-title">
        <h3 id="recovery-reasons-title">Why this search returned no package</h3>
        {diagnostic?.reasons?.length ? <ul className="recovery-reasons">{diagnostic.reasons.map((reason, index) =>
          <li key={reason.code + '-' + (reason.service || index)}>
            {reason.service && <strong>{reason.service}</strong>}
            <span>{reason.message}</span>
          </li>)}</ul>
          : <p>Detailed source counts are unavailable; review the search status and try again.</p>}
        {diagnostic?.available_priceable_services_here?.length > 0 &&
          <p className="recovery-context">Priceable categories here for this event type and guest count: <strong>{diagnostic.available_priceable_services_here.join(', ')}</strong>.</p>}
        {diagnostic?.minimum_observed_package_lower_bound_lkr != null &&
          <p className="recovery-context">The sum of the lowest observed eligible prices is {money(diagnostic.minimum_observed_package_lower_bound_lkr)}. This is a lower bound, not a guaranteed package price.{diagnostic.minimum_observed_package_lower_bound_lkr > Number(event.budget_lkr) && ' Raising the budget above this bound still does not guarantee a package.'}</p>}
      </section>
      <section className="recovery-block recovery-next" aria-labelledby="recovery-next-title">
        <h3 id="recovery-next-title">What you can try</h3>
        <p>Edit the location, requested services or budget, then regenerate. A different request may produce packages; the current result will stay truthful to the selected event.</p>
        {diagnostic?.suggested_locations?.length > 0 && <>
          <h4>Locations with priceable options in every requested category</h4>
          <ul className="recovery-locations">{diagnostic.suggested_locations.map((item) =>
            <li key={item.city + '-' + item.state}>{item.city}, {item.state}</li>)}</ul>
          <p className="recovery-caveat">{diagnostic.suggestion_basis}</p>
        </>}
      </section>
    </div>
    {diagnostic && <details className="recovery-evidence"><summary>View search evidence</summary>
      <p>Location-matching source rows: {diagnostic.location_matching_rows}. Category compatibility removed {diagnostic.category_compatibility_candidates_removed} candidates; it is a ranking rule, not a vendor collaboration test.</p>
      <p>{diagnostic.search_attempted ? 'Bounded combination search was attempted.' : generation?.missing_services?.length ? 'Combination search was not started because a required candidate group was empty.' : 'Combination search was not started because the observed minimum cost exceeded the budget.'}</p>
    </details>}
    {diagnostic?.reasons?.some((reason) => reason.code === 'SEARCH_LIMIT_REACHED') &&
      <Notice title="Search was limited" tone="warning">The examined pool is incomplete; zero returned packages does not prove none exist outside it.</Notice>}
    <Notice title="Simulation data only" tone="warning">Prices and service areas are synthetic estimates. Availability, quotations and vendor collaboration are not confirmed.</Notice>
    <div className="wizard-actions recovery-actions">
      <button type="button" className="button primary" onClick={onEdit}>Edit Event</button>
      <button type="button" className="button secondary" onClick={onCreateNew}>Create new event</button>
    </div>
  </section>;
}
export function Recommendations({ result, loading, error, navigate, selectedIds, onToggleCompare,
  onCheck, checkingId, onEdit, onCreateNew, revision }) {
  const [query, setQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [showMore, setShowMore] = useState(false);
  const generation = result?.generation;
  const packages = generation?.packages || [];
  const filtered = packages.filter((pkg) => {
    const text = [pkg.package_id, ...(pkg.vendor_ids || []), ...(pkg.service_coverage || [])].join(' ').toLowerCase();
    return text.includes(query.toLowerCase()) && (statusFilter === 'all' || pkg.feasibility?.final_status === statusFilter);
  });
  const visible = showMore ? filtered : filtered.slice(0, 3);
  return <>
    <PageHeader eyebrow="EVENT PLANNER / RECOMMENDATIONS" title="Packages for your event"
      description="Fresh combinations from current service options, ranked for this USER request."
      actions={<div className="wizard-actions">{result && <button type="button" className="button secondary" onClick={onEdit}>Edit event</button>}<button type="button" className="button primary" onClick={onCreateNew}>New event <Icon name="arrow" size={17}/></button></div>}/>
    {loading && <Loading label="Searching and validating new combinations…"/>}
    {error && <Notice title="Generation failed" tone="danger">{error}</Notice>}
    {!result && !loading && <EmptyState title="No event search yet" action={<button className="button primary" onClick={onCreateNew}>Create event</button>}>
      Complete the event wizard to request a new USER event and ranked packages.</EmptyState>}
    {result && <>
      <div className="result-banner card"><div><Badge tone="violet">NEW USER EVENT</Badge><h2>{result.event_id}</h2>
        <p>{result.event?.event_type} · {result.event?.city}, {result.event?.state} · {result.event?.event_date}</p></div>
        <StatusBadge status={generation?.status}/></div>
      {revision && <Notice title={"Session revision " + revision.number}>Regenerated from {revision.previousId}. This is a new USER request; the previous result was replaced only after this response arrived. No plan is stored on a server.</Notice>}
      <Notice title={generation?.status === 'ok' ? 'Search completed' : 'Search status'}
        tone={generation?.status === 'ok' ? 'info' : 'warning'}>{generation?.message}</Notice>
      {((packages.length > 0 && (generation?.search?.candidate_limit_reached || generation?.search?.node_limit_reached)) || result.diagnostics?.reasons?.some((reason) => reason.code === "SEARCH_LIMIT_REACHED")) &&
        <Notice title="Search limit reached" tone="warning">Only examined combinations were ranked. The first package is not guaranteed to be the best possible package.</Notice>}
      {packages.length ? <>
        <div className="section-heading recommendation-heading"><div><h2>Recommended packages</h2>
          <p>Rank describes this bounded search, not verified vendor reliability. Select two or three to compare.</p></div>
          <button className="button secondary" disabled={selectedIds.length < 2}
            onClick={() => navigate('comparison')}>Compare {selectedIds.length} selected <Icon name="arrow" size={16}/></button></div>
        <div className="filter-row"><label className="search-field"><Icon name="search" size={18}/>
          <input aria-label="Search returned packages" placeholder="Search vendor, service or package ID"
            value={query} onChange={(e) => { setQuery(e.target.value); setShowMore(false); }}/></label>
          <label className="filter-select">Feasibility <select value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setShowMore(false); }}>
            <option value="all">All statuses</option><option value="PASS_IN_SIMULATION">Pass in simulation</option>
            <option value="VERIFICATION_REQUIRED">Verification required</option></select></label></div>
        {visible.length ? <div className="package-list">{visible.map((pkg) => <PackageCard key={pkg.package_id} pkg={pkg}
          selected={selectedIds.includes(pkg.package_id)} comparisonFull={selectedIds.length >= 3}
          onToggleCompare={onToggleCompare} onCheck={onCheck} checking={checkingId === pkg.package_id}/>)}</div>
          : <EmptyState title="No packages match your filters">Try another vendor, service or feasibility filter.</EmptyState>}
        {!showMore && filtered.length > 3 && <button type="button" className="button ghost show-more-packages"
          onClick={() => setShowMore(true)}>Show More Packages ({filtered.length - 3} remaining)</button>}
        {showMore && filtered.length > 3 && <button type="button" className="button ghost show-more-packages"
          onClick={() => setShowMore(false)}>Show Top Three</button>}
      </> : <RecoveryPanel result={result} onEdit={onEdit} onCreateNew={onCreateNew}/>}
      <details className="card search-research-details"><summary>How this search was bounded</summary>
        <div className="search-meta"><div className="meta-grid">
          <div><span>Returned packages</span><strong>{packages.length}</strong></div>
          <div><span>Complete combinations checked</span><strong>{generation?.search?.combinations_evaluated ?? '—'}</strong></div>
          <div><span>Search nodes visited / cap</span><strong>{generation?.search?.nodes_visited ?? '—'} / {generation?.search?.max_search_nodes ?? '—'}</strong></div>
          <div><span>Candidate cap / service</span><strong>{generation?.search?.max_candidates_per_service ?? '—'}</strong></div>
          <div><span>Failed combinations excluded</span><strong>{generation?.feasibility_counts?.FAIL ?? 0}</strong></div>
          <div><span>Selected pool upper bound</span><strong>{generation?.search?.selected_search_space_upper_bound ?? '—'}</strong></div>
        </div>
        <div className="chip-row">{Object.entries(generation?.candidate_counts || {}).map(([name, count]) =>
          <Badge key={name}>{name}: {count} eligible, {generation?.selected_candidate_counts?.[name] ?? 0} searched</Badge>)}</div>
        <p className="subtle">{generation?.ranking_formula}</p></div>
      </details>
      <Notice title="Synthetic estimates and unverified facts" tone="warning">Prices and service areas come from synthetic records. Review-derived risk is not a real-world failure prediction. Category compatibility is not vendor collaboration. Availability still needs confirmation.</Notice>
    </>}
  </>;
}
export function Comparison({ result, selectedIds, onToggleCompare, navigate }) {
  const available = result?.generation?.packages || [];
  const packages = available.filter((pkg) => selectedIds.includes(pkg.package_id)).slice(0, 3);
  const insights = comparisonInsights(packages);
  return <>
    <PageHeader eyebrow="EVENT PLANNER / COMPARISON" title="Compare your packages"
      description="Choose two or three packages from this USER request to compare actual estimates and evidence."
      actions={<button className="button ghost" onClick={() => navigate('recommendations')}>Back to recommendations</button>}/>
    {!result ? <EmptyState title="No current event packages"
      action={<button className="button primary" onClick={() => navigate('create-event')}>Create event</button>}>
      Create an event to generate new packages before comparing.</EmptyState> : <>
      <div className="result-banner card"><div><Badge tone="violet">CURRENT USER REQUEST</Badge>
        <h2>{result.event_id}</h2><p>Selections are limited to this response.</p></div>
        <Badge>{packages.length} / 3 selected</Badge></div>
      <fieldset className="comparison-picker card"><legend>Select packages to compare</legend>
        <p>Choose two or three. Selecting another package after reaching three requires removing one first.</p>
        <div className="comparison-picker-options">{available.map((pkg) => <label key={pkg.package_id}>
          <input type="checkbox" checked={selectedIds.includes(pkg.package_id)}
            disabled={!selectedIds.includes(pkg.package_id) && selectedIds.length >= 3}
            onChange={() => onToggleCompare(pkg.package_id)}/>
          <span>Rank {pkg.rank} · {pkg.package_id}</span>
        </label>)}</div>
      </fieldset>
      {packages.length < 2 ? <EmptyState title={available.length < 2 ? 'Fewer than two packages available' : 'Choose one more package'}>
        {available.length < 2 ? 'This request did not return enough packages for a side-by-side comparison.' :
          'Select two or three packages from the current request above.'}</EmptyState>
        : <>
          <section className="difference-summary card" aria-labelledby="difference-title"><h2 id="difference-title">What’s Different?</h2>
            <ul>{insights.map((line) => <li key={line}>{line}</li>)}</ul></section>
          <Notice title="Read these scores with care">Rank is limited to the examined search pool. Review-derived risk is not a real-world failure prediction; category compatibility is not verified vendor collaboration.</Notice>
          <div className="comparison-grid comparison-redesign">
            {packages.map((pkg) => <article className="comparison-card card" key={pkg.package_id}>
              <div className="comparison-sticky-head"><span className="rank-label">RANK {pkg.rank}</span>
                <h2>{pkg.package_id}</h2><StatusBadge status={pkg.feasibility?.final_status}/></div>
              <div className="comparison-row"><span>Estimated total</span><strong>{money(pkg.total_cost_lkr)}</strong></div>
              <div className="comparison-row"><span>Remaining budget</span><strong>{money(pkg.remaining_budget_lkr)}</strong></div>
              <div className="comparison-row"><div className="comparison-row-label">Ranking score <MetricHelp label="ranking score">Orders examined packages for this request; it is not a reliability rating.</MetricHelp></div><strong>{score(pkg.ranking_score)}</strong></div>
              <div className="comparison-row"><div className="comparison-row-label">Review-based risk favorability <MetricHelp label="risk favorability">Higher is more favorable under review-derived rules, not observed vendor failure risk.</MetricHelp></div><strong>{score(pkg.risk?.mean_rule_risk_score)}</strong></div>
              <div className="comparison-row"><div className="comparison-row-label">Category compatibility <MetricHelp label="category compatibility">Service-pair rule, not vendor collaboration evidence.</MetricHelp></div><strong>{compatibilityText(pkg)}</strong></div>
              <div className="comparison-row"><div className="comparison-row-label">Pending external checks <MetricHelp label="pending checks">Missing real-world evidence requires follow-up.</MetricHelp></div><strong>{pendingCount(pkg) ?? 'Unknown'}</strong></div>
              <h3>Services and vendors</h3>
              {(pkg.service_breakdown || []).map((option) => <div className="comparison-option" key={option.option_id}>
                <strong>{option.service}</strong><span>{option.vendor_name || option.vendor_id} · {option.vendor_id}</span>
                <small>{money(option.estimated_cost_lkr)} · {option.option_id}</small></div>)}
              <details className="package-research-details"><summary>View Research Details</summary>
                <PackageDetails pkg={pkg}/></details>
            </article>)}
          </div>
        </>}
    </>}
  </>;
}
export function FeasibilityPage({ result, selectedPackage, checked, checking, error, onCheck, navigate }) {
  const current = (result?.generation?.packages || []).find((pkg) => pkg.package_id === selectedPackage);
  const validated = checked?.event_id === result?.event_id ? checked : null;
  const value = validated || current?.feasibility;
  return <>
    <PageHeader eyebrow="EVENT PLANNER / FEASIBILITY" title="Package verification"
      description="See what the current USER-event simulation checked and what still needs confirmation."
      actions={<button className="button ghost" onClick={() => navigate('recommendations')}>Back to recommendations</button>}/>
    {!current ? <EmptyState title="No generated package selected"
      action={<button className="button primary" onClick={() => navigate('recommendations')}>View recommendations</button>}>
      Generate a USER event, then choose Check feasibility on one of its returned packages.</EmptyState>
      : <>
        <section className="card feas-package-header" aria-labelledby="feas-package-title">
          <div className="feas-header-top"><div><Badge tone="violet">CURRENT USER EVENT · {result.event_id}</Badge>
            <h2 id="feas-package-title">{current.package_id}</h2>
            <p>{result.event?.event_type || 'Event type unknown'} | {result.event?.city || 'City unknown'}, {result.event?.state || 'State unknown'} | {result.event?.event_date || 'Date unknown'} | {result.event?.start_time?.slice(0, 5) || '?'}-{result.event?.end_time?.slice(0, 5) || '?'} | {result.event?.guest_count ?? 'Unknown'} guests</p></div>
            <StatusBadge status={value?.final_status}/></div>
          <div className="service-chip-row" aria-label="Required services">
            {(current.service_coverage || []).map((service) => <Badge key={service}>{service}</Badge>)}
          </div>
          <div className="feas-header-bottom">
            <div><span>Estimated package cost</span><strong>{money(value?.total_cost_lkr)}</strong></div>
            <div><span>Remaining event budget</span><strong>{money(value?.budget_remaining_lkr)}</strong></div>
            <button className="button primary" onClick={() => onCheck(current)} disabled={checking}>
              {checking ? 'Checking…' : 'Rerun feasibility check'}</button>
          </div>
        </section>
        {error && <Notice title="Feasibility request failed" tone="danger">{error}</Notice>}
        {checking && <Loading label="Checking the current USER event and source options…"/>}
        <p className="feas-source-note">{validated ? 'Dedicated USER feasibility API result' :
          'Pre-ranking check from this freshly generated package'}. The result describes synthetic option evidence, not a confirmed booking.</p>
        <FeasibilityDashboard value={value} serviceBreakdown={current.service_breakdown}/>
      </>}
  </>;
}