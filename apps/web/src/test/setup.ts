import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

class MemoryStorage implements Storage {
  private store = new Map<string, string>();

  get length(): number {
    return this.store.size;
  }

  clear(): void {
    this.store.clear();
  }

  getItem(key: string): string | null {
    return this.store.has(key) ? (this.store.get(key) ?? null) : null;
  }

  key(index: number): string | null {
    return Array.from(this.store.keys())[index] ?? null;
  }

  removeItem(key: string): void {
    this.store.delete(key);
  }

  setItem(key: string, value: string): void {
    this.store.set(key, String(value));
  }
}

function install(name: 'localStorage' | 'sessionStorage'): void {
  const memoKey = `__od_${name}`;
  const global = globalThis as Record<string, unknown>;
  const existing = global[memoKey];
  const store = existing instanceof MemoryStorage ? existing : new MemoryStorage();
  global[memoKey] = store;
  Object.defineProperty(globalThis, name, {
    value: store,
    writable: true,
    configurable: true,
  });
}

install('localStorage');
install('sessionStorage');

afterEach(() => {
  cleanup();
  localStorage.clear();
});
