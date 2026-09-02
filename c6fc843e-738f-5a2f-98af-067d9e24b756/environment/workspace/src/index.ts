import { User } from './models/user.js';
import { Order } from './models/order.js';
import { Account } from './models/account.js';
import { AuthService } from './services/auth.service.js';
import { PaymentService } from './services/payment.service.js';
import { NotificationService } from './services/notification.service.js';
import { log } from './utils/logger.js';
import { formatUserId } from './utils/formatter.js';
import { validateApiUser } from './utils/validator.js';
import type { ApiUser, ApiOrder } from 'external-api';

export async function runSmoke(): Promise<{ userLabel: string; charged: number }> {
  const apiUser: ApiUser = {
    id: 42,
    email: 'ada@example.com',
    displayName: 'Ada Lovelace',
    createdAt: '2025-01-01T00:00:00Z',
  };
  const validation = validateApiUser(apiUser);
  if (!validation.ok) {
    log('error', `invalid api user: ${validation.reasons.join(',')}`);
    throw new Error('invalid_api_user');
  }
  const user = User.fromApi(apiUser);
  const account = Account.fromApi(apiUser);
  const apiOrder: ApiOrder = { id: 7, userId: user.id, amount: 12.34, currency: 'USD', status: 'paid' };
  const order = Order.fromApi(apiOrder, user);
  const auth = new AuthService();
  const payments = new PaymentService(auth);
  const notifications = new NotificationService(auth);
  const { charged } = await payments.chargeOrder(user, 'tok_ok', order);
  await notifications.notifyPaymentSuccess(user, 'tok_ok', charged, order.currency);
  log('info', `smoke ok for ${formatUserId(user.id)} snapshot=${JSON.stringify(account.snapshot())}`);
  return { userLabel: formatUserId(user.id), charged };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  runSmoke().catch((e) => {
    log('error', `smoke failed: ${(e as Error).message}`);
    process.exit(1);
  });
}
