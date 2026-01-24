# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Investment Scorer is an AI-powered real-time stock analysis platform. It calculates investment scores (1-100) based on 15+ technical indicators and fundamental metrics, with market sentiment analysis and stock screening capabilities.

**Key principle**: Real-time analysis, stateless architecture, paper trading only.

## Project Structure

```
/
├── app.py                    # Flask backend (~1400 lines - all logic)
├── requirements.txt          # Python dependencies
├── Dockerfile               # Container configuration
├── docker-compose.yml       # Service orchestration
├── .daytona/
│   └── config.yaml          # Daytona cloud workspace config
├── .devcontainer/
│   └── devcontainer.json    # Dev container configuration
├── templates/
│   └── index.html           # Main SPA template (dark theme UI)
├── static/                  # Static assets
└── frontend/                # React frontend (optional)
    ├── package.json
    ├── public/
    └── src/
```

## Common Commands

### Run the App

```bash
# Install dependencies and run
pip install -r requirements.txt
python app.py

# Server starts on http://localhost:8080
```

### Docker

```bash
docker-compose up --build      # Build and run
docker-compose up -d           # Detached mode
docker-compose logs -f         # View logs
docker-compose down            # Stop
```

### Daytona Deployment

```bash
daytona create .
# Or from GitHub:
daytona create https://github.com/rishirevuri/Daytona_trading_agent
```

## Architecture

### Core Components in `app.py`

| Component | Lines | Description |
|-----------|-------|-------------|
| `NewsAnalyzer` | 59-161 | Fetches stock news via yfinance, analyzes sentiment |
| `TechnicalAnalyzer` | 163-271 | Support/resistance levels, pattern detection |
| `get_vix()` | 273-283 | Fetches VIX (fear index) from Yahoo Finance |
| `get_market_sentiment()` | 285-354 | Aggregates VIX, treasury yields, S&P 500 trends |
| `get_earnings_data()` | 388-443 | Historical earnings surprises, analyst targets |
| `calculate_fundamental_score()` | 445-587 | P/E, PEG, margins, growth, ROE scoring |
| `calculate_technical_score()` | 589-881 | RSI, MACD, Bollinger, Stochastic, ADX, etc. |
| `calculate_investment_score()` | 986-1268 | Main scoring function (70% tech + 30% fundamental) |
| `screen_stocks()` | 1270-1320 | Parallel screening of 100 stocks |

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serves the main SPA |
| `/api/analyze` | POST | Analyze stock: `{"ticker": "AAPL"}` |
| `/api/screen` | GET | Screen stocks: `?filter=strong_buys&limit=20` |
| `/api/market-sentiment` | GET | VIX, treasury yields, S&P 500 data |
| `/api/speak` | POST | Text-to-speech via ElevenLabs (optional) |
| `/health` | GET | Health check endpoint |

### Screening Filters

- `all` - All 100 stocks in universe
- `strong_buys` - Score >= 75
- `buys` - Score 60-74
- `sells` - Score 30-44
- `strong_sells` - Score < 30
- `shorts` - Score < 40 (short candidates)

### Technical Indicators (with weights)

| Indicator | Weight | Function |
|-----------|--------|----------|
| RSI (14) | 10% | Overbought/oversold |
| MACD | 10% | Trend momentum |
| Moving Averages | 12% | SMA 20/50/200, Golden/Death Cross |
| Earnings Surprise | 10% | Beat/miss history |
| ADX | 8% | Trend strength |
| Bollinger Bands | 8% | Volatility position |
| Stochastic | 8% | Momentum oscillator |
| VIX | 8% | Market fear gauge |
| MFI | 6% | Money flow |
| Williams %R | 5% | Overbought/oversold |
| CCI | 5% | Price deviation |
| OBV | 5% | Volume trend |
| VWAP | 5% | Volume-weighted price |

### Score Interpretation

| Score | Recommendation | Action |
|-------|---------------|--------|
| 75-100 | STRONG BUY | Long with high confidence |
| 60-74 | BUY | Long with medium confidence |
| 45-59 | HOLD | Wait for clearer signals |
| 30-44 | SELL | Short with medium confidence |
| 1-29 | STRONG SELL | Short with high confidence |

## Stock Universe

The screener analyzes 100 stocks across sectors:
- **Tech**: AAPL, MSFT, GOOGL, NVDA, META, AMD, etc.
- **Finance**: JPM, BAC, GS, V, MA, etc.
- **Healthcare**: JNJ, UNH, PFE, LLY, etc.
- **Consumer**: WMT, AMZN, HD, NKE, etc.
- **Energy**: XOM, CVX, COP, SLB, etc.
- **ETFs**: SPY, QQQ, IWM, XLF, XLE, etc.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ELEVENLABS_API_KEY` | No | For text-to-speech feature |
| `ELEVENLABS_VOICE_ID` | No | Voice ID (default: Adam) |

## Dependencies

```
flask>=2.0.0
flask-cors>=4.0.0
yfinance>=0.2.0
pandas>=1.5.0
numpy>=1.21.0
gunicorn>=21.0.0
redis>=4.0.0
```

## Key Implementation Details

1. **Parallel Processing**: Stock screening uses `ThreadPoolExecutor` for concurrent analysis
2. **Error Handling**: Each indicator calculation is wrapped in try/except to prevent single failures from crashing analysis
3. **Caching**: No caching - all data fetched fresh from Yahoo Finance
4. **Rate Limiting**: None implemented - relies on yfinance's built-in handling

## Disclaimer

Educational purposes only. Not financial advice.
