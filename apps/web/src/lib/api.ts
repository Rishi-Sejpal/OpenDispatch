import axios, { AxiosError, AxiosInstance } from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1';

export const api: AxiosInstance = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('od_access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (err: AxiosError<{ error?: { code: string; message: string } }>) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('od_access_token');
      localStorage.removeItem('od_refresh_token');
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(err);
  }
);

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export function extractError(e: unknown): ApiError {
  const err = e as AxiosError<{ error?: ApiError }>;
  if (err.response?.data?.error) {
    return err.response.data.error;
  }
  return {
    code: 'NETWORK_ERROR',
    message: err.message || 'Network error',
  };
}

export function setTokens(access: string, refresh: string) {
  localStorage.setItem('od_access_token', access);
  localStorage.setItem('od_refresh_token', refresh);
}

export function clearTokens() {
  localStorage.removeItem('od_access_token');
  localStorage.removeItem('od_refresh_token');
}

export function getAccessToken(): string | null {
  return localStorage.getItem('od_access_token');
}
