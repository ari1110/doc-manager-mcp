// Test fixture: TypeScript interface with Config naming pattern.

interface AppConfig {
  name: string;
  version?: string;
  debug: boolean;
  maxRetries: number;
}

interface DatabaseOptions {
  host: string;
  port: number;
  database: string;
  ssl?: boolean;
}

interface LoggerSettings {
  level: "debug" | "info" | "warn" | "error";
  format?: string;
  output?: string;
}
