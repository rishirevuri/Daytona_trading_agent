"""Tests for trading strategies."""

import numpy as np
import pandas as pd
import pytest

from signalops.strategies.base import Strategy, StrategyConfig
from signalops.strategies.moving_average import MovingAverageCrossover, TripleMovingAverage


@pytest.fixture
def sample_data():
    """Create sample OHLCV data."""
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=252, freq="B")

    # Generate trending price data
    returns = np.random.normal(0.0005, 0.02, 252)
    close = 100 * np.cumprod(1 + returns)

    data = pd.DataFrame(
        {
            "open": close * (1 + np.random.uniform(-0.01, 0.01, 252)),
            "high": close * (1 + np.random.uniform(0, 0.02, 252)),
            "low": close * (1 + np.random.uniform(-0.02, 0, 252)),
            "close": close,
            "volume": np.random.randint(1000000, 10000000, 252),
        },
        index=dates,
    )
    return data


class TestMovingAverageCrossover:
    """Tests for MA Crossover strategy."""

    def test_init_valid_windows(self):
        """Test initialization with valid windows."""
        strategy = MovingAverageCrossover(short_window=10, long_window=30)
        assert strategy.short_window == 10
        assert strategy.long_window == 30

    def test_init_invalid_windows(self):
        """Test initialization with invalid windows."""
        with pytest.raises(ValueError):
            MovingAverageCrossover(short_window=30, long_window=10)

    def test_generate_signals_shape(self, sample_data):
        """Test that signals have correct shape."""
        strategy = MovingAverageCrossover(short_window=10, long_window=30)
        signals = strategy.generate_signals(sample_data)

        assert len(signals) == len(sample_data)
        assert signals.index.equals(sample_data.index)

    def test_generate_signals_values(self, sample_data):
        """Test that signals are valid values."""
        strategy = MovingAverageCrossover(short_window=10, long_window=30)
        signals = strategy.generate_signals(sample_data)

        # Signals should be -1, 0, or 1
        unique_values = signals.dropna().unique()
        for val in unique_values:
            assert val in [-1.0, 0.0, 1.0]

    def test_warmup_period(self, sample_data):
        """Test that warmup period has no signals."""
        strategy = MovingAverageCrossover(short_window=10, long_window=30)
        signals = strategy.generate_signals(sample_data)

        # First `long_window` signals should be 0
        assert (signals.iloc[:30] == 0).all()

    def test_sma_vs_ema(self, sample_data):
        """Test SMA and EMA produce different signals."""
        sma_strategy = MovingAverageCrossover(
            short_window=10, long_window=30, ma_type="sma"
        )
        ema_strategy = MovingAverageCrossover(
            short_window=10, long_window=30, ma_type="ema"
        )

        sma_signals = sma_strategy.generate_signals(sample_data)
        ema_signals = ema_strategy.generate_signals(sample_data)

        # They should produce at least some different signals
        # (not guaranteed but likely with real data)
        assert not sma_signals.equals(ema_signals)

    def test_get_indicators(self, sample_data):
        """Test indicator extraction."""
        strategy = MovingAverageCrossover(short_window=10, long_window=30)
        indicators = strategy.get_indicators(sample_data)

        assert "price" in indicators.columns
        assert "ma_10" in indicators.columns
        assert "ma_30" in indicators.columns


class TestTripleMovingAverage:
    """Tests for Triple MA strategy."""

    def test_init_valid_windows(self):
        """Test initialization with valid windows."""
        strategy = TripleMovingAverage(
            fast_window=5, medium_window=20, slow_window=50
        )
        assert strategy.fast_window == 5
        assert strategy.medium_window == 20
        assert strategy.slow_window == 50

    def test_init_invalid_order(self):
        """Test initialization with invalid window order."""
        with pytest.raises(ValueError):
            TripleMovingAverage(fast_window=20, medium_window=10, slow_window=50)

    def test_generate_signals(self, sample_data):
        """Test signal generation."""
        strategy = TripleMovingAverage(
            fast_window=5, medium_window=20, slow_window=50
        )
        signals = strategy.generate_signals(sample_data)

        assert len(signals) == len(sample_data)
        # Warmup period should have no signals
        assert (signals.iloc[:50] == 0).all()


class TestStrategyValidation:
    """Tests for strategy signal validation."""

    def test_validate_good_signals(self, sample_data):
        """Test validation of good signals."""
        strategy = MovingAverageCrossover(short_window=10, long_window=30)
        signals = strategy.generate_signals(sample_data)
        validation = strategy.validate_signals(signals, sample_data)

        assert validation["valid"] is True

    def test_validate_signals_with_nan(self, sample_data):
        """Test validation catches NaN signals."""
        strategy = MovingAverageCrossover(short_window=10, long_window=30)
        signals = strategy.generate_signals(sample_data)
        signals.iloc[50] = np.nan

        validation = strategy.validate_signals(signals, sample_data)
        assert any("NaN" in issue for issue in validation["issues"])


class TestStrategyConfig:
    """Tests for strategy configuration."""

    def test_config_defaults(self):
        """Test default configuration values."""
        config = StrategyConfig(name="test")
        assert config.commission == 0.001
        assert config.slippage == 0.0005
        assert config.max_position_size == 1.0

    def test_config_custom(self):
        """Test custom configuration."""
        config = StrategyConfig(
            name="test",
            commission=0.002,
            slippage=0.001,
            stop_loss=0.05,
        )
        assert config.commission == 0.002
        assert config.slippage == 0.001
        assert config.stop_loss == 0.05
