"""Launcher fails closed unless started with a secure local token and port."""
import launcher

def test_launcher_refuses_no_token(monkeypatch):
    monkeypatch.delenv("AGENT_LOCAL_TOKEN", raising=False)
    monkeypatch.setenv("AGENT_PORT", "18765")
    assert launcher.main() == 2

def test_launcher_refuses_invalid_port(monkeypatch):
    monkeypatch.setenv("AGENT_LOCAL_TOKEN", "X"*32)
    monkeypatch.setenv("AGENT_PORT", "0")
    assert launcher.main() == 2

def test_local_backend_subprocess_starts_and_stops():
    """Real Python child process + localhost HTTP; no provider or MT5 involved."""
    import os, socket, subprocess, sys, time
    from pathlib import Path
    import httpx
    with socket.socket() as listening:
        listening.bind(("127.0.0.1", 0))
        port = listening.getsockname()[1]
    env = dict(os.environ, AGENT_LOCAL_TOKEN="unit-tests-local-token-not-a-secret", AGENT_PORT=str(port))
    process = subprocess.Popen([sys.executable, str(Path(__file__).resolve().parents[1]/"launcher.py")],
                               cwd=Path(__file__).resolve().parents[1], env=env,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        url = f"http://127.0.0.1:{port}/health"
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            try:
                result = httpx.get(url, timeout=1)
                assert result.status_code == 200
                assert result.json()["trading_enabled"] is False
                return
            except httpx.RequestError:
                if process.poll() is not None: break
                time.sleep(.1)
        raise AssertionError("Python sidecar did not start successfully")
    finally:
        process.terminate()
        try: process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
