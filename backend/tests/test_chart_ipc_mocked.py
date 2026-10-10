"""IPC file responder simulation only; no MQL5 compiler/terminal involved."""
import threading
import time
import pytest
from app.chart_ipc import ChartIPC, ChartControlError

def test_validations(tmp_path):
    ipc=ChartIPC(tmp_path)
    for params in [('EXEC','EURUSD','H1',20),('OPEN','../etc','H1',20),('SMA','EURUSD','H2',20),('SMA','EURUSD','H1',0)]:
        with pytest.raises(ValueError):ipc.execute(*params)

def test_timeout_is_unknown_and_not_retried(tmp_path):
    ipc=ChartIPC(tmp_path)
    with pytest.raises(ChartControlError,match='outcome unknown'):
        ipc.execute('OPEN','EURUSD','H1',timeout=1)
    assert (tmp_path/'agent_request.txt').exists()
    with pytest.raises(ChartControlError,match='pending'):
        ipc.execute('OPEN','EURUSD','H1',timeout=1)

def test_mocked_companion_reply(tmp_path):
    def responder():
        request=tmp_path/'agent_request.txt'
        for _ in range(200):
            if request.exists():
                ident=request.read_text().split('|')[0]
                request.unlink()
                (tmp_path/'agent_response.txt').write_text(ident+'|OK|12345|Chart opened and checked')
                return
            time.sleep(.005)
    worker=threading.Thread(target=responder);worker.start()
    out=ChartIPC(tmp_path).execute('OPEN','EURUSD','H1',timeout=3)
    worker.join(timeout=1)
    assert out['status']=='EA_REPORTED_OK'
    assert out['chart_id']==12345
    assert out['source']=='MQL5 ChartControlEA'

def test_reject_unmatched_reply(tmp_path):
    (tmp_path/'agent_response.txt').write_text('wrong|OK|1|no')
    with pytest.raises(ChartControlError,match='Unconsumed'):
        ChartIPC(tmp_path).execute('OPEN','EURUSD','H1',timeout=1)
