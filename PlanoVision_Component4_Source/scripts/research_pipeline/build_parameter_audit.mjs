import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
const require=createRequire('C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/package.json');
const {Workbook,SpreadsheetFile}=await import(pathToFileURL(require.resolve('@oai/artifact-tool')));
const evidence=JSON.parse(await fs.readFile('work/public_rate_candidates.json','utf8'));
const audit=JSON.parse(await fs.readFile('work/parameter_audit_tables.json','utf8'));
const navy='#213B58',amber='#FFF2CE',ink='#223449';
const column=n=>{let s='';for(n++;n;n=Math.floor((n-1)/26))s=String.fromCharCode(65+(n-1)%26)+s;return s;};
const dt=x=>x?new Date(x+'T00:00:00Z'):null;
function flat(wb,name,headers,rows,widths){
 const s=wb.worksheets.add(name),end=column(headers.length-1),last=rows.length+1;
 s.showGridLines=false;s.getRange(`A1:${end}${last}`).values=[headers,...rows];
 s.getRange(`A1:${end}${last}`).format={font:{name:'Arial',size:10,color:ink},verticalAlignment:'center'};
 s.getRange(`A1:${end}1`).format={fill:navy,font:{name:'Arial',size:10,color:'#FFFFFF',bold:true},rowHeight:42,wrapText:true,horizontalAlignment:'center'};
 s.getRange(`A2:${end}${last}`).format.wrapText=true;
 s.getRange(`A2:${end}${last}`).format.rowHeight=name==='Rates'?42:name==='Source_Terms'?62:62;
 for(let i=0;i<headers.length;i++){
  const c=column(i),h=headers[i];s.getRange(`${c}1:${c}${last}`).format.columnWidth=widths[i]??26;
  if(['Rate_LKR','Lower_LKR','Upper_LKR','Proposed_Value','Rows','Tax_Rate_Points','Service_Charge_Points','Published_Valid_Year'].includes(h)){
   s.getRange(`${c}2:${c}${last}`).setNumberFormat(h.includes('LKR')?'"LKR "#,##0.00':h==='Rows'?'#,##0':h==='Published_Valid_Year'?'0':'#,##0.00');
   s.getRange(`${c}2:${c}${last}`).format.horizontalAlignment='right';
  }
  if(h.includes('Date'))s.getRange(`${c}2:${c}${last}`).setNumberFormat('yyyy-mm-dd');
  if(h==='Review_Status'){
   s.getRange(`${c}2:${c}${last}`).dataValidation={rule:{type:'list',values:['Pending review','Evidence supplied','Needs amendment','Rejected']}};
   s.getRange(`${c}2:${c}${last}`).conditionalFormats.add('containsText',{text:'Pending review',format:{fill:amber,font:{color:'#805600'}}});
  }
 }
 s.tables.add(`A1:${end}${last}`,true,'T_'+name).style='TableStyleMedium2';
 s.freezePanes.freezeRows(1);s.freezePanes.freezeColumns(name==='Parameters'||name==='Controls'?2:1);
 return s;
}
const prices=Workbook.create();
const sources=new Map(evidence.sources.map(x=>[x.id,x]));
const rateHeaders=['Evidence_ID','Source_ID','Event_Type','Service','Rate_LKR','Lower_LKR','Upper_LKR','Unit','Price_Basis','Evidence_Type','Engine_Item','Effective_Date','Access_Date','Published_Valid_Year','Review_Status','Mapping_Limit','Uncertainty','','Source_URL'];
const rateRows=evidence.rates.map(r=>{const s=sources.get(r.source_id);return [r.id,r.source_id,r.event_type,r.service,r.rate_lkr,r.lower_lkr??null,r.upper_lkr??null,r.unit,r.price_basis,r.evidence_type,r.engine_item,dt(s.effective_date),dt(evidence.access_date),s.valid_year??null,'Pending review',r.restriction,s.valid_year?'Historical 2025 validity only; no 2026 quote':r.price_basis==='advertised_range'?'Unselected range; route, taxes and validity unresolved':'Effective date, availability and tax breakdown unresolved',null,s.url];});
flat(prices,'Rates',rateHeaders,rateRows,[14,12,14,48,17,17,17,39,30,36,20,18,18,19,23,68,60,3,88]);
const sourceHeaders=['Source_ID','Provider','Location','Effective_Date','Valid_Until_Date','Access_Date','Tax_Scope','Tax_Rate_Points','Service_Charge_Points','Inclusions','Exclusions','Terms','Applicability','','Source_URL'];
const sourceRows=evidence.sources.map(s=>[s.id,s.provider,s.location,dt(s.effective_date),dt(s.valid_until),dt(evidence.access_date),s.tax_scope,null,s.id==='P04'?15:null,s.inclusions,s.exclusions,s.terms,s.applicability,null,s.url]);
const sourceSheet=flat(prices,'Source_Terms',sourceHeaders,sourceRows,[14,43,26,18,18,18,53,19,22,55,55,69,62,3,88]);
sourceSheet.getRange('A13').values=[['Derived tariff illustration (not an approved quote)']];
sourceSheet.getRange('A13').format.font={name:'Arial',size:14,bold:true,color:navy};
sourceSheet.getRange('A15:A17').values=[['Caritas base hall price (LKR/day)'],['Published weekday service charge (points)'],['Subtotal before unresolved hall taxes (LKR)']];
sourceSheet.getRange('D15').formulas=[["='Rates'!E10"]];
sourceSheet.getRange('D16').formulas=[['=I5']];
sourceSheet.getRange('D17').formulas=[['=D15*(1+D16/100)']];
sourceSheet.getRange('D15:D17').setNumberFormat('#,##0.00');
sourceSheet.getRange('A15:D17').format.rowHeight=30;
sourceSheet.getRange('F15').values=[['This subtotal does not resolve VAT, extras, event selection or approval.']];
sourceSheet.getRange('F17').values=[['Do not enter service charge as tax_rate_points in the engine.']];
const leadHeaders=['Lead_ID','Category','Provider','Finding','Disposition','Rate_LKR','Access_Date','','Source_URL'];
flat(prices,'Unverified_Leads',leadHeaders,evidence.leads.map(x=>[x.id,x.category,x.provider,x.finding,x.disposition,null,dt(evidence.access_date),null,x.url]),[14,19,31,67,72,17,18,3,88]);
const r=prices.worksheets.getItem('Rates');
const priceNotes=[
 'Observed advertised numbers only. No prices are approved or loaded into the runtime configuration.',
 'Blank rate or date means unknown, not zero. Access date is not a quote date or effective date.',
 'Ranges are preserved without a selected midpoint. Provider items do not constitute a market distribution.',
 'Join Source_ID to Source_Terms for provider scope, inclusions, exclusions, tax and billing terms.',
 'The two wedding buffet entries apply only to 2025. Seek dated 2026 quotations.',
 'Review_Status and notes support review only. Formal approval requires a separate signed version/hash record.'
];
priceNotes.forEach((t,i)=>r.getRange(`A${i+24}`).values=[[t]]);
await finish(prices,'public_lkr_rate_evidence',['Rates','Source_Terms','Unverified_Leads']);

