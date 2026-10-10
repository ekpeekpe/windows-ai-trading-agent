from pydantic import ValidationError
import pytest
from app.tools import ToolRegistry
class MockTerminal:
    def quote(self,symbol):return {'symbol':symbol,'source':'MOCK'}
    def status(self):return {'connected':True}
    def positions(self):return {'positions':[]}
    def pending_orders(self):return {'orders':[]}
    def symbols(self,limit):return {'symbols':[], 'limit':limit}
    def specifications(self,symbol):return {'symbol':symbol}
    def rates(self,symbol,timeframe,count):return {'bars':[]}

def test_allowlist_and_invalid_arguments():
    r=ToolRegistry(MockTerminal())
    assert len(r.definitions())==7
    assert r.execute('quote',{'symbol':'EURUSD'})['source']=='MOCK'
    with pytest.raises(ValueError,match='Unregistered'):r.execute('order_send',{})
    with pytest.raises(ValidationError):r.execute('quote',{'symbol':'EURUSD','shell':'calc.exe'})
    with pytest.raises(ValidationError):r.execute('historical_rates',{'symbol':'EURUSD','count':501})
    with pytest.raises(ValueError):r.execute('quote', ['EURUSD'])
