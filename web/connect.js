/* Account credentials stay with Puter.js in the browser, never sent to Python. */
(() => {
  'use strict';
  const secret = location.hash.slice(1);
  history.replaceState(null, '', '/');
  const $ = id => document.getElementById(id);
  let connected = false;
  let active = null;
  const headers = { Authorization: `Bearer ${secret}`, 'Content-Type': 'application/json' };
  async function post(path, body) {
    const response = await fetch(path, {method:'POST', headers, body:JSON.stringify(body), cache:'no-store'});
    if (!response.ok) throw new Error('bridge');
    return response.json();
  }
  async function disconnect() {
    connected = false;
    active?.abort();
    try { await post('/connection', {signed_in:false}); } catch (_) {}
    $('status').textContent = 'Disconnected. Use Sign in & connect to reconnect.';
  }
  $('connect').addEventListener('click', async () => {
    if (!secret) { $('status').textContent = 'Reopen this page using Connect AI in Jarvis.'; return; }
    if (!$('consent').checked) { $('status').textContent = 'Tick the chat data disclosure to connect.'; return; }
    if (!window.puter) { $('status').textContent = 'AI SDK unavailable. Check internet and reopen Connect AI.'; return; }
    try {
      // signIn is initiated from a click, so browsers can open the auth popup.
      if (!puter.auth.isSignedIn()) await puter.auth.signIn();
      connected = puter.auth.isSignedIn();
      await post('/connection', {signed_in:connected});
      $('status').textContent = connected ? 'Connected. Return to Jarvis; keep this tab open.' : 'Sign-in did not finish.';
    } catch (_) { await disconnect(); }
  });
  $('disconnect').addEventListener('click', async () => {
    await disconnect();
    try { if (window.puter?.auth.isSignedIn()) await puter.auth.signOut(); } catch (_) {}
  });
  $('consent').addEventListener('change', () => { if (!$('consent').checked) disconnect(); });
  function chatWithAbort(messages, signal) {
    return new Promise((resolve, reject) => {
      const abort = () => reject(new DOMException('Stopped', 'AbortError'));
      if (signal.aborted) { abort(); return; }
      signal.addEventListener('abort', abort, {once:true});
      Promise.resolve().then(() => puter.ai.chat(messages, {stream:false, normalize:true, signal}))
        .then(resolve, reject).finally(() => signal.removeEventListener('abort', abort));
    });
  }
  async function loop() {
    try {
      if (connected) {
        if (!window.puter?.auth.isSignedIn() || !$('consent').checked) { await disconnect(); return; }
        const response = await fetch('/next', {headers, cache:'no-store'});
        if (!response.ok) throw new Error('bridge');
        const {task} = await response.json();
        if (task) {
          active = new AbortController();
          const timer = setTimeout(() => active?.abort(), 85000);
          const beat = setInterval(() => post('/connection', {signed_in:connected, active_id:task.id})
            .then(state => { if (!state.active) active?.abort(); }).catch(() => active?.abort()), 1000);
          try {
            const result = await chatWithAbort(task.messages, active.signal);
            if (!connected || active.signal.aborted) throw new DOMException('Stopped', 'AbortError');
            const text = result?.message?.content;
            if (typeof text !== 'string' || !text.trim() || text.length > 16000) throw new Error('invalid_reply');
            await post('/result', {id:task.id, text});
          } catch (error) {
            const code = String(error?.code || error?.error?.code || error?.status || '');
            const type = active?.signal.aborted ? 'stopped' : /402|429|insufficient|rate|fund/i.test(code) ? 'quota' : 'unavailable';
            await post('/result', {id:task.id, error:type}).catch(() => {});
          } finally {
            clearTimeout(timer); clearInterval(beat); active = null;
          }
        }
      }
    } catch (_) { await disconnect(); }
    finally { setTimeout(loop, 500); }
  }
  loop();
})();
