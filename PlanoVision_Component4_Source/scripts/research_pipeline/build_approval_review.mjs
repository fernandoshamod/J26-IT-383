import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
const require=createRequire('C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/package.json');
const {Workbook,SpreadsheetFile}=await import(pathToFileURL(require.resolve('@oai/artifact-tool')));
const data=JSON.parse(await fs.readFile('work/approval_review_tables.json','utf8'));
const wb=Workbook.create(),review=wb.worksheets.add('Review');
const navy='#213B58',ink='#223449',amber='#FFF2CE';
const col=n=>{let s='';for(n++;n;n=Math.floor((n-1)/26))s=String.fromCharCode(65+(n-1)%26)+s;return s;};
const order=['Wedding','Corporate','Formulas','Assumptions','Policies','Shared_Controls','References'];
for(const name of order){
 const t=data.tables[name],s=wb.worksheets.add(name),end=col(t.headers.length-1),last=t.rows.length+1;
 s.showGridLines=false;s.getRange(`A1:${end}${last}`).values=[t.headers,...t.rows];
 s.getRange(`A1:${end}${last}`).format={font:{name:'Arial',size:10,color:ink},verticalAlignment:'center'};
 s.getRange(`A1:${end}1`).format={fill:navy,font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},rowHeight:42,wrapText:true,horizontalAlignment:'center'};
 s.getRange(`A2:${end}${last}`).format.wrapText=true;
 s.getRange(`A2:${end}${last}`).format.rowHeight=['Formulas','Assumptions','Policies'].includes(name)?76:58;
 for(let i=0;i<t.headers.length;i++){
  const h=t.headers[i],c=col(i);
  const widths={Decision_ID:22,Assumption_ID:18,Formula_ID:18,Assumption_IDs:29,Assumption_Version:43,Config_Path:75,Unit:34,Evidence_Type:45,Supporting_Refs:39,Proposed_Value:22,Required_Decision:97,Status:27,Reviewer:30,Reviewer_Role:33,Review_Date:20,Rationale:72,Decision_Evidence_Ref:61,Record_Complete:23,Category:32,Original_Definition:100,Review_Required:85,Validation_Findings:105,Expression:100,Policy_ID:39,Scope:21,Option_Values_JSON:68,Supporting_Rationale:94,Constraints:113,Selected_Value:28,Reference_ID:20,Source_or_Document:55,Applicability_Limit:95,URL_or_Project_Reference:105};
  s.getRange(`${c}1:${c}${last}`).format.columnWidth=widths[h]??3;
  if(['Proposed_Value','Selected_Value'].includes(h)){
   s.getRange(`${c}2:${c}${last}`).setNumberFormat('#,##0.00');
   s.getRange(`${c}2:${c}${last}`).format.horizontalAlignment='right';
  }
  if(h==='Review_Date'){
   s.getRange(`${c}2:${c}${last}`).setNumberFormat('yyyy-mm-dd');
  }
  if(h==='Status'){
   s.getRange(`${c}2:${c}${last}`).dataValidation={rule:{type:'list',values:['Pending review','Needs amendment','Approved in scope','Rejected','Deferred']}};
   s.getRange(`${c}2:${c}${last}`).conditionalFormats.add('containsText',{text:'Pending review',format:{fill:amber,font:{color:'#805600'}}});
  }
 }
 if(name!=='References'){
  const hasValue=['Wedding','Corporate','Shared_Controls'].includes(name),valueCheck=hasValue?',H2<>""':name==='Policies'?',I2<>""':'';
  s.getRange('P2').formulas=[[`=AND(J2="Approved in scope",K2<>"",L2<>"",ISNUMBER(M2),N2<>"",O2<>"",C2<>""${valueCheck})`]];
  s.getRange(`P2:P${last}`).fillDown();
  s.getRange(`P2:P${last}`).format.horizontalAlignment='center';
 }
 s.tables.add(`A1:${end}${last}`,true,'T_'+name).style='TableStyleMedium2';
 s.freezePanes.freezeRows(1);s.freezePanes.freezeColumns(2);
}
review.showGridLines=false;review.tabColor=navy;
review.getRange('A1:I26').format={font:{name:'Arial',size:10,color:ink},rowHeight:27,verticalAlignment:'center'};
review.getRange('A2').values=[['Component 4 assumption and parameter decisions']];
review.getRange('A2').format.font={name:'Arial',size:14,bold:true,color:navy};
review.getRange('A3:I3').format.borders={bottom:{style:'thin',color:'#AAB9CA'}};
review.getRange('A5:D5').values=[['Review scope','Decisions','Pending','Complete records']];
review.getRange('A5:D5').format={fill:navy,font:{name:'Arial',size:10,color:'#FFFFFF',bold:true},horizontalAlignment:'center'};
review.getRange('A6:A11').values=[['Wedding inputs and controls'],['Corporate inputs and controls'],['Active formulas and utilities'],['Original assumption IDs'],['Hypothetical policy menus'],['Shared approval/reproducibility controls']];
for(const [i,name] of ['Wedding','Corporate','Formulas','Assumptions','Policies','Shared_Controls'].entries()){
 const row=i+6,last=data.tables[name].rows.length+1;
 review.getRange(`B${row}`).formulas=[[`=COUNTA('${name}'!A2:A${last})`]];
 review.getRange(`C${row}`).formulas=[[`=COUNTIFS('${name}'!J2:J${last},"Pending review")`]];
 review.getRange(`D${row}`).formulas=[[`=COUNTIFS('${name}'!P2:P${last},TRUE)`]];
}
review.getRange('A13').values=[['Unset active Wedding numeric fields']];
review.getRange('B13').formulas=[["=COUNTBLANK('Wedding'!H2:H55)"]];
review.getRange('A14').values=[['Unset active Corporate numeric fields']];
review.getRange('B14').formulas=[["=COUNTBLANK('Corporate'!H2:H55)"]];
review.getRange('B6:D14').setNumberFormat('0');
review.getRange('A16').values=[['Candidate remains proposed and unresolved. Not frozen or approved.']];
review.getRange('A16').format.font={name:'Arial',size:11,bold:true,color:'#A22B20'};
const notes=[
 'Record_Complete checks required fields only. It cannot verify a signature, expertise or evidence authenticity.',
 'All reviewer identities, review dates and rationales are blank. Status changes alone do not authorize execution.',
 'Hypothetical option menus are not active parameter values, local market prices or empirical distributions.',
 'Workbook decisions do not update the JSON automatically. Qualified scope review and explicit user selection are separate.',
 'Original register and Stage 1 evidence remain unchanged. Corrected mapping: A005 guest occupancy; A008 seated share.',
 'Resolve venue billing, independent AV steps, standing-area limitations, general staffing and tax/bundle scope.',
 'Draft content hashes identify this version. No pilot, bulk generation or model training is authorized.'
];
notes.forEach((text,i)=>review.getRange(`A${i+18}`).values=[[text]]);
review.getRange('A1:A26').format.columnWidth=55;review.getRange('B1:D26').format.columnWidth=20;
review.getRange('E1:I26').format.columnWidth=18;

