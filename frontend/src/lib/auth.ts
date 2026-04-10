const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

export interface AuthUser {
  id: string;
  email: string;
  is_admin?: boolean;
  is_operator?: boolean;
}

async function authFetch(path: string, options?: RequestInit): Promise<Response> {
  return fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    ...options,
  });
}

export async function register(email: string, password: string): Promise<AuthUser> {
  const res = await authFetch("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Registration failed (${res.status})`);
  }
  const data = await res.json();
  return data.user as AuthUser;
}

export async function login(email: string, password: string): Promise<AuthUser> {
  const res = await authFetch("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Login failed (${res.status})`);
  }
  const data = await res.json();
  return data.user as AuthUser;
}

export async function logout(): Promise<void> {
  await authFetch("/api/auth/logout", { method: "POST" });
}

export async function refreshToken(): Promise<boolean> {
  const res = await authFetch("/api/auth/refresh", { method: "POST" });
  return res.ok;
}

export async function getMe(): Promise<AuthUser | null> {
  const res = await authFetch("/api/auth/me");
  if (!res.ok) return null;
  const data = await res.json();
  return data.user as AuthUser;
}
