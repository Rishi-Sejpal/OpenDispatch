import { api, setTokens, clearTokens } from './api';
import type { User } from './types';

export async function login(email: string, password: string) {
  const r = await api.post<{ access_token: string; refresh_token: string }>('/auth/login', {
    email,
    password,
  });
  setTokens(r.data.access_token, r.data.refresh_token);
  return r.data;
}

export async function register(
  email: string,
  password: string,
  fullName: string,
  orgName?: string,
) {
  const r = await api.post<User>('/auth/register', {
    email,
    password,
    full_name: fullName,
    organization_name: orgName,
  });
  return r.data;
}

export async function logout() {
  try {
    await api.post('/auth/logout');
  } catch {
    // ignore
  }
  clearTokens();
}

export async function me() {
  const r = await api.get<User>('/auth/me');
  return r.data;
}
