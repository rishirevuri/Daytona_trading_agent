"""
Performance metrics calculations for backtesting.

Includes standard risk-adjusted return metrics like Sharpe, Sortino,
max drawdown, CAGR, and more.
"""

from typing import Optional

import numpy as np
import pandas as pd


class PerformanceMetrics:
    """Calculate trading strategy performance metrics."""

    def __init__(
        self,
        risk_free_rate: float = 0.02,
        trading_days_per_year: int = 252,
    ):
        """Initialize metrics calculator.

        Args:
            risk_free_rate: Annual risk-free rate for Sharpe/Sortino
            trading_days_per_year: Number of trading days per year
        """
        self.risk_free_rate = risk_free_rate
        self.trading_days = trading_days_per_year

    def sharpe_ratio(
        self,
        returns: pd.Series,
        annualize: bool = True,
    ) -> float:
        """Calculate Sharpe ratio.

        Args:
            returns: Series of returns
            annualize: Whether to annualize the ratio

        Returns:
            Sharpe ratio
        """
        if len(returns) < 2 or returns.std() == 0:
            return 0.0

        excess_returns = returns - self.risk_free_rate / self.trading_days
        sharpe = excess_returns.mean() / excess_returns.std()

        if annualize:
            sharpe *= np.sqrt(self.trading_days)

        return float(sharpe)

    def sortino_ratio(
        self,
        returns: pd.Series,
        annualize: bool = True,
    ) -> float:
        """Calculate Sortino ratio (downside deviation only).

        Args:
            returns: Series of returns
            annualize: Whether to annualize the ratio

        Returns:
            Sortino ratio
        """
        if len(returns) < 2:
            return 0.0

        excess_returns = returns - self.risk_free_rate / self.trading_days
        downside_returns = excess_returns[excess_returns < 0]

        if len(downside_returns) == 0 or downside_returns.std() == 0:
            return float("inf") if excess_returns.mean() > 0 else 0.0

        sortino = excess_returns.mean() / downside_returns.std()

        if annualize:
            sortino *= np.sqrt(self.trading_days)

        return float(sortino)

    def max_drawdown(self, equity_curve: pd.Series) -> float:
        """Calculate maximum drawdown.

        Args:
            equity_curve: Series of portfolio values

        Returns:
            Maximum drawdown as a positive decimal (e.g., 0.2 for 20%)
        """
        if len(equity_curve) < 2:
            return 0.0

        rolling_max = equity_curve.expanding().max()
        drawdowns = (equity_curve - rolling_max) / rolling_max
        max_dd = drawdowns.min()

        return float(abs(max_dd))

    def calmar_ratio(
        self,
        returns: pd.Series,
        equity_curve: pd.Series,
    ) -> float:
        """Calculate Calmar ratio (CAGR / Max Drawdown).

        Args:
            returns: Series of returns
            equity_curve: Series of portfolio values

        Returns:
            Calmar ratio
        """
        cagr = self.cagr(equity_curve)
        max_dd = self.max_drawdown(equity_curve)

        if max_dd == 0:
            return float("inf") if cagr > 0 else 0.0

        return float(cagr / max_dd)

    def cagr(self, equity_curve: pd.Series) -> float:
        """Calculate Compound Annual Growth Rate.

        Args:
            equity_curve: Series of portfolio values

        Returns:
            CAGR as a decimal
        """
        if len(equity_curve) < 2:
            return 0.0

        start_value = equity_curve.iloc[0]
        end_value = equity_curve.iloc[-1]
        n_years = len(equity_curve) / self.trading_days

        if start_value <= 0 or n_years <= 0:
            return 0.0

        cagr = (end_value / start_value) ** (1 / n_years) - 1
        return float(cagr)

    def total_return(self, equity_curve: pd.Series) -> float:
        """Calculate total return.

        Args:
            equity_curve: Series of portfolio values

        Returns:
            Total return as a decimal
        """
        if len(equity_curve) < 2:
            return 0.0

        return float(equity_curve.iloc[-1] / equity_curve.iloc[0] - 1)

    def volatility(
        self,
        returns: pd.Series,
        annualize: bool = True,
    ) -> float:
        """Calculate return volatility.

        Args:
            returns: Series of returns
            annualize: Whether to annualize

        Returns:
            Volatility as a decimal
        """
        if len(returns) < 2:
            return 0.0

        vol = returns.std()

        if annualize:
            vol *= np.sqrt(self.trading_days)

        return float(vol)

    def win_rate(self, returns: pd.Series) -> float:
        """Calculate win rate (percentage of positive returns).

        Args:
            returns: Series of returns

        Returns:
            Win rate as a decimal
        """
        if len(returns) == 0:
            return 0.0

        positive_returns = (returns > 0).sum()
        return float(positive_returns / len(returns))

    def profit_factor(self, returns: pd.Series) -> float:
        """Calculate profit factor (gross profit / gross loss).

        Args:
            returns: Series of returns

        Returns:
            Profit factor
        """
        gross_profit = returns[returns > 0].sum()
        gross_loss = abs(returns[returns < 0].sum())

        if gross_loss == 0:
            return float("inf") if gross_profit > 0 else 0.0

        return float(gross_profit / gross_loss)

    def average_trade(self, returns: pd.Series) -> dict:
        """Calculate average trade statistics.

        Args:
            returns: Series of returns

        Returns:
            Dictionary with average win, average loss, etc.
        """
        winning = returns[returns > 0]
        losing = returns[returns < 0]

        return {
            "avg_return": float(returns.mean()) if len(returns) > 0 else 0.0,
            "avg_win": float(winning.mean()) if len(winning) > 0 else 0.0,
            "avg_loss": float(losing.mean()) if len(losing) > 0 else 0.0,
            "largest_win": float(winning.max()) if len(winning) > 0 else 0.0,
            "largest_loss": float(losing.min()) if len(losing) > 0 else 0.0,
        }

    def drawdown_duration(self, equity_curve: pd.Series) -> dict:
        """Calculate drawdown duration statistics.

        Args:
            equity_curve: Series of portfolio values

        Returns:
            Dictionary with max duration, average duration, etc.
        """
        rolling_max = equity_curve.expanding().max()
        in_drawdown = equity_curve < rolling_max

        # Find drawdown periods
        drawdown_starts = in_drawdown & ~in_drawdown.shift(1, fill_value=False)
        drawdown_ends = ~in_drawdown & in_drawdown.shift(1, fill_value=False)

        durations = []
        current_start = None

        for i, (is_start, is_end) in enumerate(zip(drawdown_starts, drawdown_ends)):
            if is_start:
                current_start = i
            if is_end and current_start is not None:
                durations.append(i - current_start)
                current_start = None

        # Handle ongoing drawdown
        if current_start is not None:
            durations.append(len(equity_curve) - current_start)

        if not durations:
            return {"max_duration": 0, "avg_duration": 0.0, "num_drawdowns": 0}

        return {
            "max_duration": max(durations),
            "avg_duration": float(np.mean(durations)),
            "num_drawdowns": len(durations),
        }

    def calculate_all(
        self,
        returns: pd.Series,
        equity_curve: pd.Series,
    ) -> dict:
        """Calculate all performance metrics.

        Args:
            returns: Series of returns
            equity_curve: Series of portfolio values

        Returns:
            Dictionary with all metrics
        """
        dd_stats = self.drawdown_duration(equity_curve)
        trade_stats = self.average_trade(returns)

        return {
            "sharpe": self.sharpe_ratio(returns),
            "sortino": self.sortino_ratio(returns),
            "max_drawdown": self.max_drawdown(equity_curve),
            "calmar": self.calmar_ratio(returns, equity_curve),
            "cagr": self.cagr(equity_curve),
            "total_return": self.total_return(equity_curve),
            "volatility": self.volatility(returns),
            "win_rate": self.win_rate(returns),
            "profit_factor": self.profit_factor(returns),
            "max_drawdown_duration": dd_stats["max_duration"],
            "avg_drawdown_duration": dd_stats["avg_duration"],
            "num_drawdowns": dd_stats["num_drawdowns"],
            **trade_stats,
        }
