from flask import Flask, render_template, jsonify, request, send_from_directory, Response
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import requests
import re
from collections import defaultdict

app = Flask(__name__, static_folder='frontend/build', static_url_path='')
CORS(app)

# ElevenLabs Configuration
ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY', '')
ELEVENLABS_VOICE_ID = os.environ.get('ELEVENLABS_VOICE_ID', 'pNInz6obpgDQGcFmaJgB')  # Adam voice

# Sector mappings for news impact analysis
SECTOR_KEYWORDS = {
    'defense': ['defense', 'military', 'war', 'weapons', 'army', 'navy', 'pentagon', 'missile', 'drone', 'nato', 'conflict', 'troops'],
    'energy': ['oil', 'gas', 'opec', 'crude', 'petroleum', 'energy', 'drilling', 'pipeline', 'refinery', 'fuel'],
    'technology': ['tech', 'ai', 'artificial intelligence', 'semiconductor', 'chip', 'software', 'cloud', 'data center', 'cybersecurity'],
    'finance': ['fed', 'federal reserve', 'interest rate', 'banking', 'inflation', 'recession', 'gdp', 'unemployment', 'treasury'],
    'healthcare': ['fda', 'drug', 'vaccine', 'healthcare', 'hospital', 'pharma', 'biotech', 'medical', 'treatment'],
    'consumer': ['retail', 'consumer', 'spending', 'shopping', 'walmart', 'amazon', 'e-commerce', 'holiday sales'],
    'crypto': ['bitcoin', 'crypto', 'ethereum', 'blockchain', 'digital currency', 'sec crypto'],
    'china': ['china', 'tariff', 'trade war', 'beijing', 'chinese', 'taiwan'],
    'geopolitical': ['russia', 'ukraine', 'iran', 'middle east', 'sanctions', 'embargo', 'north korea']
}

# Sector to ticker mappings
SECTOR_TICKERS = {
    'defense': ['LMT', 'RTX', 'NOC', 'GD', 'BA', 'HII'],
    'energy': ['XOM', 'CVX', 'COP', 'SLB', 'EOG', 'OXY', 'XLE'],
    'technology': ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'META', 'AMD', 'INTC', 'XLK'],
    'finance': ['JPM', 'BAC', 'WFC', 'GS', 'MS', 'XLF'],
    'healthcare': ['JNJ', 'UNH', 'PFE', 'ABBV', 'MRK', 'LLY', 'XLV'],
    'consumer': ['WMT', 'AMZN', 'HD', 'MCD', 'NKE', 'SBUX', 'XLY'],
    'crypto': ['COIN', 'MARA', 'RIOT', 'MSTR'],
}

# Popular stocks/ETFs for screening
SCREENING_UNIVERSE = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'AMD', 'INTC', 'CRM',
    'ORCL', 'ADBE', 'NFLX', 'PYPL', 'SQ', 'SHOP', 'UBER', 'ABNB', 'SNOW', 'PLTR',
    'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'AXP', 'V', 'MA', 'BLK',
    'JNJ', 'UNH', 'PFE', 'ABBV', 'MRK', 'LLY', 'TMO', 'ABT', 'BMY', 'AMGN',
    'WMT', 'HD', 'MCD', 'NKE', 'SBUX', 'TGT', 'COST', 'LOW', 'DIS', 'CMCSA',
    'CAT', 'BA', 'GE', 'MMM', 'HON', 'UPS', 'RTX', 'LMT', 'DE', 'UNP',
    'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'PXD', 'MPC', 'VLO', 'PSX', 'OXY',
    'SPY', 'QQQ', 'IWM', 'DIA', 'VTI', 'VOO', 'ARKK', 'XLF', 'XLE', 'XLK',
    'GLD', 'SLV', 'TLT', 'HYG', 'EEM', 'VWO', 'IEMG', 'VEA', 'EFA', 'SOXL'
]


class NewsAnalyzer:
    """Analyzes news for market sentiment and sector impact"""

    @staticmethod
    def fetch_stock_news(ticker):
        """Fetch news for a specific ticker using yfinance"""
        news_items = []
        try:
            stock = yf.Ticker(ticker)
            news = stock.news
            if news:
                for item in news[:10]:
                    news_items.append({
                        'title': item.get('title', ''),
                        'publisher': item.get('publisher', ''),
                        'link': item.get('link', ''),
                        'published': datetime.fromtimestamp(item.get('providerPublishTime', 0)).strftime('%Y-%m-%d %H:%M'),
                        'type': item.get('type', 'STORY'),
                        'thumbnail': item.get('thumbnail', {}).get('resolutions', [{}])[0].get('url', '') if item.get('thumbnail') else ''
                    })
        except Exception as e:
            pass
        return news_items

    @staticmethod
    def analyze_sentiment(text):
        """Simple sentiment analysis based on keywords"""
        positive_words = [
            'surge', 'soar', 'jump', 'gain', 'rally', 'boom', 'bullish', 'upgrade',
            'beat', 'exceed', 'strong', 'growth', 'profit', 'success', 'breakthrough',
            'record', 'high', 'buy', 'outperform', 'optimistic', 'positive', 'up'
        ]
        negative_words = [
            'crash', 'plunge', 'drop', 'fall', 'decline', 'bearish', 'downgrade',
            'miss', 'weak', 'loss', 'fail', 'concern', 'fear', 'sell', 'cut',
            'warning', 'risk', 'down', 'low', 'pessimistic', 'negative', 'trouble'
        ]

        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)

        if positive_count > negative_count:
            return 'positive', positive_count - negative_count
        elif negative_count > positive_count:
            return 'negative', negative_count - positive_count
        return 'neutral', 0

    @staticmethod
    def analyze_news_impact(news_items, ticker, sector):
        """Analyze how news impacts the stock"""
        impacts = []
        overall_sentiment = 0
        sector_boost = 0

        for news in news_items:
            title = news.get('title', '')
            sentiment, strength = NewsAnalyzer.analyze_sentiment(title)

            # Check for sector-specific keywords
            title_lower = title.lower()
            sector_impacts = []

            for sec, keywords in SECTOR_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in title_lower:
                        sector_impacts.append(sec)
                        break

            # Determine impact
            impact = {
                'headline': title,
                'sentiment': sentiment,
                'strength': strength,
                'sectors_affected': list(set(sector_impacts)),
                'published': news.get('published', ''),
                'source': news.get('publisher', '')
            }

            # Calculate sentiment score
            if sentiment == 'positive':
                overall_sentiment += strength
            elif sentiment == 'negative':
                overall_sentiment -= strength

            # Check if news boosts this sector
            ticker_sector = sector.lower() if sector else ''
            for sec in sector_impacts:
                if sec in ticker_sector or ticker in SECTOR_TICKERS.get(sec, []):
                    if sentiment == 'positive':
                        sector_boost += 5
                    elif sentiment == 'negative':
                        sector_boost -= 5

            impacts.append(impact)

        return {
            'news_items': impacts,
            'overall_sentiment': overall_sentiment,
            'sector_boost': sector_boost,
            'sentiment_score': max(-20, min(20, overall_sentiment * 2))
        }


