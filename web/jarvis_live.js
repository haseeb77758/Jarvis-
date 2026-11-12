/* JARVIS desktop WebRTC. Pinned LiveKit v2.23.0 UMD, no native Python SDK. */
(() => {
  "use strict";
  const el = (id) => document.getElementById(id);
  const sdk = window.LivekitClient;
  const secretHash = location.hash.slice(1);
  const nonce = secretHash.split("~")[0];
  const auto = secretHash.endsWith("~auto");
  history.replaceState(null, "", location.pathname);
  let room = null, busy = false, muted = false, latestRoom = null;
  let countdown = null, poller = null, deadline = 0;
  const knownAudios = new Set();
  let micMeterTimer = null, silentTicks = 0, detectedMicSound = false;
  let microphoneReady = false, speakerBlocked = false;
  function micStatus(message, warning = false) {
    el("micStatus").textContent = message;
    el("micStatus").style.color = warning ? "#ffb47e" : "";
    el("micHint").textContent = message;
  }
  function playbackState() {
    if (!room) return;
    const blocked = room.canPlaybackAudio === false || speakerBlocked;
    el("enableAudio").hidden = !blocked;
    el("speakerStatus").textContent = blocked
      ? "BLOCKED · click Enable speaker audio" : "Audio enabled";
    if (blocked) {
      report("Agent audio is blocked by browser autoplay. Click ENABLE SPEAKER AUDIO now.", "error");
      activity("Audio playback needs one direct user click.");
    }
  }
  function startMicMeter() {
    clearInterval(micMeterTimer);
    silentTicks = 0;
    detectedMicSound = false;
    micMeterTimer = setInterval(() => {
      if (!room || !microphoneReady) return;
      const local = room.localParticipant;
      const active = local && local.isMicrophoneEnabled !== false && !muted;
      if (!active) {
        el("micLevel").value = 0;
        micStatus("Muted");
        return;
      }
      const level = Math.max(0, Math.min(1, Number(local.audioLevel) || 0));
      el("micLevel").value = Math.min(100, Math.round(level * 260));
      if (level > 0.018) {
        silentTicks = 0;
        if (!detectedMicSound) {
          detectedMicSound = true;
          activity("Microphone level detected · audio input active.");
        }
        micStatus("Input signal detected");
      } else {
        silentTicks++;
        if (silentTicks > 24 && !detectedMicSound) {
          micStatus("No input level · speak loudly or choose another mic", true);
        } else if (silentTicks > 24) {
          micStatus("Microphone active · awaiting speech");
        } else {
          micStatus("Mic published · checking input level");
        }
      }
    }, 300);
  }
  function stopMicMeter() {
    clearInterval(micMeterTimer);
    micMeterTimer = null;
    el("micLevel").value = 0;
    microphoneReady = false;
    micStatus("Stopped");
    el("micDevice").disabled = true;
    el("retryMic").hidden = true;
    el("enableAudio").hidden = true;
    el("speakerStatus").textContent = "Stopped";
  }
  async function refreshMicrophones() {
    if (!room || !sdk.Room || typeof sdk.Room.getLocalDevices !== "function") return;
    try {
      // After a mic permission grant, enumerate without a second capture prompt.
      const devices = await sdk.Room.getLocalDevices("audioinput", false);
      const list = el("micDevice");
      const selected = list.value;
      list.replaceChildren();
      const defaultOption = document.createElement("option");
      defaultOption.value = "";
      defaultOption.textContent = "System default";
      list.appendChild(defaultOption);
      for (const device of devices) {
        if (!device.deviceId) continue;
        const option = document.createElement("option");
        option.value = device.deviceId;
        option.textContent = device.label || "Microphone " + (list.options.length);
        list.appendChild(option);
      }
      if ([...list.options].some(item => item.value === selected)) list.value = selected;
      list.disabled = false;
    } catch (err) {
      activity("Microphone list unavailable: " + (err.name || "device error"));
    }
  }
  async function enableMicrophone() {
    if (!room) return false;
    try {
      micStatus("Requesting microphone permission...");
      el("retryMic").hidden = true;
      const publication = await room.localParticipant.setMicrophoneEnabled(true);
      if (!publication || !publication.audioTrack ||
          room.localParticipant.isMicrophoneEnabled === false) {
        throw new Error("No microphone track was published to LiveKit.");
      }
      microphoneReady = true;
      muted = false;
      el("mic").textContent = "Mute mic";
      micStatus("Mic published · checking input level");
      startMicMeter();
      activity("LiveKit published a microphone track.");
      await refreshMicrophones();
      return true;
    } catch (err) {
      microphoneReady = false;
      micStatus("MIC FAILED: " + (err.name || err.message), true);
      el("retryMic").hidden = false;
      report(
        "Microphone not published. Allow microphone for 127.0.0.1 in Chrome/Edge, " +
        "check Windows Settings > Privacy & security > Microphone, then click Retry microphone. " +
        "Error: " + (err.name || err.message), "error");
      activity("Microphone capture failed: " + (err.name || err.message));
      return false;
    }
  }
  async function unlockAudio() {
    if (!room) return;
    // Important: call startAudio synchronously INSIDE this actual click handler.
    const activation = room.startAudio();
    try {
      await activation;
      for (const audio of knownAudios) await audio.play();
      speakerBlocked = false;
      el("enableAudio").hidden = true;
      el("speakerStatus").textContent = "Enabled";
      activity("Speaker audio unlocked through user interaction.");
      report("Speaker audio enabled. Speak to Jarvis and watch the mic input level.");
    } catch (err) {
      speakerBlocked = true;
      playbackState();
      activity("Audio unlock failed: " + (err.name || err.message));
    }
  }

  function report(text, cls = "") {
    el("notice").textContent = text;
    if (cls === "error") el("notice").style.color = "#ff9aa6";
    else el("notice").style.color = "";
  }
  function activity(message) {
    const row = document.createElement("div");
    row.textContent = new Date().toLocaleTimeString() + " · " + String(message).slice(0, 1500);
    el("feed").prepend(row);
    while (el("feed").childElementCount > 40) el("feed").lastChild.remove();
  }
  function status(state) {
    el("state").textContent = state;
    el("connection").textContent = state;
    document.body.classList.toggle("connected",
      ["CONNECTED", "AGENT JOINED", "LISTENING", "SPEAKING"].includes(state));
  }
  function buttons(active, waiting = false) {
    el("connect").disabled = active || waiting;
    el("disconnect").disabled = !active && !waiting;
    el("mic").disabled = !active;
  }
  async function api(path, data = {}) {
    if (!nonce || nonce.length < 32) throw new Error("Session link expired. Open Talk Live again in Jarvis.");
    const result = await fetch(path, {
      method: "POST",
      headers: {"Authorization": "Bearer " + nonce, "Content-Type": "application/json"},
      cache: "no-store", body: JSON.stringify(data),
    });
    let body;
    try { body = await result.json(); } catch (_err) { throw new Error("Local bridge unavailable."); }
    if (!result.ok) throw new Error(body.error || "Local bridge denied the request.");
    return body;
  }
  function publishState(state) {
    status(state);
    api("/api/state", {state}).catch(() => {});
  }

  function isAgentCaller(identity) {
    if (!room || !identity) return false;
    const remote = room.remoteParticipants.get(identity);
    if (!remote) return false;
    // The only invited non-local participant is the dispatched Cloud agent.
    // Do not trust payload claims that a request is an agent.
    const attrs = remote.attributes || {};
    const kind = String(remote.kind || "").toLowerCase();
    return !!attrs["lk.agent.state"] || kind.includes("agent") ||
           remote.kind === 4;
  }

  function registerDesktopTool() {
    room.registerRpcMethod("desktop_command", async (invocation) => {
      if (!isAgentCaller(invocation.callerIdentity)) {
        activity("Rejected desktop RPC from unrecognized participant.");
        return JSON.stringify({ok:false,result:"DENIED: Unrecognized caller."});
      }
      let data;
      try { data = JSON.parse(invocation.payload); }
      catch (_err) { return JSON.stringify({ok:false,result:"Invalid JSON command."}); }
      if (!data || typeof data !== "object" || Array.isArray(data)) {
        return JSON.stringify({ok:false,result:"Invalid tool payload."});
      }
      activity("Agent requested desktop action: " + String(data.action).slice(0,35) +
               ". Waiting for native Jarvis approval.");
      try {
        const reply = await api("/api/action", data);
        activity("Desktop action: " + reply.result);
        return JSON.stringify(reply);
      } catch (err) {
        activity("Desktop action denied: " + err.message);
        return JSON.stringify({ok:false,result:"DENIED: " + err.message});
      }
    });
  }

  function attachRoomHandlers() {
    const {RoomEvent, Track} = sdk;
    room.on(RoomEvent.ParticipantConnected, (participant) => {
      el("agent").textContent = "Participant joined";
      activity("Remote participant joined: " + (participant.identity || "agent"));
      publishState("AGENT JOINED");
    });
    room.on(RoomEvent.ParticipantDisconnected, (participant) => {
      el("agent").textContent = "Agent left";
      activity("Remote participant disconnected: " + (participant.identity || ""));
      publishState("AGENT LEFT");
    });
    room.on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
      if (track.kind === Track.Kind.Audio) {
        const audio = track.attach();
        audio.autoplay = true;
        audio.controls = false;
        el("audios").appendChild(audio);
        knownAudios.add(audio);
        audio.play().catch(() => {
          report("Browser audio playback blocked. Click Connect/Enable Audio or allow sound.", "error");
        });
        activity("Receiving agent audio.");
        el("agent").textContent = "Audio connected";
      }
    });
    room.on(RoomEvent.TrackUnsubscribed, (track) => {
      for (const audio of track.detach()) {
        audio.remove(); knownAudios.delete(audio);
      }
    });
    room.on(RoomEvent.Disconnected, () => {
      status("DISCONNECTED");
      buttons(false);
      el("agent").textContent = "Not joined";
      activity("LiveKit room disconnected.");
    });
    room.on(RoomEvent.ConnectionQualityChanged, () => {});
    if (RoomEvent.TranscriptionReceived) {
      room.on(RoomEvent.TranscriptionReceived, (segments, participant) => {
        for (const segment of (segments || []).slice(0,5)) {
          if ((segment.final || segment.isFinal) && segment.text) {
            activity((participant ? "Jarvis" : "Voice") + ": " + segment.text.slice(0,600));
          }
        }
      });
    }
    if (RoomEvent.ParticipantAttributesChanged) room.on(
      RoomEvent.ParticipantAttributesChanged, (attributes, participant) => {
      const current = (attributes || {})["lk.agent.state"];
      if (current) {
        const view = String(current).toUpperCase();
        el("agent").textContent = view;
        if (["LISTENING","SPEAKING"].includes(view)) publishState(view);
      }
    });
  }

  async function connect({approved = false} = {}) {
    if (busy || room) return;
    if (!sdk || !sdk.Room) {
      report("LiveKit browser SDK could not load. Check internet/CDN access.", "error");
      return;
    }
    if (!approved && !window.confirm(
      "Start a LiveKit Cloud voice conversation? It uses your project credits. " +
      "Desktop actions still require separate native Jarvis approval. Session max 10 minutes.")) return;
    busy = true;
    buttons(false, true);
    report("Generating a short-lived room token locally; no API secret sent to browser...");
    status("CONNECTING");
    try {
      const ticket = await api("/api/connect");
      latestRoom = ticket.room;
      room = new sdk.Room({adaptiveStream:true,dynacast:false});
      attachRoomHandlers();
      registerDesktopTool();
      await room.connect(ticket.url, ticket.token, {autoSubscribe:true});
      await room.localParticipant.setMicrophoneEnabled(true);
      try { await room.startAudio(); } catch (_err) {
        report("Connected. If sound is muted, click browser audio permission.", "error");
      }
      publishState(room.remoteParticipants.size ? "AGENT JOINED" : "CONNECTED");
      el("agent").textContent = room.remoteParticipants.size
        ? "Participant connected" : "Waiting for training-2057";
      deadline = Date.now() + ticket.maxSeconds * 1000;
      clearInterval(countdown);
      countdown = setInterval(() => {
        const left = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
        el("remaining").textContent = "Auto end: " +
          Math.floor(left/60) + ":" + String(left%60).padStart(2,"0");
        if (left <= 0) disconnect();
      }, 1000);
      clearInterval(poller);
      poller = setInterval(async () => {
        try {
          const state = await api("/api/status");
          if (state.stopRequested || !state.active) await disconnect({serverStopped:true});
        } catch (_err) { /* On server loss, end local WebRTC as a safety fallback. */
          await disconnect({serverStopped:true});
        }
      }, 1300);
      buttons(true);
      report("LiveKit room connected. Speak normally; wait for the agent to join.");
      activity("Joined private session · " + ticket.agent);
    } catch (error) {
      activity("Connection failed: " + error.message);
      report("Could not connect: " + error.message, "error");
      if (room) {
        try { await room.disconnect(); } catch (_e) {}
        room = null;
      }
      try { await api("/api/disconnect"); } catch (_e) {}
      status("FAILED");
      buttons(false);
    } finally { busy = false; }
  }

  async function disconnect({serverStopped = false} = {}) {
    clearInterval(countdown); clearInterval(poller);
    countdown = null; poller = null;
    if (room) {
      const previous = room; room = null;
      try { await previous.disconnect(); } catch (_err) {}
    }
    for (const audio of knownAudios) audio.remove();
    knownAudios.clear();
    deadline = 0; latestRoom = null;
    el("remaining").textContent = "Session ended";
    el("agent").textContent = "Not joined";
    buttons(false); status("DISCONNECTED");
    if (!serverStopped) {
      try {
        const reply = await api("/api/disconnect");
        if (!reply.ok) report("Cloud end not confirmed: " + reply.message, "error");
        else report("LiveKit voice room ended.");
      } catch (err) { report("Cannot confirm Cloud room ended: " + err.message, "error"); }
    } else {
      report("Jarvis STOP or timeout requested; verify the call ended.");
    }
    activity("Disconnect requested.");
  }

  el("connect").addEventListener("click", () => connect());
  el("disconnect").addEventListener("click", () => disconnect());
  el("mic").addEventListener("click", async () => {
    if (!room) return;
    muted = !muted;
    try {
      await room.localParticipant.setMicrophoneEnabled(!muted);
      el("mic").textContent = muted ? "Unmute mic" : "Mute mic";
    } catch (err) {
      muted = !muted; report("Microphone change failed: " + err.message, "error");
    }
  });
  window.addEventListener("pagehide", () => {
    if (room) {
      try { room.disconnect(); } catch (_e) {}
      // Use POST with auth and keepalive; server timer is the backstop.
      fetch("/api/disconnect", {
        method:"POST",keepalive:true,
        headers: {"Authorization":"Bearer "+nonce,"Content-Type":"application/json"},
        body:"{}",
      }).catch(() => {});
    }
  });
  if (!nonce || nonce.length < 32) {
    report("Open this window through Jarvis → Talk Live. Local access token missing.", "error");
    buttons(false, true);
  } else if (auto) {
    // The native Jarvis confirmation has already approved this ONE call.
    connect({approved:true});
  }
})();