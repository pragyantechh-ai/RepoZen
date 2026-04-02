const BASE = "http://127.0.0.1:8000/api/auth";

async function request<T>(url: string, opts: RequestInit = {}): Promise<T> {
  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(opts.headers as Record<string, string>),
    },
    ...opts,
  });

  // Handle empty bodies (204, or endpoints that return no content)
  const text = await res.text();

  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    if (text) {
      try {
        const err = JSON.parse(text);
        message = err.detail || err.message || message;
      } catch {
        message = text;
      }
    }
    throw new Error(message);
  }

  // If body is empty, return empty object
  if (!text) return {} as T;

  return JSON.parse(text) as T;
}

function authHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` };
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: {
    user_id: string;
    email: string;
    display_name: string;
    created_at: string;
  };
}

export interface UserResponse {
  user_id: string;
  email: string;
  display_name: string;
  created_at: string;
}

export async function apiRegister(
  email: string,
  password: string,
  display_name: string,
): Promise<UserResponse> {
  return request<UserResponse>(`${BASE}/register`, {
    method: "POST",
    body: JSON.stringify({ email, password, display_name }),
  });
}

export async function apiLogin(email: string, password: string): Promise<TokenResponse> {
  return request<TokenResponse>(`${BASE}/login`, {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function apiLogout(token: string): Promise<void> {
  await request(`${BASE}/logout`, {
    method: "POST",
    headers: authHeaders(token),
  });
}

export async function apiRefreshToken(refreshToken: string): Promise<{ access_token: string }> {
  return request(`${BASE}/refresh`, {
    method: "POST",
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}

export async function apiGetMe(token: string): Promise<UserResponse> {
  return request<UserResponse>(`${BASE}/me`, {
    headers: authHeaders(token),
  });
}

export async function apiDeleteAccount(token: string): Promise<void> {
  await request(`${BASE}/account`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
}