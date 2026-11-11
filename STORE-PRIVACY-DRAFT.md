# HASEEB AI Jarvis — privacy policy DRAFT

**DRAFT — NOT YET A PUBLISHED PRIVACY POLICY.**

This draft describes behavior observed in the current open codebase. The future publisher must audit the exact final build, confirm the policy, add effective date and genuine contact details, and publish it at a public HTTPS address before Store submission. Do not place placeholder text in a live Store listing.

- **Application:** HASEEB AI Jarvis (Windows desktop)
- **Publisher:** [LEGAL NAME OF INDIVIDUAL DEVELOPER — required]
- **Effective date:** [EFFECTIVE DATE — required]
- **Privacy contact:** [REAL CONTACT EMAIL — required]
- **Public policy URL:** [STABLE PUBLIC HTTPS URL — required]

## Overview

Jarvis is a locally running desktop assistant offering supported application controls, notes and reviewed voice interactions. By default it does not require a Jarvis cloud account. The application does not implement a first-party analytics/advertising tracker in the audited source. This statement does not cover third-party sites or the Windows operating system.

## Information handled on your PC

- **Local preferences and shortcuts:** Settings explicitly saved by you, including local preferences, reviewed action sequences and registered application paths, are stored in a `preferences.json` file under your Windows `LOCALAPPDATA\HaseebCrafts\Jarvis` directory.
- **Files and notes:** When you choose a workspace and request notes or file searches, Jarvis accesses content and filenames in that workspace to fulfil the command. Notes that you create are stored locally; the application does not automatically upload your documents.
- **Microphone:** Audio recording starts only when you click the microphone control. Each capture is approximately six seconds, with local Whisper transcription. The recognized text is shown for review before a requested computer command runs. The current code does not intentionally store the raw microphone audio as an application recording.
- **Screenshots and computer input:** A screenshot is captured after your command; it is displayed locally for review. Screen clicking and typing require explicit opt-in and approval. The application code does not automatically upload screenshots or stream your desktop.
- **Conversation:** Your current conversation is held in the running application's session. When optional local AI is enabled, selected recent messages and saved response preferences may be sent to the Ollama service listening on your PC (`127.0.0.1`). Model runtime behavior and separate model installation should be reviewed before use.
- **Local speech output:** When enabled, text may be spoken using the Windows text-to-speech engine.

## Internet features and third parties

Jarvis can open websites in your default browser. For Google, YouTube or WhatsApp search/draft links, search terms or draft text may be included in URLs sent to the external service when your browser opens them. These services have their own privacy practices and terms.

Optional software/model setup can contact Ollama, model hosts or package-index sites for downloads. An optional **Cloud chat** link opens a separately hosted website; that site's privacy and processing practices are not covered by the local-only description above. Jarvis does not silently turn that feature on.

We do not claim that third-party network providers, installers, model downloads, browsers or the operating system collect no information.

## Data retention and control

Local preferences and saved shortcuts remain on your PC until you remove them through Jarvis or delete the associated local data. You can remove a registered app, saved preference or shortcut using the Memory interface. Files created in the selected workspace remain until you manage them. Uninstalling the application may not delete these user-created files or all locally cached models; review the respective Windows and model directories.

## Security and permissions

Jarvis supports bounded actions, explicit review and a STOP control. It is not a security product and is not guaranteed to prevent all user mistakes. The application does not intentionally run as an administrator, disable Windows security, or provide an inbound remote computer-control server. On Windows, protected or elevated applications may not be controllable.

## Children, sale of data, changes

The audited code contains no feature for selling personal information or for targeting advertising. No children's account or age-verification mechanism is implemented; the publisher must decide on appropriate suitability/age claims before release. Privacy practices may change as the product evolves; the publisher must update this policy when relevant.

## Contact and corrections

To ask about this policy or data controls, contact the verified publisher at **[REAL CONTACT EMAIL]**. Add a valid contact before publication and review all claims against the *exact* release build.

---

**Publisher verification checklist**

- [ ] Real legal publisher identity and contact added
- [ ] Effective date added
- [ ] Public HTTPS policy location published and verified
- [ ] Final app/network dependencies audited
- [ ] Correct local paths and deletion instructions confirmed
- [ ] Microsoft Store privacy/data collection answers match this policy
- [ ] External optional cloud chat policies separately linked/disclosed if included
