import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
const require=createRequire('C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/package.json');
const {Workbook,SpreadsheetFile}=await import(pathToFileURL(require.resolve('@oai/artifact-tool')));
const data=JSON.parse(await fs.readFile('reports/simulation_review_data.json','utf8'));
const wb=Workbook.create(),review=wb.worksheets.add('Review');
const navy='#183153',ink='#183153',amber='#FFF3D6';
const col=n=>String.fromCharCode(65+n);
for(const [name,t] of Object.entries(data)){
 const s=wb.worksheets.add(name),end=col(t.headers.length-1),n=t.rows.length+1;
 s.showGridLines=false;s.getRange(`A1:${end}${n}`).values=[t.headers,...t.rows];
 s.getRange(`A1:${end}${n}`).format.font={name:'Arial',size:10,color:ink};
 s.getRange(`A1:${end}${n}`).format.verticalAlignment='center';
 s.getRange(`A1:${end}1`).format={fill:navy,font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},rowHeight:46,wrapText:true,horizontalAlignment:'center'};
 s.getRange(`A2:${end}${n}`).format.rowHeight=name==='Assumptions'?112:82;
 s.getRange(`A2:${end}${n}`).format.wrapText=true;
 for(let i=0;i<t.headers.length;i++){
  const h=t.headers[i],c=col(i);
  let width=name==='Assumptions'?[15,25,38,52,64,48,28,48,32,48,48,25][i]:[15,44,34,12,15,15,15,15,15,27,68,72,72][i];
  s.getRange(`${c}1:${c}${n}`).format.columnWidth=width;
  if(name==='Observed_Evidence' && ['N','Min','Q25','Median','Q75','Max'].includes(h)){
   s.getRange(`${c}2:${c}${n}`).setNumberFormat(h==='N'?'0':'#,##0.00');
   s.getRange(`${c}2:${c}${n}`).format.horizontalAlignment='right';
  }
 }
 s.tables.add(`A1:${end}${n}`,true,'T_'+name).style='TableStyleMedium2';
 s.freezePanes.freezeRows(1);s.freezePanes.freezeColumns(2);
 if(name==='Assumptions'){
  s.getRange(`L2:L${n}`).dataValidation={rule:{type:'list',values:['Pending review','Formula approved','Approved for simulator','Rejected','Needs amendment']}};
  s.getRange(`L2:L${n}`).conditionalFormats.add('containsText',{text:'Pending review',format:{fill:amber,font:{color:'#805A00'}}});
 }
}
review.showGridLines=false;review.tabColor=navy;
review.getRange('A1:F25').format.font={name:'Arial',size:10,color:ink};
review.getRange('A1:F25').format.rowHeight=26;
review.getRange('A2').values=[['Simulator assumption review']];review.getRange('A2').format.font={name:'Arial',size:16,bold:true,color:navy};
review.getRange('A3:F3').format.borders={bottom:{style:'thin',color:'#AAB9CA'}};
review.getRange('A5:A9').values=[['Assumptions'],['Pending review'],['Formula approved only'],['Approved for simulator'],['Rejected / needs amendment']];
const last=data.Assumptions.rows.length+1;
review.getRange('B5').formulas=[[`=COUNTA('Assumptions'!$A$2:$A$${last})`]];
for(const [r,status] of [[6,'Pending review'],[7,'Formula approved'],[8,'Approved for simulator']])review.getRange(`B${r}`).formulas=[[`=COUNTIFS('Assumptions'!$L$2:$L$${last},"${status}")`]];
review.getRange('B9').formulas=[[`=COUNTIFS('Assumptions'!$L$2:$L$${last},"Rejected")+COUNTIFS('Assumptions'!$L$2:$L$${last},"Needs amendment")`]];
review.getRange('B5:B9').setNumberFormat('0');
const notes=[
 'Review draft only. No scenarios or models have been generated.',
 'Confidence labels describe evidence type, not numerical confidence or approval.',
 'Source quantiles describe the collected snapshot. They are not market estimates.',
 'Approve formulas and numeric parameters separately. Unset rates/areas block generation.',
 'Edit Approval_Status in Assumptions. Formula approved does not authorise generation.',
 'Approval needs a separate reviewer/date/rationale and versioned numeric config record.',
 'Simulated actuals/targets must retain mandatory synthetic-origin provenance.',
 'The six accompanying documents define dependencies, labels, graphs and validation.'
];
notes.forEach((t,i)=>review.getRange(`A${i+12}`).values=[[t]]);
review.getRange('A1:A25').format.columnWidth=39;review.getRange('B1:B25').format.columnWidth=14;
review.getRange('C1:F25').format.columnWidth=28;
wb.recalculate();
const check=await wb.inspect({kind:'table',range:'Review!A5:B9',include:'values,formulas',tableMaxRows:5,tableMaxCols:2,maxChars:2000});
console.log('COUNTS',check.ndjson);
// Test a status change then restore; this validates the formula-linked review counts.
wb.worksheets.getItem('Assumptions').getRange('L2').values=[['Formula approved']];wb.recalculate();
const changed=await wb.inspect({kind:'table',range:'Review!A6:B7',include:'values',tableMaxRows:2,tableMaxCols:2,maxChars:1200});
await fs.writeFile('work/simulation_status_check.ndjson',changed.ndjson);
wb.worksheets.getItem('Assumptions').getRange('L2').values=[['Pending review']];wb.recalculate();
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!',options:{useRegex:true,maxResults:20},maxChars:1000});
console.log('ERROR_SCAN',errors.ndjson);
for(const [name,range,file] of [['Review','A1:F20','review'],['Assumptions','A1:F7','assumptions_left'],['Assumptions','G1:L7','assumptions_right'],['Observed_Evidence','A1:K11','evidence']]){
 const img=await wb.render({sheetName:name,range,scale:1,format:'png'});
 await fs.writeFile(`work/simulation_${file}.png`,new Uint8Array(await img.arrayBuffer()));
}
await(await SpreadsheetFile.exportXlsx(wb)).save('reports/simulation_assumption_register.xlsx');
console.log('SAVED reports/simulation_assumption_register.xlsx');
