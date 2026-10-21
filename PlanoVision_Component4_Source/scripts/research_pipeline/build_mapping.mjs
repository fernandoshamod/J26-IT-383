import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
const require=createRequire('C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/package.json');
const {Workbook,SpreadsheetFile}=await import(pathToFileURL(require.resolve('@oai/artifact-tool')));
const data=JSON.parse(await fs.readFile('reports/mapping_workbook_data.json','utf8'));
const wb=Workbook.create();
const col=n=>String.fromCharCode(65+n);
for(const [name,t] of Object.entries(data)){
 const s=wb.worksheets.add(name),end=col(t.headers.length-1),n=t.rows.length+1;
 s.showGridLines=false;
 s.getRange(`A1:${end}${n}`).values=[t.headers,...t.rows];
 s.getRange(`A1:${end}${n}`).format.font={name:'Arial',size:10,color:'#183153'};
 s.getRange(`A1:${end}${n}`).format.verticalAlignment='center';
 s.getRange(`A1:${end}1`).format={fill:'#183153',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},rowHeight:42,wrapText:true,horizontalAlignment:'center'};
 s.getRange(`A2:${end}${n}`).format.rowHeight=72;
 for(let i=0;i<t.headers.length;i++){
  const h=t.headers[i],c=col(i),width=/Reason|Transformation|Gap/.test(h)?65:/Strategy|Status|Model/.test(h)?42:/Source_ID/.test(h)?14:32;
  s.getRange(`${c}1:${c}${n}`).format.columnWidth=width;
  s.getRange(`${c}2:${c}${n}`).format.wrapText=true;
 }
 s.tables.add(`A1:${end}${n}`,true,'Table_'+name).style='TableStyleMedium2';
 s.freezePanes.freezeRows(1);s.freezePanes.freezeColumns(2);
}
wb.recalculate();
const inspection=await wb.inspect({kind:'table',range:'Source_Mapping!A1:K6',include:'values',tableMaxRows:6,tableMaxCols:11,maxChars:2500});
await fs.writeFile('reports/mapping_inspection.ndjson',inspection.ndjson);
for(const name of Object.keys(data)){
 const img=await wb.render({sheetName:name,range:`A1:${col(data[name].headers.length-1)}7`,scale:1,format:'png'});
 await fs.writeFile(`work/${name}_review.png`,new Uint8Array(await img.arrayBuffer()));
}
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!',options:{useRegex:true,maxResults:20},maxChars:1000});
console.log('ERROR_SCAN',errors.ndjson);
await(await SpreadsheetFile.exportXlsx(wb)).save('reports/source_mapping.xlsx');
console.log('SAVED reports/source_mapping.xlsx');
