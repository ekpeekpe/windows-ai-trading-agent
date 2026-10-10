# Troubleshooting

- `503 MetaTrader5 package requires...`: use Windows Python with the official MetaTrader5 package installed.
- `MT5 initialization failed`: launch the terminal manually, sign in and ensure the selected terminal path matches `MT5_TERMINAL_PATH`.
- `No tick`: verify the actual broker symbol name, trading session and terminal connectivity.
- Chat `503`: set `OPENAI_API_KEY` only in the backend process environment.
- Desktop dev UI fails: check that Python service listens on 127.0.0.1:8765 and start `npm run dev` from desktop.
- Proposals always return no execution: intentional safety limit of the foundation.
