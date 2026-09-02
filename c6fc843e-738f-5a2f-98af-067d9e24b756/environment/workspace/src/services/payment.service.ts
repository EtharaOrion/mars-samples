import { AuthService, type Session } from './auth.service.js';
import { Order } from '../models/order.js';
import { User } from '../models/user.js';

export class PaymentService {
  constructor(private readonly auth: AuthService) {}

  async chargeOrder(user: User, token: string, order: Order): Promise<{ session: Session; charged: number }> {
    const session: Session = await this.auth.authenticate(user, token);
    if (session.userId !== user.id) {
      throw new Error(`session/user mismatch`);
    }
    return { session, charged: order.totalCents() };
  }
}
