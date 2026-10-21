import {afterEach,it,expect,vi} from 'vitest';
import {render,screen,fireEvent,cleanup} from '@testing-library/react';
import GraphRiskPanel,{decodeGraphRisk} from './GraphRiskPanel';
import LocalLLMReport,{decodeLLMReport} from './LocalLLMReport';
import {defaults} from './api';
const score={uncalibrated_score:.2,class:0,threshold:.5};
const graph={version:'lkr-graph-risk.0.1',status:'predicted',prediction_executed:true,scores:{Budget_Overrun:score,Profit_Margin_Risk:score},reason:'',calibrated:false,cad_integration:false,affects_health_score:false,model:'gat_dependencies',validation_preferred:'gat_shuffled_dependencies',manifest_sha256:'test',monetary_input_unit:'LKR',nodes:9,dependency_edges:12};
afterEach(()=>{cleanup();vi.unstubAllGlobals();});
it('shows actual graph scores and the better control without pretending CAD integration',()=>{
  render(<GraphRiskPanel baseline={decodeGraphRisk(graph)} alternative={decodeGraphRisk(graph)}/>);
  expect(screen.getByText('Saved native GAT prediction executed')).toBeInTheDocument();
  expect(screen.getByText('gat_shuffled_dependencies')).toBeInTheDocument();
  expect(screen.getByText(/not observed CAD adjacency/)).toBeInTheDocument();
});
it('rejects calibrated claims, wrong units, fake withheld predictions and invalid class outputs',()=>{
  for(const x of [{...graph,calibrated:true},{...graph,monetary_input_unit:'score'},{...graph,status:'withheld'},
                  {...graph,scores:{...graph.scores,Budget_Overrun:{...score,class:1}}}])expect(()=>decodeGraphRisk(x)).toThrow();
});
it('shows missing runtime and disables generation without a fake LLM narrative',async()=>{
  vi.stubGlobal('fetch',vi.fn(async()=>({ok:true,json:async()=>({version:'grounded-local-report.0.1',provider:'ollama_local',model:'TEST',ready:false,reason:'local_model_not_installed',network_scope:'loopback only'})})));
  render(<LocalLLMReport baseline={defaults} alternative={defaults} ready/>);
  expect(await screen.findByText(/local model not installed/)).toBeInTheDocument();expect(screen.getByRole('button',{name:'Generate local AI draft'})).toBeDisabled();
});
const report={version:'grounded-local-report.0.1',status:'generated_review_required',provider:'ollama_local',model:'TEST',model_digest:'TEST-NOT-REAL',engine_facts_sha256:'TEST',engine_facts:[{id:'cost',statement:'TEST authoritative cost: LKR 100.'}],draft:{explanations:[{fact_id:'cost',text:'Review the supplied cost estimate.'}],action_ids:[]},selected_actions:[],financial_values_modified:false,semantic_accuracy_independently_verified:false,scope:'TEST AI wording requires review.',report_text:'TEST ONLY'};
it('renders an AI draft beside its authoritative engine facts and labels review requirements',async()=>{
  vi.stubGlobal('fetch',vi.fn(async(url)=>({ok:true,json:async()=>String(url).endsWith('llm-status')?{version:report.version,provider:'ollama_local',model:'TEST',ready:true,reason:'installed_local_model',network_scope:'loopback'}:report})));
  render(<LocalLLMReport baseline={defaults} alternative={defaults} ready/>);await screen.findByText(/Installed local model available/);
  fireEvent.click(screen.getByRole('button',{name:'Generate local AI draft'}));expect(await screen.findByText('AI draft — human review required')).toBeInTheDocument();expect(screen.getByText('TEST authoritative cost: LKR 100.')).toBeInTheDocument();
});
it('does not accept a report that claims altered finances or independent semantic verification',()=>{
  expect(()=>decodeLLMReport({...report,financial_values_modified:true})).toThrow();
  expect(()=>decodeLLMReport({...report,semantic_accuracy_independently_verified:true})).toThrow();
  expect(()=>decodeLLMReport({...report,draft:{explanations:[],action_ids:[]}})).toThrow();
});
