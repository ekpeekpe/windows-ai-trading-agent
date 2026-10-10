//! Native-only authenticated bridge to the bundled, read-only Python sidecar.
//! Webview cannot retrieve the local token or spawn arbitrary processes.
use std::net::TcpListener;
use std::sync::Mutex;
use std::time::Duration;
use tauri::{Manager, State};
use tauri_plugin_shell::process::CommandChild;
use tauri_plugin_shell::ShellExt;
use tauri_plugin_opener::OpenerExt;
use serde_json::Value;

struct Backend {
    port: u16,
    token: String,
    child: Mutex<Option<CommandChild>>,
    startup_error: Option<String>,
    client: reqwest::Client,
}

fn valid_part(value: &str) -> bool {
    !value.is_empty() && value.len() <= 32 &&
    value.bytes().all(|c| c.is_ascii_alphanumeric() || matches!(c, b'.' | b'_' | b'-'))
}

fn allowed(method: &str, path: &str) -> bool {
    match (method, path) {
        ("GET", "/health" | "/terminal" | "/providers" | "/terminals" | "/chatgpt/status" | "/chatgpt/models") => true,
        ("POST", "/chat" | "/proposals" | "/chart" | "/terminals/select" | "/chatgpt/start" | "/chatgpt/test" | "/chatgpt/signout" | "/chatgpt/cancel") => true,
        _ => {
            let parts: Vec<&str> = path.split('/').collect();
            match (method, parts.as_slice()) {
                ("GET", ["", "quote", symbol]) => valid_part(symbol),
                ("POST", ["", "proposals", id, "decision"]) =>
                    id.len() == 32 && id.bytes().all(|c| c.is_ascii_hexdigit()),
                ("PUT" | "DELETE", ["", "providers", provider, "key"]) =>
                    matches!(*provider, "openai" | "anthropic" | "gemini"),
                ("POST", ["", "providers", provider, "test"]) =>
                    matches!(*provider, "openai" | "anthropic" | "gemini"),
                ("GET", ["", "providers", provider, "models"]) =>
                    matches!(*provider, "openai" | "anthropic" | "gemini"),
                _ => false,
            }
        }
    }
}

#[tauri::command]
async fn backend_request(
    state: State<'_, Backend>, method: String, path: String, body: Option<Value>
) -> Result<Value, String> {
    if !allowed(&method, &path) { return Err("This operation is not permitted".into()); }
    if let Some(error) = &state.startup_error { return Err(error.clone()); }
    let verb = reqwest::Method::from_bytes(method.as_bytes()).map_err(|_| "Invalid HTTP method")?;
    let url = format!("http://127.0.0.1:{}{}", state.port, path);
    let mut request = state.client.request(verb, url).header("x-agent-token", &state.token);
    if let Some(payload) = body { request = request.json(&payload); }
    let response = request.send().await.map_err(|_| "Local backend is unavailable; try restarting the application".to_string())?;
    let status = response.status();
    let payload: Value = response.json().await.map_err(|_| "Invalid local backend response".to_string())?;
    if status.is_success() { Ok(payload) } else {
        Err(payload.get("detail").and_then(Value::as_str).unwrap_or("Backend request failed").to_string())
    }
}

// Only native Rust sees the OAuth URL; the webview never receives the PKCE
// state, nonce, authorization URL, or bearer token. Default/Edge/Chrome
// selection lets users authorize accounts in independent browser profiles.
#[tauri::command]
async fn chatgpt_login(
    app: tauri::AppHandle,
    state: State<'_, Backend>,
    account_key: Option<String>,
    browser: String
) -> Result<Value, String> {
    let with_browser = match browser.as_str() {
        "default" => None,
        "edge" => Some("msedge"),
        "chrome" => Some("chrome"),
        _ => return Err("Choose Default, Edge, or Chrome".into())
    };
    if let Some(id) = &account_key {
        if id.len() != 36 || !id.bytes().all(|b| b.is_ascii_hexdigit()) {
            return Err("Invalid saved account reference".into());
        }
    }
    if let Some(error) = &state.startup_error { return Err(error.clone()); }
    let endpoint = format!("http://127.0.0.1:{}/chatgpt/start", state.port);
    let response = state.client.post(endpoint)
        .header("x-agent-token", &state.token)
        .json(&serde_json::json!({"account_key":account_key, "launch_browser":false}))
        .send().await.map_err(|_| "Local backend is unavailable".to_string())?;
    let success = response.status().is_success();
    let data: Value = response.json().await.map_err(|_| "Invalid sign-in response".to_string())?;
    if !success {
        return Err(data.get("detail").and_then(Value::as_str)
            .unwrap_or("Could not initialize ChatGPT sign-in").to_string());
    }
    let raw = data.get("authorization_url").and_then(Value::as_str)
        .ok_or("Backend did not provide a browser authorization URL")?;
    let parsed = reqwest::Url::parse(raw).map_err(|_| "Malformed authorization URL")?;
    if parsed.scheme() != "https" || parsed.host_str() != Some("auth.openai.com")
        || parsed.path() != "/api/accounts/authorize"
        || !parsed.username().is_empty() || parsed.password().is_some() {
        return Err("Blocked unsafe OAuth browser destination".into());
    }
    if let Err(_err) = app.opener().open_url(raw, with_browser) {
        let _ = state.client.post(format!("http://127.0.0.1:{}/chatgpt/cancel", state.port))
            .header("x-agent-token", &state.token).send().await;
        return Err("Windows could not launch that browser. Select Default browser, or ensure Edge/Chrome is installed.".into());
    }
    Ok(serde_json::json!({"state":"waiting_for_browser",
                          "expires_in":300, "browser_opened":true}))
}