class TechnicalAnalyzer:
    """Enhanced technical analysis with more accurate scoring"""

    @staticmethod
    def calculate_rsi(prices, period=14):
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    @staticmethod
    def calculate_macd(prices, fast=12, slow=26, signal=9):
        exp_fast = prices.ewm(span=fast, adjust=False).mean()
        exp_slow = prices.ewm(span=slow, adjust=False).mean()
        macd = exp_fast - exp_slow
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        histogram = macd - signal_line
        return macd, signal_line, histogram

    @staticmethod
    def calculate_bollinger_bands(prices, period=20, std_dev=2):
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        bandwidth = (upper - lower) / sma * 100
        percent_b = (prices - lower) / (upper - lower)
        return upper, sma, lower, bandwidth, percent_b

    @staticmethod
    def calculate_stochastic(high, low, close, k_period=14, d_period=3):
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        k = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        d = k.rolling(window=d_period).mean()
        return k, d

    @staticmethod
    def calculate_atr(high, low, close, period=14):
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr

    @staticmethod
    def calculate_adx(high, low, close, period=14):
        plus_dm = high.diff()
        minus_dm = low.diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0

        tr = TechnicalAnalyzer.calculate_atr(high, low, close, 1) * 1
        atr = tr.rolling(window=period).mean()

        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (abs(minus_dm).rolling(window=period).mean() / atr)

        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()
        return adx, plus_di, minus_di

    @staticmethod
    def calculate_obv(close, volume):
        obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
        obv_ema = obv.ewm(span=20, adjust=False).mean()
        return obv, obv_ema

    @staticmethod
    def calculate_mfi(high, low, close, volume, period=14):
        typical_price = (high + low + close) / 3
        money_flow = typical_price * volume

        delta = typical_price.diff()
        positive_flow = money_flow.where(delta > 0, 0).rolling(window=period).sum()
        negative_flow = money_flow.where(delta < 0, 0).rolling(window=period).sum()

        mfi = 100 - (100 / (1 + positive_flow / negative_flow))
        return mfi

    @staticmethod
    def calculate_williams_r(high, low, close, period=14):
        highest_high = high.rolling(window=period).max()
        lowest_low = low.rolling(window=period).min()
        wr = -100 * ((highest_high - close) / (highest_high - lowest_low))
        return wr

    @staticmethod
    def calculate_cci(high, low, close, period=20):
        tp = (high + low + close) / 3
        sma_tp = tp.rolling(window=period).mean()
        mad = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())
        cci = (tp - sma_tp) / (0.015 * mad)
        return cci

    @staticmethod
    def calculate_roc(prices, period=12):
        roc = ((prices - prices.shift(period)) / prices.shift(period)) * 100
        return roc

    @staticmethod
    def calculate_vwap(high, low, close, volume):
        typical_price = (high + low + close) / 3
        vwap = (typical_price * volume).cumsum() / volume.cumsum()
        return vwap


def get_vix():
    """Get current VIX value"""
    try:
        vix = yf.Ticker("^VIX")
        vix_data = vix.history(period="5d")
        if not vix_data.empty:
            return vix_data['Close'].iloc[-1]
    except:
        pass
    return 20


def get_market_sentiment():
    """Get broader market sentiment indicators"""
    sentiment = {}

    try:
        vix = yf.Ticker("^VIX")
        vix_data = vix.history(period="1mo")
        if not vix_data.empty:
            sentiment['vix'] = round(vix_data['Close'].iloc[-1], 2)
            sentiment['vix_change'] = round(vix_data['Close'].pct_change().iloc[-1] * 100, 2)
            sentiment['vix_20d_avg'] = round(vix_data['Close'].tail(20).mean(), 2)

            # VIX interpretation
            if sentiment['vix'] < 15:
                sentiment['vix_signal'] = 'LOW FEAR - Complacency, potential correction ahead'
            elif sentiment['vix'] < 20:
                sentiment['vix_signal'] = 'NORMAL - Market stable'
            elif sentiment['vix'] < 25:
                sentiment['vix_signal'] = 'ELEVATED - Increased uncertainty'
            elif sentiment['vix'] < 30:
                sentiment['vix_signal'] = 'HIGH FEAR - Significant market stress'
            else:
                sentiment['vix_signal'] = 'EXTREME FEAR - Panic selling, potential buying opportunity'
    except:
        sentiment['vix'] = 20
        sentiment['vix_change'] = 0
        sentiment['vix_signal'] = 'NORMAL'

    try:
        tny = yf.Ticker("^TNX")
        tny_data = tny.history(period="5d")
        if not tny_data.empty:
            sentiment['treasury_10y'] = round(tny_data['Close'].iloc[-1], 2)
    except:
        sentiment['treasury_10y'] = 4.0

    try:
        spy = yf.Ticker("SPY")
        spy_data = spy.history(period="1mo")
        if not spy_data.empty:
            sentiment['sp500_monthly_change'] = round(
                (spy_data['Close'].iloc[-1] / spy_data['Close'].iloc[0] - 1) * 100, 2
            )
            sentiment['sp500_current'] = round(spy_data['Close'].iloc[-1], 2)
    except:
        sentiment['sp500_monthly_change'] = 0

    # Fear & Greed approximation based on VIX and market momentum
    try:
        vix_score = 100 - min(sentiment.get('vix', 20) * 2.5, 100)
        momentum_score = 50 + sentiment.get('sp500_monthly_change', 0) * 5
        fear_greed = (vix_score * 0.6 + momentum_score * 0.4)
        sentiment['fear_greed_index'] = round(max(0, min(100, fear_greed)), 0)

        if sentiment['fear_greed_index'] < 25:
            sentiment['fear_greed_signal'] = 'EXTREME FEAR'
        elif sentiment['fear_greed_index'] < 45:
            sentiment['fear_greed_signal'] = 'FEAR'
        elif sentiment['fear_greed_index'] < 55:
            sentiment['fear_greed_signal'] = 'NEUTRAL'
        elif sentiment['fear_greed_index'] < 75:
            sentiment['fear_greed_signal'] = 'GREED'
        else:
            sentiment['fear_greed_signal'] = 'EXTREME GREED'
    except:
        sentiment['fear_greed_index'] = 50
        sentiment['fear_greed_signal'] = 'NEUTRAL'

    return sentiment


