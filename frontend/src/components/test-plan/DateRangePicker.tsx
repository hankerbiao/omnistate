/**
 * DateRangePicker — Compact date range picker wrapper.
 */
import { useState } from 'react';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';

interface DateRangePickerProps {
  startDate: string;
  endDate: string;
  onChange: (start: string, end: string) => void;
}

export function DateRangePicker({ startDate, endDate, onChange }: DateRangePickerProps) {
  const parseDate = (s: string) => s ? new Date(s + 'T00:00:00') : null;
  const fmtDate = (d: Date | null) => d ? d.toISOString().slice(0, 10) : '';
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
      />
    </div>
  );
}
