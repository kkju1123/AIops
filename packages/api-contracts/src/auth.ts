export interface RegisterRequest {
  readonly email: string;
  readonly displayName: string;
  readonly password: string;
}

export interface LoginRequest {
  readonly email: string;
  readonly password: string;
}

/** `guest` accounts are ephemeral, password-less, and limited to read-only or quota-guarded work. */
export const ACCOUNT_KINDS = ["member", "guest"] as const;
export type AccountKind = (typeof ACCOUNT_KINDS)[number];

export interface AuthUser {
  readonly id: string;
  readonly email: string;
  readonly displayName: string;
  readonly createdAt: string;
  readonly accountKind: AccountKind;
}

export interface AuthTokenResponse {
  readonly user: AuthUser;
  readonly accessToken: string;
  readonly tokenType: "bearer";
}

export interface LogoutResponse {
  readonly revoked: true;
}
