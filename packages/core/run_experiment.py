#!/usr/bin/env python3
"""
Standalone experiment runner for Daytona sandbox execution.

This script is designed to be run inside a Daytona sandbox with:
    python run_experiment.py config.yaml

It reads configuration, runs the backtest, and outputs artifacts.
"""

import json
import os
import sys
from pathlib import Path

import yaml

# Add package to path
sys.path.insert(0, str(Path(__file__).parent))

from signalops.cli import run_experiment


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_experiment.py <config.yaml>")
        sys.exit(1)

    config_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "./outputs"

    # Load config
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # Set run metadata from environment (if in Daytona)
    config["run_id"] = os.getenv("RUN_ID", "local")
    config["strategy_id"] = os.getenv("STRATEGY_ID", config.get("strategy", {}).get("name", "unknown"))

    # Configure Sentry from environment
    sentry_dsn = os.getenv("SENTRY_DSN")
    if sentry_dsn:
        config["sentry"] = {
            "enabled": True,
            "dsn": sentry_dsn,
            "environment": os.getenv("ENVIRONMENT", "sandbox"),
        }

    print("=" * 60)
    print("SignalOps Experiment Runner")
    print("=" * 60)
    print(f"Config: {config_path}")
    print(f"Output: {output_dir}")
    print(f"Run ID: {config.get('run_id')}")
    print("=" * 60)
    print()

    try:
        result = run_experiment(config, output_dir)

        print()
        print("=" * 60)
        print("EXPERIMENT COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print(f"Strategy: {result['strategy']}")
        print(f"Sharpe Ratio: {result['metrics']['sharpe']:.2f}")
        print(f"Total Return: {result['metrics']['total_return']:.2%}")
        print(f"Max Drawdown: {result['metrics']['max_drawdown']:.2%}")

        if result.get("test_metrics"):
            print()
            print("Out-of-Sample Performance:")
            print(f"  OOS Sharpe: {result['test_metrics']['sharpe']:.2f}")
            print(f"  OOS Return: {result['test_metrics']['total_return']:.2%}")

        print("=" * 60)

        # Exit with success
        sys.exit(0)

    except Exception as e:
        print()
        print("=" * 60)
        print("EXPERIMENT FAILED")
        print("=" * 60)
        print(f"Error: {e}")
        print("=" * 60)

        # Write error to output
        error_path = Path(output_dir) / "error.json"
        error_path.parent.mkdir(parents=True, exist_ok=True)
        with open(error_path, "w") as f:
            json.dump({"status": "failed", "error": str(e)}, f)

        sys.exit(1)


if __name__ == "__main__":
    main()
