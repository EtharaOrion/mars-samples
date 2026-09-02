import type { ApiSession } from 'external-api';
import { createSession } from 'external-api';
import { User } from '../models/user.js';

export interface Session {
  readonly token: string;
  readonly expiresAtEpochSeconds: number;
  readonly userId: number;
}

export class AuthService {
  authenticate(user: User, token: string): Promise<Session> {
    const api: ApiSession = createSession(user.id, token);
    return {
      token: api.token,
      expiresAtEpochSeconds: api.expiresAt,
      userId: api.userId,
    };
  }
}
