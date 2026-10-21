import { useState } from 'react';
import { AlertTriangle, FlaskConical, Play, ShieldCheck } from 'lucide-react';

type Point = [number, number];
type SceneObject = { object_id: string; class: string; group_id: string | null; footprint_coordinates_m: Point[] };
type Layout = { layout_id: string; objects: SceneObject[]; objective_metrics: Record<string, number> };
type Projection = {
  image_url: string; width_px: number; height_px: number; scale_m_per_pixel: number;
  origin_px: Point; boundary_px: Point[]; source_sha256: string;
  decoded_model_source_sha256: string; analysis_id: string; assumptions: string[];
};
type Handoff = {
  schema: string; status: 'success' | 'non_success'; scope: string; plan_projection?: Projection;
  request: { event_id: string; venue: { boundary_m: Point[] } };
  spec: { status: string; spec_sha256: string; functions: string[]; required_quantities: Record<string, number>;
    allocations: { instance_id: string; class: string; origin: string }[];
    new_equipment: { instance_id: string; class: string }[];
    retained_existing: { instance_id: string; class: string; active_supply: boolean }[]; stock_decisions: unknown[] };
  independent_spec: { valid: boolean; errors?: string[] };
  result: { run_id: string; status: string; optimizer_evaluations: number; candidate_layouts: Layout[];
    selected_ids: string[]; xai: { explanations: { layout_id: string; text: string }[] };
    verification: Record<string, { valid: boolean; minimum_clearance_m: number }>; reason?: string };
  artifact_path: string;
};
type Scenario = 'controlled_lab' | 'knox_plan';
const classColor: Record<string, string> = { stage: '#8e5b42', buffet_counter: '#c58a48', round_table: '#17857d', chair: '#7ea69f', column: '#525252', restricted_zone: '#dce7a7', lectern: '#5967a4', screen: '#6d79b5', speaker: '#ad5f8b' };

