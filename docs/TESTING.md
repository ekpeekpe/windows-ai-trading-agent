# Test plan

## Portable tests

Run on Windows or Linux:
```sh
cd backend
python -m pip install -e ".[dev]"
python -m pytest -q
```
Tests check validation, tool whitelisting, proposal rejection, exact-payload approval, replay prevention, and health-route refusal of trading. FakeTerminal in unit tests is an explicit test double; it is **not** proof of MT5 connectivity.

## Real Windows acceptance (not run yet)
Install official MT5 terminal, sign into a demo account, install Python MetaTrader5 package. Run the backend with `uvicorn app.main:app --host 127.0.0.1 --port 8765` and request `GET /terminal` and `GET /quote/EURUSD`. Check actual account and timestamp; do not interpret unavailable status as successful connection.

Chart/indicator and voice tests are blocked until those implementations exist. No order execution test should be attempted with this foundation.
