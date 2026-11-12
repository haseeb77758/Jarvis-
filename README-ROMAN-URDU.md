# JARVIS — Haseeb AI Windows 11 Desktop Helper
Created by Haseeb Crafts

## Pehle seedhi baat
Yeh Windows par chalne wala local desktop helper ka source package hai, source download mein prebuilt ya signed EXE nahi. Yeh is chat se tumhare computer par install nahi hua. Linux environment mein code, action validation, cancellation aur UI event logic test ki hai. Is runtime mein display nahi tha, is liye window visually render nahi hui; actual Windows app launching, DPI, screen input aur tumhare laptop ki AI speed yahan verify nahi hui.

Yeh tumhare poore PC ka unrestricted autonomous agent nahi. Is version mein approved Windows apps launch, selected workspace mein filename search, folder/text-note creation, primary-monitor screenshot preview aur reviewed mouse/keyboard actions hain. Screen ko AI se automatically samajh kar arbitrary websites par multi-step tasks complete karna included nahi. Model ko screenshots, file contents ya file listing automatically nahi bheje jate.

## 1 — Desktop controls start karo
1. ZIP download kar ke Extract All karo. Browser ya ZIP preview ke andar se run na karo.
2. SETUP.bat double-click karo. Python 3.10+ with Tkinter nahi mila to official Python download page khulegi. Python install mein Add python.exe to PATH enable karo, phir SETUP.bat dobara chalao. Windows 11 ka built-in Python app-store alias real Python installation nahi.
3. Setup local virtual environment banayega aur PyAutoGUI/Pillow PyPI se install karega. Internet chahiye. Admin ke taur par run karne ki zaroorat nahi.
4. Tests pass hon to desktop app khul jayegi. Baad mein sirf START.bat use karo.

Local controls ke liye AI model, API key ya cloud account nahi chahiye. SETUP-LOCAL-AI optional hai.

## 2 — Actual free local AI
SETUP-LOCAL-AI.bat chalao. Ollama installed nahi to official Windows download page khulegi. Ollama install karke file dobara chalao. Yeh qwen2.5:1.5b download karegi, model approximately 986 MB. Ollama installation khud bhi disk space leti hai; several GB free rakho.

Model downloaded hone ke baad Local AI chat mode mein baat karo. Is local mode mein API bill, subscription ya monthly cloud quota nahi; computer RAM/CPU, storage aur electricity use hoti hai. Pehla download internet se hota hai. Model ki quality ChatGPT jaisi assume na karo. 8 GB RAM aur integrated graphics par slow ho sakta hai; browser/Adobe apps band karne se memory mil sakti hai. AI speed yahan measure nahi hui.

AI action plan mode plain request ko limited JSON action plan mein badalta hai. Har action pehle display hota hai aur approval mangta hai. Plan invalid ho to execute nahi hota. Local model ghalat samajh sakta hai: exact app, folder naam aur action review karo. AI chat sirf baat karti hai; woh khud action execute nahi karti.

Cloud chat button tumhari pehle wali online app browser mein kholta hai:
https://haseeb-ai-4ybb30.v2.appdeploy.ai/
Cloud app apne free monthly allowance par hai aur us se local computer connect nahi hota.

## Direct commands
| Command | Result |
| --- | --- |
| chrome kholo / open chrome | Installed Chrome launch request |
| edge kholo | Edge launch request |
| notepad kholo | Notepad launch request |
| calculator kholo | Calculator launch request |
| paint kholo | Paint launch request |
| explorer kholo | File Explorer launch request |
| open https://example.com | Default browser mein HTTPS website |
| folder banao: Client Work | Selected workspace mein naya folder, review ke baad |
| find: invoice | Selected workspace ke andar filename search |
| note: Client meeting Monday | Selected workspace mein unique UTF-8 .txt note |
| screenshot | Local primary-screen preview; no automatic save/upload |
| type: Hello Haseeb | Reviewed single-line English/Roman Urdu input; no Enter appended |
| key: ctrl+s | Reviewed keyboard shortcut |
| click: 300,400 | Reviewed primary-screen coordinate click |

Workspace default tumhara user-home folder hai. Choose folder se Desktop, Documents, D:\ ya koi aur accessible folder select kar sakte ho. Permissions aur Windows UAC bypass nahi hotay. Search file contents nahi padhti. Max 50 matches, 12 seconds or 50,000 entries; large disk ka complete search guarantee nahi. AppData, node_modules, .git, .venv aur link/junction directories skip hoti hain.

