# Pilot status — evidence recorded 2026-10-10

This is a development pilot, **not** a verified Windows MT5 release. Real trade submission remains disabled.

## Executed in Linux development runtime (Python 3.13.5)

- **PASS:** `python -m pytest -q`: **45 passed, 2 skipped** in approximately 1.4 seconds, against the available local source snapshot with the MT5 quote and HTTP regression changes. The two opt-in tests require a real MT5 terminal and live AI credentials. The local snapshot is not a full authenticated checkout, so GitHub CI must independently verify the complete remote tree.
- **PASS:** `python -m compileall -q app`.
- **PASS:** Uvicorn started a real HTTP service on `127.0.0.1:18765`. Actual HTTP requests returned `GET /health = 200`, unauthenticated `GET /terminal = 401`, authenticated `GET /terminal = 503` with the clear missing-MT5 diagnostic, and authenticated `POST /chat = 503` with the clear missing-API-key diagnostic.
- **PASS (MOCKED ONLY):** HTTP chat route -> mocked OpenAI tool call -> restricted MT5 quote tool -> fake terminal quote -> mocked provider response. The test quote source is explicitly `MOCKED_NOT_REAL`; this is **not** a live price, provider API, UI-browser test, or broker connection.
- **PASS (MOCKED ONLY):** rejected and replayed trade proposals, exact binding/expiry, disabled execution, tool permissions, agent loop, mocked MT5 disconnect and quote rejection.
- **BLOCKED:** offline `npm ci` cannot retrieve `@tauri-apps/cli`; no dependency installation or React production build was completed locally.
- **BLOCKED:** offline `pip install -e '.[dev]' --no-index` cannot obtain build dependencies; tests used already installed portable Python packages (OpenAI/Anthropic/Gemini SDKs and MetaTrader5 are absent).
- **NOT TESTED:** GitHub Actions completion/results; workflow source includes Linux backend, Windows portable tests and one frontend build job.

## Code presently implemented (not evidence of live acceptance)

- FastAPI development backend with local token on protected routes.
- OpenAI, Anthropic, Gemini adapter source with official SDK invocation and read-only registered tools.
- MT5 Python wrapper for terminal/account status, symbol specs, fresh quotes, rates, positions and orders. A hidden symbol may be selected in Market Watch; no account trading is performed.
- React typed chat, recorded microphone transcription, browser speech playback and proposal preview.
- Restricted, opt-in chart-only MQL5 companion and file IPC, **not compiled or tested here**.
- Proposal acknowledgements return `approved_not_executed`; broker order sending is not implemented.

## Mandatory real Windows acceptance — BLOCKED

Requires Windows 10/11, 64-bit Python 3.12, Node.js 22, installed and logged-in MetaTrader 5 terminal, selected account ID, valid provider credentials and microphone/speaker hardware.

1. Follow [SETUP.md](SETUP.md) and install dependencies from a networked Windows machine.
2. Run `cd backend; python -m pytest -q` and `cd desktop; npm run build`. Check GitHub Actions independently.
3. Launch backend + frontend; check terminal status. Retrieve a real fresh bid/ask. Run `RUN_LIVE_MT5=1 python -m pytest -q -m live` in the backend on Windows. Market may be closed; stale quotes must fail rather than appear live.
4. Only with an API key and MT5, run the opt-in tool workflow `RUN_LIVE_AI=1 python -m pytest -q -m provider_live`.
5. Compile the MQL5 EA with MetaEditor and visually verify EURUSD H1 and SMA20 after confirmed IPC response. Do not treat a queued command as success.
6. Test microphone, transcription, screen-reader focus, repeat speech and speaker output on actual hardware.
7. Do not place any live or demo orders during this milestone.

## Security

The HTTP backend is loopback-only; development credentials are process environment variables, not yet an OS credential store. Never expose its port, commit tokens, or interpret fabricated test data as actual MT5 results. Approval is only a proposal acknowledgement; trade execution is disabled. Frontend cancellation cannot guarantee a synchronous provider request is terminated on the server. Tauri bundling/sidecar integration is not finished.

