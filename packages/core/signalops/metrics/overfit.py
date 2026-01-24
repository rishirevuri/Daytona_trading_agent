"""
Overfitting detection metrics.

Implements statistical tests to detect overfitting in trading strategies,
including Probability of Backtest Overfitting (PBO) and Deflated Sharpe Ratio.
"""

from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats


class OverfitDetector:
    """Detect overfitting in trading strategies using statistical methods."""

    def __init__(self, n_trials: int = 1000, confidence_level: float = 0.95):
        """Initialize overfit detector.

        Args:
            n_trials: Number of trials for simulation-based tests
            confidence_level: Confidence level for statistical tests
        """
        self.n_trials = n_trials
        self.confidence_level = confidence_level

    def probability_of_backtest_overfitting(
        self,
        train_metrics: list[dict],
        test_metrics: list[dict],
        metric_name: str = "sharpe",
    ) -> dict:
        """Calculate Probability of Backtest Overfitting (PBO).

        PBO measures the probability that the best in-sample strategy
        underperforms the median out-of-sample.

        Based on: Bailey, Borwein, Lopez de Prado, Zhu (2014)
        "Pseudo-Mathematics and Financial Charlatanism"

        Args:
            train_metrics: List of in-sample metrics from different strategies/splits
            test_metrics: List of out-of-sample metrics (corresponding)
            metric_name: Metric to use for ranking

        Returns:
            Dictionary with PBO and related statistics
        """
        if len(train_metrics) != len(test_metrics):
            raise ValueError("train_metrics and test_metrics must have same length")

        if len(train_metrics) < 2:
            return {"pbo": 0.0, "warning": "Insufficient data for PBO calculation"}

        # Extract the metric values
        train_values = np.array([m.get(metric_name, 0) for m in train_metrics])
        test_values = np.array([m.get(metric_name, 0) for m in test_metrics])

        # Rank strategies by in-sample performance
        train_ranks = stats.rankdata(-train_values)  # Negative for descending order

        # Find the best in-sample strategy
        best_is_idx = np.argmin(train_ranks)
        best_is_oos_value = test_values[best_is_idx]

        # Calculate median out-of-sample performance
        median_oos = np.median(test_values)

        # PBO is the probability that best IS strategy underperforms median OOS
        # We estimate this using relative rank
        oos_rank = stats.rankdata(-test_values)[best_is_idx]
        pbo = (oos_rank - 1) / (len(test_values) - 1) if len(test_values) > 1 else 0.0

        # Calculate rank correlation
        rank_corr, rank_pvalue = stats.spearmanr(train_values, test_values)

        return {
            "pbo": float(pbo),
            "rank_correlation": float(rank_corr),
            "rank_correlation_pvalue": float(rank_pvalue),
            "best_is_oos_performance": float(best_is_oos_value),
            "median_oos_performance": float(median_oos),
            "is_overfit": pbo > 0.5,
            "overfit_warning": pbo > 0.5,
        }

    def deflated_sharpe_ratio(
        self,
        sharpe_ratio: float,
        n_trials: int,
        variance: float,
        n_observations: int,
        skewness: float = 0.0,
        kurtosis: float = 3.0,
    ) -> dict:
        """Calculate Deflated Sharpe Ratio.

        Adjusts Sharpe ratio for multiple testing bias.

        Based on: Bailey & Lopez de Prado (2014)
        "The Deflated Sharpe Ratio: Correcting for Selection Bias"

        Args:
            sharpe_ratio: Observed Sharpe ratio
            n_trials: Number of strategies/parameters tested
            variance: Variance of returns
            n_observations: Number of observations
            skewness: Skewness of returns
            kurtosis: Kurtosis of returns

        Returns:
            Dictionary with DSR and related statistics
        """
        if n_observations < 2 or n_trials < 1:
            return {
                "dsr": sharpe_ratio,
                "expected_max_sharpe": sharpe_ratio,
                "haircut": 0.0,
                "warning": "Insufficient data",
            }

        # Expected maximum Sharpe ratio under null hypothesis
        # Using Euler-Mascheroni constant approximation
        euler_mascheroni = 0.5772156649
        expected_max = np.sqrt(2 * np.log(n_trials)) - (
            euler_mascheroni + np.log(np.pi / 2)
        ) / np.sqrt(2 * np.log(n_trials))

        # Standard error of Sharpe ratio
        # Adjusting for non-normality
        se = np.sqrt(
            (1 + 0.5 * sharpe_ratio**2 - skewness * sharpe_ratio
             + ((kurtosis - 3) / 4) * sharpe_ratio**2)
            / (n_observations - 1)
        )

        # Deflated Sharpe Ratio
        if se > 0:
            z_stat = (sharpe_ratio - expected_max) / se
            dsr = stats.norm.cdf(z_stat)
        else:
            dsr = 0.5

        # Haircut (reduction from naive to deflated)
        haircut = 1 - (sharpe_ratio - expected_max) / sharpe_ratio if sharpe_ratio != 0 else 0

        return {
            "dsr": float(dsr),
            "dsr_probability": float(dsr),  # Probability that true SR > 0
            "expected_max_sharpe": float(expected_max),
            "sharpe_standard_error": float(se),
            "haircut": float(max(0, haircut)),
            "is_significant": dsr > self.confidence_level,
        }

    def minimum_track_record_length(
        self,
        target_sharpe: float,
        observed_sharpe: float,
        n_observations: int,
        skewness: float = 0.0,
        kurtosis: float = 3.0,
        confidence_level: Optional[float] = None,
    ) -> dict:
        """Calculate minimum track record length needed.

        Determines how long a track record must be to be statistically
        confident in the observed Sharpe ratio.

        Based on: Bailey & Lopez de Prado (2012)
        "The Sharpe Ratio Efficient Frontier"

        Args:
            target_sharpe: Minimum acceptable Sharpe ratio
            observed_sharpe: Observed Sharpe ratio
            n_observations: Current number of observations
            skewness: Return skewness
            kurtosis: Return kurtosis
            confidence_level: Override default confidence level

        Returns:
            Dictionary with minimum track record length
        """
        if confidence_level is None:
            confidence_level = self.confidence_level

        z_score = stats.norm.ppf(confidence_level)

        # Variance of Sharpe ratio estimator
        sr_variance = (
            1 + 0.5 * observed_sharpe**2
            - skewness * observed_sharpe
            + ((kurtosis - 3) / 4) * observed_sharpe**2
        )

        # Minimum track record length
        if observed_sharpe > target_sharpe:
            min_length = sr_variance * (z_score / (observed_sharpe - target_sharpe)) ** 2
        else:
            min_length = float("inf")

        return {
            "min_track_record_length": float(min_length) if min_length != float("inf") else None,
            "current_observations": n_observations,
            "additional_needed": max(0, int(min_length - n_observations)) if min_length != float("inf") else None,
            "is_sufficient": n_observations >= min_length,
            "target_sharpe": target_sharpe,
            "observed_sharpe": observed_sharpe,
        }

    def combinatorial_purged_cv_pbo(
        self,
        returns_matrix: pd.DataFrame,
        n_splits: int = 10,
        embargo_pct: float = 0.01,
    ) -> dict:
        """Combinatorial Purged Cross-Validation PBO.

        More robust PBO estimation using multiple train/test combinations.

        Args:
            returns_matrix: DataFrame with strategy returns (columns are strategies)
            n_splits: Number of time splits
            embargo_pct: Percentage of data to embargo between train/test

        Returns:
            Dictionary with CPCV PBO results
        """
        n_obs = len(returns_matrix)
        embargo_size = int(n_obs * embargo_pct)

        # Split indices
        split_size = n_obs // n_splits
        splits = []
        for i in range(n_splits):
            start = i * split_size
            end = (i + 1) * split_size if i < n_splits - 1 else n_obs
            splits.append((start, end))

        # Generate all combinations of train/test splits
        pbo_values = []

        for test_split_idx in range(n_splits):
            # Test set
            test_start, test_end = splits[test_split_idx]

            # Train set (all other splits with embargo)
            train_mask = np.ones(n_obs, dtype=bool)
            train_mask[max(0, test_start - embargo_size):min(n_obs, test_end + embargo_size)] = False

            train_data = returns_matrix.iloc[train_mask]
            test_data = returns_matrix.iloc[test_start:test_end]

            if len(train_data) < 10 or len(test_data) < 10:
                continue

            # Calculate Sharpe for each strategy
            train_sharpes = train_data.mean() / train_data.std() * np.sqrt(252)
            test_sharpes = test_data.mean() / test_data.std() * np.sqrt(252)

            # Find best in-sample strategy
            best_is_idx = train_sharpes.idxmax()

            # Rank of best IS strategy in OOS
            oos_rank = test_sharpes.rank(ascending=False)[best_is_idx]
            n_strategies = len(test_sharpes)

            pbo = (oos_rank - 1) / (n_strategies - 1) if n_strategies > 1 else 0
            pbo_values.append(pbo)

        if not pbo_values:
            return {"cpcv_pbo": 0.0, "warning": "Insufficient data for CPCV PBO"}

        return {
            "cpcv_pbo": float(np.mean(pbo_values)),
            "cpcv_pbo_std": float(np.std(pbo_values)),
            "n_combinations": len(pbo_values),
            "is_overfit": np.mean(pbo_values) > 0.5,
        }

    def detect_all(
        self,
        train_metrics: list[dict],
        test_metrics: list[dict],
        n_observations: int,
        n_strategies_tested: int = 1,
    ) -> dict:
        """Run all overfitting detection tests.

        Args:
            train_metrics: In-sample metrics
            test_metrics: Out-of-sample metrics
            n_observations: Number of observations
            n_strategies_tested: Number of strategies/parameters tried

        Returns:
            Comprehensive overfitting analysis
        """
        results = {}

        # PBO
        if len(train_metrics) >= 2:
            results["pbo"] = self.probability_of_backtest_overfitting(
                train_metrics, test_metrics
            )
        else:
            results["pbo"] = {"pbo": None, "warning": "Need multiple strategies for PBO"}

        # Deflated Sharpe Ratio for the best strategy
        if train_metrics:
            best_idx = max(range(len(train_metrics)),
                          key=lambda i: train_metrics[i].get("sharpe", 0))
            best_sharpe = train_metrics[best_idx].get("sharpe", 0)
            best_vol = train_metrics[best_idx].get("volatility", 0.15)

            results["dsr"] = self.deflated_sharpe_ratio(
                sharpe_ratio=best_sharpe,
                n_trials=n_strategies_tested,
                variance=best_vol**2,
                n_observations=n_observations,
            )

            # Minimum track record
            results["min_track_record"] = self.minimum_track_record_length(
                target_sharpe=0.5,  # Minimum acceptable Sharpe
                observed_sharpe=best_sharpe,
                n_observations=n_observations,
            )

        # Overall assessment
        overfit_flags = []
        if results.get("pbo", {}).get("is_overfit"):
            overfit_flags.append("High PBO")
        if not results.get("dsr", {}).get("is_significant", True):
            overfit_flags.append("DSR not significant")
        if not results.get("min_track_record", {}).get("is_sufficient", True):
            overfit_flags.append("Track record too short")

        results["summary"] = {
            "overfit_warning": len(overfit_flags) > 0,
            "overfit_flags": overfit_flags,
            "recommendation": (
                "Strategy shows signs of overfitting. Use caution."
                if overfit_flags
                else "No significant overfitting detected."
            ),
        }

        return results
