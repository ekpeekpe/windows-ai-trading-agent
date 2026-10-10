"""MOCKED MT5 tests: these DO NOT validate a live terminal."""
import sys
from types import SimpleNamespace
import pytest
from app.mt5 import MT5ReadOnly, MT5Unavailable

def fake_module(connected=True, login=42):
    calls = []
    def record(name, ret):
        def fn(*args, **kwargs):
            calls.append((name, args, kwargs)); return ret
        return fn
    module = SimpleNamespace(
        initialize=record('initialize', True), shutdown=record('shutdown', None),
        last_error=lambda: (0, 'ok'),
        terminal_info=lambda: SimpleNamespace(connected=connected, name='TestTerminal', path='C:/fake'),
        account_info=lambda: SimpleNamespace(login=login, server='Demo', trade_mode=0),
        symbol_info=lambda name: SimpleNamespace(name=name, point=.00001, digits=5, volume_min=.01,
                  volume_max=100, volume_step=.01, trade_mode=4, visible=True),
        symbol_info_tick=lambda symbol: SimpleNamespace(bid=1.1, ask=1.2, time_msc=123000),
        symbols_get=lambda: [SimpleNamespace(name='EURUSD')],
        positions_get=lambda: [], orders_get=lambda: [],
        copy_rates_from_pos=lambda *a: [], TIMEFRAME_H1=16385,
    )
    return module, calls

def test_mocked_read_methods(monkeypatch):
    module, calls = fake_module()
    monkeypatch.setitem(sys.modules, 'MetaTrader5', module)
    gateway = MT5ReadOnly(expected_login=42)
    assert gateway.status()['account']['mode_label'] == 'demo'
    assert gateway.symbols()['total'] == 1
    assert gateway.specifications('EURUSD')['volume_step'] == .01
    assert gateway.quote('EURUSD')['time_msc'] == 123000
    assert gateway.rates('EURUSD')['bars'] == []
    assert gateway.positions()['positions'] == []
    assert gateway.pending_orders()['orders'] == []
    assert sum(n == 'shutdown' for n, _, _ in calls) == 7
    assert not any(n == 'symbol_select' for n, _, _ in calls)

def test_mocked_disconnection_and_account_mismatch(monkeypatch):
    module, calls = fake_module(connected=False)
    monkeypatch.setitem(sys.modules, 'MetaTrader5', module)
    with pytest.raises(MT5Unavailable, match='disconnected'):
        MT5ReadOnly().quote('EURUSD')
    assert calls[-1][0] == 'shutdown'
    module, _ = fake_module(login=11)
    monkeypatch.setitem(sys.modules, 'MetaTrader5', module)
    with pytest.raises(MT5Unavailable, match='account changed'):
        MT5ReadOnly(expected_login=42).status()

@pytest.mark.parametrize('bad', [0, 501])
def test_count_is_bounded(bad):
    with pytest.raises(ValueError):
        MT5ReadOnly().rates('EURUSD', count=bad)
