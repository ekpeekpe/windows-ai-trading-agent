# Windows installer candidate — status and test procedure

**Do not claim a downloadable release until the Windows GitHub Actions build uploads a real .exe and it has been checked.** The NSIS workflow is defined at `.github/workflows/windows-installer.yml`.

## What the proposed Windows CI builds

1. Windows 64-bit Python 3.12 runtime and project dependencies, including the MetaTrader5 wheel.
2. A PyInstaller one-file `agent-backend.exe` with the backend modules and supported SDK packages.
3. A Tauri 2 React/Rust desktop, bundling the backend as `externalBin`.
4. A per-user NSIS setup executable; Rust generates a new random internal token and owns the Python sidecar lifecycle.
5. A SHA-256 digest and the GitHub Actions artifact `windows-ai-trading-agent-nsis-unsigned`, if the build succeeds.

GitHub Actions > **Windows NSIS installer candidate** > latest successful run > **Artifacts** is the only intended candidate-download source at this stage. Artifacts may require GitHub sign-in, expire after 14 days, and are **unsigned**. No separate installer download URL should be advertised without checking the actual artifact.

## Installation preflight and honest limitations

The installer uses Tauri/NSIS for the per-user installation, upgrade/uninstall and WebView2 runtime bootstrapper. WebView2 downloads when absent and internet is required in that case. The current installer **does not yet have** the custom prerequisite review/download-size/disk-space progress wizard requested for the final product. The NSIS installer provides standard progress, not a validated per-component download breakdown. Node.js and Python are bundled for runtime use (Node.js is not installed); the Python runtime is frozen into the backend executable.

MetaTrader 5 is optional, **not** automatically installed, launched or changed during installation. After first launch, choose Discover installed terminals, select the intended path, then Check MT5 connection. If missing, use the official MetaQuotes page at https://www.metatrader5.com/en. Do not download a broker-branded installer automatically.

No license key, subscriptions, trial expiry or application payments are imposed in this test build.

## Windows acceptance steps — NOT YET EXECUTED

1. Inspect CI build status and SHA-256; download the unsigned installer only if its artifact exists.
2. On an isolated Windows 10/11 x64 test PC, check publisher warning, install without Python/Node, note WebView2 prompt, and launch from Start menu.
3. Confirm app starts its sidecar automatically; verify Backend ready and Trading disabled.
4. Open AI connections. Enter a test-user OpenAI or Anthropic API key. Save, verify configuration, click Test connection. Confirm success is based on a real provider call. Remove the key and verify it disappears.
5. Check missing MT5 behaviour; if installed, use terminal discovery/selection, check actual login/server, and request a fresh EURUSD quote while market data is available.
6. Test microphone permission, transcription, spoken reply, keyboard/screen-reader accessibility and stopping audio.
7. Test uninstall/upgrade preserving Windows Credential Manager entries only according to the documented credential policy; manually remove credentials if necessary.
8. Confirm the app cannot submit a broker order. Never submit a trade for this milestone.

### Known installer blockers

- Tauri and the bundled Python/MetaTrader5 wheel have not been compiled and launched on an actual Windows runner or test machine from this chat.
- CI runs for push builds are not available through the connected GitHub status endpoint; inspect the Actions UI for actionable logs.
- A frozen Python backend may require additional hidden imports or native DLL collection discovered only by actual Windows packaging.
- A proper signed release, custom preflight wizard, system permission checks, accurate download/installed-size estimates, optional MetaQuotes download installer verification and real upgrade/uninstall testing remain pending.

## Build manually on a Windows development workstation

See `docs/SETUP.md` for development prerequisites. For installer creation use the exact commands in `.github/workflows/windows-installer.yml`. Install the backend with `[windows,dev,package]`, run PyInstaller, stage `agent-backend-x86_64-pc-windows-msvc.exe`, generate icon assets, and run `cd desktop; npm run tauri build -- --bundles nsis`. Don't distribute an unverified binary.