def get_consumer_sentiment():
    """Get consumer sentiment indicators"""
    # Note: Real implementation would use FRED API or similar
    # This uses proxy indicators from market data
    consumer_data = {
        'consumer_confidence': None,
        'retail_sentiment': None,
        'unemployment_trend': None
    }

    try:
        # Use XLY (Consumer Discretionary) as proxy for consumer confidence
        xly = yf.Ticker("XLY")
        xly_data = xly.history(period="1mo")
        if not xly_data.empty:
            change = (xly_data['Close'].iloc[-1] / xly_data['Close'].iloc[0] - 1) * 100
            consumer_data['retail_sentiment'] = round(change, 2)

            if change > 5:
                consumer_data['consumer_signal'] = 'STRONG - Consumer spending robust'
            elif change > 0:
                consumer_data['consumer_signal'] = 'POSITIVE - Moderate consumer confidence'
            elif change > -5:
                consumer_data['consumer_signal'] = 'WEAK - Consumer caution'
            else:
                consumer_data['consumer_signal'] = 'NEGATIVE - Consumer pullback'
    except:
        consumer_data['consumer_signal'] = 'NEUTRAL'

    return consumer_data


def get_earnings_data(ticker):
    """Get earnings and fundamental data"""
    earnings_data = {
        'earnings_date': None,
        'earnings_history': [],
        'earnings_surprise_avg': 0,
        'recommendation_trend': {},
        'analyst_price_targets': {}
    }

    try:
        stock = yf.Ticker(ticker)

        try:
            calendar = stock.calendar
            if calendar is not None and not calendar.empty:
                if 'Earnings Date' in calendar.index:
                    earnings_data['earnings_date'] = str(calendar.loc['Earnings Date'].iloc[0])
        except:
            pass

        try:
            earnings_hist = stock.earnings_history
            if earnings_hist is not None and not earnings_hist.empty:
                recent_earnings = earnings_hist.tail(4)
                for _, row in recent_earnings.iterrows():
                    earnings_data['earnings_history'].append({
                        'date': str(row.name) if hasattr(row, 'name') else 'N/A',
                        'actual': row.get('epsActual', 0),
                        'estimate': row.get('epsEstimate', 0),
                        'surprise': row.get('surprisePercent', 0)
                    })

                surprises = [e.get('surprise', 0) for e in earnings_data['earnings_history'] if e.get('surprise')]
                if surprises:
                    earnings_data['earnings_surprise_avg'] = round(np.mean(surprises), 2)
        except:
            pass

        try:
            info = stock.info
            earnings_data['analyst_price_targets'] = {
                'target_high': info.get('targetHighPrice', 0),
                'target_low': info.get('targetLowPrice', 0),
                'target_mean': info.get('targetMeanPrice', 0),
                'target_median': info.get('targetMedianPrice', 0),
                'num_analysts': info.get('numberOfAnalystOpinions', 0)
            }
        except:
            pass

    except Exception as e:
        pass

    return earnings_data


def calculate_fundamental_score(info):
    """Calculate score based on fundamental metrics"""
    score = 50
    reasons = []

    pe = info.get('trailingPE')
    forward_pe = info.get('forwardPE')
    if pe and forward_pe:
        if forward_pe < pe:
            score += 5
            reasons.append({
                'factor': 'Forward P/E',
                'impact': 'POSITIVE',
                'detail': f'Forward P/E ({forward_pe:.1f}) lower than trailing ({pe:.1f}) - earnings growth expected',
                'weight': '+5'
            })
        if pe < 15:
            score += 5
            reasons.append({
                'factor': 'P/E Ratio',
                'impact': 'POSITIVE',
                'detail': f'Low P/E ratio ({pe:.1f}) - potentially undervalued',
                'weight': '+5'
            })
        elif pe > 40:
            score -= 5
            reasons.append({
                'factor': 'P/E Ratio',
                'impact': 'NEGATIVE',
                'detail': f'High P/E ratio ({pe:.1f}) - potentially overvalued',
                'weight': '-5'
            })

    peg = info.get('pegRatio')
    if peg:
        if peg < 1:
            score += 8
            reasons.append({
                'factor': 'PEG Ratio',
                'impact': 'POSITIVE',
                'detail': f'PEG ratio ({peg:.2f}) < 1 - growth at reasonable price',
                'weight': '+8'
            })
        elif peg > 2:
            score -= 5
            reasons.append({
                'factor': 'PEG Ratio',
                'impact': 'NEGATIVE',
                'detail': f'PEG ratio ({peg:.2f}) > 2 - expensive relative to growth',
                'weight': '-5'
            })

    profit_margin = info.get('profitMargins')
    if profit_margin:
        if profit_margin > 0.2:
            score += 5
            reasons.append({
                'factor': 'Profit Margin',
                'impact': 'POSITIVE',
                'detail': f'Strong profit margin ({profit_margin*100:.1f}%)',
                'weight': '+5'
            })
        elif profit_margin < 0:
            score -= 8
            reasons.append({
                'factor': 'Profit Margin',
                'impact': 'NEGATIVE',
                'detail': f'Negative profit margin ({profit_margin*100:.1f}%)',
                'weight': '-8'
            })

    revenue_growth = info.get('revenueGrowth')
    if revenue_growth:
        if revenue_growth > 0.2:
            score += 7
            reasons.append({
                'factor': 'Revenue Growth',
                'impact': 'POSITIVE',
                'detail': f'Strong revenue growth ({revenue_growth*100:.1f}%)',
                'weight': '+7'
            })
        elif revenue_growth < 0:
            score -= 5
            reasons.append({
                'factor': 'Revenue Growth',
                'impact': 'NEGATIVE',
                'detail': f'Revenue declining ({revenue_growth*100:.1f}%)',
                'weight': '-5'
            })

    debt_to_equity = info.get('debtToEquity')
    if debt_to_equity:
        if debt_to_equity < 50:
            score += 3
            reasons.append({
                'factor': 'Debt/Equity',
                'impact': 'POSITIVE',
                'detail': f'Low debt-to-equity ({debt_to_equity:.1f})',
                'weight': '+3'
            })
        elif debt_to_equity > 200:
            score -= 5
            reasons.append({
                'factor': 'Debt/Equity',
                'impact': 'NEGATIVE',
                'detail': f'High debt-to-equity ({debt_to_equity:.1f})',
                'weight': '-5'
            })

    roe = info.get('returnOnEquity')
    if roe:
        if roe > 0.2:
            score += 5
            reasons.append({
                'factor': 'ROE',
                'impact': 'POSITIVE',
                'detail': f'Strong ROE ({roe*100:.1f}%)',
                'weight': '+5'
            })
        elif roe < 0.05:
            score -= 3
            reasons.append({
                'factor': 'ROE',
                'impact': 'NEGATIVE',
                'detail': f'Weak ROE ({roe*100:.1f}%)',
                'weight': '-3'
            })

    fcf = info.get('freeCashflow')
    market_cap = info.get('marketCap')
    if fcf and market_cap and market_cap > 0:
        fcf_yield = fcf / market_cap
        if fcf_yield > 0.05:
            score += 5
            reasons.append({
                'factor': 'FCF Yield',
                'impact': 'POSITIVE',
                'detail': f'Strong FCF yield ({fcf_yield*100:.1f}%)',
                'weight': '+5'
            })

    return max(0, min(100, score)), reasons


