/**
 * Timezone-aware date/time formatting utilities for Sentinal frontend.
 * Enforces Indian Standard Time (IST / Asia/Kolkata, UTC+05:30) across all user-facing displays.
 */

const IST_TIMEZONE = 'Asia/Kolkata';

/**
 * Format full date and time in IST.
 * Example output: "02 Oct 2026, 23:29:56 IST"
 */
export function formatFullDateTimeIST(value?: string | Date | null): string {
  if (!value) return '—';
  const d = typeof value === 'string' ? new Date(value) : value;
  if (isNaN(d.getTime())) return String(value);

  return new Intl.DateTimeFormat('en-IN', {
    timeZone: IST_TIMEZONE,
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
    timeZoneName: 'short',
  }).format(d);
}

/**
 * Format time of day in IST.
 * Example output: "23:29:56 IST" or with ms: "23:29:56.732 IST"
 */
export function formatTimeIST(
  value?: string | Date | null,
  options: { includeSeconds?: boolean; includeMs?: boolean; includeTz?: boolean } = {
    includeSeconds: true,
    includeTz: true,
  }
): string {
  if (!value) return '—';
  const d = typeof value === 'string' ? new Date(value) : value;
  if (isNaN(d.getTime())) return String(value);

  const formatted = new Intl.DateTimeFormat('en-IN', {
    timeZone: IST_TIMEZONE,
    hour: '2-digit',
    minute: '2-digit',
    second: options.includeSeconds !== false ? '2-digit' : undefined,
    hour12: false,
  }).format(d);

  let result = formatted;
  if (options.includeMs) {
    const ms = String(d.getMilliseconds()).padStart(3, '0');
    result = `${result}.${ms}`;
  }
  if (options.includeTz !== false) {
    result = `${result} IST`;
  }
  return result;
}

/**
 * Format date in short medium style with IST time.
 * Example output: "02 Oct, 23:29:56 IST"
 */
export function formatShortDateIST(value?: string | Date | null): string {
  if (!value) return '—';
  const d = typeof value === 'string' ? new Date(value) : value;
  if (isNaN(d.getTime())) return String(value);

  return new Intl.DateTimeFormat('en-IN', {
    timeZone: IST_TIMEZONE,
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
    timeZoneName: 'short',
  }).format(d);
}
