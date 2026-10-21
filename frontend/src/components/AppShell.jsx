import React, { useState } from 'react';
import { Icon } from './UI';
import { adminWorkspaceNav, userNav, researchNav, vendorNav } from '../data/navigation';

const allNav = [...userNav, ...vendorNav, ...adminWorkspaceNav, ...researchNav];

export default function AppShell({ page, onNavigate, children }) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [researchOpen, setResearchOpen] = useState(() => researchNav.some(([id]) => id === page));
  const item = allNav.find(([id]) => id === page);
  const isResearchPage = researchNav.some(([id]) => id === page);
  const isAdminPage = adminWorkspaceNav.some(([id]) => id === page);
  const isVendorPage = vendorNav.some(([id]) => id === page);
  const group = isAdminPage ? 'Admin Workspace' : isVendorPage ? 'Vendor Portal' : isResearchPage ? 'Research & Evaluation' : 'Event Management';
  const navigate = (id) => { onNavigate(id); setMobileOpen(false); if (researchNav.some(([route]) => route === id)) setResearchOpen(true); };
  const renderLinks = (items) => items.map(([id, title, icon]) => <button key={id} type="button" className={'nav-link' + (id === page ? ' selected' : '')}
    onClick={() => navigate(id)} aria-current={id === page ? 'page' : undefined} title={collapsed ? title : undefined}>
    <Icon name={icon} size={18}/><span>{title}</span>
  </button>);
  return <div className={'app-layout' + (collapsed ? ' sidebar-collapsed' : '')}>
    {mobileOpen && <button className="mobile-scrim" aria-label="Close navigation" onClick={() => setMobileOpen(false)} />}
    <aside className={'app-sidebar' + (mobileOpen ? ' mobile-open' : '')}>
      <button className="brand" type="button" onClick={() => navigate('home')}>
        <span className="brand-mark">P</span><span className="brand-words"><strong>PlanoVision</strong><small>EVENT MANAGEMENT</small></span>
      </button>
      <nav aria-label="Main navigation">
        <div className="nav-group"><span className="nav-heading">EVENT MANAGEMENT</span>{renderLinks(userNav)}</div>
        <button type="button" className={"nav-link admin-workspace-link" + (page.startsWith("admin") ? " selected" : "")} onClick={() => navigate("admin")}><Icon name="grid" size={18}/><span>Admin Workspace</span></button>
        <div className="nav-group vendor-nav-group"><span className="nav-heading">VENDOR PORTAL</span>{renderLinks(vendorNav)}</div>
        <div className={'nav-group research-nav-group' + (researchOpen ? ' is-open' : '')}>
          <button type="button" className="research-nav-toggle" onClick={() => setResearchOpen((open) => !open)} aria-expanded={researchOpen}>
            <span><span className="nav-heading">RESEARCH &amp; EVALUATION</span></span><Icon name="chevron" size={15}/>
          </button>
          {researchOpen && <div className="research-nav-links">{renderLinks(researchNav)}</div>}
        </div>
      </nav>
      <div className="sidebar-foot"><span className="live-dot"/> Academic prototype<small>Synthetic simulation data</small></div>
      <button className="collapse-control" type="button" onClick={() => setCollapsed(!collapsed)} aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}>
        <Icon name="chevron" size={17}/><span>{collapsed ? 'Expand' : 'Collapse'} sidebar</span>
      </button>
    </aside>
    <div className="app-main">
      <header className="topbar">
        <button className="mobile-menu icon-button" aria-label="Open navigation" onClick={() => setMobileOpen(true)}><Icon name="menu"/></button>
        <div className="breadcrumbs"><span>PlanoVision</span><Icon name="chevron" size={14}/><span>{group}</span><Icon name="chevron" size={14}/><strong>{item?.[1] || 'Dashboard'}</strong></div>
        <div className="top-actions"><span className="demo-pill"><span className="live-dot"/> Academic prototype</span><span className="top-avatar" title="No user account is connected">PV</span></div>
      </header>
      <main id="main-content">{children}</main>
      <footer className="app-footer">PlanoVision · Event planning research prototype · Synthetic vendor data and unverified availability</footer>
    </div>
  </div>;
}




