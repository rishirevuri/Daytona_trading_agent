# Investment Scorer

AI-Powered Investment Scoring Application that analyzes stocks and ETFs using technical and fundamental indicators.

## Features

- **Investment Score (1-100)**: Comprehensive scoring based on 15+ technical indicators
- **Technical Analysis**: RSI, MACD, Bollinger Bands, Stochastic, Williams %R, CCI, ADX, MFI, OBV, VWAP
- **Fundamental Analysis**: P/E, PEG, Profit Margins, Revenue Growth, ROE, Debt/Equity
- **Market Sentiment**: VIX, Treasury Yields, S&P 500 trends
- **Stock Screener**: Find strong buys, sells, and short opportunities
- **Price Targets**: Entry, exit, and stop-loss levels
- **Earnings Data**: Historical earnings surprises and analyst targets

## Quick Start (Local)

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python app.py

# Open browser to http://localhost:8080
```

## Daytona Cloud Deployment

This project is configured for [Daytona](https://www.daytona.io/) cloud development environments.

### Prerequisites
- Daytona CLI installed
- Daytona account configured

### Deploy with Daytona

```bash
# Create a new workspace
daytona create https://github.com/YOUR_USERNAME/investment-scorer

# Or from local directory
daytona create .

# The workspace will automatically:
# 1. Set up Python 3.11 environment
# 2. Install all dependencies
# 3. Start the Flask server on port 8080
# 4. Forward ports for browser access
```

### Daytona Configuration

The project includes:
- `.devcontainer/devcontainer.json` - Dev container configuration
- `.daytona/config.yaml` - Daytona workspace settings
- `docker-compose.yml` - Multi-service orchestration
- `Dockerfile` - Production-ready container

## API Endpoints

### Analyze Stock
```bash
POST /api/analyze
Content-Type: application/json
{"ticker": "AAPL"}
```

### Screen Stocks
```bash
GET /api/screen?filter=strong_buys&limit=20
# Filters: all, strong_buys, buys, sells, strong_sells, shorts
```

### Market Sentiment
```bash
GET /api/market-sentiment
```

## Scoring Algorithm

The investment score combines:
- **70% Technical Score** (weighted average of indicators)
- **30% Fundamental Score** (earnings, margins, growth)

### Score Interpretation
| Score | Recommendation | Action |
|-------|---------------|--------|
| 75-100 | STRONG BUY | Long with high confidence |
| 60-74 | BUY | Long with medium confidence |
| 45-59 | HOLD | Wait for clearer signals |
| 30-44 | SELL | Short with medium confidence |
| 1-29 | STRONG SELL | Short with high confidence |

## Technical Indicators Used

| Indicator | Weight | Description |
|-----------|--------|-------------|
| RSI | 10% | Relative Strength Index (14-period) |
| MACD | 10% | Moving Average Convergence Divergence |
| Moving Averages | 12% | SMA 20/50/200, Golden/Death Cross |
| Earnings | 10% | Historical earnings surprises |
| ADX | 8% | Average Directional Index (trend strength) |
| Bollinger Bands | 8% | Price position within bands |
| Stochastic | 8% | Stochastic Oscillator |
| VIX | 8% | Market fear gauge |
| MFI | 6% | Money Flow Index |
| Williams %R | 5% | Overbought/oversold |
| CCI | 5% | Commodity Channel Index |
| OBV | 5% | On-Balance Volume |
| VWAP | 5% | Volume Weighted Average Price |

## New: Market Snapshot Dashboard

The landing page now features a comprehensive Market Snapshot:
- **Market Sentiment Bar**: VIX, Fear/Greed Index, S&P 500 trend, Treasury yields
- **Top BUY Signals**: Stocks with highest investment scores
- **Short Candidates**: Stocks with lowest scores for short opportunities
- **Daily Movers**: Biggest gainers and losers
- **Market News**: Aggregated news with sentiment analysis
- Click any stock to view detailed charts and analysis

### New API Endpoints

```bash
# Market Snapshot (all data in one call)
GET /api/snapshot

# Stock chart and details
GET /api/stock/AAPL/chart

# Stock detail page
GET /stock/AAPL
```

## Install as Native App

Investment Scorer is a Progressive Web App (PWA) that can be installed on any device for a native app experience.

### Mac (Chrome/Edge)
1. Open the app in Chrome or Edge
2. Click the install icon (+) in the address bar
3. Click "Install"

### Windows (Chrome/Edge)
1. Open the app in Chrome or Edge
2. Click the menu button and select "Install Investment Scorer"
3. Click "Install"

### Linux (Chrome)
1. Open the app in Chrome
2. Click the menu button and select "Install Investment Scorer"
3. Click "Install"

### iOS (Safari)
1. Open the app in Safari
2. Tap the Share button
3. Scroll down and tap "Add to Home Screen"
4. Tap "Add"

### Android (Chrome)
1. Open the app in Chrome
2. Tap the menu button
3. Tap "Add to Home Screen" or "Install app"
4. Tap "Install"

## PWA Features

- **Offline Support**: Static assets are cached for offline access
- **Native App Experience**: Runs in standalone mode without browser UI
- **Touch Optimized**: Dark theme UI designed for mobile
- **Real-Time Data**: API calls always fetch fresh market data

## Disclaimer

This tool is for educational purposes only. The investment score and recommendations are based on technical and fundamental analysis and should not be considered financial advice. Always do your own research and consult with a qualified financial advisor before making investment decisions.

## License

MIT
