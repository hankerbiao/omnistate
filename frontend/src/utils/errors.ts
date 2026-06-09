export function getErrorMessage(err: unknown, fallback: string): string {
  if (err instanceof Error) return `${fallback}: ${err.message}`;
  return fallback;
}
