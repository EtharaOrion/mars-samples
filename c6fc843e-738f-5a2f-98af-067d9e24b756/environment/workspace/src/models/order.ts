import type { ApiOrder } from 'external-api';
import { User } from './user.js';

export class Order {
  constructor(
    public readonly id: number,
    public readonly owner: User,
    public readonly amount: number,
    public readonly currency: string,
  ) {}

  static fromApi(api: ApiOrder, owner: User): Order {
    if (owner.id !== api.userId) {
      throw new Error(`owner mismatch: ${owner.id} vs ${api.userId}`);
    }
    return new Order(api.id, owner, api.amount, api.currency);
  }

  totalCents(): number {
    return Math.round(this.amount * 100);
  }
}
