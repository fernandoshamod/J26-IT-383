import React from 'react';
import { Badge, Notice, PageHeader } from '../components/UI';
import snapshot from '../data/vendor_conflict_research.json';

const statusText = {
  COMPATIBLE_WITH_EVIDENCE: 'No conflict in supplied simulated checks',
  CONFLICT_WITH_EVIDENCE: 'Simulated conflict detected',
  VERIFICATION_REQUIRED: 'Verification required',
};
const statusTone = {
  COMPATIBLE_WITH_EVIDENCE: 'success',
  CONFLICT_WITH_EVIDENCE: 'danger',
  VERIFICATION_REQUIRED: 'warning',
};

export default function VendorConflictResearch() {
  return <>
    <PageHeader eyebrow="RESEARCH DEMO / NOVELTY 2" title="Vendor conflict research demo"
      description="Three controlled synthetic cases show how a category planning rule differs from a named-vendor operational check."/>
    <Notice title="Synthetic test data only" tone="warning">
      Fixture times, availability claims, pair outcomes, and resource limits are simulated. Source vendor and option IDs identify records only; they do not establish real services, bookings, collaboration, or availability.
    </Notice>
    <div className="conflict-demo-explainer">
      <section className="card">
        <p className="eyebrow">CATEGORY RULE</p>
        <h2>Service-category compatibility</h2>
        <p>The recorded score comes directly from the existing category matrix. Every example below uses Photography and Decoration, so the category score stays the same.</p>
      </section>
      <section className="card">
        <p className="eyebrow">OPERATIONAL EVIDENCE</p>
        <h2>Vendor-specific conflict status</h2>
        <p>The standalone engine evaluates each supplied fixture. A resource conflict can occur even when simulated pair evidence is compatible. Missing evidence remains verification required.</p>
      </section>
    </div>
    <div className="conflict-demo-grid">
      {snapshot.examples.map((example, index) => <article className="card conflict-demo-card" key={example.fixture_id}>
        <div className="conflict-demo-head">
          <div><p className="eyebrow">SYNTHETIC EXAMPLE {index + 1}</p><h2>{example.label}</h2></div>
          <Badge tone={statusTone[example.operational_status]}>{statusText[example.operational_status]}</Badge>
        </div>
        <p className="conflict-demo-id">Fixture: <code>{example.fixture_id}</code></p>
        <div className="conflict-demo-columns">
          <section aria-label="Category compatibility"><h3>Category compatibility</h3>
            <strong className="conflict-demo-score">{example.category_score == null ? 'Unknown' : `${example.category_score}/100`}</strong>
            <p>{example.service_categories.join(' + ')}</p>
            <small>Source: {example.category_score_source || 'No recorded matrix rule'}. Category heuristic only.</small>
          </section>
          <section aria-label="Operational conflict result"><h3>Operational conflict result</h3>
            <strong>{statusText[example.operational_status]}</strong>
            {example.reason.map((reason) => <p key={reason}>{reason}</p>)}
            <small>Named pair evidence: {statusText[example.pair_evidence_status]}; IDs: {example.pair_evidence_ids.join(', ') || 'none'}.</small>
          </section>
        </div>
        <div className="conflict-demo-vendors"><h3>Vendor pair identifiers</h3>
          {example.vendors.map((vendor) => <div key={vendor.option_id}>
            <span>{vendor.service_category}</span><code>{vendor.vendor_id}</code><small>Option {vendor.option_id}</small>
          </div>)}
        </div>
        <dl className="conflict-demo-provenance">
          <div><dt>Evidence source</dt><dd>{example.evidence_source}</dd></div>
          <div><dt>Real-world availability</dt><dd>{example.real_world_availability}</dd></div>
          <div><dt>Real-world collaboration history</dt><dd>{example.real_world_collaboration_history}</dd></div>
          <div><dt>Venue suitability</dt><dd>{example.venue_suitability.replaceAll('_', ' ')}</dd></div>
        </dl>
      </article>)}
    </div>
    <p className="conflict-demo-footnote">Static research snapshot generated from {snapshot.fixture_source}, evaluated by {snapshot.engine_source}, with category scores from {snapshot.matrix_source}. This page does not submit or change event recommendations. “No conflict” covers supplied simulated checks only; unmodeled or real-world conditions remain unverified.</p>
  </>;
}
