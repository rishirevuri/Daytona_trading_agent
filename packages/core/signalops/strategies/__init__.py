"""Trading strategy implementations."""

from signalops.strategies.base import Strategy
from signalops.strategies.moving_average import MovingAverageCrossover

__all__ = ["Strategy", "MovingAverageCrossover"]
