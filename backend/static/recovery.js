'use strict';
(() => {const input=document.querySelector('[name=token]');const code=window.location.hash.slice(1);if(input && /^[A-Za-z0-9_-]{43}$/.test(code)){input.value=code;history.replaceState(null,'',window.location.pathname);}})();
