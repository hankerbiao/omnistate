/** Shared test-case priority labels and colors */

export const PRIORITY_COLORS = {
  P0: '#d93021',
  P1: '#f66a0a',
  P2: '#e3b30e',
  P3: '#0b7ece',
} as const;

export const PRIORITY_LABELS = {
  P0: '紧急',
  P1: '高',
  P2: '中',
  P3: '低',
} as const;

export type PriorityCode = keyof typeof PRIORITY_LABELS;

export const PRIORITY_FILTER_OPTIONS = [
  { value: '', label: '全部' },
  { value: 'P0', label: 'P0 - 最高' },
  { value: 'P1', label: 'P1 - 高' },
  { value: 'P2', label: 'P2 - 中' },
  { value: 'P3', label: 'P3 - 低' },
] as const;
