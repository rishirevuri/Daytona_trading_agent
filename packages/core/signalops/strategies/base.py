"""
Base strategy interface for all trading strategies.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

import pandas as pd


@dataclass
class StrategyConfig:
    """Configuration for a trading strategy."""

    name: str
    description: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    # Transaction costs
    commission: float = 0.001  # 0.1% per trade
    slippage: float = 0.0005  # 0.05% slippage
    # Position sizing
    max_position_size: float = 1.0  # Max 100% of portfolio
    # Risk management
    stop_loss: Optional[float] = None  # e.g., 0.05 for 5% stop loss
    take_profit: Optional[float] = None  # e.g., 0.10 for 10% take profit


class Strategy(ABC):
    """Abstract base class for trading strategies."""

    def __init__(self, config: StrategyConfig):
        """Initialize strategy with configuration.

        Args:
            config: Strategy configuration
        """
        self.config = config
        self._is_fitted = False

    @property
    def name(self) -> str:
        """Return strategy name."""
        return self.config.name

    @property
    def parameters(self) -> dict[str, Any]:
        """Return strategy parameters."""
        return self.config.parameters

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate trading signals from price data.

        This method must use ONLY historical data available at each timestamp.
        No lookahead bias allowed.

        Args:
            data: DataFrame with OHLCV columns indexed by date

        Returns:
            Series of signals: 1 (long), -1 (short), 0 (no position)
            Index should match input data index
        """
        pass

    def fit(self, train_data: pd.DataFrame) -> "Strategy":
        """Fit strategy parameters on training data.

        Override this method for strategies that require parameter optimization.
        Ensure proper train/test separation to avoid lookahead bias.

        Args:
            train_data: Training data DataFrame

        Returns:
            Self for method chaining
        """
        self._is_fitted = True
        return self

    def validate_signals(self, signals: pd.Series, data: pd.DataFrame) -> dict:
        """Validate generated signals for common issues.

        Args:
            signals: Generated signals
            data: Original price data

        Returns:
            Dictionary with validation results
        """
        results = {
            "valid": True,
            "issues": [],
        }

        # Check for NaN signals
        nan_count = signals.isna().sum()
        if nan_count > 0:
            results["issues"].append(f"Found {nan_count} NaN signals")

        # Check signal values
        valid_values = {-1, 0, 1}
        invalid_signals = ~signals.dropna().isin(valid_values)
        if invalid_signals.any():
            results["issues"].append(
                f"Found {invalid_signals.sum()} invalid signal values"
            )

        # Check for excessive trading
        signal_changes = (signals != signals.shift(1)).sum()
        trade_frequency = signal_changes / len(signals)
        if trade_frequency > 0.5:  # More than 50% of days have position changes
            results["issues"].append(
                f"High trading frequency: {trade_frequency:.2%}"
            )

        # Check for lookahead (signals before data exists)
        if signals.index.min() < data.index.min():
            results["issues"].append("Signals exist before data starts (possible lookahead)")
            results["valid"] = False

        if results["issues"]:
            results["valid"] = len([i for i in results["issues"] if "lookahead" in i.lower()]) == 0

        return results

    def get_info(self) -> dict:
        """Get strategy information for logging/display.

        Returns:
            Dictionary with strategy info
        """
        return {
            "name": self.config.name,
            "description": self.config.description,
            "parameters": self.config.parameters,
            "commission": self.config.commission,
            "slippage": self.config.slippage,
            "is_fitted": self._is_fitted,
        }
