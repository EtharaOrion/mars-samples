import type { ApiUser } from 'external-api';
import { User } from './user.js';

export interface AccountSnapshot {
  readonly userId: number;
  readonly email: string;
  readonly displayName: string;
  readonly memberSinceEpochSeconds: number;
}

export class Account {
  constructor(public readonly user: User, public readonly memberSinceEpochSeconds: number) {}

  static fromApi(api: ApiUser): Account {
    const memberSince = Math.floor(new Date(api.createdAt).getTime() / 1000);
    const user = User.fromApi(api);
    return new Account(user, memberSince);
  }

  snapshot(): AccountSnapshot {
    return {
      userId: this.user.id,
      email: this.user.email,
      displayName: this.user.displayName,
      memberSinceEpochSeconds: this.memberSinceEpochSeconds,
    };
  }

  ageSeconds(nowEpochSeconds: number): number {
    return nowEpochSeconds - this.memberSinceEpochSeconds;
  }
}
