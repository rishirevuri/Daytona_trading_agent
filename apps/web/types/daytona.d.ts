/**
 * Type declarations for @daytonaio/sdk
 */

declare module "@daytonaio/sdk" {
  export interface DaytonaConfig {
    apiKey: string;
    target?: "us" | "eu";
  }

  export interface CreateSandboxOptions {
    language: "python" | "javascript" | "typescript" | "go" | "rust";
    envVars?: Record<string, string>;
  }

  export interface ProcessOptions {
    cwd?: string;
    timeout?: number;
    onStdout?: (data: string) => void;
    onStderr?: (data: string) => void;
  }

  export interface ProcessResult {
    exitCode: number;
    stdout?: string;
    stderr?: string;
  }

  export interface Sandbox {
    id: string;
    process: {
      start(command: string, options?: ProcessOptions): Promise<ProcessResult>;
    };
    fs: {
      writeFile(path: string, content: string): Promise<void>;
      readFile(path: string): Promise<string>;
    };
    stop(): Promise<void>;
  }

  export class Daytona {
    constructor(config: DaytonaConfig);
    create(options: CreateSandboxOptions): Promise<Sandbox>;
  }
}
