export function cn(...args: Array<string | undefined | false | null>): string {
  return args.filter(Boolean).join(' ');
}
