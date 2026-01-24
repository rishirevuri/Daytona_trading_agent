# Investment Scorer

## Project Overview

Investment Scorer is an AI-powered real-time stock analysis platform. It provides investment scoring based on a combination of technical (65%) and fundamental (35%) analysis, supplemented by market sentiment and news impact analysis.

**Key Features:**
*   **Real-time Analysis:** Fetches live data via `yfinance`.
*   **Investment Scoring:** 1-100 score with recommendations from STRONG SELL to STRONG BUY.
*   **Technical Analysis:** 15+ indicators (RSI, MACD, Bollinger Bands, Stochastic, etc.).
*   **Fundamental Analysis:** Evaluation of P/E, PEG, margins, growth, and debt.
*   **News & Sentiment:** Sentiment analysis of recent news and broader market fear/greed (VIX).
*   **Voice Summaries:** Integration with ElevenLabs for narrated research briefings.
*   **Stock Screening:** Automated screening of a popular universe of stocks.

**Architecture:**
*   **Backend:** Flask (Python) in `app.py`. Stateless and compute-on-demand.
*   **Frontend:** React SPA (located in `frontend/`, served from `frontend/build/`).

## Building and Running

### Prerequisites
*   Python 3.10+
*   Node.js & npm (for frontend development)

### Backend (Flask)

**Setup & Installation:**
```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python app.py
# Server runs at http://localhost:8080
```

### Frontend (React)

**Setup & Installation:**
```bash
cd frontend
npm install
```

**Development:**
```bash
npm start
# Runs at http://localhost:3000
```

**Production Build:**
```bash
npm run build
# Builds to frontend/build/, which is served by the Flask app
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serves the main SPA |
| `/api/analyze` | POST | Analyze a single stock (body: `{"ticker": "AAPL"}`) |
| `/api/screen` | GET | Screen stocks (query: `filter=strong_buys&limit=20`) |
| `/api/market-sentiment` | GET | Get VIX, treasury yields, and market data |
| `/api/speak` | POST | Text-to-speech via ElevenLabs (body: `{"text": "..."}`) |
| `/health` | GET | Health check |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ELEVENLABS_API_KEY` | No | For text-to-speech feature |
| `ELEVENLABS_VOICE_ID` | No | Voice ID for TTS (default: Adam) |
| `FLASK_ENV` | No | Set to `development` for debug mode |
| `API_PORT` | No | Port to run server (default: 8080) |

## Development Conventions

### Code Style
*   **Python:** Clean, single-file backend logic in `app.py` for core scoring algorithm.
*   **Frontend:** Functional React components with Tailwind CSS for styling.

### Technical Indicators
The platform calculates and weighs:
*   **Momentum:** RSI, MACD, Stochastic, Williams %R, CCI, ROC.
*   **Trend:** SMA (20/50/200), ADX.
*   **Volatility:** Bollinger Bands, ATR.
*   **Volume:** OBV, MFI, VWAP.

### Disclaimer
This tool is for educational purposes only and does not constitute financial advice. All analysis is hypothetical and based on historical data.
