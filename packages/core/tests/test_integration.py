"""Integration tests for the complete backtest pipeline."""

import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from signalops.backtest.engine import BacktestEngine, BacktestConfig
from signalops.data.loader import DataLoader
from signalops.data.versioning import DataVersioning
from signalops.metrics.performance import PerformanceMetrics
from signalops.metrics.overfit import OverfitDetector
from signalops.reports.generator import ReportGenerator
from signalops.strategies.moving_average import MovingAverageCrossover
from signalops.validation.leakage import LeakageDetector


@pytest.fixture
def sample_ohlcv_data():
    """Generate realistic OHLCV data for testing."""
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=500, freq="B")

    # Generate trending price data with some volatility
    returns = np.random.normal(0.0003, 0.015, 500)
    close = 100 * np.cumprod(1 + returns)

    # Add intraday variation
    high = close * (1 + np.abs(np.random.normal(0, 0.01, 500)))
    low = close * (1 - np.abs(np.random.normal(0, 0.01, 500)))
    open_price = low + (high - low) * np.random.random(500)

    return pd.DataFrame(
        {
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": np.random.randint(1000000, 10000000, 500),
        },
        index=dates,
    )


class TestEndToEndBacktest:
    """End-to-end backtest pipeline tests."""

    def test_complete_backtest_pipeline(self, sample_ohlcv_data):
        """Test complete pipeline from data to results."""
        # Create strategy
        strategy = MovingAverageCrossover(
            short_window=10,
            long_window=30,
            ma_type="sma",
            commission=0.001,
            slippage=0.0005,
        )

        # Run backtest
        config = BacktestConfig(
            initial_capital=100000,
            train_ratio=0.7,
        )
        engine = BacktestEngine(config)
        result = engine.run(strategy, sample_ohlcv_data, split=True)

        # Verify results structure
        assert result.metrics is not None
        assert "sharpe" in result.metrics
        assert "max_drawdown" in result.metrics
        assert "total_return" in result.metrics

        # Verify train/test split
        assert result.train_metrics is not None
        assert result.test_metrics is not None

        # Verify returns and equity
        assert len(result.returns) == len(sample_ohlcv_data)
        assert len(result.equity_curve) == len(sample_ohlcv_data)

        # Verify no NaN values in key outputs
        assert not result.returns.isna().all()
        assert not result.equity_curve.isna().all()

    def test_strategy_produces_valid_signals(self, sample_ohlcv_data):
        """Test that strategy produces valid trading signals."""
        strategy = MovingAverageCrossover(short_window=10, long_window=30)
        signals = strategy.generate_signals(sample_ohlcv_data)

        # All signals should be -1, 0, or 1
        unique_signals = signals.unique()
        for sig in unique_signals:
            assert sig in [-1.0, 0.0, 1.0], f"Invalid signal value: {sig}"

        # Should have some trading activity
        signal_changes = (signals != signals.shift(1)).sum()
        assert signal_changes > 0, "Strategy produced no trades"

    def test_leakage_detection(self, sample_ohlcv_data):
        """Test leakage detection on valid strategy."""
        strategy = MovingAverageCrossover(short_window=10, long_window=30)
        signals = strategy.generate_signals(sample_ohlcv_data)

        detector = LeakageDetector()
        results = detector.run_all_checks(signals, sample_ohlcv_data)

        # Valid strategy should not have obvious leakage
        assert results["overall_valid"] is True

    def test_overfit_detection_integration(self, sample_ohlcv_data):
        """Test overfit detection with backtest results."""
        strategy = MovingAverageCrossover(short_window=10, long_window=30)

        config = BacktestConfig(train_ratio=0.7)
        engine = BacktestEngine(config)
        result = engine.run(strategy, sample_ohlcv_data, split=True)

        # Run overfit detection
        detector = OverfitDetector()
        dsr = detector.deflated_sharpe_ratio(
            sharpe_ratio=result.metrics["sharpe"],
            n_trials=1,
            variance=result.metrics["volatility"] ** 2,
            n_observations=len(sample_ohlcv_data),
        )

        assert "dsr" in dsr
        assert "expected_max_sharpe" in dsr
        assert isinstance(dsr["dsr"], float)


