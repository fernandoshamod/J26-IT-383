export const workspacePages = [
  {id:'planner', label:'Financial planner', title:'Plan an event, clearly.', description:'Set the original requirements and understand the cost before making a commitment.', group:'PLAN', icon:'plan'},
  {id:'events', label:'Saved events', title:'Your plans, in one place.', description:'Save, load and manage confirmed financial plans. Keep a backup when you need one.', group:'PLAN', icon:'folder'},
  {id:'calendar', label:'Booking calendar', title:'Make room for the next event.', description:'Check reserved dates, view client details and manage your planner calendar.', group:'PLAN', icon:'calendar'},
  {id:'what-if', label:'What-If comparison', title:'A change, without the commitment.', description:'Try additions or removals, compare the impact, then decide what to confirm.', group:'DECIDE', icon:'change'},
  {id:'reports', label:'Reports & explainability', title:'Understand the financial picture.', description:'Review financial health, recommendations and your explainable decision report.', group:'DECIDE', icon:'report'},
  {id:'forecast', label:'Price outlook', title:'Look ahead with context.', description:'Explore commodity forecasts and historical evidence, separate from your event ledger.', group:'RESEARCH', icon:'trend'},
  {id:'models', label:'Model evidence', title:'See the evidence behind the model.', description:'Inspect saved-model predictions, explanations, evaluation results and research limitations.', group:'RESEARCH', icon:'model'},
] as const;
export type WorkspacePage = typeof workspacePages[number]['id'];
export function readWorkspacePage():WorkspacePage {
  const id=location.hash.replace(/^#\//,'');
  return workspacePages.find(page=>page.id===id)?.id??'planner';
}
export function WorkspaceIcon({name}:{name:string}){
  const paths:Record<string,string>={
    plan:'M7 3h10v3H7z M5 5H3v16h18V5h-2 M7 11h10 M7 16h6',
    folder:'M3 6h7l2 3h9v11H3z M3 6V4h7l2 2',
    calendar:'M4 5h16v16H4z M8 3v4 M16 3v4 M4 10h16 M8 14h2 M14 14h2 M8 18h2',
    change:'M4 7h15 M15 3l4 4-4 4 M20 17H5 M9 13l-4 4 4 4',
    report:'M5 3h10l4 4v14H5z M14 3v5h5 M9 12h6 M9 16h6',
    trend:'M3 3v18h18 M6 16l5-5 4 3 6-8 M17 6h4v4',
    model:'M12 3l9 5-9 5-9-5z M3 12l9 5 9-5 M3 16l9 5 9-5',
  };
  return <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]??paths.plan}/></svg>;
}
