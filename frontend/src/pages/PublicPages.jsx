import React, { useState } from 'react';
import { Badge, EmptyState, Icon, Kpi, Notice, PageHeader } from '../components/UI';
import { summary, percentage } from '../data/catalog';

export function Landing({ navigate }) {
  return <>
    <section className="hero card">
      <div className="hero-copy">
        <Badge tone="violet">RESEARCH-LED EVENT INTELLIGENCE</Badge>
        <h1>Plan smarter. Discover intelligent vendor combinations.</h1>
        <p>PlanoVision assembles fresh vendor packages from current synthetic service-option records for each request, then explains cost, rule-derived risk, compatibility and simulation feasibility.</p>
        <div className="button-row">
          <button className="button primary" onClick={() => navigate('create-event')}>Start event planning <Icon name="arrow" size={18}/></button>
          <button className="button ghost" onClick={() => navigate('methodology')}>Explore the methodology</button>
        </div>
        <p className="hero-caption">No bookings, confirmed availability or live quotations are provided.</p>
      </div>
      <div className="hero-panel" aria-label="Recommendation process preview">
        <span className="hero-panel-label">THE PLANOVISION WORKFLOW</span>
        {[
          ['01', 'Describe your event', 'Services, location, guests and LKR budget'],
          ['02', 'Explore fresh combinations', 'Bounded search over current option records'],
          ['03', 'Review transparent evidence', 'Cost, risk rules, compatibility and pending checks'],
        ].map(([num, title, detail]) => <div className="hero-step" key={num}>
          <span>{num}</span><div><strong>{title}</strong><small>{detail}</small></div>
        </div>)}
        <div className="hero-panel-note"><Icon name="info" size={17}/> Synthetic simulation · verification required</div>
      </div>
    </section>
    <section className="content-section">
      <div className="section-heading"><div><p className="eyebrow">HOW IT WORKS</p><h2>One request, a new search</h2></div>
        <p>Recommendations are generated at request time, not selected from saved packages.</p></div>
      <div className="feature-grid">
        {[
          ['layers', 'Dynamic packages', 'Source service options are filtered by category, event type, simulated area, capacity and budget.'],
          ['shield', 'Risk intelligence', 'An existing Random Forest classifies rule-derived vendor labels. Its outputs are not validated real-world failure predictions.'],
          ['compare', 'Compatibility rules', 'Static service-category pair scores describe category fit, not proven collaboration between vendors.'],
          ['check', 'Feasibility checks', 'Every examined complete combination is checked before ranking. Missing external evidence remains pending.'],
        ].map(([icon, title, description]) => <article className="feature-card card" key={title}>
          <span className="feature-icon"><Icon name={icon}/></span><h3>{title}</h3><p>{description}</p>
        </article>)}
      </div>
    </section>
    <section className="transparency card">
      <div><p className="eyebrow">RESEARCH TRANSPARENCY</p><h2>Evidence with clear boundaries.</h2>
        <p>Prices and service areas are synthetic estimates. Search is bounded, so results may omit other feasible combinations. Vendor availability, collaboration and outcomes require independent checks.</p></div>
      <button className="button secondary" onClick={() => navigate('admin-reports')}>Read research reports <Icon name="arrow" size={17}/></button>
    </section>
  </>;
}
export function Methodology({ navigate }) {
  const config = summary.configuration;
  return <>
    <PageHeader eyebrow="PUBLIC / METHODOLOGY" title="How recommendations are made"
      description="The production pipeline turns each event request into a bounded, explainable search."/>
    <div className="kpi-grid">
      <Kpi icon="layers" label="Candidates per service" value={config.max_candidates_per_service} note="Production default cap"/>
      <Kpi icon="chart" label="Search nodes" value={config.max_search_nodes.toLocaleString()} note="Production default cap" tone="blue"/>
      <Kpi icon="grid" label="Top recommendations" value={config.top_k} note="Default requested Top-K" tone="green"/>
    </div>
    <div className="two-column">
      <section className="card text-card"><h2>From requirements to package</h2>
        <ol className="method-steps">
          <li><strong>Validate the event.</strong> Check type, future date, times, location, guests, budget and selected services.</li>
          <li><strong>Select eligible options.</strong> Use current records for service, simulated area, type, capacity and priceable cost.</li>
          <li><strong>Search with limits.</strong> Combine one option per service with unique vendors and a budget cap; disclose truncation.</li>
          <li><strong>Check before ranking.</strong> Exclude FAIL, prioritize PASS_IN_SIMULATION, then score cost, rule-derived risk and category compatibility.</li>
          <li><strong>Explain remaining uncertainty.</strong> Return reasons, trade-offs and verification requirements.</li>
        </ol>
      </section>
      <section className="card text-card"><h2>Production scoring defaults</h2>
        <div className="weight-row"><span>Cost efficiency</span><strong>{percentage(config.production_weights.cost)}</strong></div>
        <div className="weight-row"><span>Rule-derived risk favorability</span><strong>{percentage(config.production_weights.risk)}</strong></div>
        <div className="weight-row"><span>Service-category compatibility</span><strong>{percentage(config.production_weights.compatibility)}</strong></div>
        <p>Unknown risk or compatibility components are omitted and the available weights are normalized by the backend. A higher risk favorability score is better: Low=100, Medium=60, High=20.</p>
        <Notice title="Important research limit" tone="warning">The saved model’s perfect holdout agreement concerns labels built from related review features; it does not measure real-world vendor failures.</Notice>
      </section>
    </div>
    <div className="button-row"><button className="button primary" onClick={() => navigate('create-event')}>Create an event <Icon name="arrow" size={17}/></button>
      <button className="button ghost" onClick={() => navigate('admin-reports')}>Read the research reports</button></div>
  </>;
}
export function UserDashboard({ navigate, result, locations, events = [] }) {
  const packages = result?.generation?.packages || [];
  const [today] = useState(() => new Date().toISOString().slice(0, 10));
  const upcoming = events.filter((event) => event.event_date >= today).sort((a, b) => a.event_date.localeCompare(b.event_date)).slice(0, 3);
  return <>
    <section className="dashboard-welcome card">
      <div><p className="eyebrow">EVENT MANAGEMENT / DASHBOARD</p><h1>Plan a memorable event with confidence.</h1>
        <p>Build an event brief, explore intelligent vendor combinations, and keep your saved plans in one place.</p>
        <div className="button-row"><button className="button primary" onClick={() => navigate('create-event')}>Create an event <Icon name="arrow" size={17}/></button>
          <button className="button ghost" onClick={() => navigate('saved-events')}>View my events</button></div></div>
      <div className="dashboard-welcome-art"><span className="welcome-orb">✦</span><strong>Thoughtful planning</strong><small>Recommendations shaped around your event brief.</small></div>
    </section>
    <div className="kpi-grid dashboard-kpis">
      <Kpi icon="calendar" label="Saved events" value={events.length} note="From the SQLite event store" tone="green"/>
      <Kpi icon="clock" label="Upcoming events" value={upcoming.length} note="Based on saved event dates" tone="blue"/>
      <Kpi icon="layers" label="Latest packages" value={result ? packages.length : '—'} note="From the latest request"/>
      <Kpi icon="grid" label="Supported locations" value={locations.length || '—'} note="Current synthetic service areas" tone="green"/>
    </div>
    <div className="dashboard-columns">
      <section className="card upcoming-panel"><div className="section-heading"><div><p className="eyebrow">YOUR PLANS</p><h2>Upcoming events</h2></div><button className="button ghost" onClick={() => navigate('saved-events')}>See all</button></div>
        {upcoming.length ? <div className="upcoming-list">{upcoming.map((event) => <button className="upcoming-item" key={event.event_id} onClick={() => navigate('saved-events')}><span className="date-tile"><strong>{event.event_date.slice(8, 10)}</strong><small>{event.event_date.slice(5, 7)}</small></span><span><strong>{event.event_type} in {event.city}</strong><small>{event.guest_count} guests · {event.required_services.join(' · ')}</small></span><Icon name="arrow" size={16}/></button>)}</div>
          : <EmptyState title="No upcoming events" action={<button className="button primary" onClick={() => navigate('create-event')}>Create your first event</button>}>Saved events will appear here once you complete the event brief.</EmptyState>}
      </section>
      <section className="card dashboard-next"><p className="eyebrow">NEXT STEP</p><h2>Turn your brief into options.</h2><p>Use the recommendation engine to compare estimated packages while keeping simulation limits visible.</p><div className="next-step-list"><button onClick={() => navigate('create-event')}><span>01</span><strong>Create an event brief</strong><Icon name="arrow" size={15}/></button><button onClick={() => navigate('recommendations')}><span>02</span><strong>Review recommendations</strong><Icon name="arrow" size={15}/></button><button onClick={() => navigate('methodology')}><span>03</span><strong>Understand the evidence</strong><Icon name="arrow" size={15}/></button></div></section>
    </div>
    <Notice title="Research transparency">Prices and service areas are synthetic estimates. Availability, quotations and vendor collaboration require independent confirmation.</Notice>
  </>;
}


