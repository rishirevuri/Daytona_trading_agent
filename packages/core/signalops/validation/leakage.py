"""
Data leakage detection for trading strategies.

Detects common forms of lookahead bias and data leakage that can
cause overly optimistic backtest results.
"""

import ast
import inspect
from typing import Any, Callable, Optional

import pandas as pd
import numpy as np


class LeakageDetector:
    """Detect data leakage and lookahead bias in trading strategies."""

    # Common patterns that may indicate lookahead bias
    SUSPICIOUS_PATTERNS = [
        "shift(-",  # Future data access
        ".iloc[-1]",  # End of series access (might be future)
        "future",
        "tomorrow",
        "next_day",
        ".loc[:",  # Slice that might include future
    ]

    # Safe patterns (rolling with proper window)
    SAFE_PATTERNS = [
        ".rolling(",
        ".ewm(",
        ".expanding(",
        ".shift(1)",
        ".shift(2)",
        ".diff(",
    ]

    def __init__(self):
        """Initialize leakage detector."""
        self._warnings = []

    def check_signal_timing(
        self,
        signals: pd.Series,
        prices: pd.DataFrame,
        signal_column: str = "signal",
    ) -> dict:
        """Check if signals could have been generated at each timestamp.

        Verifies that signals only use data available up to that point.

        Args:
            signals: Series of trading signals indexed by date
            prices: Price data DataFrame
            signal_column: Name of signal column if signals is a DataFrame

        Returns:
            Dictionary with timing analysis results
        """
        results = {
            "valid": True,
            "issues": [],
            "stats": {},
        }

        # Check signal index alignment
        if not signals.index.equals(prices.index):
            # Signals should be a subset of or equal to price dates
            signal_dates = set(signals.index)
            price_dates = set(prices.index)

            future_dates = signal_dates - price_dates
            if future_dates:
                results["valid"] = False
                results["issues"].append(
                    f"Signals exist for {len(future_dates)} dates not in price data"
                )

        # Check for signals on the first day (usually impossible)
        if len(signals) > 0 and signals.iloc[0] != 0:
            results["issues"].append(
                "Signal on first day may indicate lookahead (no prior data)"
            )

        # Check signal changes vs price data availability
        signal_changes = (signals != signals.shift(1)).sum()
        results["stats"]["signal_changes"] = int(signal_changes)
        results["stats"]["signal_change_rate"] = float(signal_changes / len(signals))

        return results

    def check_train_test_separation(
        self,
        train_data: pd.DataFrame,
        test_data: pd.DataFrame,
        embargo_days: int = 5,
    ) -> dict:
        """Check for proper separation between train and test sets.

        Args:
            train_data: Training data
            test_data: Test data
            embargo_days: Minimum gap between train and test

        Returns:
            Dictionary with separation analysis
        """
        results = {
            "valid": True,
            "issues": [],
        }

        train_end = train_data.index.max()
        test_start = test_data.index.min()

        # Check for overlap
        train_dates = set(train_data.index)
        test_dates = set(test_data.index)
        overlap = train_dates.intersection(test_dates)

        if overlap:
            results["valid"] = False
            results["issues"].append(
                f"Train and test sets overlap on {len(overlap)} dates"
            )

        # Check embargo period
        if hasattr(train_end, 'date') and hasattr(test_start, 'date'):
            gap = (test_start - train_end).days
            results["gap_days"] = gap

            if gap < embargo_days:
                results["issues"].append(
                    f"Gap between train and test ({gap} days) is less than "
                    f"recommended embargo ({embargo_days} days)"
                )

        return results

    def check_feature_leakage(
        self,
        features: pd.DataFrame,
        target: pd.Series,
        max_correlation: float = 0.95,
    ) -> dict:
        """Check for feature leakage through high correlations.

        Features with extremely high correlation to future returns
        may indicate data leakage.

        Args:
            features: Feature DataFrame
            target: Target variable (e.g., future returns)
            max_correlation: Maximum acceptable correlation

        Returns:
            Dictionary with leakage analysis
        """
        results = {
            "valid": True,
            "issues": [],
            "suspicious_features": [],
        }

        for col in features.columns:
            # Calculate correlation with target
            corr = features[col].corr(target)

            if abs(corr) > max_correlation:
                results["valid"] = False
                results["suspicious_features"].append({
                    "feature": col,
                    "correlation": float(corr),
                    "warning": "Suspiciously high correlation with target",
                })

        if results["suspicious_features"]:
            results["issues"].append(
                f"Found {len(results['suspicious_features'])} features with "
                f"correlation > {max_correlation}"
            )

        return results

    def check_rolling_window_leakage(
        self,
        data: pd.DataFrame,
        window_columns: list[str],
        price_column: str = "close",
    ) -> dict:
        """Check rolling calculations for proper window alignment.

        Args:
            data: DataFrame with price and indicator columns
            window_columns: Columns that should be rolling calculations
            price_column: Price column name

        Returns:
            Dictionary with window alignment analysis
        """
        results = {
            "valid": True,
            "issues": [],
        }

        prices = data[price_column]

        for col in window_columns:
            if col not in data.columns:
                continue

            indicator = data[col]

            # Check if indicator uses future data by comparing
            # correlation with shifted prices
            for shift in range(-5, 1):  # Check shifts from -5 to 0
                if shift < 0:  # Future data
                    future_corr = indicator.corr(prices.shift(shift))
                    present_corr = indicator.corr(prices)

                    # If correlation with future is higher, possible leakage
                    if abs(future_corr) > abs(present_corr) + 0.1:
                        results["issues"].append(
                            f"Column '{col}' shows higher correlation with "
                            f"future prices (shift={shift})"
                        )

        if results["issues"]:
            results["valid"] = False

        return results

    def analyze_code(self, code: str) -> dict:
        """Analyze strategy code for potential leakage patterns.

        Static analysis to identify suspicious patterns.

        Args:
            code: Python source code of the strategy

        Returns:
            Dictionary with code analysis results
        """
        results = {
            "valid": True,
            "warnings": [],
            "suspicious_patterns": [],
        }

        lines = code.split("\n")

        for i, line in enumerate(lines, 1):
            line_lower = line.lower()

            # Check for suspicious patterns
            for pattern in self.SUSPICIOUS_PATTERNS:
                if pattern.lower() in line_lower:
                    # Verify it's not a safe use
                    is_safe = any(
                        safe.lower() in line_lower
                        for safe in self.SAFE_PATTERNS
                    )

                    if not is_safe:
                        results["suspicious_patterns"].append({
                            "line": i,
                            "pattern": pattern,
                            "code": line.strip(),
                        })

        if results["suspicious_patterns"]:
            results["warnings"].append(
                f"Found {len(results['suspicious_patterns'])} potentially "
                "suspicious patterns that may indicate lookahead bias"
            )

        return results

    def validate_strategy_function(
        self,
        strategy_func: Callable,
        sample_data: pd.DataFrame,
    ) -> dict:
        """Validate a strategy function by testing with masked data.

        Args:
            strategy_func: Function that takes data and returns signals
            sample_data: Sample data to test with

        Returns:
            Validation results
        """
        results = {
            "valid": True,
            "issues": [],
        }

        # Get signals on full data
        try:
            full_signals = strategy_func(sample_data)
        except Exception as e:
            results["valid"] = False
            results["issues"].append(f"Strategy failed on full data: {e}")
            return results

        # Get signals on partial data (first 80%)
        partial_idx = int(len(sample_data) * 0.8)
        partial_data = sample_data.iloc[:partial_idx].copy()

        try:
            partial_signals = strategy_func(partial_data)
        except Exception as e:
            results["valid"] = False
            results["issues"].append(f"Strategy failed on partial data: {e}")
            return results

        # Compare signals - they should be identical for overlapping period
        overlap_signals_full = full_signals.iloc[:partial_idx]

        # Allow for NaN differences at the edges due to rolling calculations
        comparison = overlap_signals_full.compare(partial_signals) if hasattr(overlap_signals_full, 'compare') else None

        if comparison is not None and len(comparison) > 0:
            # Check if differences are only at the edges (acceptable for rolling)
            diff_indices = comparison.index
            edge_threshold = 50  # First 50 values might differ due to warmup

            non_edge_diffs = [idx for idx in diff_indices
                            if isinstance(idx, int) and idx > edge_threshold]

            if non_edge_diffs:
                results["valid"] = False
                results["issues"].append(
                    f"Signals differ at {len(non_edge_diffs)} non-edge positions "
                    "when computed on partial vs full data (possible lookahead)"
                )

        return results

    def run_all_checks(
        self,
        signals: pd.Series,
        prices: pd.DataFrame,
        train_data: Optional[pd.DataFrame] = None,
        test_data: Optional[pd.DataFrame] = None,
        strategy_code: Optional[str] = None,
    ) -> dict:
        """Run all leakage detection checks.

        Args:
            signals: Trading signals
            prices: Price data
            train_data: Optional training data
            test_data: Optional test data
            strategy_code: Optional strategy source code

        Returns:
            Comprehensive leakage analysis
        """
        results = {
            "overall_valid": True,
            "checks": {},
        }

        # Signal timing check
        results["checks"]["signal_timing"] = self.check_signal_timing(
            signals, prices
        )

        # Train/test separation
        if train_data is not None and test_data is not None:
            results["checks"]["train_test_separation"] = self.check_train_test_separation(
                train_data, test_data
            )

        # Code analysis
        if strategy_code:
            results["checks"]["code_analysis"] = self.analyze_code(strategy_code)

        # Aggregate validity
        for check_name, check_result in results["checks"].items():
            if not check_result.get("valid", True):
                results["overall_valid"] = False

        # Summary
        all_issues = []
        for check_result in results["checks"].values():
            all_issues.extend(check_result.get("issues", []))
            all_issues.extend(check_result.get("warnings", []))

        results["summary"] = {
            "total_issues": len(all_issues),
            "issues": all_issues,
            "recommendation": (
                "Review flagged issues before using this strategy in production."
                if all_issues
                else "No obvious data leakage detected."
            ),
        }

        return results
