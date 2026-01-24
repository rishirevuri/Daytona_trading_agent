"""
Sentry integration for observability and performance monitoring.

Provides tracing, custom metrics, and alerting for backtest runs.
"""

import os
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Optional

import sentry_sdk
from sentry_sdk import Hub, capture_exception, capture_message, set_tag, set_context


class SentryTracer:
    """Sentry integration for SignalOps observability."""

    def __init__(
        self,
        dsn: Optional[str] = None,
        environment: str = "development",
        release: Optional[str] = None,
        traces_sample_rate: float = 1.0,
    ):
        """Initialize Sentry SDK.

        Args:
            dsn: Sentry DSN (defaults to SENTRY_DSN env var)
            environment: Environment name (development, staging, production)
            release: Release version
            traces_sample_rate: Percentage of transactions to trace (0.0 to 1.0)
        """
        self.dsn = dsn or os.getenv("SENTRY_DSN")
        self.environment = environment
        self.initialized = False

        if self.dsn:
            sentry_sdk.init(
                dsn=self.dsn,
                environment=environment,
                release=release,
                traces_sample_rate=traces_sample_rate,
                profiles_sample_rate=traces_sample_rate,
                enable_tracing=True,
            )
            self.initialized = True

    @contextmanager
    def trace_run(
        self,
        strategy_id: str,
        run_id: str,
        commit_sha: Optional[str] = None,
        sandbox_id: Optional[str] = None,
    ):
        """Context manager for tracing a complete backtest run.

        Args:
            strategy_id: Strategy identifier
            run_id: Run identifier
            commit_sha: Git commit SHA
            sandbox_id: Daytona sandbox ID

        Yields:
            Transaction object
        """
        if not self.initialized:
            yield None
            return

        with sentry_sdk.start_transaction(
            op="backtest",
            name="strategy_run",
        ) as transaction:
            # Set tags for filtering
            set_tag("strategy_id", strategy_id)
            set_tag("run_id", run_id)
            if commit_sha:
                set_tag("commit_sha", commit_sha)
            if sandbox_id:
                set_tag("daytona_sandbox_id", sandbox_id)

            try:
                yield transaction
            except Exception as e:
                capture_exception(e)
                raise

    @contextmanager
    def trace_span(self, operation: str, description: Optional[str] = None):
        """Context manager for tracing a span within a transaction.

        Args:
            operation: Span operation name (e.g., 'data.load', 'backtest.run')
            description: Optional description

        Yields:
            Span object
        """
        if not self.initialized:
            yield None
            return

        with sentry_sdk.start_span(op=operation, description=description) as span:
            yield span

    def record_metric(
        self,
        name: str,
        value: float,
        unit: str = "",
        tags: Optional[dict] = None,
    ):
        """Record a custom metric.

        Args:
            name: Metric name (e.g., 'sharpe_oos', 'max_drawdown')
            value: Metric value
            unit: Unit of measurement
            tags: Additional tags
        """
        if not self.initialized:
            return

        # Set as measurement on current span
        hub = Hub.current
        if hub.scope.span:
            hub.scope.span.set_measurement(name, value, unit)

        # Also set as context for filtering
        set_context(
            "metrics",
            {name: {"value": value, "unit": unit, **(tags or {})}},
        )

    def record_backtest_metrics(
        self,
        metrics: dict,
        is_oos: bool = False,
    ):
        """Record all backtest metrics to Sentry.

        Args:
            metrics: Dictionary of metrics
            is_oos: Whether these are out-of-sample metrics
        """
        if not self.initialized:
            return

        prefix = "oos_" if is_oos else "is_"

        # Key metrics to track
        key_metrics = [
            ("sharpe", ""),
            ("sortino", ""),
            ("max_drawdown", "percent"),
            ("cagr", "percent"),
            ("total_return", "percent"),
            ("volatility", "percent"),
            ("win_rate", "percent"),
        ]

        for metric_name, unit in key_metrics:
            if metric_name in metrics:
                self.record_metric(
                    f"{prefix}{metric_name}",
                    metrics[metric_name],
                    unit=unit,
                )

        # Set full metrics as context
        set_context(f"{'oos' if is_oos else 'is'}_metrics", metrics)

    def check_overfit_alert(
        self,
        train_sharpe: float,
        test_sharpe: float,
        pbo: Optional[float] = None,
        threshold: float = 0.2,
    ) -> bool:
        """Check and alert for potential overfitting.

        Args:
            train_sharpe: In-sample Sharpe ratio
            test_sharpe: Out-of-sample Sharpe ratio
            pbo: Probability of Backtest Overfitting
            threshold: Alert threshold for Sharpe degradation

        Returns:
            True if alert was triggered
        """
        if not self.initialized:
            return False

        alert_triggered = False

        # Check Sharpe degradation
        if train_sharpe > 0:
            degradation = (train_sharpe - test_sharpe) / train_sharpe
            if degradation > threshold:
                capture_message(
                    f"Sharpe ratio degradation alert: {degradation:.1%} drop from "
                    f"IS ({train_sharpe:.2f}) to OOS ({test_sharpe:.2f})",
                    level="warning",
                )
                alert_triggered = True

        # Check PBO
        if pbo is not None and pbo > 0.5:
            capture_message(
                f"High probability of overfitting: PBO = {pbo:.2f}",
                level="warning",
            )
            set_tag("overfit_flag", "1")
            alert_triggered = True

        return alert_triggered

    def trace_function(self, operation: str):
        """Decorator to trace a function.

        Args:
            operation: Operation name for the span

        Returns:
            Decorated function
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                with self.trace_span(operation, func.__name__):
                    return func(*args, **kwargs)
            return wrapper
        return decorator

    def capture_error(self, error: Exception, context: Optional[dict] = None):
        """Capture an exception with optional context.

        Args:
            error: Exception to capture
            context: Additional context
        """
        if not self.initialized:
            return

        if context:
            set_context("error_context", context)
        capture_exception(error)


# Global tracer instance
_tracer: Optional[SentryTracer] = None


def init_sentry(
    dsn: Optional[str] = None,
    environment: str = "development",
    **kwargs,
) -> SentryTracer:
    """Initialize the global Sentry tracer.

    Args:
        dsn: Sentry DSN
        environment: Environment name
        **kwargs: Additional arguments for SentryTracer

    Returns:
        SentryTracer instance
    """
    global _tracer
    _tracer = SentryTracer(dsn=dsn, environment=environment, **kwargs)
    return _tracer


def get_tracer() -> Optional[SentryTracer]:
    """Get the global Sentry tracer.

    Returns:
        SentryTracer instance or None if not initialized
    """
    return _tracer