// A status without any reviewer fields must never become a complete record.
const wedding=wb.worksheets.getItem('Wedding');
wedding.getRange('J2').values=[['Approved in scope']];wedding.getRange('H2').values=[[0]];wb.recalculate();
console.log('PARTIAL_RECORD', (await wb.inspect({kind:'table',range:'Wedding!J2:P2',include:'values',tableMaxRows:1,tableMaxCols:7,maxChars:900})).ndjson);
console.log('PARTIAL_COUNT', (await wb.inspect({kind:'table',range:'Review!A6:D6',include:'values',tableMaxRows:1,tableMaxCols:4,maxChars:700})).ndjson);
wedding.getRange('J2').values=[['Pending review']];wedding.getRange('H2').values=[[null]];wb.recalculate();
const summary=await wb.inspect({kind:'table',range:'Review!A6:D14',include:'values,formulas',tableMaxRows:9,tableMaxCols:4,maxChars:2000});
await fs.writeFile('work/approval_review.inspect.ndjson',summary.ndjson);
console.log('COUNTS',summary.ndjson);
console.log('ERROR_SCAN',(await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:20},maxChars:800})).ndjson);
for(const name of ['Review',...order]){
 const ranges=name==='Review'?['A1:I26']:name==='References'?['A1:C5','E1:E5']:['A1:H5','I1:P5'];
 for(let i=0;i<ranges.length;i++){
  const img=await wb.render({sheetName:name,range:ranges[i],scale:1,format:'png'});
  await fs.writeFile(`work/stage2_${name}_${i}.png`,new Uint8Array(await img.arrayBuffer()));
 }
}
await(await SpreadsheetFile.exportXlsx(wb)).save('reports/assumption_decision_matrix.xlsx');
console.log('SAVED reports/assumption_decision_matrix.xlsx');
