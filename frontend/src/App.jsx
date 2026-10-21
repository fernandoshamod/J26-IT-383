import React, { useEffect, useRef, useState } from 'react';
import AppShell from './components/AppShell';
import { adminNav, adminWorkspaceNav, publicNav, researchNav, userNav, vendorNav } from './data/navigation';
import { Methodology, UserDashboard } from './pages/PublicPages';
import SavedEvents from './pages/SavedEvents';
import EventWizard from './pages/EventWizard';
import VendorConflictResearch from './pages/VendorConflictResearch';
import { Recommendations, Comparison, FeasibilityPage } from './pages/PackageViews';
import { AdminOverview, VendorIntelligence, ServiceOptionExplorer, ModelMonitoring,
  RecommendationAnalytics, CompatibilityIntelligence, ResearchReports } from './pages/AdminPages';
import { dateForInput } from './data/catalog';
import AdminWorkspace from './pages/AdminWorkspace';
import VendorPortal from './pages/VendorPortal';
import { createSavedEvent, deleteSavedEvent, generateDynamic, getLocations, getSavedEvents, updateSavedEvent, validateDynamic } from './services/api';
import './App.css';

const validPages = new Set([...publicNav, ...userNav, ...vendorNav, ...researchNav, ...adminNav, ...adminWorkspaceNav].map(([id]) => id));
const fromHash = () => {
  const page = window.location.hash.replace(/^#\/?/, '');
  return validPages.has(page) ? page : 'home';
};
const defaultEvent = (locations) => {
  const preferred = locations.find((item) => item.city === 'Philadelphia' && item.state === 'PA') || locations[0];
  return {
    event_type: 'Wedding', event_date: dateForInput(),
    start_time: '10:00', end_time: '18:00', city: preferred?.city || '', state: preferred?.state || '',
    guest_count: 50, budget_lkr: 1000000, top_k: 10,
    required_services: ['Photography', 'Decoration'],
  };
};
const editableEvent = (result) => ({
  event_type: result.event.event_type,
  event_date: result.event.event_date,
  start_time: result.event.start_time.slice(0, 5),
  end_time: result.event.end_time.slice(0, 5),
  city: result.event.city,
  state: result.event.state,
  guest_count: result.event.guest_count,
  budget_lkr: result.event.budget_lkr,
  top_k: result.generation?.search?.top_k ?? 10,
  required_services: [...result.required_services],
});

export default function App() {
  const [page, setPage] = useState(fromHash);
  const [locations, setLocations] = useState([]);
  const [savedEvents, setSavedEvents] = useState([]);
  const [savedEventsLoading, setSavedEventsLoading] = useState(true);
  const [savedEventsError, setSavedEventsError] = useState('');
  const [locationsLoading, setLocationsLoading] = useState(true);
  const [locationsError, setLocationsError] = useState('');
  const [event, setEvent] = useState(() => defaultEvent([]));
  const [result, setResult] = useState(null);
  const [generationLoading, setGenerationLoading] = useState(false);
  const [generationError, setGenerationError] = useState('');
  const [editing, setEditing] = useState(false);
  const [revision, setRevision] = useState(null);
  const [selectedIds, setSelectedIds] = useState([]);
  const [selectedPackage, setSelectedPackage] = useState('');
  const [feasibilityResult, setFeasibilityResult] = useState(null);
  const [feasibilityLoading, setFeasibilityLoading] = useState(false);
  const [feasibilityError, setFeasibilityError] = useState('');
  const [researchView, setResearchView] = useState('simple');
  const generationSerial = useRef(0);
  const feasibilitySerial = useRef(0);

  useEffect(() => {
    const onHashChange = () => {
      const next = fromHash();
      if (next === 'home' && window.location.hash && !['#home', '#/home'].includes(window.location.hash)) {
        window.history.replaceState(null, '', '#home');
      }
      setPage(next);
    };
    onHashChange();
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);
  useEffect(() => {
    let active = true;
    getSavedEvents().then((data) => { if (active) setSavedEvents(data.events || []); }).catch((caught) => { if (active) setSavedEventsError(caught.message); }).finally(() => { if (active) setSavedEventsLoading(false); });
    getLocations().then((data) => {
      if (!active) return;
      const values = data.locations || [];
      setLocations(values);
      const preferred = values.find((item) => item.city === 'Philadelphia' && item.state === 'PA') || values[0];
      if (preferred) setEvent((previous) => previous.city ? previous : {
        ...previous, city: preferred.city, state: preferred.state,
      });
    }).catch((caught) => { if (active) setLocationsError(caught.message); })
      .finally(() => { if (active) setLocationsLoading(false); });
    return () => { active = false; };
  }, []);

  const navigate = (next) => {
    if (!validPages.has(next) && !(next === 'vendor' || next.startsWith('vendor/'))) return;
    if (window.location.hash !== '#' + next) window.location.hash = next;
    setPage(next);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };
  const createNewEvent = () => {
    generationSerial.current += 1;
    feasibilitySerial.current += 1;
    setEditing(false);
    setGenerationLoading(false);
    setEvent(defaultEvent(locations));
    setGenerationError('');
    navigate('create-event');
  };
  const editEvent = () => {
    if (!result) return;
    generationSerial.current += 1;
    feasibilitySerial.current += 1;
    setEvent(editableEvent(result));
    setGenerationLoading(false);
    setGenerationError('');
    setEditing(true);
    navigate('create-event');
  };
  const cancelEdit = () => {
    generationSerial.current += 1;
    setGenerationLoading(false);
    setGenerationError('');
    setEvent(editableEvent(result));
    setEditing(false);
    navigate('recommendations');
  };
  const generate = async () => {
    const serial = ++generationSerial.current;
    const draft = {
      ...event,
      required_services: [...event.required_services],
      guest_count: Number(event.guest_count),
      budget_lkr: Number(event.budget_lkr),
      top_k: Number(event.top_k),
    };
    const previousId = editing ? result?.event_id : null;
    setGenerationLoading(true);
    setGenerationError('');
    try {
      const saved = editing ? await updateSavedEvent(result.event_id, draft) : await createSavedEvent(draft);
      const persisted = saved.event;
      setSavedEvents((previous) => [persisted, ...previous.filter((item) => item.event_id !== persisted.event_id)]);
      const data = await generateDynamic({ ...draft, event_id: persisted.event_id });
      if (serial !== generationSerial.current) return;
      feasibilitySerial.current += 1;
      setResult(data);
      setSelectedIds([]);
      setSelectedPackage('');
      setFeasibilityResult(null);
      setFeasibilityLoading(false);
      setFeasibilityError('');
      setEditing(false);
      setRevision(previousId ? {
        previousId, number: (revision?.number || 1) + 1,
      } : null);
      navigate('recommendations');
    } catch (caught) {
      if (serial === generationSerial.current) setGenerationError((caught.status === 422 ? 'INVALID_REQUEST: ' : 'BACKEND_ERROR: ') + caught.message);
    } finally {
      if (serial === generationSerial.current) setGenerationLoading(false);
    }
  };
  const openSavedEvent = (saved) => { setEvent({ ...saved, start_time: saved.start_time.slice(0, 5), end_time: saved.end_time.slice(0, 5) }); setResult(null); navigate('create-event'); };
  const editSavedEvent = (saved) => { openSavedEvent(saved); setEditing(true); };
  const removeSavedEvent = async (saved) => { if (!window.confirm('Delete this saved test event? This removes it from the SQLite database.')) return; try { await deleteSavedEvent(saved.event_id); setSavedEvents((previous) => previous.filter((item) => item.event_id !== saved.event_id)); if (result?.event_id === saved.event_id) setResult(null); } catch (caught) { setSavedEventsError(caught.message); } };
  const toggleCompare = (id) => setSelectedIds((previous) =>
    previous.includes(id) ? previous.filter((item) => item !== id)
      : previous.length < 3 ? [...previous, id] : previous);
  const checkFeasibility = async (pkg) => {
    if (!result) return;
    const serial = ++feasibilitySerial.current;
    const currentResult = result;
    setSelectedPackage(pkg.package_id);
    setFeasibilityLoading(true);
    setFeasibilityError('');
    setFeasibilityResult(null);
    navigate('feasibility');
    try {
      const checked = await validateDynamic(currentResult.event, pkg);
      if (serial === feasibilitySerial.current) setFeasibilityResult(checked);
    } catch (caught) {
      if (serial === feasibilitySerial.current) setFeasibilityError(caught.message);
    } finally {
      if (serial === feasibilitySerial.current) setFeasibilityLoading(false);
    }
  };
  const content = {
    home: <UserDashboard navigate={navigate} result={result} locations={locations} events={savedEvents}/>,
    methodology: <Methodology navigate={navigate}/>,
    'saved-events': <SavedEvents events={savedEvents} loading={savedEventsLoading} error={savedEventsError}
      onOpen={openSavedEvent} onEdit={editSavedEvent} onDelete={removeSavedEvent} onCreate={createNewEvent}/>,
    'user-dashboard': <UserDashboard navigate={navigate} result={result} locations={locations} events={savedEvents}/>,
    'create-event': <EventWizard event={event} setEvent={setEvent} locations={locations}
      locationsLoading={locationsLoading} locationsError={locationsError}
      onGenerate={generate} loading={generationLoading} error={generationError}
      editing={editing} editingEventId={result?.event_id} onCancel={cancelEdit}/>,
    recommendations: <Recommendations result={result} loading={generationLoading} error={generationError}
      navigate={navigate} selectedIds={selectedIds} onToggleCompare={toggleCompare}
      onCheck={checkFeasibility} checkingId={feasibilityLoading ? selectedPackage : ''}
      onEdit={editEvent} onCreateNew={createNewEvent} revision={revision}/>,
    comparison: <Comparison result={result} selectedIds={selectedIds} onToggleCompare={toggleCompare} navigate={navigate}/>,
    feasibility: <FeasibilityPage result={result} selectedPackage={selectedPackage}
      checked={feasibilityResult} checking={feasibilityLoading} error={feasibilityError}
      onCheck={checkFeasibility} navigate={navigate}/>,
    vendor: <VendorPortal page="vendor" navigate={navigate}/>,
    'vendor/profile': <VendorPortal page="vendor/profile" navigate={navigate}/>,
    'vendor/services': <VendorPortal page="vendor/services" navigate={navigate}/>,
    'vendor/availability': <VendorPortal page="vendor/availability" navigate={navigate}/>,
    admin: <AdminWorkspace page="admin" navigate={navigate}/>,
    'admin/vendors': <AdminWorkspace page="admin/vendors" navigate={navigate}/>,
    'admin/service-options': <AdminWorkspace page="admin/service-options" navigate={navigate}/>,
    'admin/events': <AdminWorkspace page="admin/events" navigate={navigate}/>,
    'admin/model': <AdminWorkspace page="admin/model" navigate={navigate}/>,
    'admin/reports': <AdminWorkspace page="admin/reports" navigate={navigate}/>,
    'admin-overview': <AdminOverview navigate={navigate}/>,
    'admin-vendors': <VendorIntelligence result={result}/>,
    'admin-options': <ServiceOptionExplorer result={result}/>,
    'admin-model': <ModelMonitoring/>,
    'admin-analytics': <RecommendationAnalytics/>,
    'admin-compatibility': <CompatibilityIntelligence view={researchView} onViewChange={setResearchView}/>,
    'admin-conflicts': <VendorConflictResearch/>,
    'admin-reports': <ResearchReports view={researchView} onViewChange={setResearchView}/>,
  };
  return <AppShell page={page} onNavigate={navigate}>{content[page] || content.home}</AppShell>;
}








