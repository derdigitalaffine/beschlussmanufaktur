/* Encrypted local storage. No credential, session cookie or key is persisted. */
(() => {
  'use strict';
  const enc=new TextEncoder(), dec=new TextDecoder();
  const b64=bytes=>{const array=new Uint8Array(bytes);let value='';for(let i=0;i<array.length;i+=32768)value+=String.fromCharCode(...array.subarray(i,i+32768));return btoa(value);};
  const un64=value=>Uint8Array.from(atob(value),c=>c.charCodeAt(0));
  async function derive(password,salt) {
    if(typeof password!=='string'||password.length<12)throw new Error('Offline-Passwort benötigt mindestens zwölf Zeichen.');
    const material=await crypto.subtle.importKey('raw',enc.encode(password),'PBKDF2',false,['deriveKey']);
    return crypto.subtle.deriveKey({name:'PBKDF2',salt,iterations:250000,hash:'SHA-256'},material,{name:'AES-GCM',length:256},false,['encrypt','decrypt']);
  }
  async function seal(data,password,id) {
    const salt=crypto.getRandomValues(new Uint8Array(16)), iv=crypto.getRandomValues(new Uint8Array(12)),key=await derive(password,salt);
    const cipher=await crypto.subtle.encrypt({name:'AES-GCM',iv,additionalData:enc.encode(id)},key,enc.encode(JSON.stringify(data)));
    return {id,salt:b64(salt),iv:b64(iv),cipher:b64(cipher),expires_at:data.expires_at};
  }
  async function open(record,password) {
    const key=await derive(password,un64(record.salt));
    const plain=await crypto.subtle.decrypt({name:'AES-GCM',iv:un64(record.iv),additionalData:enc.encode(record.id)},key,un64(record.cipher));
    return JSON.parse(dec.decode(plain));
  }
  function database(){return new Promise((resolve,reject)=>{const r=indexedDB.open('beschlussmanufaktur-offline-v1',1);r.onupgradeneeded=()=>r.result.createObjectStore('sessions',{keyPath:'id'});r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});}
  async function operation(mode,fn){const db=await database();return new Promise((resolve,reject)=>{const tx=db.transaction('sessions',mode),r=fn(tx.objectStore('sessions'));tx.oncomplete=()=>{db.close();resolve(r.result);};tx.onerror=()=>{db.close();reject(tx.error);};tx.onabort=()=>{db.close();reject(tx.error);};});}
  const api={seal,open,list:()=>operation('readonly',s=>s.getAll()),get:id=>operation('readonly',s=>s.get(id)),put:record=>operation('readwrite',s=>s.put(record)),remove:id=>operation('readwrite',s=>s.delete(id)),clear:()=>operation('readwrite',s=>s.clear())};
  globalThis.OfflineStore=api;
  if(typeof module!=='undefined')module.exports=api;
})();
