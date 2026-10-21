import React from 'react';
import { Badge, EmptyState, Icon, StatusBadge } from '../components/UI';
import { money } from '../data/catalog';
import { buildFeasibilityView } from '../data/feasibilityViewModel';

const displayCount = (count) => count == null ? 'Unknown' : count;
function outcomeText(status, counts, total) {
  if (total === null) return 'The check breakdown is unavailable. Review the original response before drawing conclusions.';
  if (total === 0) return 'No checks were recorded for this package. The displayed status cannot be explained by individual checks.';
  if (status === 'FAIL') return counts.failed + ' recorded check' + (counts.failed === 1 ? '' : 's') +
    ' failed. This package did not pass the simulation checks.';
  if (status === 'VERIFICATION_REQUIRED') return counts.passed + ' recorded checks passed in the simulation; ' +
    counts.pending + ' still need confirmation. The package is not verified for a real event.';
  if (status === 'PASS_IN_SIMULATION') return 'All ' + counts.passed +
    ' recorded checks passed in this simulation. Real-world availability and booking are not confirmed.';
  return 'The backend returned an unrecognized status. Inspect the recorded checks below.';
}
function CountTile({ label, count, tone }) {
  return <div className={'feas-count-tile feas-count-' + tone}>
    <strong>{displayCount(count)}</strong><span>{label}</span>
  </div>;
}
function CheckSegments({ counts, total }) {
  if (total === null || total === 0) return <p className="subtle">No complete check count is available for a chart.</p>;
  const segments = [
    ['passed', counts.passed], ['pending', counts.pending], ['failed', counts.failed],
  ];
  return <div className="feas-segments" role="img"
    aria-label={counts.passed + ' passed, ' + counts.pending + ' pending, ' +
      counts.failed + ' failed, out of ' + total + ' recorded checks'}>
    {segments.map(([status, count]) => count > 0 && <span key={status}
      className={'feas-segment feas-segment-' + status} style={{ flexGrow: count }}
      aria-hidden="true"/>)}
  </div>;
}
function GroupCards({ groups, kind }) {
  if (!groups.length) return <p className="feas-empty-copy">No {kind} checks were recorded.</p>;
  return <div className="feas-group-grid">{groups.map((group) => <article
    className={'feas-group-card feas-group-' + kind} key={group.key}>
    <div className="feas-group-icon"><Icon name={kind === 'pending' ? 'clock' : 'check'} size={19}/></div>
    <div><h3>{group.title}</h3><p>{group.items.length} recorded {group.items.length === 1 ? 'check' : 'checks'} · {kind === 'pending' ? 'confirmation needed' : 'passed in simulation'}</p>
      {!!group.services.length && <div className="feas-group-services" aria-label="Affected services">
        {group.services.map((service) => <Badge key={service}>{service}</Badge>)}</div>}
    </div>
  </article>)}</div>;
}
function RawCheckList({ title, checks, tone }) {
  return <details className="feas-raw-group">
    <summary><span>{title}</span><Badge tone={tone}>{checks?.length ?? 'Unknown'}</Badge></summary>
    {checks == null ? <p>Check details were not included in the response.</p>
      : checks.length === 0 ? <p>No {title.toLowerCase()} recorded.</p>
        : <ol>{checks.map((check, index) => <li key={index}>
          <div className="feas-raw-meta"><code>{check.code || 'Code unavailable'}</code>
            <strong>{check.status || 'Unknown'}</strong></div>
          <p>{check.message || 'Message unavailable'}</p>
          <small>Evidence origin: {check.evidence_origin || 'Unknown'}</small>
        </li>)}</ol>}
  </details>;
}
export default function FeasibilityDashboard({ value, serviceBreakdown }) {
  if (!value) return <EmptyState title="No feasibility evidence returned">
    Run the USER feasibility check to inspect the recorded result.</EmptyState>;
  const view = buildFeasibilityView(value, serviceBreakdown);
  const { counts, total } = view;
  return <div className="feas-dashboard">
    <section className={'feas-outcome card feas-outcome-' + String(value.final_status || '').toLowerCase()}
      aria-labelledby="feas-outcome-title">
      <div className="feas-outcome-icon"><Icon name={value.final_status === 'FAIL' ? 'warning' : 'shield'} size={25}/></div>
      <div><p className="eyebrow">FEASIBILITY OUTCOME</p><h2 id="feas-outcome-title">
        {value.final_status === 'VERIFICATION_REQUIRED' ? 'Further confirmation is needed' :
          value.final_status === 'FAIL' ? 'Simulation checks found a problem' :
            value.final_status === 'PASS_IN_SIMULATION' ? 'Recorded simulation checks passed' : 'Status needs review'}
      </h2><p>{outcomeText(value.final_status, counts, total)}</p>
        <StatusBadge status={value.final_status}/></div>
    </section>
    <section className="card feas-counts" aria-labelledby="feas-count-title">
      <div className="feas-section-heading"><div><p className="eyebrow">RECORDED CHECKS</p>
        <h2 id="feas-count-title">Check summary</h2></div>
        <span>{total == null ? 'Total unknown' : total + ' total recorded checks'}</span></div>
      <div className="feas-count-grid">
        <CountTile label="Passed in simulation" count={counts.passed} tone="passed"/>
        <CountTile label="Pending confirmation" count={counts.pending} tone="pending"/>
        <CountTile label="Failed" count={counts.failed} tone="failed"/>
      </div>
      <CheckSegments counts={counts} total={total}/>
      <p className="subtle">Bar lengths represent recorded check counts only. They are not a real-world readiness or reliability score.</p>
    </section>
    {counts.failed > 0 && <section className="card feas-summary-section feas-failed-section">
      <div className="feas-section-heading"><h2>Checks that failed</h2><Badge tone="danger">{counts.failed}</Badge></div>
      <p>Review the failed raw checks in Research Details before considering this package.</p>
    </section>}
    <section className="card feas-summary-section" aria-labelledby="feas-pending-title">
      <div className="feas-section-heading"><div><p className="eyebrow">NEXT STEPS</p>
        <h2 id="feas-pending-title">What Still Needs Confirmation?</h2></div>
        <Badge tone="warning">{displayCount(counts.pending)} pending</Badge></div>
      <GroupCards groups={view.pendingGroups} kind="pending"/>
    </section>
    <section className="card feas-summary-section" aria-labelledby="feas-passed-title">
      <div className="feas-section-heading"><div><p className="eyebrow">SIMULATION EVIDENCE</p>
        <h2 id="feas-passed-title">Checks Already Satisfied</h2></div>
        <Badge tone="success">{displayCount(counts.passed)} passed</Badge></div>
      <GroupCards groups={view.passedGroups} kind="passed"/>
    </section>
    <details className="card feas-research-details">
      <summary>Research Details <span>Every original check, status, vendor ID and message</span></summary>
      <div className="feas-research-body">
        <p>{value.evidence_scope || 'Evidence scope unavailable.'}</p>
        <div className="feas-raw-metrics"><span>Event ID <strong>{value.event_id || 'Unknown'}</strong></span>
          <span>Estimated cost <strong>{money(value.total_cost_lkr)}</strong></span>
          <span>Budget <strong>{money(value.budget_lkr)}</strong></span>
          <span>Remaining <strong>{money(value.budget_remaining_lkr)}</strong></span><span>Real-world verification <strong>{value.is_real_world_feasible == null ? 'Unknown' : value.is_real_world_feasible ? 'Backend marked feasible' : 'Not verified'}</strong></span></div>
        <RawCheckList title="Passed checks" checks={view.passed} tone="success"/>
        <RawCheckList title="Pending checks" checks={view.pending} tone="warning"/>
        <RawCheckList title="Failed checks" checks={view.failed} tone="danger"/>
      </div>
    </details>
  </div>;
}

