# Windows installer trust and malware-warning investigation

**Current state:** The previous 0.2.0 Windows NSIS pilot was **unsigned**. The exact alert observed on the developer's computer has not been supplied. An instruction to "remove" a file can arise from Microsoft Defender Antivirus, Smart App Control, another endpoint product, or a reputation warning; these require different investigation.

## Identify the actual warning before further distribution

1. Open **Windows Security → Virus & threat protection → Protection history** and record: detection name (for example Trojan, PUA, or Suspicious), affected file name/path, event time, and remediation status. Do not disable Defender or add broad exclusions.
2. For "Windows protected your PC" specifically, note that SmartScreen can block a new unsigned app based on file and publisher reputation; this is not a malware diagnosis.
3. In PowerShell, on a copied release artifact, run:
   `Get-FileHash -Algorithm SHA256 ".\Windows AI Trading Agent_0.3.0_x64-setup.exe"`
   `Get-AuthenticodeSignature ".\Windows AI Trading Agent_0.3.0_x64-setup.exe" | Format-List Status,SignerCertificate`
   Compare the hash with the successful build log. A missing signature must be reported as **NotSigned**, not a valid publisher.
4. If Defender detected a threat, stop distributing the affected artifact, identify the suspected file/dependency, inspect the detection, rebuild from trusted dependencies, scan on an isolated Windows machine, and only then consider submitting a **public release artifact** to Microsoft's official malware submission process if the classification appears wrong. Do not upload private credentials or user files.
5. This project freezes Python + MetaTrader5 with PyInstaller and wraps it in Tauri/NSIS. Packaging alone does not establish maliciousness, but bundled binaries and subprocess startup deserve scrutiny.

## CI checks now implemented

The Windows installer workflow checks `Get-AuthenticodeSignature` on the built setup executable, calculates its SHA-256 digest and uses Defender custom scanning if the runner reports antivirus enabled. If a detector reports a match against the installer, it fails before upload. If Defender is unavailable, the workflow prints a **not verified** warning. This cannot replace scanning on end-user hardware. The new 0.3.0 pilot is still expected to be unsigned unless the separate approved signing workflow is run.

## Official publisher signing workflow

The separate manual `.github/workflows/sign-installer.yml` is **NOT** a signing certificate. It becomes operational only after the publisher completes Microsoft Azure Artifact Signing identity validation and configures:

- GitHub environment `production-signing` with human approval.
- Azure federated workload identity and GitHub secrets: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`.
- GitHub variables: `ARTIFACT_SIGNING_ENDPOINT`, `ARTIFACT_SIGNING_ACCOUNT`, `ARTIFACT_SIGNING_PROFILE`, `ARTIFACT_SIGNING_PUBLISHER` (expected certificate subject).
- Azure **Artifact Signing Certificate Profile Signer** role for the federated identity.

The manual workflow downloads a successfully built unsigned installer, signs it using `azure/artifact-signing-action@v2`, checks **Valid** Authenticode status and expected signer identity, timestamps it, hashes it and uploads a separate signed artifact. Nothing is falsely labelled signed when configuration is absent. Signing credentials are never checked into Git.

**Eligibility:** Microsoft's public-trust Artifact Signing has identity and geographic eligibility restrictions. If the legal publisher is in a noneligible region or identity class, obtain an organization-validated Windows code-signing certificate through a reputable CA instead and implement the corresponding hardware/cloud-key signing workflow before release. This repository does **not** currently include that alternative. Avoid self-signed or exportable private-key shortcuts for public distribution.

A legitimate Authenticode signature improves publisher identity, but **does not guarantee no SmartScreen warnings** on new binaries. Smart App Control and antivirus classifications are distinct. Free-signing and Microsoft Store distribution have separate requirements.

References:
- https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation
- https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options
- https://learn.microsoft.com/en-us/azure/artifact-signing/quickstart
- https://github.com/Azure/artifact-signing-action

## Release policy

Do not publicly announce an installer as "Defender safe" without trustworthy scan evidence. An unsigned build is a development artifact only. Do not instruct users to suppress warnings without first verifying their exact cause. Always publish the exact build SHA, signature status, file size and hash. Store no provider credentials or account data in logs.
