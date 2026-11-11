# HASEEB AI — Personal Windows 11 testing (individual developer)

## Current goal

Test Jarvis privately on your own Windows 11 PC first. Haseeb Crafts is a brand/project name, **not a registered company**. Do not claim to be a registered organization in Microsoft Partner Center. Choose an **Individual** developer account and complete Microsoft's actual identity checks under your legal identity. The app's public-facing display title can remain "HASEEB AI Jarvis", subject to Store naming rules.

This is a **publisher-guided release process**, not a bypass for Windows Smart App Control. Microsoft's approval and distribution signing are required before this route can resolve the blocked unsigned EXE.

## No-code steps that require the owner

1. Visit https://storedeveloper.microsoft.com/ and sign in with the Microsoft account you control.
2. Register as an **Individual**. Confirm any fees/eligibility shown for your country directly in Microsoft Partner Center before submitting.
3. Complete identity verification. Do not upload ID or passwords to the Jarvis GitHub repository or ChatGPT.
4. Reserve the name **HASEEB AI Jarvis** if available, then open the new app's identity page.
5. Copy only the **Package identity** and the **Publisher (CN=...)** values. These are public application metadata, not passwords or certificates.
6. In GitHub open **Actions → Microsoft Store MSIX submission candidate → Run workflow**. Supply the *exact* two values from Partner Center and an appropriate four-part version. The workflow builds and tests the existing app, then packages an **unsigned Store-submission-only MSIX**.
7. Download the workflow artifact and submit the MSIX to the corresponding app in Partner Center, with the required store listing, privacy policy/permissions and age/content declarations.
8. Select the most restricted audience/visibility controls supported by your Partner Center account and app category (for example a private audience if offered). Do not assume a draft or unapproved submission is installable. Store flight/private audience features and eligibility can vary; check the controls that Partner Center actually shows.
9. After certification and Microsoft's signing/distribution, install from the official Microsoft Store listing while signed into an allowed account. Test microphone, local model, window automation, STOP button and Smart App Control on **your actual laptop**.

**Never sideload** the unsigned GitHub MSIX. Do not turn off Smart App Control or Microsoft Defender. The GitHub CI passing does not mean Store certification or laptop compatibility has passed.

## Personal test acceptance checklist

- [ ] Published package shows a verified publisher in Windows/Store
- [ ] Installation completes without security bypass
- [ ] Desktop UI opens with sidebar, status, and chat
- [ ] Local AI model setup is disclosed and user-initiated
- [ ] Microphone records only after opt-in and transcription review
- [ ] Notepad, Calculator, window focus and browser shortcuts function as supported
- [ ] Screen input requires approval; emergency STOP stops a pending action
- [ ] No message is sent and no file is deleted automatically
- [ ] All failures appear in visible logs; no false claims of complete autonomous PC control

## Future commercial version

Keep the **HASEEB AI Jarvis** product identity, code and tests in this repository. A later commercial business account may require registered company verification. Do not presume an individual account can be converted directly to an organization account. Microsoft may offer an app transfer procedure subject to eligibility and both accounts' approval; check the current rules *before* publishing a commercial edition. Store policies can also change.

For now: personal test, no payment features, no customer accounts, no remote desktop takeover.

## Related files

- [Store packaging workflow](.github/workflows/store-msix.yml)
- [Store submission instructions](MICROSOFT-STORE-SETUP.md)
- [Windows signed release](TRUSTED-WINDOWS-RELEASE.md)
