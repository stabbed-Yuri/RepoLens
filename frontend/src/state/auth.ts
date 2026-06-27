export type AuthMode = "firebase-email-link";

export type AuthState = {
  mode: AuthMode;
  userId: string | null;
  isAuthenticated: boolean;
};

export const initialAuthState: AuthState = {
  mode: "firebase-email-link",
  userId: null,
  isAuthenticated: false,
};

