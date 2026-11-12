# HASEEB AI — Microsoft Store submission path

## Why this exists

On the target Windows 11 laptop, Smart App Control blocked both the unsigned Jarvis EXE and the downloaded CMD installer. The source-bundle and unsigned EXE are **not** a verified installation solution for that machine.

A Microsoft Store distribution may solve the trust/distribution problem after Microsoft approves the app and signs its submitted MSIX package. This repository can build a **Store submission candidate** but does not create an approved Store listing, acquire a Partner Center account or sign on Microsoft's behalf.

## What has been automated

- Windows regression tests, desktop UI smoke test and synthetic voice smoke test
- PyInstaller onedir build to keep all application DLL/PYD dependencies visible
- A Store-compatible MSIX layout with Windows desktop/full-trust and microphone declarations
- Asset generation, package manifest XML validation, MSIX packaging and an unpack/integrity check
- Upload of a distinctly named **UNSIGNED Store SUBMISSION ONLY** artifact, never advertised as an installer

## Publisher steps that cannot be done without you

1. Sign in to Microsoft Partner Center and complete the developer account/identity verification and applicable fees or eligibility.
2. Reserve an app name and obtain the exact **Package identity**, **Publisher** and versioning requirements from Partner Center. Do not invent these values: they must match the Store listing.
3. In GitHub, run **Actions → Microsoft Store MSIX submission candidate → Run workflow**, supplying the exact identity/publisher and a four-part version such as 1.0.0.0.
4. After workflow success, download `Jarvis-UNSIGNED-Microsoft-Store-SUBMISSION-ONLY`, extract its ZIP and upload the contained MSIX to the corresponding Partner Center listing.
5. Complete Store listing assets, privacy declaration, age classification, capabilities disclosure and certification. Only after Microsoft approves and signs the app should it be installed via the Store.
6. On your actual PC verify microphone, installed-app control, account AI, STOP, and Smart App Control behavior. A packaged desktop app may have limitations compared with an unpackaged Python application.

**Do not double-click or sideload** the unsigned MSIX artifact. It is a submission candidate for Partner Center, not a locally trusted installer. A Store approval is not guaranteed. The publisher owns the Store account and listing.

## Alternative publisher route

The other release workflow, **Trusted signed Jarvis Windows release**, needs a valid publicly trusted publisher code-signing certificate. Certificates, certificate passwords and private keys must never be shared in chat or committed to this repository. See [TRUSTED-WINDOWS-RELEASE.md](TRUSTED-WINDOWS-RELEASE.md).

## Current state

The GitHub automation can prepare candidates, but neither workflow has obtained a publicly trusted certificate nor completed Store certification. Therefore the Windows Smart App Control block remains **unresolved** until one publisher-trust route is completed.

Official guidance:
- https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/overview
- https://learn.microsoft.com/en-us/windows/msix/desktop/desktop-to-uwp-manual-conversion
- https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/code-signing-for-smart-app-control

