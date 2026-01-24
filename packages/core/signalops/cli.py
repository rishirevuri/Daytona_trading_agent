"""
SignalOps CLI for running backtests and experiments.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

import yaml

from signalops.backtest.engine import BacktestEngine, BacktestConfig
from signalops.data.loader import DataLoader
from signalops.metrics.overfit import OverfitDetector
from signalops.observability.sentry import init_sentry
from signalops.reports.generator import ReportGenerator
from signalops.strategies.moving_average import MovingAverageCrossover
from signalops.validation.leakage import LeakageDetector


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def run_experiment(config: dict, output_dir: str) -> dict:
    """Run a backtest experiment based on configuration.

    Args:
        config: Experiment configuration
        output_dir: Directory to save outputs

    Returns:
        Results dictionary
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Initialize Sentry if configured
    tracer = None
    if config.get("sentry", {}).get("enabled", False):
        tracer = init_sentry(
            dsn=config["sentry"].get("dsn"),
            environment=config["sentry"].get("environment", "development"),
        )

    # Load data
    print("[1/6] Loading data...")
    loader = DataLoader(config.get("data_dir", "./data"))

    data_config = config.get("data", {})
    if data_config.get("source") == "yahoo":
        data = loader.fetch_yahoo(
            symbol=data_config.get("symbol", "SPY"),
            period=data_config.get("period", "5y"),
        )
    elif data_config.get("file"):
        if data_config["file"].endswith(".parquet"):
            data = loader.load_parquet(data_config["file"])
        else:
            data = loader.load_csv(data_config["file"])
    else:
        raise ValueError("No data source specified in config")

    print(f"   Loaded {len(data)} rows from {data.index.min()} to {data.index.max()}")

    # Create strategy
    print("[2/6] Creating strategy...")
    strategy_config = config.get("strategy", {})
    strategy_type = strategy_config.get("type", "moving_average")

    if strategy_type == "moving_average":
        strategy = MovingAverageCrossover(
            short_window=strategy_config.get("short_window", 20),
            long_window=strategy_config.get("long_window", 50),
            ma_type=strategy_config.get("ma_type", "sma"),
            commission=strategy_config.get("commission", 0.001),
            slippage=strategy_config.get("slippage", 0.0005),
        )
    else:
        raise ValueError(f"Unknown strategy type: {strategy_type}")

    print(f"   Strategy: {strategy.name}")

    # Run backtest
    print("[3/6] Running backtest...")
    backtest_config = BacktestConfig(
        initial_capital=config.get("backtest", {}).get("initial_capital", 100000),
        train_ratio=config.get("backtest", {}).get("train_ratio", 0.7),
    )
    engine = BacktestEngine(backtest_config)

    # Trace the run if Sentry is enabled
    run_id = config.get("run_id", "local")
    strategy_id = config.get("strategy_id", strategy.name)

    if tracer:
        with tracer.trace_run(strategy_id, run_id):
            with tracer.trace_span("backtest.run"):
                result = engine.run(strategy, data, split=True)
            tracer.record_backtest_metrics(result.metrics, is_oos=False)
            if result.test_metrics:
                tracer.record_backtest_metrics(result.test_metrics, is_oos=True)
    else:
        result = engine.run(strategy, data, split=True)

    print(f"   Sharpe: {result.metrics['sharpe']:.2f}")
    print(f"   Max Drawdown: {result.metrics['max_drawdown']:.2%}")

    # Validate for leakage
    print("[4/6] Checking for data leakage...")
    leakage_detector = LeakageDetector()
    signals = strategy.generate_signals(data)
    leakage_results = leakage_detector.run_all_checks(signals, data)

    if not leakage_results["overall_valid"]:
        print("   WARNING: Potential data leakage detected!")
        for issue in leakage_results["summary"]["issues"]:
            print(f"   - {issue}")
    else:
        print("   No obvious leakage detected")

    # Check for overfitting
    print("[5/6] Analyzing overfitting risk...")
    overfit_detector = OverfitDetector()

    if result.train_metrics and result.test_metrics:
        dsr = overfit_detector.deflated_sharpe_ratio(
            sharpe_ratio=result.metrics["sharpe"],
            n_trials=1,
            variance=result.metrics["volatility"] ** 2,
            n_observations=len(data),
        )

        if tracer:
            tracer.check_overfit_alert(
                result.train_metrics["sharpe"],
                result.test_metrics["sharpe"],
            )

        print(f"   Deflated Sharpe Ratio: {dsr['dsr']:.2f}")
        print(f"   IS Sharpe: {result.train_metrics['sharpe']:.2f}, OOS Sharpe: {result.test_metrics['sharpe']:.2f}")
    else:
        print("   Skipped (no train/test split)")

    # Generate report
    print("[6/6] Generating report...")
    report_generator = ReportGenerator()

    report_path = output_path / "report.html"
    report_generator.generate(result, report_path)
    print(f"   Report saved to: {report_path}")

    # Save artifacts
    artifact_paths = result.save(output_path)
    print(f"   Artifacts saved to: {output_path}")

    # Summary
    summary = {
        "status": "completed",
        "strategy": strategy.name,
        "metrics": result.metrics,
        "train_metrics": result.train_metrics,
        "test_metrics": result.test_metrics,
        "leakage_check": leakage_results["summary"],
        "artifacts": artifact_paths,
    }

    # Save summary
    summary_path = output_path / "summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    return summary


def main():
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="SignalOps - Stock Market Prediction Research Platform"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Run experiment command
    run_parser = subparsers.add_parser("run", help="Run a backtest experiment")
    run_parser.add_argument(
        "config",
        help="Path to experiment config YAML file",
    )
    run_parser.add_argument(
        "-o", "--output",
        default="./outputs",
        help="Output directory for results",
    )

    # Quick test command
    test_parser = subparsers.add_parser("test", help="Run quick test with defaults")
    test_parser.add_argument(
        "-s", "--symbol",
        default="SPY",
        help="Stock symbol to test",
    )
    test_parser.add_argument(
        "-o", "--output",
        default="./outputs",
        help="Output directory",
    )

    args = parser.parse_args()

    if args.command == "run":
        config = load_config(args.config)
        result = run_experiment(config, args.output)
        print("\n" + "=" * 50)
        print("Experiment completed!")
        print(f"Sharpe Ratio: {result['metrics']['sharpe']:.2f}")
        print(f"Total Return: {result['metrics']['total_return']:.2%}")
        print("=" * 50)

    elif args.command == "test":
        # Quick test with default config
        config = {
            "data": {
                "source": "yahoo",
                "symbol": args.symbol,
                "period": "5y",
            },
            "strategy": {
                "type": "moving_average",
                "short_window": 20,
                "long_window": 50,
            },
            "backtest": {
                "initial_capital": 100000,
                "train_ratio": 0.7,
            },
        }
        result = run_experiment(config, args.output)
        print("\n" + "=" * 50)
        print("Quick test completed!")
        print(f"Symbol: {args.symbol}")
        print(f"Sharpe Ratio: {result['metrics']['sharpe']:.2f}")
        print("=" * 50)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
