import { describe, expect, it } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import { useTheme } from './theme';

describe('useTheme', () => {
  it('defaults to dark theme', () => {
    const { result } = renderHook(() => useTheme());
    expect(result.current[0]).toBe('dark');
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });

  it('toggles the theme and persists it to localStorage', () => {
    const { result } = renderHook(() => useTheme());

    act(() => result.current[1]());
    expect(result.current[0]).toBe('light');
    expect(localStorage.getItem('od_theme')).toBe('light');
    expect(document.documentElement.classList.contains('dark')).toBe(false);

    act(() => result.current[1]());
    expect(result.current[0]).toBe('dark');
    expect(localStorage.getItem('od_theme')).toBe('dark');
  });

  it('respects a stored theme preference', () => {
    localStorage.setItem('od_theme', 'light');
    const { result } = renderHook(() => useTheme());
    expect(result.current[0]).toBe('light');
  });
});
