export const EVENT_PROJECTS_KEY = 'component1.event-projects.v1';
export const EVENT_PROJECTS_SCHEMA = 'COMPONENT1_EVENT_PROJECTS_V1';

export type EventKind = 'Wedding' | 'Birthday' | 'Corporate' | 'Conference' | 'Musical Show';
export interface EventProject {
  id: string;
  schema: typeof EVENT_PROJECTS_SCHEMA;
  name: string;
  type: EventKind;
  date: string;
  startTime: string;
  endTime: string;
  venue: string;
  guests: number;
  budget: number | null;
  venueMode: 'indoor' | 'outdoor' | 'hybrid';
  clientRequirements: string;
  plannerNotes: string;
  status: 'draft' | 'review_pending' | 'active' | 'completed' | 'archived';
  analysisId?: string;
  twinId?: string;
  twinVersion?: number;
  runIds?: string[];
  createdAt: string;
  updatedAt: string;
}

interface StoreEnvelope { schema: typeof EVENT_PROJECTS_SCHEMA; version: 1; projects: EventProject[] }

export function readEventProjects(storage: Storage = localStorage): EventProject[] {
  try {
    const parsed: unknown = JSON.parse(storage.getItem(EVENT_PROJECTS_KEY) ?? 'null');
    if (!parsed || typeof parsed !== 'object') return [];
    const envelope = parsed as Partial<StoreEnvelope>;
    if (envelope.schema !== EVENT_PROJECTS_SCHEMA || envelope.version !== 1 || !Array.isArray(envelope.projects)) return [];
    return envelope.projects.filter((p): p is EventProject => !!p && typeof p === 'object' && (p as EventProject).schema === EVENT_PROJECTS_SCHEMA);
  } catch { return []; }
}

export function writeEventProjects(projects: EventProject[], storage: Storage = localStorage): void {
  storage.setItem(EVENT_PROJECTS_KEY, JSON.stringify({ schema: EVENT_PROJECTS_SCHEMA, version: 1, projects } satisfies StoreEnvelope));
}

export function putEventProject(project: EventProject, storage: Storage = localStorage): EventProject[] {
  const rows = readEventProjects(storage);
  const index = rows.findIndex(x => x.id === project.id);
  if (index < 0) rows.unshift(project); else rows[index] = project;
  writeEventProjects(rows, storage);
  return rows;
}

async function sqliteRequest(path: string, method = 'GET', body?: EventProject): Promise<unknown> {
  const response = await fetch(`/companion${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (response.status === 204) return { ok: true };
  const payload = await response.json().catch(() => ({})) as Record<string, unknown>;
  if (!response.ok) {
    const detail = payload.detail && typeof payload.detail === 'object' ? payload.detail as Record<string, unknown> : payload;
    throw new Error(String(detail.reason ?? `EVENT_SQLITE_HTTP_${response.status}`));
  }
  return payload;
}

function eventPayload(value: unknown): EventProject {
  const root = value && typeof value === 'object' ? value as Record<string, unknown> : {};
  const project = root.project;
  if (!project || typeof project !== 'object' || (project as EventProject).schema !== EVENT_PROJECTS_SCHEMA) throw new Error('INVALID_SQLITE_EVENT_PROJECT_RESPONSE');
  return project as EventProject;
}

export async function listSqliteEventProjects(): Promise<EventProject[]> {
  const payload = await sqliteRequest('/event-projects') as { projects?: unknown; storage?: unknown };
  if (payload.storage !== 'local_sqlite' || !Array.isArray(payload.projects)) throw new Error('INVALID_SQLITE_EVENT_PROJECT_LIST');
  return payload.projects.filter((p): p is EventProject => !!p && typeof p === 'object' && (p as EventProject).schema === EVENT_PROJECTS_SCHEMA);
}

export async function createSqliteEventProject(project: EventProject): Promise<EventProject> {
  return eventPayload(await sqliteRequest('/event-projects', 'POST', project));
}

export async function updateSqliteEventProject(project: EventProject): Promise<EventProject> {
  return eventPayload(await sqliteRequest(`/event-projects/${encodeURIComponent(project.id)}`, 'PUT', project));
}

export async function deleteSqliteEventProject(id: string): Promise<void> {
  await sqliteRequest(`/event-projects/${encodeURIComponent(id)}`, 'DELETE');
}

export function isWeddingOptimizerEligible(project: Pick<EventProject, 'type'|'guests'|'venueMode'>): boolean {
  return project.type === 'Wedding' && project.venueMode === 'indoor' && Number.isInteger(project.guests) && project.guests >= 8 && project.guests <= 240 && project.guests % 8 === 0;
}
