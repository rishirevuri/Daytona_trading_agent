"""
SignalOps - Reproducible Stock Market Prediction Research Platform

A backtesting engine for quantitative trading strategies with full audit trails,
overfitting detection, and isolated sandbox execution.
"""

__version__ = "0.1.0"
__author__ = "SignalOps Team"

from signalops.backtest.engine import BacktestEngine
from signalops.strategies.base import Strategy
from signalops.metrics.performance import PerformanceMetrics

__all__ = ["BacktestEngine", "Strategy", "PerformanceMetrics"]
