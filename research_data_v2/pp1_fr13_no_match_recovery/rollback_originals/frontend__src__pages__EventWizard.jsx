import React, { useState } from 'react';
import { Badge, Icon, Notice, PageHeader, Loading } from '../components/UI';
import { EVENT_TYPES, SERVICES, money, dateForInput } from '../data/catalog';

const steps = ['Event information', 'Services & guests', 'Budget & ranking', 'Review & generate'];

export default function EventWizard({ event, setEvent, locations, locationsLoading, locationsError,
  onGenerate, loading, error }) {
  const [step, setStep] = useState(0);
  const [localError, setLocalError] = useState('');
  const [locationQuery, setLocationQuery] = useState('');
  const [minimumDate] = useState(() => dateForInput(0));
  const update = (name, value) => setEvent((previous) => ({ ...previous, [name]: value }));
  const toggleService = (service) => setEvent((previous) => ({
    ...previous,
    required_services: previous.required_services.includes(service)
      ? previous.required_services.filter((name) => name !== service)
      : [...previous.required_services, service],
  }));
  const selectedLocation = event.city && event.state ? event.city + '|' + event.state : '';
  const locationMatches = locations.filter((item) => (item.city + ', ' + item.state).toLowerCase().includes(locationQuery.toLowerCase()));
  const visibleLocations = locationQuery ? locationMatches.slice(0, 80) : locationMatches.slice(0, 40);
  const chosen = locations.find((item) => item.city + '|' + item.state === selectedLocation);
  if (chosen && !visibleLocations.some((item) => item.city + '|' + item.state === selectedLocation)) visibleLocations.unshift(chosen);
  const validate = (index) => {
    if (index === 0) {
      if (!event.event_type || !event.event_date || !event.start_time || !event.end_time)
        return 'Choose an event type, date and both event times.';
      if (event.event_date < minimumDate)
        return 'Choose today or a future event date.';
      if (!locations.some((item) => item.city === event.city && item.state === event.state))
        return 'Choose a supported location from the list.';
    }
    if (index === 1) {
      if (!Number.isInteger(Number(event.guest_count)) || Number(event.guest_count) < 1)
        return 'Guest count must be a positive whole number.';
      if (!event.required_services.length) return 'Select at least one required service.';
    }
    if (index === 2) {
      if (!Number.isFinite(Number(event.budget_lkr)) || Number(event.budget_lkr) <= 0)
        return 'Budget must be a positive LKR amount.';
      if (!Number.isInteger(Number(event.top_k)) || Number(event.top_k) < 1 || Number(event.top_k) > 50)
        return 'Choose between 1 and 50 recommendations.';
    }
    return '';
  };
  const next = () => {
    const validation = validate(step);
    setLocalError(validation);
    if (!validation) setStep(Math.min(3, step + 1));
  };
  const submit = (submitEvent) => {
    submitEvent.preventDefault();
    const validation = [0, 1, 2].map(validate).find(Boolean);
    setLocalError(validation || '');
    if (!validation) onGenerate();
  };
  return <>
    <PageHeader eyebrow="EVENT PLANNER / CREATE EVENT" title="Build your event brief"
      description="Four short steps turn your requirements into a fresh, bounded recommendation search."/>
    <div className="wizard-layout">
      <aside className="wizard-rail card" aria-label="Form progress">
        {steps.map((label, index) => <button type="button" key={label}
          className={'wizard-step' + (step === index ? ' active' : '')}
          onClick={() => { if (index < step) { setStep(index); setLocalError(''); } }}>
          <span>{index < step ? <Icon name="check" size={16}/> : index + 1}</span>
          <div><strong>{label}</strong><small>{index === step ? 'Current step' : index < step ? 'Completed' : 'Coming next'}</small></div>
        </button>)}
        <div className="rail-note"><Icon name="info" size={18}/><p>New USER event IDs are issued only when you submit this form. Nothing is saved as a plan.</p></div>
      </aside>
      <form className="wizard-main card" onSubmit={submit} noValidate>
        <div className="wizard-top"><Badge tone="violet">STEP {step + 1} OF 4</Badge><h2>{steps[step]}</h2>
          <p>{['Set the context for eligible vendor options.', 'Choose the services the package must cover exactly once.',
            'Set a positive budget and the number of results to display.', 'Confirm your inputs before the live search.'][step]}</p></div>
        {step === 0 && <div className="form-grid">
          <label className="form-field"><span>Event type</span><select value={event.event_type} onChange={(e) => update('event_type', e.target.value)}>
            {EVENT_TYPES.map((value) => <option key={value}>{value}</option>)}</select></label>
          <label className="form-field"><span>Event date</span><input type="date" min={minimumDate}
            value={event.event_date} onChange={(e) => update('event_date', e.target.value)}/></label>
          <label className="form-field"><span>Start time</span><input type="time" value={event.start_time}
            onChange={(e) => update('start_time', e.target.value)}/></label>
          <label className="form-field"><span>End time</span><input type="time" value={event.end_time}
            onChange={(e) => update('end_time', e.target.value)}/></label>
          <label className="form-field full"><span>City and state</span><input type="search" value={locationQuery}
            onChange={(e) => setLocationQuery(e.target.value)} placeholder="Search supported cities or states" aria-label="Search supported locations"/>
            <select aria-label="Supported city and state" value={selectedLocation}
            onChange={(e) => {
              const location = locations.find((item) => item.city + '|' + item.state === e.target.value);
              if (location) setEvent((previous) => ({ ...previous, city: location.city, state: location.state }));
            }}>
            <option value="">Select a supported location</option>
            {visibleLocations.map((item) => <option value={item.city + '|' + item.state} key={item.city + '|' + item.state}>
              {item.city}, {item.state}</option>)}
          </select><small>Showing up to 80 matches from the current synthetic service-area API. Type to find another location.</small></label>
          {locationsLoading && <Loading label="Loading supported locations"/>}
          {locationsError && <Notice title="Locations unavailable" tone="danger">{locationsError}</Notice>}
        </div>}
        {step === 1 && <div className="form-stack">
          <label className="form-field"><span>Guest count</span><input type="number" min="1" step="1"
            value={event.guest_count} onChange={(e) => update('guest_count', e.target.value)}/></label>
          <fieldset className="services-fieldset"><legend>Required service categories</legend>
            <div className="services-grid">{SERVICES.map(([name, description]) => <label className={'service-choice' +
              (event.required_services.includes(name) ? ' checked' : '')} key={name}>
              <input type="checkbox" checked={event.required_services.includes(name)}
                onChange={() => toggleService(name)}/>
              <span><strong>{name}</strong><small>{description}</small></span><Icon name="check" size={16}/>
            </label>)}</div></fieldset>
        </div>}
        {step === 2 && <div className="form-stack">
          <div className="form-grid">
            <label className="form-field"><span>Total budget (LKR)</span><input type="number" min="1" step="0.01"
              value={event.budget_lkr} onChange={(e) => update('budget_lkr', e.target.value)}/></label>
            <label className="form-field"><span>Ranked packages (Top-K)</span><input type="number" min="1" max="50" step="1"
              value={event.top_k} onChange={(e) => update('top_k', e.target.value)}/></label>
          </div>
          <Notice title="Production ranking criteria">Cost efficiency 40%, rule-derived low-risk favorability 40%, and service-category compatibility 20%. Unknown factors are omitted and weights renormalized by the backend. These are fixed production defaults, not user preferences.</Notice>
        </div>}
        {step === 3 && <div className="review-stack">
          <div className="review-grid">
            {[
              ['Event', event.event_type + ' · ' + event.event_date],
              ['Schedule', event.start_time + '–' + event.end_time],
              ['Location', event.city + ', ' + event.state],
              ['Guests', event.guest_count],
              ['Budget', money(event.budget_lkr)],
              ['Recommendations', event.top_k],
            ].map(([label, value]) => <div key={label}><span>{label}</span><strong>{value}</strong></div>)}
          </div>
          <div><strong>Required services</strong><div className="chip-row">{event.required_services.map((name) =>
            <Badge key={name} tone="violet">{name}</Badge>)}</div></div>
          <Notice title="Simulation disclosure" tone="warning">Packages use current synthetic option records and estimates. Availability, quotations and vendor collaboration are not independently confirmed.</Notice>
        </div>}
        {(localError || error) && <Notice title="Please review your event" tone="danger">{localError || error}</Notice>}
        <div className="wizard-actions">
          {step > 0 && <button className="button ghost" type="button"
            onClick={() => { setStep(step - 1); setLocalError(''); }}>Back</button>}
          {step < 3 ? <button className="button primary" type="button" onClick={next}>Continue <Icon name="arrow" size={17}/></button>
            : <button className="button primary" type="submit" disabled={loading || locationsLoading}>
              {loading ? 'Generating fresh packages…' : 'Generate my packages'} <Icon name="arrow" size={17}/></button>}
        </div>
      </form>
    </div>
  </>;
}