def calculate_technical_score(hist, current_price):
    """Calculate comprehensive technical score"""
    close = hist['Close']
    high = hist['High']
    low = hist['Low']
    volume = hist['Volume']

    ta = TechnicalAnalyzer()
    scores = {}
    indicators = {}
    signals = []
    evidence = []

    # RSI
    rsi = ta.calculate_rsi(close)
    rsi_val = rsi.iloc[-1]
    indicators['RSI'] = round(rsi_val, 2)

    if rsi_val < 30:
        scores['rsi'] = 85
        signals.append({'indicator': 'RSI', 'signal': 'BULLISH', 'reason': f'Oversold at {rsi_val:.1f}'})
        evidence.append({
            'factor': 'RSI (Relative Strength Index)',
            'value': f'{rsi_val:.1f}',
            'impact': 'BULLISH',
            'detail': f'RSI at {rsi_val:.1f} indicates oversold conditions. Historically, RSI below 30 suggests the stock may be due for a bounce.',
            'weight': '+35 points',
            'category': 'technical'
        })
    elif rsi_val > 70:
        scores['rsi'] = 15
        signals.append({'indicator': 'RSI', 'signal': 'BEARISH', 'reason': f'Overbought at {rsi_val:.1f}'})
        evidence.append({
            'factor': 'RSI (Relative Strength Index)',
            'value': f'{rsi_val:.1f}',
            'impact': 'BEARISH',
            'detail': f'RSI at {rsi_val:.1f} indicates overbought conditions. The stock may be due for a pullback.',
            'weight': '-35 points',
            'category': 'technical'
        })
    else:
        scores['rsi'] = 50
        signals.append({'indicator': 'RSI', 'signal': 'NEUTRAL', 'reason': f'Neutral at {rsi_val:.1f}'})

    # MACD
    macd, signal_line, histogram = ta.calculate_macd(close)
    macd_val = macd.iloc[-1]
    hist_val = histogram.iloc[-1]
    indicators['MACD'] = round(macd_val, 4)
    indicators['MACD_Signal'] = round(signal_line.iloc[-1], 4)
    indicators['MACD_Histogram'] = round(hist_val, 4)

    prev_hist = histogram.iloc[-2] if len(histogram) > 1 else 0
    if hist_val > 0 and prev_hist <= 0:
        scores['macd'] = 80
        signals.append({'indicator': 'MACD', 'signal': 'BULLISH', 'reason': 'Bullish crossover detected'})
        evidence.append({
            'factor': 'MACD Crossover',
            'value': 'Bullish',
            'impact': 'BULLISH',
            'detail': 'MACD line crossed above signal line, indicating building upward momentum.',
            'weight': '+30 points',
            'category': 'technical'
        })
    elif hist_val < 0 and prev_hist >= 0:
        scores['macd'] = 20
        signals.append({'indicator': 'MACD', 'signal': 'BEARISH', 'reason': 'Bearish crossover detected'})
        evidence.append({
            'factor': 'MACD Crossover',
            'value': 'Bearish',
            'impact': 'BEARISH',
            'detail': 'MACD line crossed below signal line, indicating building downward momentum.',
            'weight': '-30 points',
            'category': 'technical'
        })
    elif hist_val > 0:
        scores['macd'] = 60 + min(hist_val / current_price * 3000, 20)
        signals.append({'indicator': 'MACD', 'signal': 'BULLISH', 'reason': 'Positive momentum'})
    else:
        scores['macd'] = 40 + max(hist_val / current_price * 3000, -20)
        signals.append({'indicator': 'MACD', 'signal': 'BEARISH', 'reason': 'Negative momentum'})

    # Bollinger Bands
    bb_upper, bb_mid, bb_lower, bandwidth, percent_b = ta.calculate_bollinger_bands(close)
    indicators['BB_Upper'] = round(bb_upper.iloc[-1], 2)
    indicators['BB_Middle'] = round(bb_mid.iloc[-1], 2)
    indicators['BB_Lower'] = round(bb_lower.iloc[-1], 2)
    indicators['BB_PercentB'] = round(percent_b.iloc[-1] * 100, 2)

    pb_val = percent_b.iloc[-1]
    if pb_val < 0:
        scores['bollinger'] = 90
        signals.append({'indicator': 'Bollinger Bands', 'signal': 'BULLISH', 'reason': 'Price below lower band'})
        evidence.append({
            'factor': 'Bollinger Bands',
            'value': f'Below lower band',
            'impact': 'BULLISH',
            'detail': f'Price broke below lower Bollinger Band - extreme oversold condition, potential mean reversion expected.',
            'weight': '+40 points',
            'category': 'technical'
        })
    elif pb_val < 0.2:
        scores['bollinger'] = 75
        signals.append({'indicator': 'Bollinger Bands', 'signal': 'BULLISH', 'reason': 'Price near lower band'})
    elif pb_val > 1:
        scores['bollinger'] = 10
        signals.append({'indicator': 'Bollinger Bands', 'signal': 'BEARISH', 'reason': 'Price above upper band'})
        evidence.append({
            'factor': 'Bollinger Bands',
            'value': f'Above upper band',
            'impact': 'BEARISH',
            'detail': f'Price broke above upper Bollinger Band - extreme overbought condition, potential pullback expected.',
            'weight': '-40 points',
            'category': 'technical'
        })
    elif pb_val > 0.8:
        scores['bollinger'] = 25
        signals.append({'indicator': 'Bollinger Bands', 'signal': 'BEARISH', 'reason': 'Price near upper band'})
    else:
        scores['bollinger'] = 50
        signals.append({'indicator': 'Bollinger Bands', 'signal': 'NEUTRAL', 'reason': 'Price within bands'})

    # Stochastic
    stoch_k, stoch_d = ta.calculate_stochastic(high, low, close)
    k_val = stoch_k.iloc[-1]
    d_val = stoch_d.iloc[-1]
    indicators['Stochastic_K'] = round(k_val, 2)
    indicators['Stochastic_D'] = round(d_val, 2)

    if k_val < 20:
        scores['stochastic'] = 80
        signals.append({'indicator': 'Stochastic', 'signal': 'BULLISH', 'reason': f'Oversold at {k_val:.1f}'})
    elif k_val > 80:
        scores['stochastic'] = 20
        signals.append({'indicator': 'Stochastic', 'signal': 'BEARISH', 'reason': f'Overbought at {k_val:.1f}'})
    else:
        scores['stochastic'] = 50

    # Williams %R
    williams_r = ta.calculate_williams_r(high, low, close)
    wr_val = williams_r.iloc[-1]
    indicators['Williams_R'] = round(wr_val, 2)

    if wr_val < -80:
        scores['williams_r'] = 80
    elif wr_val > -20:
        scores['williams_r'] = 20
    else:
        scores['williams_r'] = 50 - wr_val * 0.4

    # CCI
    cci = ta.calculate_cci(high, low, close)
    cci_val = cci.iloc[-1]
    indicators['CCI'] = round(cci_val, 2)

    if cci_val < -200:
        scores['cci'] = 90
    elif cci_val < -100:
        scores['cci'] = 75
    elif cci_val > 200:
        scores['cci'] = 10
    elif cci_val > 100:
        scores['cci'] = 25
    else:
        scores['cci'] = 50 - cci_val * 0.15

    # ADX
    adx, plus_di, minus_di = ta.calculate_adx(high, low, close)
    adx_val = adx.iloc[-1] if not pd.isna(adx.iloc[-1]) else 20
    indicators['ADX'] = round(adx_val, 2)

    if adx_val > 25:
        if plus_di.iloc[-1] > minus_di.iloc[-1]:
            scores['adx'] = 70
            signals.append({'indicator': 'ADX', 'signal': 'BULLISH', 'reason': f'Strong uptrend (ADX: {adx_val:.1f})'})
            evidence.append({
                'factor': 'ADX Trend Strength',
                'value': f'{adx_val:.1f}',
                'impact': 'BULLISH',
                'detail': f'ADX at {adx_val:.1f} with +DI > -DI indicates a strong uptrend is in place.',
                'weight': '+20 points',
                'category': 'technical'
            })
        else:
            scores['adx'] = 30
            signals.append({'indicator': 'ADX', 'signal': 'BEARISH', 'reason': f'Strong downtrend (ADX: {adx_val:.1f})'})
            evidence.append({
                'factor': 'ADX Trend Strength',
                'value': f'{adx_val:.1f}',
                'impact': 'BEARISH',
                'detail': f'ADX at {adx_val:.1f} with -DI > +DI indicates a strong downtrend is in place.',
                'weight': '-20 points',
                'category': 'technical'
            })
    else:
        scores['adx'] = 50
        signals.append({'indicator': 'ADX', 'signal': 'NEUTRAL', 'reason': f'Weak trend (ADX: {adx_val:.1f})'})

    # MFI
    mfi = ta.calculate_mfi(high, low, close, volume)
    mfi_val = mfi.iloc[-1]
    indicators['MFI'] = round(mfi_val, 2)

    if mfi_val < 20:
        scores['mfi'] = 80
    elif mfi_val > 80:
        scores['mfi'] = 20
    else:
        scores['mfi'] = 50

    # OBV
    obv, obv_ema = ta.calculate_obv(close, volume)
    if obv.iloc[-1] > obv_ema.iloc[-1]:
        scores['obv'] = 65
        signals.append({'indicator': 'OBV', 'signal': 'BULLISH', 'reason': 'Volume confirming price action'})
    else:
        scores['obv'] = 35
        signals.append({'indicator': 'OBV', 'signal': 'BEARISH', 'reason': 'Volume diverging from price'})

    # Moving Averages
    sma_20 = close.rolling(window=20).mean().iloc[-1]
    sma_50 = close.rolling(window=50).mean().iloc[-1]
    sma_200 = close.rolling(window=200).mean().iloc[-1] if len(close) >= 200 else close.mean()

    indicators['SMA_20'] = round(sma_20, 2)
    indicators['SMA_50'] = round(sma_50, 2)
    indicators['SMA_200'] = round(sma_200, 2)

    ma_score = 50
    ma_signals = []

    if current_price > sma_20:
        ma_score += 8
        ma_signals.append("Above SMA20")
    else:
        ma_score -= 8
        ma_signals.append("Below SMA20")

    if current_price > sma_50:
        ma_score += 10
        ma_signals.append("Above SMA50")
    else:
        ma_score -= 10
        ma_signals.append("Below SMA50")

    if current_price > sma_200:
        ma_score += 15
        ma_signals.append("Above SMA200")
        evidence.append({
            'factor': 'Moving Average (200-day)',
            'value': f'${sma_200:.2f}',
            'impact': 'BULLISH',
            'detail': f'Price (${current_price:.2f}) is above the 200-day SMA (${sma_200:.2f}), indicating long-term uptrend.',
            'weight': '+15 points',
            'category': 'technical'
        })
    else:
        ma_score -= 15
        ma_signals.append("Below SMA200")
        evidence.append({
            'factor': 'Moving Average (200-day)',
            'value': f'${sma_200:.2f}',
            'impact': 'BEARISH',
            'detail': f'Price (${current_price:.2f}) is below the 200-day SMA (${sma_200:.2f}), indicating long-term downtrend.',
            'weight': '-15 points',
            'category': 'technical'
        })

    scores['moving_avg'] = max(0, min(100, ma_score))
    signals.append({'indicator': 'Moving Averages', 'signal': 'BULLISH' if ma_score > 50 else 'BEARISH' if ma_score < 50 else 'NEUTRAL', 'reason': ', '.join(ma_signals)})

    # ATR
    atr = ta.calculate_atr(high, low, close)
    atr_val = atr.iloc[-1]
    indicators['ATR'] = round(atr_val, 2)
    indicators['ATR_Percent'] = round(atr_val / current_price * 100, 2)

    # ROC
    roc = ta.calculate_roc(close)
    indicators['ROC'] = round(roc.iloc[-1], 2)

    # VWAP
    vwap = ta.calculate_vwap(high, low, close, volume)
    vwap_val = vwap.iloc[-1]
    indicators['VWAP'] = round(vwap_val, 2)

    if current_price > vwap_val:
        scores['vwap'] = 60
    else:
        scores['vwap'] = 40

    return scores, indicators, signals, evidence


