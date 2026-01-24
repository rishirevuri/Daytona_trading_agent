"""
Vectorized backtesting engine using vectorbt.

Provides high-performance backtesting with proper handling of
transaction costs, slippage, and position sizing.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Union

import numpy as np
import pandas as pd
import vectorbt as vbt

from signalops.metrics.performance import PerformanceMetrics
from signalops.strategies.base import Strategy


@dataclass
class BacktestConfig:
    """Configuration for backtesting."""

    initial_capital: float = 100_000.0
    commission: float = 0.001  # 0.1% per trade
    slippage: float = 0.0005  # 0.05% slippage
    size_type: str = "percent"  # 'percent', 'fixed', 'value'
    size: float = 1.0  # 100% of portfolio per trade
    freq: str = "D"  # Daily frequency
    allow_short: bool = True
    # Train/test split
    train_ratio: float = 0.7  # 70% for training
    # Risk-free rate for Sharpe calculation
    risk_free_rate: float = 0.02  # 2% annual


@dataclass
class BacktestResult:
    """Results from a backtest run."""

    # Core results
    returns: pd.Series
    equity_curve: pd.Series
    positions: pd.Series
    trades: pd.DataFrame

    # Metrics
    metrics: dict[str, float]
    train_metrics: Optional[dict[str, float]] = None
    test_metrics: Optional[dict[str, float]] = None

    # Metadata
    strategy_name: str = ""
    config: dict[str, Any] = None
    run_timestamp: str = ""

    # Split info
    train_end_date: Optional[str] = None
    test_start_date: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert result to dictionary for serialization."""
        return {
            "strategy_name": self.strategy_name,
            "config": self.config,
            "run_timestamp": self.run_timestamp,
            "metrics": self.metrics,
            "train_metrics": self.train_metrics,
            "test_metrics": self.test_metrics,
            "train_end_date": self.train_end_date,
            "test_start_date": self.test_start_date,
            "summary": {
                "total_return": float(self.equity_curve.iloc[-1] / self.equity_curve.iloc[0] - 1),
                "num_trades": len(self.trades) if self.trades is not None else 0,
                "start_date": str(self.returns.index.min()),
                "end_date": str(self.returns.index.max()),
            },
        }

    def save(self, output_dir: Union[str, Path]) -> dict[str, str]:
        """Save results to files.

        Args:
            output_dir: Directory to save results

        Returns:
            Dictionary with file paths
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        paths = {}

        # Save metrics
        metrics_path = output_dir / "metrics.json"
        with open(metrics_path, "w") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)
        paths["metrics"] = str(metrics_path)

        # Save returns
        returns_path = output_dir / "returns.csv"
        self.returns.to_csv(returns_path)
        paths["returns"] = str(returns_path)

        # Save equity curve
        equity_path = output_dir / "equity.csv"
        self.equity_curve.to_csv(equity_path)
        paths["equity"] = str(equity_path)

        # Save trades
        if self.trades is not None and len(self.trades) > 0:
            trades_path = output_dir / "trades.csv"
            self.trades.to_csv(trades_path)
            paths["trades"] = str(trades_path)

        # Save manifest
        manifest = {
            "generated_at": datetime.now().isoformat(),
            "strategy": self.strategy_name,
            "files": paths,
        }
        manifest_path = output_dir / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
        paths["manifest"] = str(manifest_path)

        return paths


class BacktestEngine:
    """High-performance vectorized backtesting engine."""

    def __init__(self, config: Optional[BacktestConfig] = None):
        """Initialize backtesting engine.

        Args:
            config: Backtest configuration
        """
        self.config = config or BacktestConfig()
        self.metrics_calculator = PerformanceMetrics(
            risk_free_rate=self.config.risk_free_rate
        )

    def run(
        self,
        strategy: Strategy,
        data: pd.DataFrame,
        price_column: str = "close",
        split: bool = True,
    ) -> BacktestResult:
        """Run backtest on historical data.

        Args:
            strategy: Trading strategy to test
            data: Historical price data with OHLCV columns
            price_column: Column to use for price
            split: Whether to perform train/test split

        Returns:
            BacktestResult with performance metrics
        """
        # Generate signals
        signals = strategy.generate_signals(data)

        # Validate signals
        validation = strategy.validate_signals(signals, data)
        if not validation["valid"]:
            raise ValueError(f"Invalid signals: {validation['issues']}")

        # Get price series
        prices = data[price_column]

        # Convert signals to entries/exits for vectorbt
        # Entry when signal changes to 1 (long) or -1 (short)
        entries = (signals != signals.shift(1)) & (signals != 0)
        exits = (signals != signals.shift(1)) & (signals.shift(1) != 0)

        # Determine direction (long or short)
        direction = signals.copy()
        direction[direction == 0] = np.nan
        direction = direction.ffill()

        # Run backtest with vectorbt
        portfolio = vbt.Portfolio.from_signals(
            close=prices,
            entries=entries & (direction == 1),  # Long entries
            exits=exits & (direction.shift(1) == 1),  # Long exits
            short_entries=entries & (direction == -1) if self.config.allow_short else None,
            short_exits=exits & (direction.shift(1) == -1) if self.config.allow_short else None,
            init_cash=self.config.initial_capital,
            fees=self.config.commission + self.config.slippage,
            freq=self.config.freq,
        )

        # Extract results
        returns = portfolio.returns()
        equity_curve = portfolio.value()
        positions = portfolio.positions.records_readable if hasattr(portfolio.positions, 'records_readable') else pd.DataFrame()

        # Calculate metrics on full period
        full_metrics = self.metrics_calculator.calculate_all(returns, equity_curve)

        # Train/test split analysis
        train_metrics = None
        test_metrics = None
        train_end_date = None
        test_start_date = None

        if split and len(data) > 50:
            split_idx = int(len(data) * self.config.train_ratio)
            train_end_date = str(data.index[split_idx - 1])
            test_start_date = str(data.index[split_idx])

            train_returns = returns.iloc[:split_idx]
            test_returns = returns.iloc[split_idx:]
            train_equity = equity_curve.iloc[:split_idx]
            test_equity = equity_curve.iloc[split_idx:]

            train_metrics = self.metrics_calculator.calculate_all(train_returns, train_equity)
            test_metrics = self.metrics_calculator.calculate_all(test_returns, test_equity)

        # Build result
        result = BacktestResult(
            returns=returns,
            equity_curve=equity_curve,
            positions=signals,
            trades=positions if isinstance(positions, pd.DataFrame) else pd.DataFrame(),
            metrics=full_metrics,
            train_metrics=train_metrics,
            test_metrics=test_metrics,
            strategy_name=strategy.name,
            config=strategy.get_info(),
            run_timestamp=datetime.now().isoformat(),
            train_end_date=train_end_date,
            test_start_date=test_start_date,
        )

        return result

    def run_walk_forward(
        self,
        strategy: Strategy,
        data: pd.DataFrame,
        n_splits: int = 5,
        train_ratio: float = 0.7,
        price_column: str = "close",
    ) -> list[BacktestResult]:
        """Run walk-forward analysis.

        Splits data into multiple train/test periods to evaluate
        strategy robustness over time.

        Args:
            strategy: Trading strategy
            data: Historical data
            n_splits: Number of walk-forward splits
            train_ratio: Ratio of training data in each split
            price_column: Price column to use

        Returns:
            List of BacktestResult for each split
        """
        results = []
        split_size = len(data) // n_splits

        for i in range(n_splits):
            start_idx = i * split_size
            end_idx = min((i + 2) * split_size, len(data))

            split_data = data.iloc[start_idx:end_idx]
            if len(split_data) < 50:
                continue

            # Run backtest on this split
            result = self.run(
                strategy,
                split_data,
                price_column=price_column,
                split=True,
            )
            results.append(result)

        return results

    def compare_strategies(
        self,
        strategies: list[Strategy],
        data: pd.DataFrame,
        price_column: str = "close",
    ) -> pd.DataFrame:
        """Compare multiple strategies on the same data.

        Args:
            strategies: List of strategies to compare
            data: Historical data
            price_column: Price column to use

        Returns:
            DataFrame with metrics comparison
        """
        comparisons = []

        for strategy in strategies:
            result = self.run(strategy, data, price_column=price_column)
            metrics = result.metrics.copy()
            metrics["strategy"] = strategy.name
            if result.test_metrics:
                for key, value in result.test_metrics.items():
                    metrics[f"oos_{key}"] = value
            comparisons.append(metrics)

        return pd.DataFrame(comparisons).set_index("strategy")
