"""Chart helper below is a mock, not a real EA."""
from app.tools import ToolRegistry
class FakeChart:
    def execute(self,op,symbol,tf,period):
        return {'status':'MOCK_EA_ONLY','operation':op,'symbol':symbol}

def test_chart_tools_require_explicit_registry_opt_in():
    assert 'open_chart' not in [x['function']['name'] for x in ToolRegistry().definitions()]
    registered=ToolRegistry(chart_ipc=FakeChart())
    assert 'open_chart' in [x['function']['name'] for x in registered.definitions()]
    assert registered.execute('add_sma',{'symbol':'EURUSD','timeframe':'H1','period':20})['status']=='MOCK_EA_ONLY'
