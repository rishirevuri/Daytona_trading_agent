/**
 * Daytona SDK client wrapper for sandbox execution.
 *
 * Provides isolated sandbox environments for running backtests
 * with reproducibility and security.
 */

export interface SandboxConfig {
  language: "python";
  image?: string;
  envVars?: Record<string, string>;
  resources?: {
    cpu?: number;
    memory?: string;
  };
}

export interface ProcessResult {
  exitCode: number;
  stdout: string;
  stderr: string;
}

export interface SandboxInfo {
  id: string;
  status: string;
  createdAt: Date;
  snapshotId?: string;
}

interface DaytonaClient {
  create(options: { language: string; envVars?: Record<string, string> }): Promise<Sandbox>;
}

interface Sandbox {
  id: string;
  process: {
    start(
      command: string,
      options?: { cwd?: string; timeout?: number }
    ): Promise<{ exitCode: number; stdout?: string; stderr?: string }>;
  };
  fs: {
    writeFile(path: string, content: string): Promise<void>;
    readFile(path: string): Promise<string>;
  };
  stop(): Promise<void>;
}

// Lazily load the Daytona client
let daytonaClient: DaytonaClient | null = null;

async function getDaytonaClient(): Promise<DaytonaClient> {
  if (!daytonaClient) {
    const apiKey = process.env.DAYTONA_API_KEY;
    if (!apiKey) {
      throw new Error("DAYTONA_API_KEY environment variable is required");
    }

    try {
      // Dynamic import to avoid build-time errors if SDK not installed
      const { Daytona } = await import("@daytonaio/sdk");
      daytonaClient = new Daytona({
        apiKey,
        target: "us",
      });
    } catch (error) {
      throw new Error(
        "Daytona SDK not installed. Run: npm install @daytonaio/sdk"
      );
    }
  }
  return daytonaClient;
}

/**
 * Create a new sandbox for running backtests.
 */
export async function createSandbox(
  config: SandboxConfig = { language: "python" }
): Promise<{ sandbox: Sandbox; sandboxId: string }> {
  const client = await getDaytonaClient();

  const sandbox = await client.create({
    language: config.language,
    envVars: {
      SENTRY_DSN: process.env.SENTRY_DSN || "",
      ...config.envVars,
    },
  });

  return {
    sandbox,
    sandboxId: sandbox.id,
  };
}

/**
 * Run a command in an existing sandbox.
 */
export async function runProcess(
  sandbox: Sandbox,
  command: string,
  cwd: string = "/home/daytona"
): Promise<ProcessResult> {
  const response = await sandbox.process.start(command, {
    cwd,
    timeout: 600, // 10 minutes max for backtests
  });

  return {
    exitCode: response.exitCode,
    stdout: response.stdout || "",
    stderr: response.stderr || "",
  };
}

/**
 * Stream logs from a running process.
 */
export async function* streamLogs(
  sandbox: Sandbox,
  command: string,
  cwd: string = "/home/daytona"
): AsyncGenerator<string> {
  const process = await sandbox.process.start(command, { cwd });

  // Note: Actual streaming implementation depends on Daytona SDK version
  // This is a simplified version that yields the full output
  if (process.stdout) {
    yield process.stdout;
  }
  if (process.stderr) {
    yield `[stderr] ${process.stderr}`;
  }
}

/**
 * Upload a file to the sandbox.
 */
export async function uploadFile(
  sandbox: Sandbox,
  localContent: string,
  remotePath: string
): Promise<void> {
  await sandbox.fs.writeFile(remotePath, localContent);
}

/**
 * Download a file from the sandbox.
 */
export async function downloadFile(
  sandbox: Sandbox,
  remotePath: string
): Promise<string> {
  const content = await sandbox.fs.readFile(remotePath);
  return content;
}

/**
 * Check if a file exists in the sandbox.
 */
export async function fileExists(
  sandbox: Sandbox,
  remotePath: string
): Promise<boolean> {
  try {
    await sandbox.fs.readFile(remotePath);
    return true;
  } catch {
    return false;
  }
}

/**
 * List files in a directory.
 */
