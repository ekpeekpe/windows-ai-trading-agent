"""Speech SDK mock and input validation; microphone/provider NOT tested live."""
from types import SimpleNamespace
import pytest
from app.speech import transcribe, SpeechError
from fastapi.testclient import TestClient
from app.main import app

class MockClient:
    def __init__(self):
        self.calls=[]
        self.audio=SimpleNamespace(transcriptions=SimpleNamespace(create=self.create))
    def create(self,**kw):
        self.calls.append(kw)
        return SimpleNamespace(text='  Show EURUSD quote  ')

def test_mocked_transcription():
    c=MockClient()
    assert transcribe(b'x'*100, 'audio/webm', client=c)=='Show EURUSD quote'
    assert c.calls[0]['model']=='whisper-1'

def test_input_limits():
    with pytest.raises(SpeechError): transcribe(b'xyz','audio/webm')
    with pytest.raises(SpeechError): transcribe(b'x'*100,'application/octet-stream')

def test_endpoint_audio_requires_auth(monkeypatch):
    monkeypatch.setenv('AGENT_LOCAL_TOKEN','a-very-long-development-local-token')
    monkeypatch.setenv('OPENAI_API_KEY','fake-test-key')
    assert TestClient(app).post('/transcribe',files={'audio':('clip.webm',b'x'*100,'audio/webm')}).status_code==401
