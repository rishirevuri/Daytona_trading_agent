# Investment Scorer - Developer Guide

## Project Overview

Investment Scorer is an AI-powered real-time stock analysis platform. it calculates comprehensive investment scores (1-100) based on a blend of technical analysis, fundamental metrics, and market sentiment.

**Key Features:**
*   **Real-time Analysis:** Live market data via `yfinance`.
*   **Investment Scoring:** 1-100 score with recommendations from STRONG SELL to STRONG BUY.
*   **Technical Analysis:** 15+ indicators including RSI, MACD, Bollinger Bands, and Candlestick Pattern detection.
*   **Fundamental Analysis:** Evaluation of P/E, PEG, margins, growth, and ROE.
*   **Market Sentiment:** Aggregates VIX, consumer sentiment, and news impact analysis.
*   **Voice Summaries:** Narrated research briefings using ElevenLabs (optional).
*   **Stock Screener:** Parallelized screening of a 100-stock universe.
*   **Progressive Web App:** Installable as a native app on all platforms.

## Architecture

*   **Backend:** Python/Flask in `app.py`. A single-file core (approx. 3800 lines) containing all scoring logic, data fetching, and API endpoints.
*   **Frontend:** React SPA in `frontend/`. Built assets are served by the Flask app from `frontend/build/`.
*   **Static Assets:** `templates/index.html` and `static/` provide additional UI components and styling.
*   **Deployment:** Containerized with Docker and configured for Daytona cloud development.

## Project Structure

```
/
├── app.py                    # Core Flask backend (Scoring engine & API)
├── requirements.txt          # Python dependencies
├── Dockerfile               # Container configuration
├── docker-compose.yml       # Service orchestration
├── AGENTS.md                # Detailed repository guidelines
├── CLAUDE.md                # Claude Code specific guidance
├── README.md                # Public project overview
├── .daytona/                # Daytona workspace configuration
├── .devcontainer/           # Dev container configuration
├── frontend/                # React frontend (Source)
│   ├── src/                 # React components and hooks
│   └── package.json         # Node.js dependencies
├── static/                  # Static assets and PWA service worker
└── templates/               # HTML templates (index.html)
```

## Setup and Development

### Local Development

**Backend (Python 3.10+):**
```bash
pip install -r requirements.txt
python app.py
# Server runs at http://localhost:8080
```

**Frontend (Node.js & npm):**
```bash
cd frontend
npm install
npm start
# Runs at http://localhost:3000
```

**Production Build:**
```bash
cd frontend && npm run build
# Flask will now serve the updated frontend from build/
```

### Daytona Deployment

This project is optimized for [Daytona](https://www.daytona.io/).
```bash
daytona create https://github.com/rishirevuri/Daytona_trading_agent
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serves the main SPA |
| `/api/snapshot` | GET | Comprehensive market snapshot (VIX, Top Buys, Shorts, News) |
| `/api/analyze` | POST | Analyze a single ticker: `{"ticker": "AAPL"}` |
| `/api/stock/<ticker>/chart` | GET | Historical chart data and stock details |
| `/api/screen` | GET | Screen 100 stocks: `?filter=strong_buys&limit=20` |
| `/api/market-sentiment` | GET | VIX, treasury yields, and S&P 500 trends |
| `/api/speak` | POST | Text-to-speech via ElevenLabs: `{"text": "..."}` |
| `/health` | GET | Health check |

## Scoring Algorithm

The Investment Score (1-100) is calculated as:
**Final Score = (Technical Score * 0.65) + (Fundamental Score * 0.35)**

### Technical Indicator Weights (within Technical Score)

| Indicator | Weight | Description |
|-----------|--------|-------------|
| Candlestick Patterns | 16% | Pattern detection and trend analysis |
| Earnings Surprise | 10% | Average surprise over last 4 quarters |
| Moving Averages | 9% | SMA 20/50/200 and Golden/Death Crosses |
| VIX (Fear Index) | 8% | Market-wide volatility sentiment |
| RSI | 7% | Relative Strength Index (14-period) |
| MACD | 7% | Moving Average Convergence Divergence |
| News Sentiment | 7% | NLP-based sentiment from recent news |
| ADX | 5% | Average Directional Index (trend strength) |
| Bollinger Bands | 5% | Price position relative to volatility bands |
| Stochastic | 5% | Momentum oscillator |
| MFI / OBV | 8% | Money Flow Index (4%) and On-Balance Volume (4%) |
| Others | 13% | Williams %R, CCI, VWAP, Consumer Sentiment |

### Score Interpretation

| Score | Recommendation | Action |
|-------|---------------|--------|
| 75-100 | STRONG BUY | Long with high confidence |
| 60-74 | BUY | Long with medium confidence |
| 45-59 | HOLD | Wait for clearer signals |
| 30-44 | SELL | Short with medium confidence |
| 1-29 | STRONG SELL | Short with high confidence |

## Development Conventions

*   **Logic Consolidation:** Core scoring logic resides in `app.py`. Ensure any new indicators are added to the `calculate_technical_score` or `calculate_fundamental_score` functions.
*   **Statelessness:** The backend is designed to be stateless. Data is fetched fresh from `yfinance` with minimal caching.
*   **Error Handling:** Every indicator calculation is wrapped in try-except blocks to ensure the overall score remains available even if specific data points are missing.
*   **Frontend UI:** Dark theme, responsive design using Tailwind CSS. Components are modularized in `frontend/src/components`.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ELEVENLABS_API_KEY` | No | Required for the "Speak Analysis" feature |
| `ELEVENLABS_VOICE_ID` | No | Custom voice ID (default: Adam) |
| `FLASK_ENV` | No | Set to `development` for auto-reloading |

## Disclaimer

This tool is for educational purposes only. It is not financial advice. All analysis is hypothetical and based on historical data.