def calculate_price_targets(current_price, atr, rsi, score, support_resistance):
    """Calculate price targets based on technical analysis"""
    risk_mult = 2.0
    reward_mult = 3.0

    confidence = abs(score - 50) / 50
    if confidence > 0.4:
        reward_mult = 3.5

    long_stop = current_price - (atr * risk_mult)
    long_target = current_price + (atr * reward_mult)

    short_stop = current_price + (atr * risk_mult)
    short_target = current_price - (atr * reward_mult)

    if rsi < 30:
        long_target *= 1.1
    elif rsi > 70:
        short_target *= 0.9

    return {
        'long_entry': round(current_price, 2),
        'long_stop_loss': round(long_stop, 2),
        'long_target_1': round(current_price + atr * 1.5, 2),
        'long_target_2': round(current_price + atr * 2.5, 2),
        'long_target_3': round(long_target, 2),
        'short_entry': round(current_price, 2),
        'short_stop_loss': round(short_stop, 2),
        'short_target_1': round(current_price - atr * 1.5, 2),
        'short_target_2': round(current_price - atr * 2.5, 2),
        'short_target_3': round(short_target, 2),
        'risk_reward_ratio': round(reward_mult / risk_mult, 2)
    }


def generate_summary(data):
    """Generate a concise summary for voice narration"""
    ticker = data['ticker']
    company = data['company_name']
    score = data['score']
    rec = data['recommendation']
    price = data['current_price']
    tech_score = data['technical_score']
    fund_score = data['fundamental_score']

    # Determine the tone
    if score >= 70:
        tone = "bullish"
        action = "strong buy opportunity"
    elif score >= 55:
        tone = "positive"
        action = "buying opportunity"
    elif score >= 45:
        tone = "neutral"
        action = "hold position"
    elif score >= 30:
        tone = "bearish"
        action = "selling or shorting opportunity"
    else:
        tone = "very bearish"
        action = "strong short candidate"

    # Build summary
    summary = f"{company}, ticker symbol {ticker}, currently trading at ${price}. "
    summary += f"Overall investment score is {score} out of 100, indicating a {rec.lower()} rating. "

    # Technical analysis summary
    rsi = data['indicators'].get('RSI', 50)
    if rsi < 30:
        summary += f"The RSI at {rsi:.0f} shows the stock is oversold. "
    elif rsi > 70:
        summary += f"The RSI at {rsi:.0f} shows the stock is overbought. "

    # VIX impact
    vix = data['market_sentiment'].get('vix', 20)
    if vix > 25:
        summary += f"Market volatility is elevated with VIX at {vix:.0f}, suggesting caution. "
    elif vix < 15:
        summary += f"Market volatility is low with VIX at {vix:.0f}, indicating calm markets. "

    # News sentiment
    if 'news_analysis' in data and data['news_analysis'].get('overall_sentiment', 0) != 0:
        news_sent = data['news_analysis']['overall_sentiment']
        if news_sent > 2:
            summary += "Recent news sentiment is positive. "
        elif news_sent < -2:
            summary += "Recent news sentiment is negative. "

    # Price targets
    if data['action'] == 'long':
        target = data['price_targets']['long_target_2']
        stop = data['price_targets']['long_stop_loss']
        summary += f"For a long position, target price is ${target} with a stop loss at ${stop}. "
    elif data['action'] == 'short':
        target = data['price_targets']['short_target_2']
        stop = data['price_targets']['short_stop_loss']
        summary += f"For a short position, cover target is ${target} with a stop loss at ${stop}. "

    summary += f"This analysis combines technical score of {tech_score:.0f} and fundamental score of {fund_score:.0f}."

    return summary