export async function listFiles(
  sandbox: Sandbox,
  dirPath: string
): Promise<string[]> {
  try {
    const result = await sandbox.process.start(`ls -la ${dirPath}`);
    return result.stdout?.split("\n").filter(Boolean) || [];
  } catch {
    return [];
  }
}

/**
 * Get sandbox information.
 */
export async function getSandboxInfo(sandboxId: string): Promise<SandboxInfo> {
  // Note: Implementation depends on Daytona SDK
  return {
    id: sandboxId,
    status: "running",
    createdAt: new Date(),
  };
}

/**
 * Stop and cleanup a sandbox.
 */
export async function destroySandbox(sandbox: Sandbox): Promise<void> {
  try {
    await sandbox.stop();
  } catch (error) {
    console.error("Error stopping sandbox:", error);
  }
}

/**
 * Run a complete backtest in an isolated sandbox.
 */
export async function runBacktestInSandbox(params: {
  strategyCode: string;
  config: Record<string, unknown>;
  runId: string;
  strategyId: string;
  onLog?: (log: string) => void;
}): Promise<{
  success: boolean;
  sandboxId: string;
  metrics?: Record<string, unknown>;
  artifacts?: Record<string, string>;
  error?: string;
}> {
  const { strategyCode, config, runId, strategyId, onLog } = params;
  let sandbox: Sandbox | null = null;

  try {
    onLog?.("[1/6] Creating sandbox...");

    // Create sandbox
    const { sandbox: sb, sandboxId } = await createSandbox({
      language: "python",
      envVars: {
        RUN_ID: runId,
        STRATEGY_ID: strategyId,
        SENTRY_DSN: process.env.SENTRY_DSN || "",
      },
    });
    sandbox = sb;

    onLog?.(`[2/6] Sandbox created: ${sandboxId}`);

    // Install dependencies
    onLog?.("[3/6] Installing dependencies...");
    await runProcess(
      sandbox,
      "pip install vectorbt pandas numpy scipy yfinance plotly jinja2 sentry-sdk pyyaml"
    );

    // Upload strategy code and config
    onLog?.("[4/6] Uploading strategy and config...");
    await uploadFile(sandbox, strategyCode, "/home/daytona/strategy.py");
    await uploadFile(
      sandbox,
      JSON.stringify(config, null, 2),
      "/home/daytona/config.json"
    );

    // Create a simple runner script
    const runnerScript = `
import json
import sys
sys.path.insert(0, '/home/daytona')

# Load config
with open('/home/daytona/config.json') as f:
    config = json.load(f)

# Import and run the strategy
exec(open('/home/daytona/strategy.py').read())

print("Backtest completed!")
`;
    await uploadFile(sandbox, runnerScript, "/home/daytona/runner.py");

    // Run the backtest
    onLog?.("[5/6] Running backtest...");
    const result = await runProcess(sandbox, "python /home/daytona/runner.py");

    if (result.exitCode !== 0) {
      throw new Error(`Backtest failed: ${result.stderr}`);
    }

    onLog?.(result.stdout);

    // Collect artifacts
    onLog?.("[6/6] Collecting artifacts...");
    const artifacts: Record<string, string> = {};

    const artifactFiles = [
      "metrics.json",
      "returns.csv",
      "equity.csv",
      "report.html",
    ];

    for (const file of artifactFiles) {
      const path = `/home/daytona/outputs/${file}`;
      if (await fileExists(sandbox, path)) {
        artifacts[file] = await downloadFile(sandbox, path);
      }
    }

    // Parse metrics
    let metrics: Record<string, unknown> = {};
    if (artifacts["metrics.json"]) {
      try {
        metrics = JSON.parse(artifacts["metrics.json"]);
      } catch {
        // Ignore parse errors
      }
    }

    onLog?.("Backtest completed successfully!");

    return {
      success: true,
      sandboxId,
      metrics,
      artifacts,
    };
  } catch (error) {
    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";
    onLog?.(`Error: ${errorMessage}`);

    return {
      success: false,
      sandboxId: sandbox?.id || "",
      error: errorMessage,
    };
  } finally {
    if (sandbox) {
      await destroySandbox(sandbox);
    }
  }
}
