import {afterEach,describe,it,expect,vi} from 'vitest';
import {render,screen,cleanup,fireEvent} from '@testing-library/react';
import EvidenceWorkspace,{validateEvidence} from './EvidenceWorkspace';
import {decode} from './api';
import response from './test-fixtures/training-evaluation.response.json';
import errors from '../../reports/diagnostics/v3_1_steps1_2_20261016/error_audit.json';
import curves from '../../reports/diagnostics/v3_1_steps1_2_20261016/learning_curve_summary.json';
import robust from '../../reports/robustness/v3_1_frozen_robustness_20261016/performance_summary.json';
// Actual frozen reports, reshaped like the read-only endpoint; no invented metrics.
const evidence={version:'v3.1-frozen-diagnostics',model_run:'expense_risk_v3_1_20261016',
  sources:{errors:{path:'reports/diagnostics/v3_1_steps1_2_20261016/error_audit.json',sha256:'b5fb0cf8ef574c42c91b4a15f7edda39d89f5598dd0992bf6f62af3d3b0b4fb3'}},
  errors:Object.fromEntries(Object.entries(errors.strata_and_counts).map(([t,v])=>[t,{counts:v.test.counts,near_boundary:v.test.errors_near_boundary,paired_conflicts:v.test.paired_label_ambiguity.conflicting_label_vectors}])),
  curves:Object.fromEntries(Object.entries(curves.curves).map(([t,v])=>[t,v.current_selected.map(r=>({families:r.training_families,train_accuracy:r.train_accuracy.mean,validation_accuracy:r.validation_accuracy.mean,validation_log_loss:r.validation_log_loss.mean}))])),
  robustness:Object.fromEntries(Object.entries(robust.pooled).map(([regime,targets])=>[regime,Object.fromEntries(Object.entries(targets).map(([t,v])=>[t,{cases:v.matched_model_supported_cases.cases,metrics:v.matched_model_supported_cases.metrics.frozen_xgboost}]))]))};
afterEach(()=>{cleanup();vi.unstubAllGlobals();});
function setup(){vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>evidence}));render(<EvidenceWorkspace data={decode(response)}/>);}
describe('Model Evidence Lab',()=>{
  it('separates rules and inference and switches views without duplication',async()=>{
    setup();expect(screen.getByText('Model Evidence Lab')).toBeInTheDocument();
    expect(screen.getByText('Financial rules')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Learning curves'}));
    expect(await screen.findByText('Does more training data help?')).toBeInTheDocument();
    expect(screen.getAllByText('94.69%').length).toBeGreaterThan(0);
    expect(screen.queryByText('Training quality, not just an accuracy number')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Training evaluation'}));
    expect(screen.getByText('Training quality, not just an accuracy number')).toBeInTheDocument();
    expect(screen.queryByText('Does more training data help?')).not.toBeInTheDocument();
  });
  it('exposes actual error counts and adverse robustness failures',async()=>{
    setup();fireEvent.click(screen.getByRole('button',{name:'Error analysis'}));
    expect(await screen.findByText('32 target-specific errors')).toBeInTheDocument();
    expect(screen.getByText('49 target-specific errors')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Robustness'}));
    expect(screen.getByText('37.29%')).toBeInTheDocument();
    expect(screen.getByText(/cannot guarantee profitability/)).toBeInTheDocument();
  });
  it('fails closed when evidence cannot be loaded',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false}));render(<EvidenceWorkspace data={decode(response)}/>);
    fireEvent.click(screen.getByRole('button',{name:'Robustness'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('No substitute metrics');
    expect(screen.queryByText('37.29%')).not.toBeInTheDocument();
  });
  it('rejects malformed metrics and mismatched versions',()=>{
    const d=structuredClone(evidence);d.robustness.coupled_adverse.Profit_Margin_Risk.metrics.recall=NaN;
    expect(()=>validateEvidence(d)).toThrow();
    expect(()=>validateEvidence({...evidence,model_run:'another_run'})).toThrow();
    expect(()=>validateEvidence(null)).toThrow();
  });
  it('reports a missing figure without replacing it with a mock',async()=>{
    setup();fireEvent.click(screen.getByRole('button',{name:'Learning curves'}));
    const img=await screen.findByRole('img');fireEvent.error(img);
    expect(screen.getByRole('alert')).toHaveTextContent('Verified chart unavailable');
  });
});
