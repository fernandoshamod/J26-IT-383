import React, { useEffect, useState } from 'react';
import AppShell from './components/AppShell';
import { adminNav, publicNav, userNav } from './data/navigation';
import { Landing, Methodology, UserDashboard } from './pages/PublicPages';
import EventWizard from './pages/EventWizard';
import { Recommendations, Comparison, FeasibilityPage } from './pages/PackageViews';
import { AdminOverview, VendorIntelligence, ServiceOptionExplorer, ModelMonitoring,
  RecommendationAnalytics, CompatibilityIntelligence, ResearchReports } from './pages/AdminPages';
import { dateForInput } from './data/catalog';
import { generateDynamic, getLocations, validateDynamic } from './services/api';
import './App.css';

const validPages = new Set([...publicNav, ...userNav, ...adminNav].map(([id]) => id));
const fromHash = () => {
  const page = window.location.hash.replace(/^#\/?/, '');
  return validPages.has(page) ? page : 'home';
};

export default function App() {
  const [page, setPage] = useState(fromHash);
  const [locations, setLocations] = useState([]);
  const [locationsLoading, setLocationsLoading] = useState(true);
  const [locationsError, setLocationsError] = useState('');
  const [event, setEvent] = useState({
    event_type: 'Wedding', event_date: dateForInput(),
    start_time: '10:00', end_time: '18:00', city: '', state: '',
    guest_count: 50, budget_lkr: 1000000, top_k: 10,
    required_services: ['Photography', 'Decoration'],
  });
  const [result, setResult] = useState(null);
  const [generationLoading, setGenerationLoading] = useState(false);
  const [generationError, setGenerationError] = useState('');
  const [selectedIds, setSelectedIds] = useState([]);
  const [selectedPackage, setSelectedPackage] = useState('');
  const [feasibilityResult, setFeasibilityResult] = useState(null);
  const [feasibilityLoading, setFeasibilityLoading] = useState(false);
  const [feasibilityError, setFeasibilityError] = useState('');
  const [researchView, setResearchView] = useState('simple');

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
    if (!validPages.has(next)) return;
    if (window.location.hash !== '#' + next) window.location.hash = next;
    setPage(next);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };
  const generate = async () => {
    setGenerationLoading(true); setGenerationError(''); setResult(null);
    setSelectedIds([]); setSelectedPackage(''); setFeasibilityResult(null); setFeasibilityError('');
    try {
      const data = await generateDynamic({
        ...event, guest_count: Number(event.guest_count), budget_lkr: Number(event.budget_lkr),
        top_k: Number(event.top_k),
      });
      setResult(data); navigate('recommendations');
    } catch (caught) { setGenerationError(caught.message); }
    finally { setGenerationLoading(false); }
  };
  const toggleCompare = (id) => setSelectedIds((previous) =>
    previous.includes(id) ? previous.filter((item) => item !== id)
      : previous.length < 3 ? [...previous, id] : previous);
  const checkFeasibility = async (pkg) => {
    if (!result) return;
    setSelectedPackage(pkg.package_id); setFeasibilityLoading(true); setFeasibilityError('');
    setFeasibilityResult(null); navigate('feasibility');
    try { setFeasibilityResult(await validateDynamic(result.event, pkg)); }
    catch (caught) { setFeasibilityError(caught.message); }
    finally { setFeasibilityLoading(false); }
  };
  const content = {
    home: <Landing navigate={navigate}/>,
    methodology: <Methodology navigate={navigate}/>,
    'user-dashboard': <UserDashboard navigate={navigate} result={result} locations={locations}/>,
    'create-event': <EventWizard event={event} setEvent={setEvent} locations={locations}
      locationsLoading={locationsLoading} locationsError={locationsError}
      onGenerate={generate} loading={generationLoading} error={generationError}/>,
    recommendations: <Recommendations result={result} loading={generationLoading} error={generationError}
      navigate={navigate} selectedIds={selectedIds} onToggleCompare={toggleCompare}
      onCheck={checkFeasibility} checkingId={feasibilityLoading ? selectedPackage : ''}/>,
    comparison: <Comparison result={result} selectedIds={selectedIds} onToggleCompare={toggleCompare} navigate={navigate}/>,
    feasibility: <FeasibilityPage result={result} selectedPackage={selectedPackage}
      checked={feasibilityResult} checking={feasibilityLoading} error={feasibilityError}
      onCheck={checkFeasibility} navigate={navigate}/>,
    'admin-overview': <AdminOverview navigate={navigate}/>,
    'admin-vendors': <VendorIntelligence result={result}/>,
    'admin-options': <ServiceOptionExplorer result={result}/>,
    'admin-model': <ModelMonitoring/>,
    'admin-analytics': <RecommendationAnalytics/>,
    'admin-compatibility': <CompatibilityIntelligence view={researchView} onViewChange={setResearchView}/>,
    'admin-reports': <ResearchReports view={researchView} onViewChange={setResearchView}/>,
  };
  return <AppShell page={page} onNavigate={navigate}>{content[page] || content.home}</AppShell>;
}




