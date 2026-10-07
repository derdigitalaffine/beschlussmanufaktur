'use strict';
const CACHE='beschlussmanufaktur-shell-v1';
const SHELL=['/static/offline.html','/static/offline.js','/static/offline_store.js','/static/app.css'];
self.addEventListener('install',event=>{event.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting()));});
self.addEventListener('activate',event=>{event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('beschlussmanufaktur-shell-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
self.addEventListener('fetch',event=>{
 const url=new URL(event.request.url);
 // Only public static shell resources. Never cache authenticated HTML, API,
 // PDFs, session responses or a navigation elsewhere in the application.
 if(event.request.method!=='GET'||url.origin!==self.location.origin||!SHELL.includes(url.pathname))return;
 event.respondWith(fetch(event.request).then(async response=>{
  if(response.ok&&url.search===''){const cache=await caches.open(CACHE);await cache.put(url.pathname,response.clone());}
  return response;
 }).catch(()=>caches.match(url.pathname)));
});
