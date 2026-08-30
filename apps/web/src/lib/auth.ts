import { api } from './api';
import { supabase } from './supabase';
import type { User } from './types';

export type BootstrapOrganization = (organizationName: string) => Promise<User>;

export async function login(email: string, password: string) {
  if (!supabase) {
    throw Object.assign(new Error('Supabase is not configured.'), { code: 'SUPABASE_MISSING' });
  }
  const { error } = await supabase.auth.signInWithPassword({ email, password });
  if (error) {
    throw Object.assign(new Error(error.message), { code: error.name });
  }
}

export async function register(
  email: string,
  password: string,
  fullName: string,
  organizationName?: string,
) {
  if (!supabase) {
    throw Object.assign(new Error('Supabase is not configured.'), { code: 'SUPABASE_MISSING' });
  }
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      data: { full_name: fullName, organization_name: organizationName ?? null },
    },
  });
  if (error) {
    throw Object.assign(new Error(error.message), { code: error.name });
  }
  if (organizationName && data.session) {
    await api.post('/auth/bootstrap', { organization_name: organizationName });
  }
}

export async function logout() {
  if (supabase) {
    try {
      await supabase.auth.signOut();
    } catch {
      // ignore
    }
  }
  try {
    await api.post('/auth/logout');
  } catch {
    // ignore
  }
}

export async function me() {
  const r = await api.get<User>('/auth/me');
  return r.data;
}
