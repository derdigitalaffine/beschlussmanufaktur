'use strict';
const csrf = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
for (const area of document.querySelectorAll('[data-editor]')) {
  const tools = document.createElement('div'); tools.className = 'editor-tools';
  for (const [label, before, after] of [['Fett','**','**'],['Kursiv','*','*'],['Überschrift','## ',''],['Liste','- ',''],['Zitat','> ',''],['Tabelle','| Spalte | Spalte |\n| --- | --- |\n| Inhalt | Inhalt |','']]) {
    const button = document.createElement('button');button.type='button';button.textContent=label;
    button.addEventListener('click',()=>{const start=area.selectionStart,end=area.selectionEnd;const text=area.value.slice(start,end);area.setRangeText(before+text+after,start,end,'select');area.focus();});tools.append(button);
  }
  const previewButton=document.createElement('button');previewButton.type='button';previewButton.textContent='Formatierte Vorschau';tools.append(previewButton);
  const output=document.createElement('section');output.className='markdown-preview';output.hidden=true;
  previewButton.addEventListener('click',async()=>{
    try {const res=await fetch('/vorlagen/vorschau/',{method:'POST',headers:{'X-CSRFToken':csrf},body:new URLSearchParams({markdown:area.value})});if(!res.ok)throw Error();output.innerHTML=(await res.json()).html;output.hidden=false;}
    catch {output.textContent='Vorschau derzeit nicht verfügbar. Ihr Text bleibt erhalten.';output.hidden=false;}
  });
  area.before(tools);area.after(output);
}
const presence=document.querySelector('[data-presence]');
async function heartbeat(){
  if(!presence)return;
  try {const res=await fetch(presence.dataset.presence,{method:'POST',headers:{'X-CSRFToken':csrf}});if(!res.ok)throw Error();presence.textContent='Aktuell beteiligt: '+(await res.json()).people.join(', ');}
  catch {presence.textContent='Verbindung zur Bearbeitungsanzeige unterbrochen. Speichern prüft den aktuellen Stand.';}
}
if(presence){heartbeat();setInterval(heartbeat,30000);}
// A local formatted editing surface. Paste enters plain text; server rendering remains authoritative.
function domMarkdown(node) {
  if(node.nodeType===Node.TEXT_NODE)return node.textContent;
  if(node.nodeType!==Node.ELEMENT_NODE)return '';
  const tag=node.tagName.toLowerCase(), inner=[...node.childNodes].map(domMarkdown).join('');
  if(['strong','b'].includes(tag))return '**'+inner+'**';
  if(['em','i'].includes(tag))return '*'+inner+'*';
  if(/^h[1-4]$/.test(tag))return '\n\n'+'#'.repeat(Number(tag[1]))+' '+inner+'\n\n';
  if(tag==='br')return '\n';
  if(tag==='p'||tag==='div')return inner+'\n\n';
  if(tag==='blockquote')return '\n'+inner.trim().split('\n').map(x=>'> '+x).join('\n')+'\n\n';
  if(tag==='pre')return '\n\n```\n'+node.textContent+'\n```\n\n';
  if(tag==='code')return '`'+inner+'`';
  if(tag==='li')return '- '+inner.trim()+'\n';
  if(tag==='ul'||tag==='ol')return '\n'+inner+'\n';
  if(tag==='a') {const href=node.getAttribute('href')||'';return /^(https:|mailto:)/.test(href)?'['+inner+']('+href+')':inner;}
  if(tag==='table') {const rows=[...node.querySelectorAll('tr')].map(tr=>[...tr.children].map(td=>domMarkdown(td).trim().replaceAll('|','\\|')).join(' | '));if(!rows.length)return '';const cols=node.querySelector('tr').children.length;return '\n\n| '+rows[0]+' |\n| '+Array(cols).fill('---').join(' | ')+' |\n'+rows.slice(1).map(x=>'| '+x+' |').join('\n')+'\n\n';}
  return inner;
}
for(const area of document.querySelectorAll('[data-editor]')) {
  const button=document.createElement('button');button.type='button';button.textContent='Formatiert bearbeiten';
  const surface=document.createElement('div');surface.className='formatted-editor markdown-preview';surface.contentEditable='true';surface.setAttribute('role','textbox');surface.setAttribute('aria-label','Formatierter Vorlagentext');surface.hidden=true;
  const formatTools=document.createElement('div');formatTools.className='editor-tools';formatTools.hidden=true;
  for(const [label,command,arg] of [['Fett','bold',null],['Kursiv','italic',null],['Überschrift','formatBlock','h2'],['Absatz','formatBlock','p'],['Liste','insertUnorderedList',null]]) {const b=document.createElement('button');b.type='button';b.textContent=label;b.addEventListener('mousedown',e=>e.preventDefault());b.addEventListener('click',()=>{surface.focus();document.execCommand(command,false,arg);surface.dispatchEvent(new Event('input'));});formatTools.append(b);}
  const sync=()=>{if(!surface.hidden)area.value=domMarkdown(surface).trim()+'\n';};
  surface.addEventListener('input',sync);
  surface.addEventListener('paste',e=>{e.preventDefault();document.execCommand('insertText',false,e.clipboardData.getData('text/plain'));sync();});
  button.addEventListener('click',async()=>{
    if(surface.hidden){try {const res=await fetch('/vorlagen/vorschau/',{method:'POST',headers:{'X-CSRFToken':csrf},body:new URLSearchParams({markdown:area.value})});if(!res.ok)throw Error();surface.innerHTML=(await res.json()).html;surface.hidden=false;formatTools.hidden=false;area.hidden=true;button.textContent='Markdown-Quelle bearbeiten';surface.focus();}catch {button.textContent='Verbindung prüfen – erneut formatiert öffnen';}}
    else{sync();surface.hidden=true;formatTools.hidden=true;area.hidden=false;button.textContent='Formatiert bearbeiten';area.focus();}
  });
  area.before(button,formatTools);area.after(surface);area.closest('form').addEventListener('submit',sync);
}