def calculate_investment_score(ticker_symbol):
    """Main function to calculate comprehensive investment score"""
    try:
        ticker = yf.Ticker(ticker_symbol)

        hist = ticker.history(period="1y")
        if hist.empty or len(hist) < 200:
            hist = ticker.history(period="max")

        if hist.empty or len(hist) < 50:
            return {"error": f"Insufficient data for {ticker_symbol}"}

        close = hist['Close']
        current_price = close.iloc[-1]

        # Get market sentiment
        vix = get_vix()
        market_sentiment = get_market_sentiment()
        consumer_sentiment = get_consumer_sentiment()

        # Calculate technical scores
        tech_scores, indicators, signals, tech_evidence = calculate_technical_score(hist, current_price)

        # Get fundamental data
        info = ticker.info
        fund_score, fund_evidence = calculate_fundamental_score(info)

        # Get earnings data
        earnings = get_earnings_data(ticker_symbol)

        # Get news and analyze
        news_items = NewsAnalyzer.fetch_stock_news(ticker_symbol)
        sector = info.get('sector', '')
        news_analysis = NewsAnalyzer.analyze_news_impact(news_items, ticker_symbol, sector)

        # All evidence combined
        all_evidence = tech_evidence.copy()

        # Add fundamental evidence
        for fe in fund_evidence:
            all_evidence.append({
                'factor': fe['factor'],
                'value': fe.get('value', ''),
                'impact': fe['impact'],
                'detail': fe['detail'],
                'weight': fe['weight'],
                'category': 'fundamental'
            })

        # Add VIX evidence
        if vix < 15:
            tech_scores['vix'] = 70
            all_evidence.append({
                'factor': 'VIX (Volatility Index)',
                'value': f'{vix:.1f}',
                'impact': 'BULLISH',
                'detail': f'VIX at {vix:.1f} indicates low market fear and complacency - favorable for stocks.',
                'weight': '+20 points',
                'category': 'sentiment'
            })
        elif vix < 20:
            tech_scores['vix'] = 60
        elif vix < 25:
            tech_scores['vix'] = 50
        elif vix < 30:
            tech_scores['vix'] = 40
            all_evidence.append({
                'factor': 'VIX (Volatility Index)',
                'value': f'{vix:.1f}',
                'impact': 'BEARISH',
                'detail': f'VIX at {vix:.1f} indicates elevated market fear - suggests caution.',
                'weight': '-10 points',
                'category': 'sentiment'
            })
        else:
            tech_scores['vix'] = 25
            all_evidence.append({
                'factor': 'VIX (Volatility Index)',
                'value': f'{vix:.1f}',
                'impact': 'BEARISH',
                'detail': f'VIX at {vix:.1f} indicates extreme fear - potential capitulation but high risk.',
                'weight': '-25 points',
                'category': 'sentiment'
            })

        indicators['VIX'] = round(vix, 2)

        # Consumer sentiment impact
        consumer_change = consumer_sentiment.get('retail_sentiment', 0)
        if consumer_change:
            if consumer_change > 3:
                tech_scores['consumer'] = 65
                all_evidence.append({
                    'factor': 'Consumer Sentiment',
                    'value': f'+{consumer_change:.1f}%',
                    'impact': 'BULLISH',
                    'detail': f'Consumer discretionary sector up {consumer_change:.1f}% this month, indicating strong consumer confidence.',
                    'weight': '+15 points',
                    'category': 'sentiment'
                })
            elif consumer_change < -3:
                tech_scores['consumer'] = 35
                all_evidence.append({
                    'factor': 'Consumer Sentiment',
                    'value': f'{consumer_change:.1f}%',
                    'impact': 'BEARISH',
                    'detail': f'Consumer discretionary sector down {abs(consumer_change):.1f}% this month, indicating weak consumer confidence.',
                    'weight': '-15 points',
                    'category': 'sentiment'
                })
            else:
                tech_scores['consumer'] = 50

        # News sentiment impact
        news_sentiment_score = news_analysis.get('sentiment_score', 0)
        if news_sentiment_score > 5:
            tech_scores['news'] = 65
            all_evidence.append({
                'factor': 'News Sentiment',
                'value': 'Positive',
                'impact': 'BULLISH',
                'detail': f'Recent news coverage is predominantly positive with sentiment score of {news_sentiment_score}.',
                'weight': '+15 points',
                'category': 'news'
            })
        elif news_sentiment_score < -5:
            tech_scores['news'] = 35
            all_evidence.append({
                'factor': 'News Sentiment',
                'value': 'Negative',
                'impact': 'BEARISH',
                'detail': f'Recent news coverage is predominantly negative with sentiment score of {news_sentiment_score}.',
                'weight': '-15 points',
                'category': 'news'
            })
        else:
            tech_scores['news'] = 50

        # Sector news boost
        sector_boost = news_analysis.get('sector_boost', 0)
        if sector_boost != 0:
            all_evidence.append({
                'factor': 'Sector News Impact',
                'value': f'{sector_boost:+d}',
                'impact': 'BULLISH' if sector_boost > 0 else 'BEARISH',
                'detail': f"Sector-specific news {'positively' if sector_boost > 0 else 'negatively'} impacts this stock.",
                'weight': f'{sector_boost:+d} points',
                'category': 'news'
            })

        # Earnings surprise impact
        if earnings['earnings_surprise_avg'] > 5:
            tech_scores['earnings'] = 70
            all_evidence.append({
                'factor': 'Earnings Surprises',
                'value': f'+{earnings["earnings_surprise_avg"]:.1f}%',
                'impact': 'BULLISH',
                'detail': f'Company beats earnings estimates by average of {earnings["earnings_surprise_avg"]:.1f}% over last 4 quarters.',
                'weight': '+20 points',
                'category': 'fundamental'
            })
        elif earnings['earnings_surprise_avg'] > 0:
            tech_scores['earnings'] = 60
        elif earnings['earnings_surprise_avg'] < -5:
            tech_scores['earnings'] = 30
            all_evidence.append({
                'factor': 'Earnings Surprises',
                'value': f'{earnings["earnings_surprise_avg"]:.1f}%',
                'impact': 'BEARISH',
                'detail': f'Company misses earnings estimates by average of {abs(earnings["earnings_surprise_avg"]):.1f}% over last 4 quarters.',
                'weight': '-20 points',
                'category': 'fundamental'
            })
        else:
            tech_scores['earnings'] = 50

        # Calculate weighted final score
        weights = {
            'rsi': 0.08,
            'macd': 0.08,
            'bollinger': 0.06,
            'stochastic': 0.06,
            'williams_r': 0.04,
            'cci': 0.04,
            'adx': 0.06,
            'mfi': 0.05,
            'obv': 0.04,
            'moving_avg': 0.10,
            'vwap': 0.04,
            'vix': 0.10,
            'consumer': 0.05,
            'news': 0.08,
            'earnings': 0.12
        }

        technical_score = sum(tech_scores.get(k, 50) * weights.get(k, 0) for k in weights)

        # Add sector news boost
        technical_score += sector_boost

        # Combine technical and fundamental
        final_score = technical_score * 0.65 + fund_score * 0.35
        final_score = max(1, min(100, round(final_score)))

        # Determine recommendation
        if final_score >= 75:
            recommendation = "STRONG BUY"
            action = "long"
            confidence = "HIGH"
        elif final_score >= 60:
            recommendation = "BUY"
            action = "long"
            confidence = "MEDIUM"
        elif final_score >= 45:
            recommendation = "HOLD"
            action = "hold"
            confidence = "LOW"
        elif final_score >= 30:
            recommendation = "SELL"
            action = "short"
            confidence = "MEDIUM"
        else:
            recommendation = "STRONG SELL"
            action = "short"
            confidence = "HIGH"

        # Calculate price targets
        atr = indicators.get('ATR', current_price * 0.02)
        rsi = indicators.get('RSI', 50)
        price_targets = calculate_price_targets(current_price, atr, rsi, final_score, {})

        # Company info
        company_name = info.get('longName', info.get('shortName', ticker_symbol))
        industry = info.get('industry', 'N/A')

        result = {
            'ticker': ticker_symbol.upper(),
            'company_name': company_name,
            'sector': sector,
            'industry': industry,
            'current_price': round(current_price, 2),
            'score': final_score,
            'technical_score': round(technical_score, 1),
            'fundamental_score': round(fund_score, 1),
            'recommendation': recommendation,
            'action': action,
            'confidence': confidence,
            'price_targets': price_targets,
            'indicators': indicators,
            'individual_scores': {k: round(v, 1) for k, v in tech_scores.items()},
            'signals': signals,
            'evidence': all_evidence,
            'news_analysis': news_analysis,
            'news_items': news_items[:5],
            'earnings': earnings,
            'market_sentiment': market_sentiment,
            'consumer_sentiment': consumer_sentiment,
            'fundamentals': {
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE'),
                'forward_pe': info.get('forwardPE'),
                'peg_ratio': info.get('pegRatio'),
                'price_to_book': info.get('priceToBook'),
                'dividend_yield': round(info.get('dividendYield', 0) * 100, 2) if info.get('dividendYield') else 0,
                'profit_margin': round(info.get('profitMargins', 0) * 100, 2) if info.get('profitMargins') else 0,
                'revenue_growth': round(info.get('revenueGrowth', 0) * 100, 2) if info.get('revenueGrowth') else 0,
                'debt_to_equity': info.get('debtToEquity'),
                'return_on_equity': round(info.get('returnOnEquity', 0) * 100, 2) if info.get('returnOnEquity') else 0,
                '52_week_high': info.get('fiftyTwoWeekHigh', hist['High'].max()),
                '52_week_low': info.get('fiftyTwoWeekLow', hist['Low'].min()),
                'avg_volume': info.get('averageVolume', 0),
                'beta': info.get('beta'),
            }
        }

        # Generate summary for voice
        result['voice_summary'] = generate_summary(result)

        return result

    except Exception as e:
        return {"error": str(e)}


