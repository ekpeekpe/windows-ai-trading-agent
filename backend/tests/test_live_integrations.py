"""Real integration tests: skipped unless explicitly opted in on Windows."""
import os
import pytest
from app.mt5 import MT5ReadOnly
from app.agent import OpenAIAgent
from app.tools import ToolRegistry

@pytest.mark.live
def test_actual_authenticated_mt5_quote():
    if os.getenv('RUN_LIVE_MT5') != '1':
        pytest.skip('Needs Windows MT5 terminal: set RUN_LIVE_MT5=1')
    login = os.getenv('MT5_EXPECTED_LOGIN')
    mt5 = MT5ReadOnly(os.getenv('MT5_TERMINAL_PATH'), int(login) if login else None)
    account = mt5.status()
    quote = mt5.quote(os.getenv('MT5_TEST_SYMBOL', 'EURUSD'))
    assert account['connected'] and account['source']=='MetaTrader5'
    assert quote['source']=='MetaTrader5' and quote['time_msc'] > 0
    assert quote['ask'] > 0 and quote['bid'] > 0

@pytest.mark.live
@pytest.mark.provider_live
def test_actual_openai_calls_real_mt5_tool():
    if os.getenv('RUN_LIVE_AI') != '1':
        pytest.skip('Needs OpenAI API key and Windows MT5 terminal: set RUN_LIVE_AI=1')
    if not os.getenv('OPENAI_API_KEY'):
        pytest.fail('Live API test requires OPENAI_API_KEY')
    class SpyTerminal:
        def __init__(self):
            self.real = MT5ReadOnly(os.getenv('MT5_TERMINAL_PATH'))
            self.called = False
        def quote(self, symbol):
            self.called = True
            return self.real.quote(symbol)
    terminal = SpyTerminal()
    model = os.getenv('OPENAI_TEST_MODEL', 'gpt-4.1-mini')
    result = OpenAIAgent(tools=ToolRegistry(terminal)).ask('Use the quote tool for EURUSD. Report the actual bid and ask.', model)
    assert terminal.called, 'Provider did not call MT5 quote tool'
    assert result.strip()