#[tauri::command]
async fn backend_transcribe(state: State<'_, Backend>, audio: Vec<u8>, mime: String) -> Result<Value, String> {
    if audio.len() < 100 || audio.len() > 10 * 1024 * 1024 ||
       !matches!(mime.as_str(), "audio/webm" | "audio/mp4" | "audio/wav") {
        return Err("Unsupported audio format or size".into());
    }
    if let Some(error) = &state.startup_error { return Err(error.clone()); }
    let part = reqwest::multipart::Part::bytes(audio)
        .file_name(if mime == "audio/mp4" { "speech.m4a" } else { "speech.webm" })
        .mime_str(&mime).map_err(|_| "Invalid audio content type")?;
    let response = state.client
        .post(format!("http://127.0.0.1:{}/transcribe", state.port))
        .header("x-agent-token", &state.token)
        .multipart(reqwest::multipart::Form::new().part("audio", part))
        .send().await.map_err(|_| "Speech backend unavailable".to_string())?;
    let success = response.status().is_success();
    let payload: Value = response.json().await.map_err(|_| "Invalid transcription response")?;
    if success { Ok(payload) } else {
        Err(payload.get("detail").and_then(Value::as_str).unwrap_or("Transcription failed").to_string())
    }
}

/// Kill the frozen PyInstaller parent and its child worker on Windows.
///
/// A one-file Python executable can spawn a second process. Killing only the
/// Tauri sidecar handle can leave that worker running after the UI exits.
fn stop_backend_process_tree(process: CommandChild) {
    let pid = process.pid();
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        let system_root = std::env::var_os("SystemRoot").unwrap_or_else(|| "C:\\Windows".into());
        let taskkill = std::path::PathBuf::from(system_root).join("System32").join("taskkill.exe");
        let _ = std::process::Command::new(taskkill)
            .args(["/PID", &pid.to_string(), "/T", "/F"])
            .creation_flags(0x08000000)
            .status();
    }
    #[cfg(not(windows))]
    let _ = pid;
    let _ = process.kill();
}

pub fn run() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_opener::init())
        .setup(|app| {
            let listener = TcpListener::bind("127.0.0.1:0")?;
            let port = listener.local_addr()?.port();
            drop(listener);
            let token = format!("{}{}", uuid::Uuid::new_v4().simple(), uuid::Uuid::new_v4().simple());
            let result = app.shell().sidecar("agent-backend")
                .and_then(|command| command
                    .env("AGENT_LOCAL_TOKEN", &token)
                    .env("AGENT_PORT", port.to_string()).spawn());
            let (child, startup_error) = match result {
                Ok((mut events, child)) => {
                    tauri::async_runtime::spawn(async move { while events.recv().await.is_some() {} });
                    (Some(child), None)
                },
                Err(_err) => (None, Some("Packaged Python backend could not start. Check the installation or reinstall.".to_string())),
            };
            app.manage(Backend { port, token, child: Mutex::new(child), startup_error,
                client: reqwest::Client::builder().timeout(Duration::from_secs(100)).build()? });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![backend_request, backend_transcribe, chatgpt_login])
        .build(tauri::generate_context!()).expect("Failed to initialize desktop application");
    app.run(|handle, event| {
        if matches!(event, tauri::RunEvent::Exit) {
            if let Some(state) = handle.try_state::<Backend>() {
                if let Ok(mut child) = state.child.lock() {
                    if let Some(process) = child.take() { stop_backend_process_tree(process); }
                }
            }
        }
    });
}

#[cfg(test)]
mod tests {
    use super::allowed;
    #[test] fn deny_unsafe_paths() {
        assert!(allowed("GET", "/health"));
        assert!(allowed("POST", "/providers/openai/test"));
        assert!(allowed("POST", "/chatgpt/start"));
        assert!(allowed("POST", "/chatgpt/cancel"));
        assert!(allowed("GET", "/chatgpt/status"));
        assert!(!allowed("GET", "/chatgpt/callback"));
        assert!(!allowed("POST", "/order_send"));
        assert!(!allowed("GET", "/quote/../secret"));
        assert!(!allowed("POST", "/providers/other/test"));
    }
}
