# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Investment Scorer is an AI-powered real-time stock analysis platform. It provides investment scoring based on technical and fundamental indicators, with market sentiment analysis and stock screening capabilities.

**Key principle**: Real-time analysis, stateless architecture, paper trading only.

## Project Structure

```
/
├── app.py                    # Flask backend (core logic - all analysis endpoints)
├── requirements.txt          # Python dependencies
├── Dockerfile               # Container configuration
├── docker-compose.yml       # Service orchestration
├── .daytona/
│   └── config.yaml          # Daytona cloud workspace config
├── .devcontainer/
│   └── devcontainer.json    # Dev container configuration
├── templates/
│   └── index.html           # Main SPA template
├── static/                  # Static assets
└── frontend/                # React frontend (optional)
    ├── package.json
    └── src/
```

## Common Commands

### Backend Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the Flask server
python app.py
# Server starts on http://localhost:8080

# Run with environment variable for ElevenLabs (optional)
ELEVENLABS_API_KEY=your_key python app.py
```

### Docker Development

```bash
# Build and run with Docker Compose
docker-compose up --build

# Run in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Frontend Development (if using React)

```bash
cd frontend
npm install
npm start
# Development server on http://localhost:3000

npm run build
# Builds to frontend/build/ for production
```

### Daytona Deployment

```bash
# Create a new Daytona workspace
daytona create .

# Or from GitHub
daytona create https://github.com/YOUR_USERNAME/Daytona_trading_agent
```

## Architecture

### Flask Backend (`app.py`)

The entire backend is in a single `app.py` file with these components:

- **NewsAnalyzer class** - Fetches and analyzes stock news sentiment
- **Investment scoring algorithm** - Combines technical (70%) and fundamental (30%) analysis
- **Stock screener** - Scans universe of stocks for buy/sell signals

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serves the main SPA |
| `/api/analyze` | POST | Analyze a single stock (body: `{"ticker": "AAPL"}`) |
| `/api/screen` | GET | Screen stocks (query: `filter=strong_buys&limit=20`) |
| `/api/market-sentiment` | GET | Get VIX, treasury yields, market data |
| `/api/news/<ticker>` | GET | Get news for a specific ticker |
| `/api/speak` | POST | Text-to-speech via ElevenLabs (optional) |
| `/health` | GET | Health check endpoint |

### Technical Indicators Used

The scoring algorithm analyzes 15+ indicators:
- **RSI** - Relative Strength Index (14-period)
- **MACD** - Moving Average Convergence Divergence
- **Moving Averages** - SMA 20/50/200, Golden/Death Cross
- **Bollinger Bands** - Price position within bands
- **Stochastic** - Stochastic Oscillator
- **Williams %R** - Overbought/oversold indicator
- **CCI** - Commodity Channel Index
- **ADX** - Average Directional Index (trend strength)
- **MFI** - Money Flow Index
- **OBV** - On-Balance Volume
- **VWAP** - Volume Weighted Average Price

### Score Interpretation

| Score | Recommendation | Action |
|-------|---------------|--------|
| 75-100 | STRONG BUY | Long with high confidence |
| 60-74 | BUY | Long with medium confidence |
| 45-59 | HOLD | Wait for clearer signals |
| 30-44 | SELL | Short with medium confidence |
| 1-29 | STRONG SELL | Short with high confidence |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ELEVENLABS_API_KEY` | No | For text-to-speech feature |
| `ELEVENLABS_VOICE_ID` | No | Voice ID for TTS (default: Adam) |
| `FLASK_ENV` | No | Set to `development` for debug mode |
| `API_PORT` | No | Port to run server (default: 8080) |

## Data Sources

All data is fetched in real-time via `yfinance`:
- Historical price data for technical analysis
- Fundamental data (P/E, margins, growth rates)
- News and analyst recommendations
- Earnings calendar and surprises

## Dependencies

Core Python packages:
- `flask` - Web framework
- `flask-cors` - CORS support
- `yfinance` - Yahoo Finance data
- `pandas` - Data manipulation
- `numpy` - Numerical computing
- `requests` - HTTP client

## Stateless Architecture

The application is completely stateless:
- No database required
- All analysis is computed on-demand
- Results are not persisted
- Each request is independent

## Disclaimer

This tool is for educational purposes only. Investment scores and recommendations are based on technical and fundamental analysis and should not be considered financial advice.
