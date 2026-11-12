"""Browser/WebRTC frontend flow with mocked LiveKit network, real loopback HTTP.

Does not start Cloud sessions, expose user keys, or require microphone audio.
"""
import json
import os
import queue
import threading
import unittest
from unittest.mock import patch

from playwright.sync_api import sync_playwright

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import direct_livekit as lk

MOCK_BROWSER_SDK = r"""
window.__rooms = [];
window.__denyMic = false;
window.__permitAudio = false;
window.LivekitClient = {
  Track: {Kind:{Audio:"audio"}, Source:{Microphone:"microphone"}},
  RoomEvent: {
    ParticipantConnected:"participantConnected",
    ParticipantDisconnected:"participantDisconnected",
    TrackSubscribed:"trackSubscribed",
    TrackUnsubscribed:"trackUnsubscribed",
    Disconnected:"disconnected",
    ConnectionQualityChanged:"connectionQualityChanged",
    TranscriptionReceived:"transcriptionReceived",
    ParticipantAttributesChanged:"attributesChanged",
    AudioPlaybackStatusChanged:"audioPlaybackChanged",
    MediaDevicesError:"mediaDevicesError",
    LocalTrackSubscribed:"localTrackSubscribed",
    LocalAudioSilenceDetected:"localAudioSilenceDetected",
    TrackSubscriptionFailed:"trackSubscriptionFailed",
  },
  Room: class MockRoom {
    static async getLocalDevices(kind, requestPermissions){
      return [{deviceId:"default-mic",label:"Real Windows Microphone"}];
    }
    constructor(){
      window.__rooms.push(this);
      this.events = {};
      this.remoteParticipants = new Map();
      this.canPlaybackAudio = false;
      this.localParticipant = {
        isMicrophoneEnabled: false,
        audioLevel: 0.24,
        setMicrophoneEnabled: async(value) => {
          if (window.__denyMic) {
            const err = new Error("Microphone permission denied");
            err.name = "NotAllowedError";
            throw err;
          }
          this.localParticipant.isMicrophoneEnabled = value;
          this.micOn = value;
          return {audioTrack:{mediaStreamTrack:{readyState:"live"}}};
        }
      };
    }
    on(name, handler){this.events[name] = handler;}
    registerRpcMethod(name, handler){ if(name === "desktop_command")window.__desktopRPC=handler; }
    async connect(url, token){ this.connected = true; window.__lastConnect = {url,token}; }
    async startAudio(){
      if (!window.__permitAudio) throw new Error("Autoplay blocked without direct click");
      this.canPlaybackAudio = true;
      if(this.events.audioPlaybackChanged)this.events.audioPlaybackChanged();
    }
    async switchActiveDevice(kind, deviceId){this.micDevice=kind+":"+deviceId;return true;}
    async disconnect(){this.connected=false;this.localParticipant.isMicrophoneEnabled=false;
      if(this.events.disconnected)this.events.disconnected();}
  }
};
"""

SETTINGS = {
    "LIVEKIT_URL": "wss://sample-project.livekit.cloud",
    "LIVEKIT_API_KEY": "example-key",
    "LIVEKIT_API_SECRET": "not-a-real-livekit-project-secret",
}


class DirectBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.jobs = queue.Queue()
        cls.service = lk.DirectVoiceService(cls.jobs)
        cls.url = cls.service.start()
        cls.patch_settings = patch("direct_livekit.get_project_settings", return_value=SETTINGS)
        cls.patch_delete = patch("direct_livekit.delete_room", return_value=True)
        cls.patch_settings.start()
        cls.patch_delete.start()
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(
            channel=os.environ.get("JARVIS_BROWSER_CHANNEL") or None)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.service.close()
        cls.patch_settings.stop()
        cls.patch_delete.stop()

    def setUp(self):
        self.page = self.browser.new_page()
        self.page.route(
            "https://cdn.jsdelivr.net/npm/livekit-client@2.23.0/dist/livekit-client.umd.min.js",
            lambda route: route.fulfill(content_type="application/javascript",
                                        body=MOCK_BROWSER_SDK))
        self.page.goto(self.url + "~auto")
        self.page.get_by_text("CONNECTED", exact=True).first.wait_for(timeout=10000)

    def tearDown(self):
        self.page.close()
        self.service.disconnect()

    def test_one_click_browser_connect_and_disconnect(self):
        self.assertTrue(self.page.evaluate("window.__rooms[0].connected"))
        self.assertEqual(self.page.evaluate("window.__lastConnect.url"),
                         SETTINGS["LIVEKIT_URL"])
        self.assertNotIn(SETTINGS["LIVEKIT_API_SECRET"],
                         self.page.content())
        self.assertTrue(self.service.status()["active"])
        self.page.locator("#disconnect").click()
        self.page.get_by_text("DISCONNECTED", exact=True).first.wait_for()
        self.assertFalse(self.service.status()["active"])

    def test_app_mode_autoplay_requires_click_and_explicit_unlock(self):
        # Opening Chrome --app from a native Python process is not a browser
        # click; LiveKit's startAudio fails until invoked by user interaction.
        unlock = self.page.locator("#enableAudio")
        unlock.wait_for(state="visible", timeout=10000)
        self.assertIn("BLOCKED", self.page.locator("#speakerStatus").inner_text())
        self.assertTrue(self.page.evaluate("window.__rooms[0].micOn"))
        self.page.evaluate("window.__permitAudio=true")
        unlock.click()
        unlock.wait_for(state="hidden", timeout=5000)
        self.assertIn("Enabled", self.page.locator("#speakerStatus").inner_text())
        self.assertTrue(self.page.evaluate("window.__rooms[0].canPlaybackAudio"))

    def test_microphone_is_published_and_input_level_is_visible(self):
        self.page.wait_for_function(
            "() => Number(document.querySelector('#micLevel').value) > 0",
            timeout=4000)
        self.assertIn("Input signal", self.page.locator("#micStatus").inner_text())
        self.assertTrue(self.page.evaluate("window.__rooms[0].micOn"))

    def test_microphone_input_selector_can_switch_devices(self):
        select = self.page.locator("#micDevice")
        select.wait_for(state="visible")
        self.page.wait_for_function(
            "() => !document.querySelector('#micDevice').disabled", timeout=3000)
        select.select_option("default-mic")
        self.assertEqual(
            self.page.evaluate("window.__rooms[0].micDevice"),
            "audioinput:default-mic")

    def test_microphone_permission_failure_is_visible_and_retryable(self):
        # New session: simulate rejected microphone permission.
        self.page.locator("#disconnect").click()
        self.page.get_by_text("DISCONNECTED", exact=True).first.wait_for()
        self.page.evaluate("window.__denyMic=true")
        self.page.once("dialog", lambda dialog: dialog.accept())
        self.page.locator("#connect").click()
        self.page.get_by_text("CONNECTED", exact=True).first.wait_for(timeout=6000)
        self.page.locator("#retryMic").wait_for(state="visible", timeout=5000)
        self.assertIn("MIC FAILED", self.page.locator("#micStatus").inner_text())
        self.page.evaluate("window.__denyMic=false")
        self.page.locator("#retryMic").click()
        self.page.locator("#retryMic").wait_for(state="hidden", timeout=5000)
        self.assertTrue(self.page.evaluate("window.__rooms[1].micOn"))

    def test_client_rpc_denies_unknown_remote_caller(self):
        response = self.page.evaluate("""async () => {
          return await window.__desktopRPC({
            callerIdentity: "evil", payload: JSON.stringify({
              action: "launch", app: "notepad"
            })
          });
        }""")
        self.assertFalse(json.loads(response)["ok"])
        self.assertTrue(self.jobs.empty())

    def test_agent_rpc_requires_native_approval_then_returns_result(self):
        self.page.evaluate("""() => {
          window.__rooms[0].remoteParticipants.set(
            "agent1", {kind:4,attributes:{"lk.agent.state":"listening"}});
        }""")
        def approve():
            task = self.jobs.get(timeout=8)
            self.assertEqual(task.action, {"action":"launch","app":"calculator"})
            task.result = "DONE: calculator opened after native approval"
            task.event.set()
        responder = threading.Thread(target=approve)
        responder.start()
        response = self.page.evaluate("""async () => {
          return await window.__desktopRPC({
            callerIdentity:"agent1",
            payload:JSON.stringify({action:"launch",app:"calculator"})
          });
        }""")
        responder.join(5)
        self.assertFalse(responder.is_alive())
        self.assertTrue(json.loads(response)["ok"])
        self.assertIn("native approval", json.loads(response)["result"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
