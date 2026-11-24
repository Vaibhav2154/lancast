export interface HealthInfo {
  status: string;
  service: string;
  version: string;
  deployment_profile: "standalone" | "central" | string;
  environment: string;
}

export interface ReadinessInfo {
  status: "ready" | "degraded" | string;
  deployment_profile: string;
  dependencies: {
    postgres: string;
    redis: string;
  };
}

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  is_platform_admin: boolean;
}

export interface AuthMembership {
  tenant_id: string;
  role: string;
}

export interface MeResponse {
  user: AuthUser;
  memberships: AuthMembership[];
}

export interface LoginResponse {
  access_token: string;
  token_type: "bearer";
  expires_at: string;
}

const TOKEN_KEY = "lancast-token";

export function getStoredToken(): string | null {
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string | null): void {
  if (token) {
    window.localStorage.setItem(TOKEN_KEY, token);
  } else {
    window.localStorage.removeItem(TOKEN_KEY);
  }
}

export async function fetchHealth(): Promise<HealthInfo> {
  const res = await fetch("/api/health");
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return (await res.json()) as HealthInfo;
}

export async function fetchReadiness(): Promise<ReadinessInfo> {
  const res = await fetch("/api/ready");
  return (await res.json()) as ReadinessInfo;
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  const res = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = data?.detail?.message || data?.detail || "Invalid email or password";
    throw new Error(typeof msg === "string" ? msg : "Sign in failed");
  }
  return data as LoginResponse;
}

export async function fetchMe(token: string): Promise<MeResponse> {
  const res = await fetch("/api/auth/me", {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Session expired");
  return (await res.json()) as MeResponse;
}

export async function logout(token: string): Promise<void> {
  await fetch("/api/auth/logout", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  }).catch(() => {});
}
