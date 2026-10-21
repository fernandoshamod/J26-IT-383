import React from 'react';
import { Badge, EmptyState, Icon, Loading, Notice, PageHeader } from '../components/UI';
import { money } from '../data/catalog';

export default function SavedEvents({ events, loading, error, onOpen, onEdit, onDelete, onCreate }) {
  return <>
    <PageHeader eyebrow="EVENT PLANNER / MY EVENTS" title="Saved event briefs"
      description="These records are loaded from the backend SQLite database and remain available after refresh or restart."
      actions={<button className="button primary" onClick={onCreate}>Create event <Icon name="arrow" size={17}/></button>} />
    {error && <Notice title="Could not load saved events" tone="danger">{error}</Notice>}
    {loading && <Loading label="Loading saved events from SQLite" />}
    {!loading && !events.length && <EmptyState title="No saved events yet" action={<button className="button primary" onClick={onCreate}>Create your first event</button>}>Save an event brief from the Create Event screen to see the persisted record here.</EmptyState>}
    {!!events.length && <section className="saved-events-grid" aria-label="Saved events">
      {events.map((event) => <article className="card saved-event-card" key={event.event_id}>
        <div className="saved-event-head"><div><Badge tone="violet">{event.event_type}</Badge><h2>{event.city}, {event.state}</h2></div><span className="status-dot">Saved</span></div>
        <div className="saved-event-meta"><span><strong>{event.event_date}</strong><small>Date</small></span><span><strong>{event.guest_count}</strong><small>Guests</small></span><span><strong>{money(event.budget_lkr)}</strong><small>Budget</small></span></div>
        <p className="subtle">{event.required_services.join(' · ')}</p>
        <details><summary>Technical details</summary><code>{event.event_id}</code><small>Updated {event.updated_at}</small></details>
        <div className="saved-event-actions"><button className="button secondary" onClick={() => onOpen(event)}>View details</button><button className="button ghost" onClick={() => onEdit(event)}>Edit</button><button className="button danger" onClick={() => onDelete(event)}>Delete</button></div>
      </article>)}
    </section>}
  </>;
}
