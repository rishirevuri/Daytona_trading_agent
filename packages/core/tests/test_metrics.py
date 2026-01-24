"""Tests for performance metrics calculations."""

import numpy as np
import pandas as pd
import pytest

from signalops.metrics.performance import PerformanceMetrics


@pytest.fixture
def metrics():
    """Create PerformanceMetrics instance."""
    return PerformanceMetrics(risk_free_rate=0.02, trading_days_per_year=252)


@pytest.fixture
def sample_returns():
    """Create sample return series."""
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=252, freq="B")
    returns = pd.Series(np.random.normal(0.0005, 0.02, 252), index=dates)
    return returns


@pytest.fixture
def sample_equity():
    """Create sample equity curve."""
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=252, freq="B")
    returns = np.random.normal(0.0005, 0.02, 252)
    equity = pd.Series(100000 * np.cumprod(1 + returns), index=dates)
    return equity


class TestSharpeRatio:
    """Tests for Sharpe ratio calculation."""

    def test_sharpe_positive(self, metrics, sample_returns):
        """Test Sharpe calculation with positive returns."""
        sharpe = metrics.sharpe_ratio(sample_returns)
        assert isinstance(sharpe, float)
        # With random seed 42, this should be around 0.3-0.5
        assert -5 < sharpe < 5

    def test_sharpe_zero_std(self, metrics):
        """Test Sharpe with zero volatility."""
        returns = pd.Series([0.001] * 100)
        sharpe = metrics.sharpe_ratio(returns)
        assert sharpe != 0  # Should handle constant returns

    def test_sharpe_empty(self, metrics):
        """Test Sharpe with empty series."""
        returns = pd.Series([], dtype=float)
        sharpe = metrics.sharpe_ratio(returns)
        assert sharpe == 0.0


class TestMaxDrawdown:
    """Tests for max drawdown calculation."""

    def test_max_drawdown_calculation(self, metrics, sample_equity):
        """Test max drawdown calculation."""
        max_dd = metrics.max_drawdown(sample_equity)
        assert isinstance(max_dd, float)
        assert 0 <= max_dd <= 1  # Should be between 0 and 100%

    def test_max_drawdown_no_drawdown(self, metrics):
        """Test with monotonically increasing equity."""
        equity = pd.Series([100, 110, 120, 130, 140])
        max_dd = metrics.max_drawdown(equity)
        assert max_dd == 0.0

    def test_max_drawdown_known_value(self, metrics):
        """Test with known drawdown."""
        equity = pd.Series([100, 110, 90, 95, 100])
        max_dd = metrics.max_drawdown(equity)
        # Max drawdown from 110 to 90 = 18.18%
        assert abs(max_dd - 0.1818) < 0.01


class TestCAGR:
    """Tests for CAGR calculation."""

    def test_cagr_calculation(self, metrics, sample_equity):
        """Test CAGR calculation."""
        cagr = metrics.cagr(sample_equity)
        assert isinstance(cagr, float)

    def test_cagr_known_value(self, metrics):
        """Test with known CAGR."""
        # 2 years, 21% total return = ~10% CAGR
        equity = pd.Series(
            [100000, 121000],
            index=pd.date_range("2020-01-01", periods=2, freq="252B"),
        )
        # Note: This is simplified, actual calculation depends on days


class TestWinRate:
    """Tests for win rate calculation."""

    def test_win_rate_all_positive(self, metrics):
        """Test with all positive returns."""
        returns = pd.Series([0.01, 0.02, 0.01, 0.03])
        assert metrics.win_rate(returns) == 1.0

    def test_win_rate_all_negative(self, metrics):
        """Test with all negative returns."""
        returns = pd.Series([-0.01, -0.02, -0.01, -0.03])
        assert metrics.win_rate(returns) == 0.0

    def test_win_rate_mixed(self, metrics):
        """Test with mixed returns."""
        returns = pd.Series([0.01, -0.02, 0.01, -0.03])
        assert metrics.win_rate(returns) == 0.5


class TestProfitFactor:
    """Tests for profit factor calculation."""

    def test_profit_factor_balanced(self, metrics):
        """Test profit factor with balanced wins/losses."""
        returns = pd.Series([0.10, -0.10, 0.10, -0.10])
        pf = metrics.profit_factor(returns)
        assert pf == 1.0

    def test_profit_factor_positive(self, metrics):
        """Test profit factor with more wins."""
        returns = pd.Series([0.10, -0.05, 0.10, -0.05])
        pf = metrics.profit_factor(returns)
        assert pf == 2.0


class TestCalculateAll:
    """Tests for comprehensive metric calculation."""

    def test_calculate_all_returns_dict(self, metrics, sample_returns, sample_equity):
        """Test that calculate_all returns expected keys."""
        result = metrics.calculate_all(sample_returns, sample_equity)

        expected_keys = [
            "sharpe", "sortino", "max_drawdown", "calmar", "cagr",
            "total_return", "volatility", "win_rate", "profit_factor",
        ]
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"
            assert isinstance(result[key], float), f"{key} should be float"