## Continuation 4 — Windows installer candidate (2026-10-10)

**No installable .exe has been verified or linked yet.** The GitHub `windows-installer.yml` build definition has been committed, but the connected GitHub status interface did not return a completed push-build or downloadable installer artifact. Rust, the Windows MetaTrader5 wheel and frontend dependencies are unavailable to the Linux container, so local NSIS compilation and Windows installation are **BLOCKED**.

**PASS (executed portable Python only):** `PYTHONPATH=. pytest -q` in the available project snapshot returned **54 passed, 2 skipped**, including mocked provider credential lifecycle, mocked full HTTP chat/MT5 tool calls, terminal discovery against fake paths, and one **real local Python subprocess HTTP startup/shutdown** test. Python source and Tauri JSON/Cargo manifest parsing were also checked. The two skipped cases require real MT5 and AI provider credentials.

**NOT TESTED:** Tauri Rust compilation, PyInstaller Windows sidecar, React production build, NSIS output, installer preflight/progress, installation/upgrade/uninstall, live OpenAI/Anthropic/Gemini, actual MT5, real charts, voice hardware, application credential storage on Windows. The prior Linux frontend attempt failed because npm dependencies were unavailable; this is **BLOCKED**, not a passing build.

**Implemented source (unverified on Windows):** Tauri Rust bridge launches a frozen Python sidecar and keeps a random local HTTP token in Rust; only permitted endpoints can be invoked by React. Python Windows Credential Manager interface stores provider keys; connection tests call official SDK model listing. First-run UI offers API key save/test/remove and optional terminal discovery, and labels ChatGPT/Claude account authorization unimplemented. CI attempts the PyInstaller/Tauri NSIS build and uploads only a successful .exe. This is not evidence the resulting binary works.

**Remaining work:** Inspect GitHub Actions output; fix any Windows compile/freezing defects; run unsigned setup in an isolated Windows 10/11 test environment; verify WebView2, sidecar auto-start, provider key persistence and real provider call; perform genuine terminal discovery and fresh EURUSD quote; test WebView2 microphone and speaker; implement the custom install-plan/progress wizard. Trading remains disabled. See [INSTALLER.md](INSTALLER.md) and [PROVIDER_AUTH.md](PROVIDER_AUTH.md).

## Continuation 5 — verified installer and Windows installation (2026-10-10)

The first unsigned Windows installer **exists and is available**. This supersedes earlier statements in this document that no installer had been produced.

