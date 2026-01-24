"""
Moving Average Crossover Strategy.

A classic technical analysis strategy that generates signals based on
the crossover of short-term and long-term moving averages.
"""

from typing import Literal

import pandas as pd

from signalops.strategies.base import Strategy, StrategyConfig


class MovingAverageCrossover(Strategy):
    """Moving Average Crossover trading strategy.

    Generates buy signals when short MA crosses above long MA,
    and sell signals when short MA crosses below long MA.
    """

    def __init__(
        self,
        short_window: int = 20,
        long_window: int = 50,
        ma_type: Literal["sma", "ema"] = "sma",
        price_column: str = "close",
        commission: float = 0.001,
        slippage: float = 0.0005,
    ):
        """Initialize Moving Average Crossover strategy.

        Args:
            short_window: Period for short-term moving average
            long_window: Period for long-term moving average
            ma_type: Type of moving average ('sma' or 'ema')
            price_column: Column to use for price data
            commission: Commission per trade (as decimal)
            slippage: Slippage per trade (as decimal)
        """
        if short_window >= long_window:
            raise ValueError("short_window must be less than long_window")

        config = StrategyConfig(
            name=f"MA_Crossover_{short_window}_{long_window}",
            description=f"{ma_type.upper()} crossover strategy with {short_window}/{long_window} periods",
            parameters={
                "short_window": short_window,
                "long_window": long_window,
                "ma_type": ma_type,
                "price_column": price_column,
            },
            commission=commission,
            slippage=slippage,
        )
        super().__init__(config)

        self.short_window = short_window
        self.long_window = long_window
        self.ma_type = ma_type
        self.price_column = price_column

    def _compute_ma(self, series: pd.Series, window: int) -> pd.Series:
        """Compute moving average based on configured type.

        Args:
            series: Price series
            window: MA window period

        Returns:
            Moving average series
        """
        if self.ma_type == "sma":
            return series.rolling(window=window).mean()
        elif self.ma_type == "ema":
            return series.ewm(span=window, adjust=False).mean()
        else:
            raise ValueError(f"Unknown MA type: {self.ma_type}")

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate trading signals from price data.

        Args:
            data: DataFrame with OHLCV columns indexed by date

        Returns:
            Series of signals: 1 (long), -1 (short), 0 (no position)
        """
        if self.price_column not in data.columns:
            raise ValueError(f"Price column '{self.price_column}' not found in data")

        prices = data[self.price_column]

        # Compute moving averages
        short_ma = self._compute_ma(prices, self.short_window)
        long_ma = self._compute_ma(prices, self.long_window)

        # Generate signals based on crossover
        # 1 when short MA > long MA (bullish), -1 when short MA < long MA (bearish)
        signals = pd.Series(index=data.index, dtype=float)
        signals[short_ma > long_ma] = 1.0
        signals[short_ma < long_ma] = -1.0
        signals[short_ma == long_ma] = 0.0

        # First `long_window` periods have no signal (insufficient data)
        signals.iloc[: self.long_window] = 0.0

        return signals

    def get_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Get the moving average indicators for visualization.

        Args:
            data: DataFrame with price data

        Returns:
            DataFrame with price and MA columns
        """
        prices = data[self.price_column]
        short_ma = self._compute_ma(prices, self.short_window)
        long_ma = self._compute_ma(prices, self.long_window)

        return pd.DataFrame(
            {
                "price": prices,
                f"ma_{self.short_window}": short_ma,
                f"ma_{self.long_window}": long_ma,
            },
            index=data.index,
        )


class TripleMovingAverage(Strategy):
    """Triple Moving Average strategy with trend filter.

    Uses three MAs: fast, medium, slow.
    Only trades in direction of the slow MA trend.
    """

    def __init__(
        self,
        fast_window: int = 10,
        medium_window: int = 30,
        slow_window: int = 100,
        ma_type: Literal["sma", "ema"] = "ema",
        price_column: str = "close",
        commission: float = 0.001,
        slippage: float = 0.0005,
    ):
        """Initialize Triple Moving Average strategy.

        Args:
            fast_window: Period for fast moving average
            medium_window: Period for medium moving average
            slow_window: Period for slow moving average (trend filter)
            ma_type: Type of moving average
            price_column: Column to use for price data
            commission: Commission per trade
            slippage: Slippage per trade
        """
        if not (fast_window < medium_window < slow_window):
            raise ValueError("Windows must be in ascending order: fast < medium < slow")

        config = StrategyConfig(
            name=f"TripleMA_{fast_window}_{medium_window}_{slow_window}",
            description=f"Triple {ma_type.upper()} strategy with trend filter",
            parameters={
                "fast_window": fast_window,
                "medium_window": medium_window,
                "slow_window": slow_window,
                "ma_type": ma_type,
                "price_column": price_column,
            },
            commission=commission,
            slippage=slippage,
        )
        super().__init__(config)

        self.fast_window = fast_window
        self.medium_window = medium_window
        self.slow_window = slow_window
        self.ma_type = ma_type
        self.price_column = price_column

    def _compute_ma(self, series: pd.Series, window: int) -> pd.Series:
        """Compute moving average."""
        if self.ma_type == "sma":
            return series.rolling(window=window).mean()
        return series.ewm(span=window, adjust=False).mean()

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate trading signals with trend filter.

        Args:
            data: DataFrame with OHLCV columns

        Returns:
            Series of trading signals
        """
        prices = data[self.price_column]

        fast_ma = self._compute_ma(prices, self.fast_window)
        medium_ma = self._compute_ma(prices, self.medium_window)
        slow_ma = self._compute_ma(prices, self.slow_window)

        signals = pd.Series(0.0, index=data.index)

        # Long: fast > medium > slow (uptrend)
        long_condition = (fast_ma > medium_ma) & (medium_ma > slow_ma)
        signals[long_condition] = 1.0

        # Short: fast < medium < slow (downtrend)
        short_condition = (fast_ma < medium_ma) & (medium_ma < slow_ma)
        signals[short_condition] = -1.0

        # No signal during warmup period
        signals.iloc[: self.slow_window] = 0.0

        return signals
