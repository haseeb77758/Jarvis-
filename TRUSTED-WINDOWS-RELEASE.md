# Jarvis Windows 11: Trusted signed release

## What the existing problem actually is

Windows 11 Smart App Control has blocked both the unsigned `Jarvis.exe` and an Internet-downloaded `.cmd` installer on the target laptop. Running the EXE build through GitHub Actions successfully does **not** establish publisher trust. Rebuilding the same unsigned EXE or using a different filename cannot fix that. Do not disable or bypass Smart App Control.

## Required publisher action — one time

A responsible publisher must acquire and configure a valid **publicly trusted code-signing certificate** suitable for Windows Smart App Control. A self-signed certificate is not an acceptable public distribution fix. Valid publisher verification and purchase may involve a certificate authority or Microsoft's Azure Artifact Signing service, depending on eligibility. No code, pipeline or AI assistant can substitute for publisher identity checks.

This repository currently supports a publisher-owned PFX signing certificate through GitHub encrypted repository secrets. Configure **Settings → Secrets and variables → Actions**:

- `JARVIS_SIGN_PFX_BASE64`: Base64 encoding of the PFX certificate *including its private key*, entered directly as an encrypted secret in GitHub; never placed in chat or committed to a file
- `JARVIS_SIGN_PFX_PASSWORD`: The corresponding private-key password, also as an encrypted GitHub Actions secret

The private key and password must remain protected; only the publisher should provision them. On a locally secured Windows PowerShell machine, an authorized publisher can encode an existing PFX with `[Convert]::ToBase64String([IO.File]::ReadAllBytes('C:\secure\publisher.pfx'))` and paste it **only into GitHub's secret-setting UI**. Do not share the value with ChatGPT or collaborators.

## Release process

1. After adding the two secrets, open **Actions → Trusted signed Jarvis Windows release → Run workflow** on main.
2. Workflow installs dependencies and runs the existing Windows unit/UI/voice smoke tests.
3. PyInstaller builds an **onedir** bundle, allowing all bundled EXE, DLL and PYD files to be inspected and signed.
4. Script verifies the signing certificate has a private key, proper Code Signing extended key usage and valid dates; signs every Windows binary with a trusted timestamp, then runs Windows Authenticode verification. Any failure aborts without uploading a release.
5. Only after every check passes, download `Jarvis-TRUSTED-SIGNED-Windows-x64`. Unzip and run the Jarvis executable in its bundle directory.
6. On the actual Windows 11 laptop, additionally test Smart App Control trust, microphone, application launch, screen approval, STOP and local AI setup before calling it production-ready.

**Important:** Code signing establishes publisher authenticity and makes an app eligible for trust assessment; it is not a malware clearance or a guarantee that Smart App Control will accept a particular release. Publisher identity, certificate trust chain and Windows reputation policies can still matter. The same signing identity should be maintained across releases.

## What is NOT finished

Until the publisher provides valid credentials and the signed workflow passes, **the Smart App Control block on the user's laptop remains unresolved**. The ordinary `Windows test and build` workflow now labels artifacts `UNSIGNED-Development` so they cannot be mistaken for a working signed installer. The separate source ZIP remains available for developers but may also be blocked by Smart App Control. Do not tell end users to turn security features off.

## Official references

- https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/code-signing-for-smart-app-control
- https://support.microsoft.com/en-us/windows/smart-app-control-frequently-asked-questions-285ea03d-fa88-4c5c-882e-6718e9ae06e3