def screen_stocks(filter_type='all', limit=20):
    """Screen stocks for strong buys or sells"""
    results = []

    def analyze_ticker(ticker):
        try:
            result = calculate_investment_score(ticker)
            if 'error' not in result:
                return {
                    'ticker': result['ticker'],
                    'company_name': result['company_name'],
                    'sector': result['sector'],
                    'score': result['score'],
                    'recommendation': result['recommendation'],
                    'current_price': result['current_price'],
                    'rsi': result['indicators'].get('RSI', 0),
                    'confidence': result['confidence']
                }
        except:
            pass
        return None

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(analyze_ticker, ticker): ticker for ticker in SCREENING_UNIVERSE}

        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)

    if filter_type == 'strong_buys':
        results = [r for r in results if r['score'] >= 70]
        results.sort(key=lambda x: x['score'], reverse=True)
    elif filter_type == 'buys':
        results = [r for r in results if 60 <= r['score'] < 70]
        results.sort(key=lambda x: x['score'], reverse=True)
    elif filter_type == 'strong_sells':
        results = [r for r in results if r['score'] <= 30]
        results.sort(key=lambda x: x['score'])
    elif filter_type == 'sells':
        results = [r for r in results if 30 < r['score'] <= 40]
        results.sort(key=lambda x: x['score'])
    elif filter_type == 'shorts':
        results = [r for r in results if r['score'] <= 35]
        results.sort(key=lambda x: x['score'])
    else:
        results.sort(key=lambda x: x['score'], reverse=True)

    return results[:limit]