export default function SceneCompiler() {
  const [guests, setGuests] = useState(160);
  const [state, setState] = useState<'empty' | 'partially_furnished'>('empty');
  const [scenario, setScenario] = useState<Scenario>('controlled_lab');
  const [busy, setBusy] = useState(false);
  const [handoff, setHandoff] = useState<Handoff>();
  const [error, setError] = useState('');
  const [selected, setSelected] = useState('');

  async function run() {
    setBusy(true); setError(''); setHandoff(undefined);
    try {
      const route = scenario === 'knox_plan' ? '/scene/knox-plan/compile-and-optimize' : '/scene/compile-and-optimize';
      const payload = scenario === 'knox_plan' ? { event_type: 'wedding', guest_count: guests } : { event_type: 'wedding', guest_count: guests, scene_state: state };
      const response = await fetch(route, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail?.reason ?? JSON.stringify(body.detail ?? body));
      if (body.status !== 'success') throw new Error(body.result?.reason ?? body.reason ?? 'SCENE_SEARCH_NON_SUCCESS');
      setHandoff(body as Handoff);
      setSelected(body.result.selected_ids?.[0] ?? body.result.candidate_layouts?.[0]?.layout_id ?? '');
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  }

  const layout = handoff?.result.candidate_layouts.find(x => x.layout_id === selected) ?? handoff?.result.candidate_layouts[0];
  const boundary = handoff?.request.venue.boundary_m ?? [];
  const projection = handoff?.plan_projection;
  const width = Math.max(...boundary.map(p => p[0]), 32), height = Math.max(...boundary.map(p => p[1]), 24);
  const svgWidth = projection?.width_px ?? width, svgHeight = projection?.height_px ?? height;
  const project = (p: Point): Point => projection ? [projection.origin_px[0] + p[0] / projection.scale_m_per_pixel, projection.origin_px[1] + p[1] / projection.scale_m_per_pixel] : p;

  return <section className="panel scene-compiler" data-testid="scene-compiler">
    <div className="section-title"><div><span className="eyebrow">EXISTING COMPILER + FROZEN SEARCH BRIDGE</span><h2>Event scene compiler</h2><p className="muted">Uses the existing policy compiler, independent oracle, and local NSGA-II adapter.</p></div><span className="badge amber">Controlled research demo</span></div>
    <div className="event-form-grid">
      <label className="field">Demo source<select aria-label="Scene demo source" value={scenario} onChange={e => { const value = e.target.value as Scenario; setScenario(value); setGuests(value === 'knox_plan' ? 64 : 160); setHandoff(undefined); setError(''); }}><option value="controlled_lab">Separate controlled 32 × 24 m lab</option><option value="knox_plan">KNOX drawing-derived plan case</option></select><small>KNOX mode overlays the original plan; its geometry and review are explicit controlled assumptions.</small></label>
      <label className="field">Wedding guest count<select aria-label="Compiler guest count" value={guests} onChange={e => setGuests(Number(e.target.value))}>{[64, 80, 120, 160, 200, 240].map(n => <option key={n} value={n}>{n}</option>)}</select><small>Supported engine: multiples of 8, maximum 240. The KNOX demonstrator defaults to 64 because higher counts fail the preserved initializer with the transcribed columns.</small></label>
      {scenario === 'controlled_lab' && <label className="field">Controlled scene state<select aria-label="Controlled scene state" value={state} onChange={e => setState(e.target.value as typeof state)}><option value="empty">Empty generated venue</option><option value="partially_furnished">Partially furnished: pinned stage + buffets</option></select></label>}
    </div>
    {scenario === 'knox_plan' ? <div className="notice warning"><FlaskConical size={17}/><div><strong>KNOX plan-derived controlled search.</strong> The original drawing and frozen-model analysis identity are attached. Printed overall dimensions, the event-space boundary and ten columns are analyst transcriptions with simulated review. This is not an as-built or approved venue Twin; doors/routes are not optimizer constraints, and no safety validation is claimed.</div></div> : <div className="notice warning"><FlaskConical size={17}/><div><strong>Separate controlled simulated case.</strong> This uses a synthetic 32 × 24 m Wedding scenario with simulated client/planner/venue records. It is not KNOX, Ravenswood, genuine venue evidence or human approval.</div></div>}
    <button className="primary" data-testid="compile-scene-run" disabled={busy} onClick={run}><Play size={15}/>{busy ? 'Compiling and searching…' : scenario === 'knox_plan' ? 'Build KNOX plan layout + run actual local NSGA-II' : 'Compile controlled scene + run actual local NSGA-II'}</button>
    {error && <div role="alert" className="notice error"><AlertTriangle size={17}/><div><strong>Scene run did not succeed</strong><p>{error}</p></div></div>}
    {handoff && <div className="scene-result" data-testid="scene-result">
      <div className="section-title"><div><h3>Verified scene specification</h3><p><span className="badge green">{handoff.spec.status}</span> · Independent demand/allocation oracle: {String(handoff.independent_spec.valid)} · policy SHA: <code>{handoff.spec.spec_sha256.slice(0, 16)}…</code></p></div><span className="badge amber">{handoff.result.optimizer_evaluations} evaluations</span></div>
      <div className="scene-summary"><div><strong>Required functions</strong><p>{handoff.spec.functions.join(' · ')}</p></div><div><strong>Demand quantities</strong><p>{Object.entries(handoff.spec.required_quantities).map(([k, v]) => `${k}: ${v}`).join(' · ')}</p></div><div><strong>Stock accounting</strong><p>{handoff.spec.allocations.length} allocations · {handoff.spec.new_equipment.length} new equipment · {handoff.spec.retained_existing.filter(x => x.active_supply).length} reused existing</p></div><div><strong>Search identity</strong><p><code>{handoff.result.run_id}</code> · {handoff.result.candidate_layouts.length} returned layouts</p></div></div>
      <div className="scene-layout-grid"><div><div className="section-title"><h3>{projection ? 'KNOX source drawing + returned layout' : 'Actual returned metric polygons'}</h3><select aria-label="Scene alternative" value={selected} onChange={e => setSelected(e.target.value)}>{handoff.result.candidate_layouts.map((l, i) => <option key={l.layout_id} value={l.layout_id}>Alternative {i + 1} · {l.layout_id}</option>)}</select></div>
        <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} role="img" aria-label={projection ? 'KNOX source drawing with plan-derived optimized event layout' : 'Actual compiler bridge returned scene geometry'} className="scene-svg">
          {projection ? <image href={projection.image_url} x="0" y="0" width={svgWidth} height={svgHeight} preserveAspectRatio="none"/> : <polygon points={boundary.map(p => p.join(',')).join(' ')} fill="#fbfaf6" stroke="#627b80" strokeWidth=".12"/>}
          {projection && <polygon points={projection.boundary_px.map(p => p.join(',')).join(' ')} fill="none" stroke="#1b8075" strokeWidth="2" strokeDasharray="5 3"/>}
          {layout?.objects.map(o => { const pts = o.footprint_coordinates_m.map(project); return <polygon key={o.object_id} data-object-class={o.class} points={pts.map(p => p.join(',')).join(' ')} fill={classColor[o.class] ?? '#778899'} fillOpacity={o.class === 'chair' || o.class === 'round_table' ? .74 : .82} stroke="#163b3d" strokeWidth={projection ? 1.2 : .035}><title>{o.class} · {o.object_id}</title></polygon>; })}
        </svg>
        <div className="legend">{Object.entries(classColor).filter(([c]) => layout?.objects.some(o => o.class === c)).map(([c, color]) => <span key={c}><i style={{ background: color }}/>{c}</span>)}</div>
        {projection && <details><summary>Source and geometry assumptions</summary><p>Source image SHA-256: <code>{projection.source_sha256}</code></p><p>Frozen model analysis: <code>{projection.analysis_id}</code>; decoded raster SHA-256: <code>{projection.decoded_model_source_sha256}</code></p><p>Plan scale used: {projection.scale_m_per_pixel.toFixed(6)} m/px. This is a drawing interpretation; approval remains simulated.</p><ul>{projection.assumptions.map(a => <li key={a}>{a}</li>)}</ul></details>}
      </div><aside className="panel"><h3>Candidate trade-offs</h3>{handoff.result.candidate_layouts.map((l, i) => <button key={l.layout_id} className={`alternative ${selected === l.layout_id ? 'selected' : ''}`} onClick={() => setSelected(l.layout_id)}><strong>Alternative {i + 1} · {l.layout_id}</strong><small>Stage distance {l.objective_metrics.mean_stage_distance_m.toFixed(2)} m · initializer displacement {l.objective_metrics.initializer_assignment_movement_m.toFixed(2)} m</small><span className="badge green">{handoff.result.verification[l.layout_id]?.valid ? 'independently checked' : 'check missing'}</span></button>)}</aside></div>
      <div className="notice info"><ShieldCheck size={17}/><div>{handoff.result.xai.explanations.find(x => x.layout_id === layout?.layout_id)?.text ?? 'No matching explanation was returned.'} This Scene compiler result is separate from frozen backend approval/adaptation/history.</div></div>
      <details><summary>Inspect source-bound controlled request, stock decisions and raw result</summary><pre className="long-json">{JSON.stringify({ scope: handoff.scope, request: handoff.request, spec: handoff.spec, independent_spec: handoff.independent_spec, result: handoff.result, artifact_path: handoff.artifact_path }, null, 2)}</pre></details>
    </div>}
  </section>;
}
