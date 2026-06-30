/**
 * DateRangePicker — Compact inline calendar with range selection.
 * Uses react-datepicker's selectsRange mode.
 * No separate "start" and "end" inputs — pick both on one calendar.
 */
import DatePicker from 'react-datepicker';
import { zhCN } from 'date-fns/locale';
import 'react-datepicker/dist/react-datepicker.css';

/* ── Date string ↔ Date helpers (YYYY-MM-DD) ── */
function parseDate(s: string): Date | null {
  if (!s) return null;
  const [y, m, d] = s.split('-').map(Number);
  if (!y || !m || !d) return null;
  return new Date(y, m - 1, d);
}

function formatDate(d: Date | null): string {
  if (!d) return '';
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

/* ── Props ── */
interface DateRangePickerProps {
  startDate: string;
  endDate: string;
  onChange: (start: string, end: string) => void;
}

export function DateRangePicker({ startDate, endDate, onChange }: DateRangePickerProps) {
  const start = parseDate(startDate);
  const end = parseDate(endDate);

  const handleChange = (dates: [Date | null, Date | null]) => {
    const [s, e] = dates;
    onChange(formatDate(s), formatDate(e));
  };

  return (
    <div className="flex flex-col items-center">
      {/* ── Selected range indicator ── */}
      <div className="w-full flex items-center justify-center gap-2 mb-2.5 text-sm">
        <span className={`px-2.5 py-1 rounded-md font-medium tabular-nums ${
          startDate ? 'text-[var(--accent-primary)] bg-[var(--accent-primary)]/8' : 'text-[var(--text-tertiary)]'
        }`}>
          {startDate || '开始日期'}
        </span>
        <span className="text-[var(--text-tertiary)]">→</span>
        <span className={`px-2.5 py-1 rounded-md font-medium tabular-nums ${
          endDate ? 'text-[var(--accent-primary)] bg-[var(--accent-primary)]/8' : 'text-[var(--text-tertiary)]'
        }`}>
          {endDate || '结束日期'}
        </span>
      </div>

      {/* ── Inline calendar ── */}
      <div className="w-full max-w-[320px]">
        <DatePicker
          selectsRange
          inline
          monthsShown={1}
          locale={zhCN}
          startDate={start ?? undefined}
          endDate={end ?? undefined}
          onChange={handleChange as any}
          calendarClassName="compact-datepicker"
          disabledKeyboardNavigation
        />
      </div>
    </div>
  );
}
