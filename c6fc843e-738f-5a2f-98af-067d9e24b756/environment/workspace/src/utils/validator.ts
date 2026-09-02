import type { ApiUser } from 'external-api';
import { log } from './logger.js';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function isValidEmail(email: string): boolean {
  const ok = EMAIL_RE.test(email);
  log('debug', `isValidEmail(${email}) => ${ok}`);
  return ok;
}

export function validateApiUser(api: ApiUser): { ok: true } | { ok: false; reasons: string[] } {
  const reasons: string[] = [];
  const numericId: number = api.id;
  if (!Number.isFinite(numericId) || numericId <= 0) reasons.push('id_not_positive_number');
  if (!isValidEmail(api.email)) reasons.push('email_invalid');
  if (!api.displayName) reasons.push('displayName_empty');
  return reasons.length === 0 ? { ok: true } : { ok: false, reasons };
}
