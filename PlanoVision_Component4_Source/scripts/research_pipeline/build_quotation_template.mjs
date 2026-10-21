import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
const require=createRequire('C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/package.json');
const {Workbook,SpreadsheetFile}=await import(pathToFileURL(require.resolve('@oai/artifact-tool')));
const metadata=JSON.parse(await fs.readFile('reports/quotation_template_metadata.json','utf8'));
const wb=Workbook.create(),navy='#183153';
function col(n){let s='';for(n++;n;n=Math.floor((n-1)/26))s=String.fromCharCode(65+(n-1)%26)+s;return s;}
const options={Event_Type:['Wedding','Corporate'],Currency:['LKR'],Tax_Scope:['inclusive','exclusive','unresolved'],Evidence_Kind:['observed_quote','observed_contract','declared_plan','measured_layout','unverified'],Approval_Status:['pending','approved','rejected'],Decision:['pending','approved','rejected','needs_amendment'],Approval_Kind:['technical_recommendation','formula_approval','parameter_approval'],Permission_Status:['pending','permitted','restricted']};
for(const [name,headers] of Object.entries(metadata)){
 const s=wb.worksheets.add(name),end=col(headers.length-1);
 s.showGridLines=false;
 s.getRange(`A1:${end}26`).values=[headers,...Array.from({length:25},()=>headers.map(()=>null))];
 s.getRange(`A1:${end}26`).format={font:{name:'Arial',size:10,color:navy},verticalAlignment:'center',rowHeight:24};
 s.getRange(`A1:${end}1`).format={fill:navy,font:{name:'Arial',size:10,color:'#FFFFFF',bold:true},rowHeight:64,wrapText:true,horizontalAlignment:'center'};
 for(let i=0;i<headers.length;i++){
  const h=headers[i],c=col(i),r=s.getRange(`${c}2:${c}26`);
  s.getRange(`${c}1:${c}26`).format.columnWidth=h.length>24?28:23;
  if(options[h])r.dataValidation={rule:{type:'list',values:options[h]}};
  if(/Date|Valid_Until/.test(h))r.setNumberFormat('yyyy-mm-dd');
  else if(/LKR|Rate$|Quoted_Total/.test(h)){r.setNumberFormat('#,##0.00');r.format.horizontalAlignment='right';}
  else if(/Hours|Area|_m$|_m2|Share|Ratio|Points|Multiplier|Quantity$|Approved_Min|Approved_Max/.test(h)){r.setNumberFormat('0.00');r.format.horizontalAlignment='right';}
  else if(/Guests|Seats|Staff_Count|Base_Staff|Capacity_Persons/.test(h)){r.setNumberFormat('0');r.format.horizontalAlignment='right';}
 }
 s.tables.add(`A1:${end}26`,true,'Collection_'+name).style='TableStyleMedium2';
 s.freezePanes.freezeRows(1);s.freezePanes.freezeColumns(2);
}
const notes=wb.worksheets.add('ReadMe');notes.showGridLines=false;notes.tabColor='#8797AA';
notes.getRange('A1:B18').format={font:{name:'Arial',size:10,color:navy},rowHeight:48,verticalAlignment:'center',wrapText:true};
notes.getRange('A1:A18').format.columnWidth=27;notes.getRange('B1:B18').format.columnWidth=105;
notes.getRange('A2').values=[['Sri Lankan event quotations']];notes.getRange('A2').format.font={name:'Arial',size:14,bold:true,color:navy};
notes.getRange('A4:B16').values=[
 ['Contents','Blank collection tables. Reserved rows are not observations. No market rates or synthetic event records are supplied.'],
 ['Identifiers','Use Event_ID and Quote_ID consistently. Keep vendor names pseudonymous and store source evidence with permission.'],
 ['Rates / units','Record original rates, LKR, quantity units, quote date and validity. Unknown is blank, not zero.'],
 ['Tax','Record inclusive/exclusive scope and percentage points from the quotation. Do not assume a tax rate.'],
 ['Inclusions','Identify bundled services and exclusions, fixed charges, discounts and overtime. Avoid duplicate charges.'],
 ['Geometry','Record measured dimensions and arrangement-specific approved capacity. Do not derive floor area from capacity.'],
 ['Staffing','Record role, count, paid setup/event/clearance hours, regular hours, overtime and vendor-package coverage.'],
 ['Fractions / points','Seat_Share and Reserve_Ratio use 0–1 fractions. Margin and tax use 0–100 percentage points. Areas are m².'],
 ['Revenue','Expected retained service receipts are not observed actual revenue. Confirm contract scope and pass-through exclusions.'],
 ['Approvals','Technical recommendations are NOT formal approvals. Record reviewer name/role/date, rationale, scope and evidence.'],
 ['POC limits','Only Wedding and Corporate, package catering and a separate general-staff pool. Unsupported quote terms require engine amendment.'],
 ['Evidence','Evidence_Ref belongs beside each record. Keep raw quotes/plans intact; store consent and source hashes separately.'],
 ['Next step','Use the accompanying collection guide and pilot conditions. Missing parameters and approvals block live simulation.']
 ];
wb.recalculate();
for(const name of [...Object.keys(metadata),'ReadMe']){
 const range=name==='ReadMe'?'A1:B16':'A1:F5';
 const inspect=await wb.inspect({kind:'table',range:`${name}!${range}`,include:'values,formulas',tableMaxRows:5,tableMaxCols:6,maxChars:1300});
 await fs.writeFile(`work/quotation_${name}.inspect.ndjson`,inspect.ndjson);
 const preview=await wb.render({sheetName:name,range,scale:1,format:'png'});
 await fs.writeFile(`work/quotation_${name}.png`,new Uint8Array(await preview.arrayBuffer()));
}
const scan=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:20},maxChars:1000});
console.log('ERROR_SCAN',scan.ndjson);
const dest='reports/sri_lanka_quotation_collection_template.xlsx';
await(await SpreadsheetFile.exportXlsx(wb)).save(dest);
console.log('SAVED',dest);
