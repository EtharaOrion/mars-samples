import type { ApiUser } from 'external-api';

export interface IUser {
  readonly id: number;
  readonly email: string;
  readonly displayName: string;
  readonly roles: readonly string[];
}

export class User implements IUser {
  constructor(
    public readonly id: number,
    public readonly email: string,
    public readonly roles: readonly string[],
  ) {}

  static fromApi(api: ApiUser): User {
    return new User(api.id, api.email, api.displayName, []);
  }

  hasRole(role: string): boolean {
    return this.roles.includes(role);
  }
}
