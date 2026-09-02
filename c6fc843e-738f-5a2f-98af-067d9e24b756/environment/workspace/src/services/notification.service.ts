import { AuthService, type Session } from './auth.service.js';
import { User } from '../models/user.js';
import { formatCurrency } from '../utils/formatter.js';
import { log } from '../utils/logger.js';

export class NotificationService {
  constructor(private readonly auth: AuthService) {}

  async notifyPaymentSuccess(user: User, token: string, amountCents: number, currency: string): Promise<void> {
    const session: Session = await this.auth.authenticate(user, token);
    const formatted = formatCurrency(amountCents, currency);
    log('info', `sent receipt for ${formatted} to user ${session.userId}`);
  }
}
