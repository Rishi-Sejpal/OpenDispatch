import { describe, expect, it } from 'vitest';
import { cn } from './cn';

describe('cn', () => {
  it('joins truthy classes with a single space', () => {
    expect(cn('a', 'b', undefined, 'c', false, '')).toBe('a b c');
  });

  it('returns an empty string when no classes are given', () => {
    expect(cn()).toBe('');
  });
});
