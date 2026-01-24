/**
 * Daytona configuration for SignalOps backtesting.
 */

export const DAYTONA_CONFIG = {
  // Default Python image for backtesting
  defaultImage: "python:3.11-slim",

  // Resource limits for sandbox
  resources: {
    cpu: 2,
    memory: "4Gi",
  },

  // Timeout settings (in seconds)
  timeouts: {
    create: 60,
    install: 300,
    backtest: 600,
    cleanup: 30,
  },

  // Python dependencies to pre-install
  pythonDependencies: [
    "vectorbt>=0.26.0",
    "pandas>=2.0.0",
    "numpy>=1.24.0",
    "scipy>=1.10.0",
    "yfinance>=0.2.35",
    "plotly>=5.18.0",
    "jinja2>=3.1.0",
    "sentry-sdk>=1.40.0",
    "pyyaml>=6.0.0",
    "pyarrow>=15.0.0",
  ],

  // Network allowlist for data providers
  networkAllowlist: [
    "query1.finance.yahoo.com",
    "query2.finance.yahoo.com",
    "data.alpaca.markets",
    "api.polygon.io",
    "*.sentry.io",
  ],

  // Volume mounts for data
  volumes: {
    data: "/data",
    outputs: "/outputs",
  },
};

/**
 * Generate experiment configuration YAML for Daytona execution.
 */
export function generateExperimentConfig(params: {
  strategyId: string;
  runId: string;
  strategyName: string;
  strategyParams: Record<string, any>;
  dataConfig: {
    source: "yahoo" | "csv" | "parquet";
    symbol?: string;
    period?: string;
    file?: string;
  };
  backtestConfig?: {
    initialCapital?: number;
    trainRatio?: number;
    commission?: number;
    slippage?: number;
  };
}): string {
  const {
    strategyId,
    runId,
    strategyName,
    strategyParams,
    dataConfig,
    backtestConfig,
  } = params;

  const config = {
    // Metadata
    strategy_id: strategyId,
    run_id: runId,

    // Data configuration
    data: {
      source: dataConfig.source,
      ...(dataConfig.symbol && { symbol: dataConfig.symbol }),
      ...(dataConfig.period && { period: dataConfig.period }),
      ...(dataConfig.file && { file: dataConfig.file }),
    },

    // Strategy configuration
    strategy: {
      type: strategyName,
      ...strategyParams,
    },

    // Backtest configuration
    backtest: {
      initial_capital: backtestConfig?.initialCapital || 100000,
      train_ratio: backtestConfig?.trainRatio || 0.7,
      commission: backtestConfig?.commission || 0.001,
      slippage: backtestConfig?.slippage || 0.0005,
    },

    // Sentry configuration (will be filled from env)
    sentry: {
      enabled: true,
    },
  };

  // Convert to YAML-like format (simple for now)
  return JSON.stringify(config, null, 2);
}

/**
 * Environment fingerprint for reproducibility.
 */
export interface EnvironmentFingerprint {
  imageDigest: string;
  pythonVersion: string;
  dependencies: Record<string, string>;
  timestamp: string;
}

/**
 * Generate environment fingerprint from sandbox.
 */
export async function captureEnvironmentFingerprint(
  sandbox: any
): Promise<EnvironmentFingerprint> {
  // Get Python version
  const pythonResult = await sandbox.process.start("python --version");
  const pythonVersion = pythonResult.stdout?.trim() || "unknown";

  // Get installed packages
  const pipResult = await sandbox.process.start("pip freeze");
  const dependencies: Record<string, string> = {};

  (pipResult.stdout || "").split("\n").forEach((line: string) => {
    const [pkg, version] = line.split("==");
    if (pkg && version) {
      dependencies[pkg.trim()] = version.trim();
    }
  });

  return {
    imageDigest: "sha256:placeholder", // Would come from actual image
    pythonVersion,
    dependencies,
    timestamp: new Date().toISOString(),
  };
}