- **PASS:** GitHub Windows NSIS build run [38072956116](https://github.com/ekpeekpe/windows-ai-trading-agent/actions/runs/38072956116), source commit `cf6f6232cc71dba2e88356b55c516aa6ec2a9b3b`. All build steps succeeded: 61 Windows Python tests passed (2 skipped), frozen PyInstaller Python/MT5 sidecar started and returned authenticated `/providers` results, React/TypeScript built, Rust/Tauri compiled, NSIS installer created and uploaded.
- **PASS:** Installer artifact ID `11677851528`, [GitHub download](https://github.com/ekpeekpe/windows-ai-trading-agent/actions/runs/38072956116/artifacts/11677851528). The artifact ZIP is 50,735,070 bytes and SHA-256 `48599fa6ebf83e01c6af1b65e1542c8722f333210b6c1d80acff0c312bc1794f`. It contains `Windows AI Trading Agent_0.2.0_x64-setup.exe`, 50,738,713 bytes, SHA-256 `733afb86584e09fcce5cf4f8b455951e6ac1d70b76764c8ae2a9993fa8e5fac1`.
- **PASS:** Independent Windows installer acceptance run [38073839304](https://github.com/ekpeekpe/windows-ai-trading-agent/actions/runs/38073839304) downloaded the artifact, installed it silently in the current-user context, located and launched the desktop EXE, and confirmed that its own bundled Python backend answered a read-only health endpoint. The test did not require a user to install Python or Node separately.
- **PARTIAL / NOT TESTED:** Automated installation passed on a hosted Windows runner; a separate clean-machine, interactive install and UI accessibility test have not been performed. API keys, real AI model calls, authenticated MT5 account/quote retrieval, voice hardware, NSIS upgrades, manual uninstall, and optional MT5 installer remain untested. A custom preflight/progress wizard is not yet implemented. The file is unsigned; SmartScreen may warn.
- **SHUTDOWN FOLLOW-UP:** The initial acceptance runner cleaned up an orphaned `agent-backend` worker after closing the UI, so a Rust Windows process-tree cleanup fix is committed as `0028d69a479f036adde7935c6907ca9f3db8713d`, with automated lifecycle assertion added in `649b026c96283370bef965bbda8550481f4fc8fb`. **Do not describe this shutdown fix as verified until its replacement Windows build and acceptance report finish.** The successful installer artifact above predates the shutdown fix.
- **Trading:** Broker order submission remains disabled; tests and installer workflows do not submit trades.

Latest build reports are written to `latest.json` and `acceptance-latest.json` on branch `installer-build-reports`. They are evidence of actual CI runs, not substitutes for the GitHub Actions logs.

## Continuation 6 — v0.3.0 premium UI, CI and install acceptance (2026-10-10)

**PASS — source baseline:** The existing private `main` repository was inspected at `53c219d040e9272426d277d0c41df7d01b7ecea6`. The new v0.3 application source was compiled from `d5bd91bb8297f1490e7fcae1272275526b8ad128`.

**PASS — portable GitHub tests:** [run 38077393695](https://github.com/ekpeekpe/windows-ai-trading-agent/actions/runs/38077393695) passed. Backend: **61 passed, 2 skipped** on Linux Python 3.11, Linux Python 3.12 and Windows Python 3.12. React production build passed. Browser-based Playwright UI: **5 passed** using explicitly mocked backend routes. Actual browser screenshots for empty chat, populated chat, provider dialog and dark theme were uploaded as artifact **11678986836**. They do **not** demonstrate live AI, MT5, or a Windows WebView accessibility test.

**PASS — Windows installer build and security stage:** [run 38077393850](https://github.com/ekpeekpe/windows-ai-trading-agent/actions/runs/38077393850) succeeded. Python/MetaTrader5 sidecar was frozen, tested over authenticated local HTTP, React compiled, Rust/Tauri and NSIS compiled. Actual artifact ID **11679612926**, ZIP size **50,736,804 bytes**, ZIP SHA-256 `1ada8e4d4393251b8ce9b4e4ddeb431364189a32c926b15afdd6285249f4ca25`. ZIP contains `Windows AI Trading Agent_0.3.0_x64-setup.exe`, size **50,740,443 bytes**, SHA-256 `c2b84e547d4d34a714d4cf327d2c4716827474219079f3ae0b28c5b81c9e7d6e`. The setup executable was also extracted and independently hashed in the working environment.

**SECURITY STATUS — unsigned:** GitHub Actions `Get-AuthenticodeSignature` returned `NotSigned`. The PE security directory is empty. A Windows Defender custom scan completed without detection on the hosted build runner. This is **not evidence that the developer's separate Windows detection was a false positive**; the original Defender/SmartScreen detection name and affected file are still unknown. No publisher identity is verified or signed release artifact published. A separate approved Azure signing workflow exists but requires a verified publisher account, OIDC enrollment, certificate profile, expected certificate subject and approvals.

**PASS — actual Windows installation:** [run 38078016474](https://github.com/ekpeekpe/windows-ai-trading-agent/actions/runs/38078016474) installed the exact v0.3.0 NSIS file silently on a Windows GitHub runner, launched `windows-ai-trading-agent.exe`, verified bundled Python backend health with trading disabled, and confirmed graceful UI shutdown removed the Python process tree. This is an automated Windows install/launch test, **not** an interactive visual test on the developer's PC.

**Implemented redesign:** `desktop/src/App.tsx` and `desktop/src/app.css` create a compact chat workspace with anchored composer, File / AI Provider / MetaTrader / Tools / View / Help menus and focused dialogs. Accessible names, keyboard focus trapping, menu arrow keys and Escape actions have been added. `desktop/playwright.config.ts` and `desktop/tests/premium-ui.spec.ts` test browser interactions, not the installed WebView. `docs/FEATURE_AUDIT.md`, `docs/WINDOWS_SECURITY.md`, and `docs/CHATGPT_CODEX_ELIGIBILITY.md` record remaining limitations and official eligibility guidance.

**BLOCKED / NOT TESTED:** Real OpenAI/Anthropic/Gemini API credentials and inference, ChatGPT OAuth/Codex-plan inference (no registered approved commercial client), Codex usage metrics, a real broker-authenticated MT5 quote, compiled EA chart operation, Windows credential store with an actual user key, keyboard/screen-reader acceptance in installed Windows WebView, actual microphone/speakers, installer upgrade/uninstall, the custom installation preflight wizard, and the original Windows security-warning classification.

**Safety remains enforced:** Broker order submission has not been enabled. Proposals cannot execute trades; chart IPC remains opt-in. Never interpret mock browser market data as live MT5.

## Continuation 7 — public-source ChatGPT-plan sign-in v0.3.1 (2026-10-10)

**Repository:** public at `ekpeekpe/windows-ai-trading-agent`, but a LICENSE file is still missing. Publishing an OSI-compatible license is a remaining owner decision; public visibility by itself does not grant open-source redistribution rights.

**Implemented:** Official OpenAI OSS dynamic OAuth registration (`dynamic_agent_client` bootstrap; OpenAI-issued per-account `oaiapp_...` client ID) and system-browser authorization, loopback PKCE/state/nonce verification, signed OIDC ID token validation, Windows Credential Manager session storage, expiry/refresh rotation, account reconnect/signout, account model catalog, real streamed Responses inference with `store=False`, `stream=True` and existing read-only MT5 function tools. OpenAI API-key access remains independent, and no broker order execution has been enabled. These implementation properties are NOT proof of real personal-account authorization.

**PASS — portable and Windows CI:** [run 38085541145](https://github.com/ekpeekpe/windows-ai-trading-agent/actions/runs/38085541145) succeeded, including **73 passed, 2 skipped** on both Linux versions and Windows, and **6 Playwright browser tests passed** with mocked endpoints. The first browser test run for sign-in failed because its progress text was hidden, fixed in commit `574b5c63de0f9e515b58589ff032dd55ff726fdf`; the subsequent full portable workflow passed.

**PASS — installer:** [Windows build 38085541147](https://github.com/ekpeekpe/windows-ai-trading-agent/actions/runs/38085541147) generated **Windows AI Trading Agent_0.3.1_x64-setup.exe** from source `574b5c63de0f9e515b58589ff032dd55ff726fdf`. GitHub artifact ID **11682207721** is a ZIP of 50,996,485 bytes; ZIP SHA-256 `c75395d2f85494b43775c7eb59655d3d64f07c8abfef52b829077eead35f1806`. The EXE is **51,000,041 bytes**; independently verified SHA-256 `aafed6ad6b2b5c7083657935f6ff9880dc25761c3e51370a2c6f2d1ac745a125`. Build pipeline verified `NotSigned` Authenticode and a Defender custom scan without detection on its own Windows runner. A scan on one runner is not a determination of the user's prior Windows warning.

**PASS — actual Windows package acceptance:** [run 38086191001](https://github.com/ekpeekpe/windows-ai-trading-agent/actions/runs/38086191001) downloaded this exact v0.3.1 installer, installed silently as current user, launched the installed Tauri executable, detected healthy bundled localhost backend (trading disabled), and verified graceful application close removed the frozen Python process tree.

**NOT TESTED — real account:** No personal ChatGPT OAuth authorization, actual issued client ID, model entitlement, or real subscription-backed inference was performed in CI or this environment. Users must consent in their own system browser and verify an inference turn; neither the developer nor the assistant can mint their private issued client ID in advance. No real MT5 terminal, chart changes, or audio-hardware tests were executed.

**Important:** This is the direct official OAuth Responses integration for ChatGPT-plan inference, **not** a bundled Codex app-server executable or unrestricted code-execution agent. Separate paid/hosted commercialization requires OpenAI's specific eligibility process. Windows publisher signing remains blocked by missing approved signing credentials. See `CHATGPT_CODEX_ELIGIBILITY.md`.


## Continuation — v0.3.2 Windows sign-in and model picker fixes (2026-10-10)

**User-reported defect:** v0.3.1's installed ChatGPT account login showed unavailable status and did not open a browser. v0.3.2 fixes the native launch flow and credential diagnostics; an actual person's browser login is still **NOT TESTED**.

**Implemented:** The Tauri native command opens official `auth.openai.com` authorization in the selected default, Edge, or Chrome browser; validates the OAuth URL and keeps it outside the renderer. Edge/Chrome executables are discovered from standard Windows installation paths instead of relying on PATH. Signed-in accounts can be individually added, reauthorized, or selected, while native authorization state, bearer tokens, and refresh tokens remain inaccessible to React. ChatGPT OAuth status now returns useful Windows credential errors instead of opaque failures. The broker execution path stays disabled.

**Real Windows Credential Manager correction:** Generic credential blobs have a size limit; ChatGPT OAuth session JSON can exceed it. The OS-protected `SegmentedWindowsVault` stores long values in revisioned protected chunks with a hash-checked manifest, safe rotation, and cleanup. No unprotected local credential files are introduced.

**Provider-specific models:** OpenAI API, Anthropic, Gemini, and ChatGPT-plan model choices are selected from provider-specific model lists in dropdowns (never freely typed). Release dates determine chronological order only when provided by the upstream provider. Missing or disconnected credentials disable model selection. The AI connection dialog has been redesigned into a compact Windows settings pane with a provider rail and no nested scrolling.

**PASS — automated tests:** [portable and Windows CI run 38089044732](https://github.com/ekpeekpe/windows-ai-trading-agent/actions/runs/38089044732) passed; **82 backend tests passed, 2 skipped on Windows**, including real Windows Credential Manager synthetic-credential and large-token round-trip checks, and **8 browser UI tests passed** using explicitly mocked providers. Separate Linux backend matrix jobs passed. These tests do not establish a real user's OAuth login, ChatGPT inference entitlement, or a real broker terminal.

**PASS — packaged build:** [NSIS run 38089044761](https://github.com/ekpeekpe/windows-ai-trading-agent/actions/runs/38089044761) succeeded from source commit `c4df206b4b86e2f13f31ead6d60ae0974595ec06`. The PyInstaller-frozen Windows backend passed actual authenticated readiness, Windows Credential Manager and native-browser OAuth callback initialization (no user login performed); React, Rust/Tauri and NSIS compiled. Unsigned artifact ID **11683373093**: ZIP size **51,064,738 bytes**, ZIP SHA-256 `c836fe80eb694608c001ff8e6d7a877b7efa3a85003e171f5e1dcefd77c15f84`. The extracted setup executable is `Windows AI Trading Agent_0.3.2_x64-setup.exe`, **51,068,267 bytes**, SHA-256 `2057515ce70de2a88eedb43ef27dc459edba04d188c3a302848cbc8765e56edb`. The build runner reported no Defender threat in its custom installer scan, but Authenticode remains `NotSigned`; neither fact explains any security alert on a user's different computer.

**PASS — Windows installation acceptance:** [run 38089566581](https://github.com/ekpeekpe/windows-ai-trading-agent/actions/runs/38089566581) installed the **exact v0.3.2** NSIS executable on a hosted Windows runner, started the installed Tauri executable and authenticated bundled localhost backend, confirmed no trading was enabled, then closed the UI and verified its Python process tree shut down.

**NOT TESTED:** Real OpenAI browser consent/account selection on a developer's own two Chrome/Edge profiles, a completed ChatGPT-plan inference, live OpenAI/Anthropic/Gemini credentials, MetaTrader 5 terminal and current EURUSD price, MQL5 chart actions, and voice hardware. The app is still an unsigned development build. The public GitHub repository has no `LICENSE` file yet; its owner must choose a redistribution license before calling the code open-source in the legal sense.