const checklist=Workbook.create(),review=checklist.worksheets.add('Review');
for(const name of ['Parameters','Controls','Existing_Sources','Master_Schema','Assumption_Links']){
 const t=audit[name];
 const widths={Parameters:[14,68,29,23,43,43,28,20,85,24,24,55],Controls:[14,74,34,20,83,34,24,55],Existing_Sources:[31,23,14,47,57,84,105,72],Master_Schema:[37,19,32,62,58,53,77],Assumption_Links:[17,25,53,70,43,94,25,63]}[name];
 flat(checklist,name,t.headers,t.rows,widths);
}
review.showGridLines=false;review.tabColor=navy;
review.getRange('A1:H25').format={font:{name:'Arial',size:10,color:ink},rowHeight:27,verticalAlignment:'center'};
review.getRange('A2').values=[['Wedding and Corporate parameter audit']];
review.getRange('A2').format.font={name:'Arial',size:14,bold:true,color:navy};
review.getRange('A3:H3').format.borders={bottom:{style:'thin',color:'#B0BDC9'}};
review.getRange('A5:B5').values=[['Review metric','Count']];
review.getRange('A5:B5').format={fill:navy,font:{color:'#FFFFFF',bold:true}};
review.getRange('A6:A12').values=[['Base parameters, service rates and tax fields'],['Wedding fields'],['Corporate fields'],['Unset proposed numerical values'],['Controls and approval records'],['Master schema columns'],['Simulator assumptions']];
review.getRange('B6').formulas=[["=COUNTA('Parameters'!A2:A109)"]];
review.getRange('B7').formulas=[["=COUNTIFS('Parameters'!A2:A109,\"Wedding\")"]];
review.getRange('B8').formulas=[["=COUNTIFS('Parameters'!A2:A109,\"Corporate\")"]];
review.getRange('B9').formulas=[["=COUNTBLANK('Parameters'!H2:H109)"]];
review.getRange('B10').formulas=[[`=COUNTA('Controls'!A2:A${audit.Controls.rows.length+1})`]];
review.getRange('B11').formulas=[["=COUNTA('Master_Schema'!A2:A47)"]];
review.getRange('B12').formulas=[["=COUNTA('Assumption_Links'!A2:A35)"]];
review.getRange('B6:B12').setNumberFormat('0');
review.getRange('A14').values=[['Numeric configuration approval: NOT READY']];
review.getRange('A14').format.font={name:'Arial',size:11,bold:true,color:'#A22B20'};
const reviewNotes=[
 'Published price evidence is separate from active parameter selection. All active numeric values remain null.',
 'Review status changes do not grant approval or authorize calculations, scenarios or model training.',
 'Evidence supplied must still pass unit, date, tax, inclusion, engine compatibility and formal-review checks.',
 'Shared formulas and controls are listed separately. Wedding and Corporate have separate numerical profiles.',
 'Original cleaned tables, schema, assumption register, quotation templates and engine are preserved.',
 'Resolve billing mismatches and approve frozen formula/parameter hashes before considering a diagnostic pilot.'
];
reviewNotes.forEach((t,i)=>review.getRange(`A${i+16}`).values=[[t]]);
review.getRange('A1:A25').format.columnWidth=51;review.getRange('B1:B25').format.columnWidth=14;
review.getRange('C1:H25').format.columnWidth=20;
// Disposable edit tests blank versus genuine zero in the audit count, then restore.
checklist.worksheets.getItem('Parameters').getRange('H2').values=[[0]];checklist.recalculate();
const test=await checklist.inspect({kind:'table',range:'Review!A9:B9',include:'values',tableMaxRows:1,tableMaxCols:2,maxChars:600});
console.log('ZERO_IS_NOT_MISSING',test.ndjson);
checklist.worksheets.getItem('Parameters').getRange('H2').values=[[null]];
await finish(checklist,'unresolved_parameter_checklist',['Review','Parameters','Controls','Existing_Sources','Master_Schema','Assumption_Links']);

