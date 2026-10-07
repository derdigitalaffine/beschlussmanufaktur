"use strict";

// The secret stays in the URL fragment, which browsers do not send to servers.
// Remove it from the address bar before exchanging it by CSRF-protected POST.
const form = document.getElementById("invitation-code-form");
const token = window.location.hash.slice(1);
if (window.location.hash) {
  window.history.replaceState(null, "", window.location.pathname);
}
if (form && /^[A-Za-z0-9_-]{43}$/.test(token)) {
  document.getElementById("invitation-token").value = token;
  form.requestSubmit();
}
