import axios, { AxiosError, type AxiosInstance } from 'axios';

import { supabase } from './supabase';

const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1';

export const api: AxiosInstance = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use(async (config) => {
  if (supabase) {
    const {
      data: { session },
    } = await supabase.auth.getSession();
    if (session?.access_token) {
      config.headers.Authorization = `Bearer ${session.access_token}`;
    }
  }
  return config;
});

api.interceptors.response.use(
  (r) => r,
  async (err: AxiosError<{ error?: { code: string; message: string } }>) => {
    if (err.response?.status === 401 && supabase) {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (session) {
        await supabase.auth.signOut();
      }
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(err);
  },
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

export async function getAccessToken(): Promise<string | null> {
  if (!supabase) return null;
  const {
    data: { session },
  } = await supabase.auth.getSession();
  return session?.access_token ?? null;
}
