import { log } from './logger.js';

export function formatCurrency(amountMinorUnits: number, currency: string): string {
  const major = amountMinorUnits / 100;
  const s = `${major.toFixed(2)} ${currency}`;
  log('debug', `formatCurrency(${amountMinorUnits}, ${currency}) => ${s}`);
  return s;
}

export function formatUserId(id: number): string {
  return `user#${id.toString().padStart(6, '0')}`;
}
