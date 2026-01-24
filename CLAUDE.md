# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SignalOps is a reproducible stock market prediction research platform. It combines a Python backtesting engine with a Next.js dashboard for running and analyzing trading strategy experiments in isolated Daytona sandboxes.

**Key principle**: Paper trading only, no live trades, full audit trails.

## Monorepo Structure

- `apps/web/` - Next.js 14 frontend with App Router
- `packages/core/` - Python backtesting engine (signalops)

## Common Commands

### Python Core (`packages/core/`)

```bash
# Run all tests with coverage
cd packages/core && PYTHONPATH=. python -m pytest tests/ -v

# Run a single test file
cd packages/core && PYTHONPATH=. python -m pytest tests/test_metrics.py -v

# Run a specific test
cd packages/core && PYTHONPATH=. python -m pytest tests/test_metrics.py::TestSharpeRatio::test_sharpe_positive -v

# Lint with ruff
cd packages/core && ruff check .

# Type check
cd packages/core && mypy signalops --ignore-missing-imports

# Run CLI
cd packages/core && python -m signalops.cli --help
```

### Next.js Web (`apps/web/`)

```bash
# Development server
cd apps/web && npm run dev

# Build
cd apps/web && npm run build

# Lint
cd apps/web && npm run lint

# Type check
cd apps/web && npx tsc --noEmit

# Database commands
cd apps/web && npx prisma db push      # Apply schema
cd apps/web && npx prisma generate     # Generate client
cd apps/web && npx prisma studio       # Visual editor
```

## Architecture

### Python Backtesting Engine

The `signalops` package in `packages/core/` provides:

- **`backtest/engine.py`** - Vectorized backtesting using vectorbt. The `BacktestEngine` class runs strategies against historical data and produces `BacktestResult` objects with returns, positions, and metrics.

- **`strategies/base.py`** - Abstract `Strategy` class that all strategies inherit from. Strategies implement `generate_signals(prices)` returning 1 (long), 0 (flat), -1 (short).

- **`strategies/moving_average.py`** - `MovingAverageCrossover` and `TripleMovingAverage` implementations.

- **`metrics/performance.py`** - Performance calculations: Sharpe ratio, Sortino ratio, max drawdown, CAGR, win rate, profit factor.

- **`metrics/overfit.py`** - Overfitting detection: Probability of Backtest Overfitting (PBO), Deflated Sharpe Ratio.

- **`validation/leakage.py`** - Data leakage detection for strategy code analysis.

- **`reports/generator.py`** - HTML report generation with equity curves, drawdown charts, monthly returns.

- **`earnings/analyzer.py`** - Earnings call transcript sentiment analysis.

### Next.js Dashboard

The web app in `apps/web/` uses:

- **Prisma ORM** with SQLite (dev) / Postgres (prod). Schema defines `Strategy`, `Run`, `Artifact`, `Log`, `DatasetVersion`.

- **API Routes** at `app/api/`:
  - `strategies/` - CRUD for strategies
  - `strategies/[id]/runs/` - Trigger backtest runs
  - `runs/[id]/logs/` - SSE log streaming
  - `runs/[id]/artifacts/` - Download results
  - `runs/[id]/reproduce/` - Re-run from snapshot

- **Daytona Integration** (`lib/daytona.ts`) - Creates isolated sandboxes for running backtests. Uses dynamic import since `@daytonaio/sdk` is optional.

- **Sentry Integration** - Performance tracing for backtest runs with custom metrics (sharpe_oos, max_drawdown, pbo).

- **GitHub Integration** (`lib/github.ts`) - Creates PRs with experiment results using Octokit.

## Environment Variables

Required variables (see `.env.example`):
- `DAYTONA_API_KEY` - For sandbox execution
- `SENTRY_DSN` / `SENTRY_AUTH_TOKEN` - For observability
- `GITHUB_TOKEN` - For PR creation
- `DATABASE_URL` - Prisma database connection

## CodeRabbit Integration

The `.coderabbit.yaml` configures automated code review with special attention to:
- Lookahead bias in backtests
- Data leakage patterns
- Transaction cost assumptions
- Reproducibility (fixed seeds, versioned data)
- Train/test temporal separation

## Data Flow

1. User creates strategy via dashboard or API
2. User triggers run → API creates `Run` record with status "pending"
3. Backend creates Daytona sandbox, uploads strategy code
4. Backtest executes in sandbox, logs stream via SSE
5. Results collected: metrics.json, returns.csv, report.html
6. Sandbox snapshot saved for reproducibility
7. PR created on GitHub with results (optional)