async function finish(wb,file,names){
 wb.recalculate();
 const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:20},maxChars:1000});
 console.log('ERROR_SCAN',file,errors.ndjson);
 for(const name of names){
  const specs=name==='Review'?['A1:H22']:name==='Rates'?['A1:H6','I1:P6']:name==='Source_Terms'?['A1:F5','G1:M5','A13:H18']:name==='Parameters'?['A1:F5','G1:L5']:['A1:D5','E1:'+column(wb.worksheets.getItem(name).getUsedRange().values[0].length-1)+'5'];
  for(let i=0;i<specs.length;i++){
   const img=await wb.render({sheetName:name,range:specs[i],scale:1,format:'png'});
   await fs.writeFile(`work/audit_${file}_${name}_${i}.png`,new Uint8Array(await img.arrayBuffer()));
  }
 }
 const inspect=await wb.inspect({kind:'table',range:file==='public_lkr_rate_evidence'?'Source_Terms!A15:D17':'Review!A6:B12',include:'values,formulas',tableMaxRows:7,tableMaxCols:4,maxChars:2500});
 await fs.writeFile(`work/${file}.inspect.ndjson`,inspect.ndjson);
 await(await SpreadsheetFile.exportXlsx(wb)).save(`reports/${file}.xlsx`);
 console.log('SAVED',file);
}