## Screen input / STOP
- Mouse/keyboard controls checkbox default OFF hai. Enable karna hoga.
- Screen preview par click karke point select karo, phir Review click button use karo. Screenshot stale ho sakta hai: target window ko same jagah rakho.
- Har mouse/keyboard action ka review dialog aata hai. OK ke baad app minimize hoti hai aur 4-second countdown milta hai; target window select karo.
- PyAutoGUI input ke waqt mouse ko screen ke corner mein le jao to fail-safe abort hota hai. FAILSAFE off mat karo.
- App focused ho to Esc ya STOP button pending actions cancel karta hai. Global Ctrl+Alt+F12 stop bhi app running hone par available hai agar Windows hotkey register kar de. Status log registration failure batayega.
- Stop pehle se bheje gaye click/key ko undo nahi karta; running Ollama inference finish ho sakti hai lekin result discard hoga. Resume worker finish hone ke baad chalega.
- Click, Enter ya Tab apne aap context ko nahi samajhte. Message send, form submit, delete ya payment karne wala target ho to khud verify karo; automatic approval mat do. Built-in delete/send/payment action nahi hai.
- Keyboard typing only printable single-line ASCII: English/Roman Urdu. Urdu script keyboard pasting included nahi. Naye EXE mein Urdu/English microphone transcription aur Windows speech output included hain; DESKTOP-FIRST.md follow karein.
- Primary monitor controls only. Elevated/UAC/secure desktop windows supported nahi. Screen scaling / coordinates pehle Notepad mein test karo.

## Pehla Windows smoke test
1. START.bat kholo aur calculator kholo bhejo; Calculator nazar aaye to launch verified.
2. Choose folder se ek test folder select karo. folder banao: HC Test bhejo, review approve karo, Explorer mein folder check karo.
3. note: Hello Haseeb bhejo. Naya .txt note selected folder mein check karo. Existing file overwrite nahi hoti.
4. find: Haseeb bhejo aur listed path check karo.
5. screenshot bhejo; preview aani chahiye. Save screenshot optional hai.
6. Notepad kholo, Enable mouse / keyboard controls ON karo. type: Hello Haseeb bhejo, approve karke 4 seconds mein Notepad focus karo. Text aaye aur automatically submit na ho.
7. STOP dabao. Koi command bhejo: stopped message aana chahiye. Resume karke next command test karo.
8. Local AI setup ke baad Local AI chat mein Salam bhejo. Response ki quality/speed PC par judge karo.

## EXE banana (optional)
BUILD-EXE.bat Windows par PyInstaller install aur build karega. Output dist\Jarvis.exe. Yeh one-file EXE hai; _internal folder saath rakhna nahi hota. Yeh unsigned build hoga. Source download mein compiled EXE nahi. GitHub Actions → Windows test and build ke successful run mein Jarvis-Single-EXE-Windows-x64 artifact milega; us mein built EXE hoti hai.

## Privacy / limits
No background monitoring, no automatic startup, no inbound web server, no remote-control tunnel, no arbitrary PowerShell/CMD execution. Local AI calls only fixed loopback Ollama address with proxy disabled. Chat history app close/new chat par clear; automatic chat logs nahi. User-selected notes/screenshots locally save hotay hain. Cloud chat open karne par us app ki cloud data flow apply hoti hai.

Windows Defender/SmartScreen ya installer ki warning ko blindly bypass na karo. Official dependency downloads use karo. App ko Administrator mode mein run na karo.

## Verification in this delivery
See TEST-RESULTS.txt for actual checks. Automated tests mock OS launching and AI where needed. Passing tests do not mean the package was run on your Windows laptop.

## References checked 11 November 2026
https://docs.ollama.com/windows
https://docs.ollama.com/api/chat
https://ollama.com/library/qwen2.5:1.5b
https://pyautogui.readthedocs.io/en/latest/


## Latest additions: browser + single EXE
Repo ke README.md mein Option 2 aur Option 3 dekhein. Single-EXE app mein Setup local AI button included hai, is liye EXE ke saath setup BAT carry karna zaroori nahi. Ollama aur model phir bhi first-time download/install hote hain.

GitHub Pages ke liye repo plan/Pages settings configure honi chahiye; private repo ko public is update mein nahi kiya gaya. Private Codespaces preview bhi configured hai. Browser Puter sign-in use karta hai; desktop local chat Ollama use karti hai. Dono ki capabilities aur allowances alag hain.


## Desktop-first / voice / memory update
Latest instructions: **DESKTOP-FIRST.md**. Naye build mein voice model bundled hai; Setup voice source-run fallback ke liye hai. Urdu mic accuracy aur spoken output target PC par verify karein. Preferences/shortcuts explicit memory hain, executable self-upgrade nahi.


## ElevenLabs voice replies

Jarvis update karke **Voices** ya **••• → Voice / ElevenLabs** kholo. Provider
ElevenLabs select karo, apni API key aur voice ID paste karo, language `ur`/`en`
ya `auto` choose karo. Spoken text bhejne ka checkbox tick karke Save, phir
Test voice dabao. **Speak replies** on karne par main chat aur Sandbox ka jawab
selected voice mein bolega. API key chat mein paste nahi karni.

ElevenLabs ke credits aur internet chahiye. Remember key sirf current Windows
account ke liye encrypted save karta hai; off ho to session-only hai. STOP local
playback rokta hai, lekin bheji hui request ke credits wapas hone ki guarantee
nahi. Urdu script aur matching accent ki voice behtar rahegi. Windows provider
select karke offline speech use kar sakte ho. ELEVENLABS-VOICE.md dekho.
