/* Static GitHub Pages client. No API keys or desktop-control bridge. */
(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const history = [];
  let controller = null;
  const system = 'You are JARVIS, a practical creative assistant created by Haseeb Crafts for Abdul Haseeb. Reply in concise natural Roman Urdu unless another language is requested. Help with writing, coding, prompts and planning. This is browser chat: no desktop control, files, web search or execution tools are connected. Never pretend an action succeeded. Answer only with useful final output, not hidden reasoning.';

  function message(role, text) {
    const block = document.createElement('article');
    block.className = `message ${role}`;
    const name = document.createElement('b');
    name.textContent = role === 'user' ? 'YOU' : role === 'error' ? 'CONNECTION NOTICE' : 'JARVIS';
    const body = document.createElement('p');
    body.textContent = text;
    block.append(name, body);
    $('chat').append(block);
    $('chat').scrollTop = $('chat').scrollHeight;
  }

  function connection() {
    if (!window.puter) {
      $('status').textContent = 'AI SDK unavailable · reload and connect again';
      return false;
    }
    const signed = window.puter.auth.isSignedIn();
    $('login').textContent = signed ? 'Disconnect AI' : 'Connect AI';
    $('status').textContent = signed ? 'AI connected · allowance applies' : 'Connect AI to start chatting';
    return signed;
  }

  $('login').addEventListener('click', async () => {
    if (controller) return;
    if (!window.puter) {
      message('error', 'AI connection load nahi hui. Internet/ad blocker check karke page reload karein, phir reload karke Connect AI dobara try karein.');
      return;
    }
    try {
      if (window.puter.auth.isSignedIn()) {
        await window.puter.auth.signOut();
        history.length = 0;
        $('chat').textContent = '';
        message('assistant', 'AI disconnect ho gayi. Nayi chat ke liye Connect AI dabayein.');
      } else {
        // Called directly by a user click so sign-in can open its popup.
        await window.puter.auth.signIn();
      }
      connection();
    } catch (err) {
      message('error', 'Sign-in complete nahi hui. Connect AI dobara try karein aur browser mein popup allow karein.');
      connection();
    }
  });

  $('newChat').addEventListener('click', () => {
    if (controller) return;
    history.length = 0;
    $('chat').textContent = '';
    message('assistant', 'Salam Haseeb bhai! Aaj kya banayein?');
  });

  document.querySelectorAll('#suggestions button').forEach((button) => {
    button.addEventListener('click', () => {
      $('message').value = button.textContent;
      $('message').focus();
    });
  });

  $('message').addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      $('form').requestSubmit();
    }
  });
  $('stop').addEventListener('click', () => controller?.abort());

  $('form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const text = $('message').value.trim();
    if (!text || controller) return;
    if (text.length > 4000) {
      message('error', 'Message 4,000 characters se chhota rakhein.');
      return;
    }
    if (!connection()) {
      message('error', 'Pehle upar Connect AI dabayein. API key nahi chahiye; Puter sign-in aur free allowance use hogi.');
      return;
    }
    const next = history.concat({ role: 'user', content: text }).slice(-10);
    if (next.reduce((n, item) => n + item.content.length, 0) > 18000) {
      message('error', 'Conversation lambi ho gayi. New conversation se dobara shuru karein.');
      return;
    }
    message('user', text);
    $('message').value = '';
    controller = new AbortController();
    const active = controller;
    $('send').disabled = true;
    $('login').disabled = true;
    $('newChat').disabled = true;
    $('stop').hidden = false;
    $('status').textContent = 'Jarvis is thinking…';
    const timer = setTimeout(() => active.abort(), 90000);
    try {
      const result = await window.puter.ai.chat(
        [{ role: 'system', content: system }, ...next],
        { stream: false, normalize: true, signal: active.signal }
      );
      if (active.signal.aborted) throw new DOMException('Stopped', 'AbortError');
      const reply = result?.message?.content;
      if (typeof reply !== 'string' || !reply.trim()) throw new Error('empty_reply');
      history.splice(0, history.length, ...next, { role: 'assistant', content: reply });
      if (history.length > 10) history.splice(0, history.length - 10);
      message('assistant', reply);
    } catch (err) {
      const code = String(err?.code || err?.error?.code || err?.status || '');
      if (active.signal.aborted || err?.name === 'AbortError') {
        message('error', 'Reply rok di ya timeout hua. Zaroorat ho to dobara bhejein.');
      } else if (/402|429|insufficient|rate|fund/i.test(code)) {
        message('error', 'Free allowance ya rate limit poori ho gayi. Puter account usage check karein; koi paid upgrade automatic nahi ki gayi.');
      } else {
        message('error', 'AI reply nahi aa saki. Internet, sign-in aur account allowance check karein, phir dobara bhejein.');
      }
      // Keep the input so retry does not require rewriting it.
      if (!$('message').value) $('message').value = text;
    } finally {
      clearTimeout(timer);
      controller = null;
      $('send').disabled = false;
      $('login').disabled = false;
      $('newChat').disabled = false;
      $('stop').hidden = true;
      connection();
    }
  });

  message('assistant', 'Salam Haseeb bhai! Main Jarvis hoon. Writing, coding, video prompts aur planning mein madad kar sakta hoon. Shuru karne ke liye Connect AI dabayein.');
  connection();
})();