class TestReportGeneration:
    """Test report generation functionality."""

    def test_html_report_generation(self, sample_ohlcv_data):
        """Test HTML report is generated correctly."""
        strategy = MovingAverageCrossover(short_window=10, long_window=30)

        config = BacktestConfig()
        engine = BacktestEngine(config)
        result = engine.run(strategy, sample_ohlcv_data, split=True)

        generator = ReportGenerator()

        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "report.html"
            html = generator.generate(result, report_path)

            # Verify HTML was generated
            assert len(html) > 1000
            assert "<html" in html
            assert "SignalOps" in html
            assert result.strategy_name in html

            # Verify file was written
            assert report_path.exists()
            assert report_path.stat().st_size > 0

    def test_json_summary_generation(self, sample_ohlcv_data):
        """Test JSON summary is generated correctly."""
        strategy = MovingAverageCrossover(short_window=10, long_window=30)

        config = BacktestConfig()
        engine = BacktestEngine(config)
        result = engine.run(strategy, sample_ohlcv_data, split=True)

        generator = ReportGenerator()
        summary = generator.generate_summary_json(result)

        assert "strategy" in summary
        assert "metrics" in summary
        assert "full_period" in summary["metrics"]


class TestDataHandling:
    """Test data loading and versioning."""

    def test_data_loader_checksum(self):
        """Test checksum calculation."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("Date,Close\n2020-01-01,100\n2020-01-02,101\n")
            f.flush()

            checksum = DataLoader.compute_checksum(f.name)
            assert len(checksum) == 64  # SHA256 produces 64 hex chars

            # Same file should produce same checksum
            checksum2 = DataLoader.compute_checksum(f.name)
            assert checksum == checksum2

            os.unlink(f.name)

    def test_data_validation(self, sample_ohlcv_data):
        """Test data validation functionality."""
        loader = DataLoader()
        validation = loader.validate_data(sample_ohlcv_data)

        assert validation["row_count"] == 500
        assert validation["date_range"]["start"] is not None
        assert validation["date_range"]["end"] is not None
        assert validation["negative_prices"] is False


class TestMetricsAccuracy:
    """Test metrics calculations are accurate."""

    def test_known_sharpe_calculation(self):
        """Test Sharpe ratio with known values."""
        metrics = PerformanceMetrics(risk_free_rate=0.0, trading_days_per_year=252)

        # Create returns with known mean and std
        # Mean daily return of 0.1%, std of 1%
        np.random.seed(42)
        returns = pd.Series(np.random.normal(0.001, 0.01, 252))

        sharpe = metrics.sharpe_ratio(returns)

        # With 0 risk-free rate, Sharpe = mean/std * sqrt(252)
        expected_sharpe = (returns.mean() / returns.std()) * np.sqrt(252)
        assert abs(sharpe - expected_sharpe) < 0.01

    def test_known_max_drawdown(self):
        """Test max drawdown with known sequence."""
        metrics = PerformanceMetrics()

        # Equity: 100 -> 120 -> 90 -> 100
        # Max DD from 120 to 90 = 25%
        equity = pd.Series([100, 110, 120, 100, 90, 95, 100])
        max_dd = metrics.max_drawdown(equity)

        assert abs(max_dd - 0.25) < 0.001

    def test_perfect_win_rate(self):
        """Test win rate with all positive returns."""
        metrics = PerformanceMetrics()
        returns = pd.Series([0.01, 0.02, 0.015, 0.005, 0.008])

        assert metrics.win_rate(returns) == 1.0

    def test_profit_factor_calculation(self):
        """Test profit factor with known values."""
        metrics = PerformanceMetrics()

        # Gross profit = 0.30, Gross loss = 0.15
        # Profit factor = 2.0
        returns = pd.Series([0.10, -0.05, 0.10, -0.05, 0.10, -0.05])
        pf = metrics.profit_factor(returns)

        assert abs(pf - 2.0) < 0.001


class TestStrategyComparison:
    """Test strategy comparison functionality."""

    def test_compare_multiple_strategies(self, sample_ohlcv_data):
        """Test comparing multiple strategies."""
        strategies = [
            MovingAverageCrossover(short_window=10, long_window=30),
            MovingAverageCrossover(short_window=20, long_window=50),
            MovingAverageCrossover(short_window=5, long_window=20),
        ]

        engine = BacktestEngine()
        comparison = engine.compare_strategies(strategies, sample_ohlcv_data)

        assert len(comparison) == 3
        assert "sharpe" in comparison.columns
        assert "total_return" in comparison.columns
