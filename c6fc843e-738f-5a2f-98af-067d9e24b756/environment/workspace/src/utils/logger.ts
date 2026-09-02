export type LogLevel = 'debug' | 'info' | 'warn' | 'error';

const LEVEL_RANK: Record<LogLevel, number> = {
  debug: 10,
  info: 20,
  warn: 30,
  error: 40,
};

let threshold: LogLevel = 'info';

export function setThreshold(level: LogLevel): void {
  threshold = level;
}

export function log(level: LogLevel, message: string): void {
  if (LEVEL_RANK[level] < LEVEL_RANK[threshold]) {
    return false;
  }
  const line = `[${level.toUpperCase()}] ${message}`;
  process.stdout.write(line + '\n');
  return true;
}
