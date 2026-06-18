/**
 * DateRangePicker - 日期范围选择器
 */
import { useState } from 'react';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';

interface DateRangePickerProps {
  startDate: string;
  endDate: string;
  onChange: (start: string, end: string) => void;
}

export default function DateRangePicker({ startDate, endDate, onChange }: DateRangePickerProps) {
  const parseDate = (s: string) => (s ? new Date(s + 'T00:00:00') : null);
  const fmtDate = (d: Date | null) => (d ? d.toISOString().slice(0, 10) : '');
  const [start, setStart] = useState<Date | null>(parseDate(startDate));
  const [end, setEnd] = useState<Date | null>(parseDate(endDate));

  const handleChange = (dates: [Date | null, Date | null]) => {
    const [s, e] = dates;
    setStart(s);
    setEnd(e);
    onChange(fmtDate(s), fmtDate(e));
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <DatePicker
        selected={start}
        onChange={handleChange}
        startDate={start}
        endDate={end}
        selectsRange
        inline
        monthsShown={1}
        dateFormat="yyyy-MM-dd"
        calendarClassName="compact-datepicker"
        dayClassName={(d) => {
          const ds = fmtDate(d);
          if (startDate && endDate && ds >= startDate && ds <= endDate) return 'rdp-in-range';
          if (ds === startDate || ds === endDate) return 'rdp-selected';
          return '';
        }}
      />
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11 }}>
        <span style={{ fontWeight: 500, color: start ? 'var(--accent-primary)' : 'var(--text-tertiary)' }}>
          {startDate || '未选'}
        </span>
        <span style={{ color: 'var(--text-tertiary)' }}>至</span>
        <span style={{ fontWeight: 500, color: end ? 'var(--accent-primary)' : 'var(--text-tertiary)' }}>
          {endDate || '未选'}
        </span>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 3 }}>
          {[
            { label: '清除', fn: () => { setStart(null); setEnd(null); onChange('', ''); } },
            { label: '今天', fn: () => { const t = new Date(); setStart(t); setEnd(new Date(t)); onChange(fmtDate(t), fmtDate(t)); } },
            { label: '7 天', fn: () => { const t = new Date(); const n = new Date(t); n.setDate(t.getDate() + 7); setStart(t); setEnd(n); onChange(fmtDate(t), fmtDate(n)); } },
            { label: '30 天', fn: () => { const t = new Date(); const n = new Date(t); n.setDate(t.getDate() + 30); setStart(t); setEnd(n); onChange(fmtDate(t), fmtDate(n)); } },
          ].map((b) => (
            <button
              key={b.label}
              className="btn btn--ghost btn--sm"
              onClick={b.fn}
              style={{ fontSize: 9, padding: '2px 6px', lineHeight: 1.5 }}
            >
              {b.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}