# API Routes
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze():
    data = request.json
    ticker = data.get('ticker', '').strip().upper()

    if not ticker:
        return jsonify({"error": "Please enter a ticker symbol"})

    result = calculate_investment_score(ticker)
    return jsonify(result)

@app.route('/api/screen', methods=['GET'])
def screen():
    filter_type = request.args.get('filter', 'all')
    limit = int(request.args.get('limit', 20))

    results = screen_stocks(filter_type, limit)
    return jsonify({
        'filter': filter_type,
        'count': len(results),
        'stocks': results
    })

@app.route('/api/market-sentiment', methods=['GET'])
def sentiment():
    return jsonify(get_market_sentiment())

@app.route('/api/speak', methods=['POST'])
def speak():
    """Generate speech using ElevenLabs API"""
    if not ELEVENLABS_API_KEY:
        return jsonify({"error": "ElevenLabs API key not configured"}), 400

    data = request.json
    text = data.get('text', '')

    if not text:
        return jsonify({"error": "No text provided"}), 400

    try:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": ELEVENLABS_API_KEY
        }
        payload = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }

        response = requests.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            return Response(
                response.content,
                mimetype="audio/mpeg",
                headers={"Content-Disposition": "inline; filename=speech.mp3"}
            )
        else:
            return jsonify({"error": "Failed to generate speech"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.errorhandler(404)
def not_found(e):
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
