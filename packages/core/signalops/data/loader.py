"""
Data loading utilities for historical price data.
Supports CSV, Parquet, and Yahoo Finance data sources.
"""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

import pandas as pd
import yfinance as yf


class DataLoader:
    """Load and manage historical price data."""

    def __init__(self, data_dir: Union[str, Path] = "./data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def load_csv(
        self,
        filepath: Union[str, Path],
        date_column: str = "Date",
        parse_dates: bool = True,
    ) -> pd.DataFrame:
        """Load price data from CSV file.

        Args:
            filepath: Path to CSV file
            date_column: Name of the date column
            parse_dates: Whether to parse the date column

        Returns:
            DataFrame with OHLCV data indexed by date
        """
        df = pd.read_csv(
            filepath,
            parse_dates=[date_column] if parse_dates else False,
            index_col=date_column if parse_dates else None,
        )

        # Standardize column names
        df.columns = df.columns.str.lower()
        if "adj close" in df.columns:
            df = df.rename(columns={"adj close": "adj_close"})

        return df.sort_index()

    def load_parquet(self, filepath: Union[str, Path]) -> pd.DataFrame:
        """Load price data from Parquet file.

        Args:
            filepath: Path to Parquet file

        Returns:
            DataFrame with OHLCV data
        """
        df = pd.read_parquet(filepath)
        df.columns = df.columns.str.lower()
        return df.sort_index()

    def fetch_yahoo(
        self,
        symbol: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        period: str = "5y",
        interval: str = "1d",
        cache: bool = True,
    ) -> pd.DataFrame:
        """Fetch historical data from Yahoo Finance.

        Args:
            symbol: Stock ticker symbol (e.g., 'AAPL')
            start: Start date (YYYY-MM-DD)
            end: End date (YYYY-MM-DD)
            period: Period to fetch if start/end not provided (e.g., '1y', '5y')
            interval: Data interval ('1d', '1wk', '1mo')
            cache: Whether to cache data locally

        Returns:
            DataFrame with OHLCV data indexed by date
        """
        cache_path = self.data_dir / f"{symbol}_{interval}_{period}.parquet"

        if cache and cache_path.exists():
            df = pd.read_parquet(cache_path)
            # Check if cache is recent enough (within 1 day for daily data)
            if interval == "1d":
                cache_age = datetime.now() - datetime.fromtimestamp(
                    cache_path.stat().st_mtime
                )
                if cache_age.days < 1:
                    return df

        ticker = yf.Ticker(symbol)

        if start and end:
            df = ticker.history(start=start, end=end, interval=interval)
        else:
            df = ticker.history(period=period, interval=interval)

        # Standardize column names
        df.columns = df.columns.str.lower()
        df = df.rename(columns={"adj close": "adj_close"})

        # Remove timezone info for consistency
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)

        if cache:
            df.to_parquet(cache_path)

        return df

    def get_multiple(
        self,
        symbols: list[str],
        start: Optional[str] = None,
        end: Optional[str] = None,
        period: str = "5y",
    ) -> dict[str, pd.DataFrame]:
        """Fetch data for multiple symbols.

        Args:
            symbols: List of ticker symbols
            start: Start date
            end: End date
            period: Period to fetch

        Returns:
            Dictionary mapping symbol to DataFrame
        """
        data = {}
        for symbol in symbols:
            try:
                data[symbol] = self.fetch_yahoo(
                    symbol, start=start, end=end, period=period
                )
            except Exception as e:
                print(f"Warning: Failed to fetch {symbol}: {e}")
        return data

    @staticmethod
    def compute_checksum(filepath: Union[str, Path]) -> str:
        """Compute SHA256 checksum of a data file.

        Args:
            filepath: Path to data file

        Returns:
            Hexadecimal checksum string
        """
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    def validate_data(self, df: pd.DataFrame) -> dict:
        """Validate data quality and return statistics.

        Args:
            df: DataFrame to validate

        Returns:
            Dictionary with validation results
        """
        results = {
            "row_count": len(df),
            "date_range": {
                "start": str(df.index.min()) if len(df) > 0 else None,
                "end": str(df.index.max()) if len(df) > 0 else None,
            },
            "missing_values": df.isnull().sum().to_dict(),
            "has_gaps": False,
            "negative_prices": False,
        }

        # Check for date gaps (for daily data)
        if len(df) > 1 and hasattr(df.index, "to_series"):
            date_diffs = df.index.to_series().diff()
            # Allow for weekends (3 days) but flag longer gaps
            max_gap = date_diffs.max()
            if hasattr(max_gap, "days") and max_gap.days > 5:
                results["has_gaps"] = True
                results["max_gap_days"] = max_gap.days

        # Check for negative prices
        price_cols = ["open", "high", "low", "close", "adj_close"]
        for col in price_cols:
            if col in df.columns and (df[col] < 0).any():
                results["negative_prices"] = True
                break

        return results
