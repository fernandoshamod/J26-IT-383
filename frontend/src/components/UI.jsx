import React from 'react';

const paths = {
  spark: <><path d="m12 2 1.6 6.4L20 10l-6.4 1.6L12 18l-1.6-6.4L4 10l6.4-1.6L12 2Z"/><path d="m19 18 .6 2.4L22 21l-2.4.6L19 24l-.6-2.4L16 21l2.4-.6L19 18Z"/></>,
  grid: <><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></>,
  calendar: <><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4M17 3v4M3 10h18"/></>,
  layers: <><rect x="3" y="3" width="18" height="6" rx="2"/><rect x="3" y="11" width="18" height="6" rx="2"/><path d="M7 20h10"/></>,
  compare: <><path d="M12 3v18M3 7h6M15 7h6M5 7l-3 6h9L8 7M17 7l-3 6h9l-3-6"/></>,
  shield: <><path d="M12 2 4 5v6c0 5 3 8 8 11 5-3 8-6 8-11V5l-8-3Z"/><path d="m9 12 2 2 4-4"/></>,
  chart: <><path d="M3 21h18M5 18V11M10 18V7M15 18v-4M20 18V4"/></>,
  book: <><path d="M4 4h7a3 3 0 0 1 3 3v14a3 3 0 0 0-3-3H4V4Zm16 0h-3a3 3 0 0 0-3 3v14a3 3 0 0 1 3-3h3V4Z"/></>,
  search: <><circle cx="11" cy="11" r="7"/><path d="m16 16 5 5"/></>,
  menu: <path d="M4 6h16M4 12h16M4 18h16"/>,
  chevron: <path d="m9 6 6 6-6 6"/>,
  arrow: <path d="M4 12h16m-6-6 6 6-6 6"/>,
  check: <path d="m4 12 5 5L20 6"/>,
  warning: <><path d="M12 3 2 21h20L12 3Z"/><path d="M12 9v5M12 18h.01"/></>,
  info: <><circle cx="12" cy="12" r="10"/><path d="M12 11v6M12 7h.01"/></>,
  clock: <><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></>,
  close: <path d="M5 5 19 19M19 5 5 19"/>,
};
export function Icon({ name, size = 20 }) {
  return <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24"
    fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    {paths[name] || paths.info}
  </svg>;
}
export function Badge({ children, tone = 'neutral' }) {
  return <span className={'badge badge-' + tone}>{children}</span>;
}
export function StatusBadge({ status }) {
  const tone = status === 'PASS_IN_SIMULATION' || status === 'complete' || status === 'ok'
    ? 'success' : status === 'FAIL' ? 'danger' : 'warning';
  return <Badge tone={tone}>{String(status || 'Unknown').replaceAll('_', ' ')}</Badge>;
}
export function PageHeader({ eyebrow, title, description, actions }) {
  return <header className="page-header">
    <div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p className="page-description">{description}</p></div>
    {actions && <div className="header-actions">{actions}</div>}
  </header>;
}
export function Kpi({ label, value, note, icon, tone = 'violet' }) {
  return <article className="kpi card">
    <div className={'kpi-icon tone-' + tone}><Icon name={icon || 'chart'} /></div>
    <div><p>{label}</p><strong>{value}</strong>{note && <small>{note}</small>}</div>
  </article>;
}
export function EmptyState({ title, children, action }) {
  return <div className="empty-state card"><span className="empty-icon"><Icon name="layers" size={28}/></span>
    <h3>{title}</h3><p>{children}</p>{action}</div>;
}
export function Notice({ title, children, tone = 'info' }) {
  return <div className={'notice notice-' + tone} role={tone === 'danger' ? 'alert' : 'status'}>
    <Icon name={tone === 'danger' || tone === 'warning' ? 'warning' : 'info'} />
    <div><strong>{title}</strong>{children && <p>{children}</p>}</div>
  </div>;
}
export function Loading({ label = 'Loading' }) {
  return <div className="loading-state" role="status" aria-live="polite">
    <span className="spinner" aria-hidden="true"/><span>{label}</span>
    <div className="skeleton"/><div className="skeleton short"/>
  </div>;
}
export function ProgressBar({ value, color = 'violet' }) {
  const width = Math.max(0, Math.min(100, Number(value) || 0));
  return <div className="progress-track" role="img" aria-label={width.toFixed(0) + ' percent'}>
    <div className={'progress-fill fill-' + color} style={{ width: width + '%' }}/></div>;
}
