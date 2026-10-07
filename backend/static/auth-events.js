'use strict';
const logout=document.querySelector('form[action="/abmelden/"]');
if(logout&&'BroadcastChannel' in window)logout.addEventListener('submit',()=>{new BroadcastChannel('beschlussmanufaktur-auth').postMessage('logout');});
