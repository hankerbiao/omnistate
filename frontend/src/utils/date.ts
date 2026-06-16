import { format, formatDistanceToNow, parseISO, isValid } from 'date-fns';
import { zhCN } from 'date-fns/locale';

/**
 * 解析后端返回的日期字符串。
 * 后端存储为 UTC，但返回的 ISO 字符串不带时区后缀（如 "2026-06-16T06:19:31.118000"），
 * 需要显式追加 Z 标记为 UTC 时间，避免 parseISO 误当作本地时间解析。
 */
function parseDate(date: string | Date): Date {
  if (typeof date !== 'string') return date;
  const normalized = /[Z+-]\d{2}:\d{2}$/.test(date) ? date : date + 'Z';
  const d = parseISO(normalized);
  return isValid(d) ? d : new Date(NaN);
}

/**
 * 格式化日期为 yyyy-MM-dd
 */
export function formatDate(date: string | Date): string {
  const d = parseDate(date);
  if (!isValid(d)) return '—';
  return format(d, 'yyyy-MM-dd');
}

/**
 * 格式化日期时间为 yyyy-MM-dd HH:mm
 */
export function formatDateTime(date: string | Date): string {
  const d = parseDate(date);
  if (!isValid(d)) return '—';
  return format(d, 'yyyy-MM-dd HH:mm');
}

/**
 * 格式化相对时间（如"3 分钟前"）
 */
export function formatRelativeTime(date: string | Date): string {
  const d = parseDate(date);
  if (!isValid(d)) return '—';
  return formatDistanceToNow(d, { addSuffix: true, locale: zhCN });
}

/**
 * 格式化短日期（用于移动端或紧凑布局）
 */
export function formatShortDate(date: string | Date): string {
  const d = parseDate(date);
  if (!isValid(d)) return '—';
  return format(d, 'MM-dd');
}

/**
 * 格式化时间（仅时间部分）
 */
export function formatTime(date: string | Date): string {
  const d = parseDate(date);
  if (!isValid(d)) return '—';
  return format(d, 'HH:mm');
}
