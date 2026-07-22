// 轻量内联图标集（线性风格，继承 currentColor）
import type { CSSProperties } from "react";

interface IconProps {
  size?: number;
  style?: CSSProperties;
}

const base = (size: number): CSSProperties => ({
  width: size,
  height: size,
  display: "inline-block",
  verticalAlign: "middle",
  flexShrink: 0,
});

export function IconOverview({ size = 18, style }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={{ ...base(size), ...style }}>
      <rect x="3" y="3" width="7" height="9" rx="1.5" />
      <rect x="14" y="3" width="7" height="5" rx="1.5" />
      <rect x="14" y="12" width="7" height="9" rx="1.5" />
      <rect x="3" y="16" width="7" height="5" rx="1.5" />
    </svg>
  );
}

export function IconKey({ size = 18, style }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={{ ...base(size), ...style }}>
      <circle cx="7.5" cy="15.5" r="4.5" />
      <path d="M10.7 12.3 21 2m-4 0 3 3m-6 3 3 3" />
    </svg>
  );
}

export function IconUsers({ size = 18, style }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={{ ...base(size), ...style }}>
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  );
}

export function IconPlay({ size = 18, style }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ ...base(size), ...style }}>
      <path d="m8 5 11 7-11 7V5Z" />
    </svg>
  );
}

export function IconCapability({ size = 18, style }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={{ ...base(size), ...style }}>
      <path d="M8 6h13M8 12h13M8 18h13" />
      <path d="M3 6h.01M3 12h.01M3 18h.01" />
    </svg>
  );
}

export function IconLogs({ size = 18, style }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={{ ...base(size), ...style }}>
      <path d="M14 3v4a1 1 0 0 0 1 1h4" />
      <path d="M17 21H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7l5 5v11a2 2 0 0 1-2 2Z" />
      <path d="M9 13h6M9 17h4" />
    </svg>
  );
}

export function IconMcp({ size = 18, style }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={{ ...base(size), ...style }}>
      <path d="M12 2v4m0 12v4M2 12h4m12 0h4" />
      <circle cx="12" cy="12" r="3.2" />
      <path d="m5.6 5.6 2.8 2.8m7.2 7.2 2.8 2.8m0-12.8-2.8 2.8M8.4 15.6l-2.8 2.8" />
    </svg>
  );
}

export function IconQuota({ size = 18, style }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={{ ...base(size), ...style }}>
      <path d="M4 17a8 8 0 0 1 16 0" />
      <path d="M12 17l4.5-4" />
      <circle cx="12" cy="17" r="1.3" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function IconPlus({ size = 16, style }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ ...base(size), ...style }}>
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

export function IconCopy({ size = 15, style }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={{ ...base(size), ...style }}>
      <rect x="9" y="9" width="12" height="12" rx="2" />
      <path d="M5 15V5a2 2 0 0 1 2-2h10" />
    </svg>
  );
}

export function IconCheck({ size = 14, style }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" style={{ ...base(size), ...style }}>
      <path d="M20 6 9 17l-5-5" />
    </svg>
  );
}

export function IconArrowUp({ size = 14, style }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ ...base(size), ...style }}>
      <path d="M12 19V5M5 12l7-7 7 7" />
    </svg>
  );
}

export function IconArrowDown({ size = 14, style }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ ...base(size), ...style }}>
      <path d="M12 5v14M5 12l7 7 7-7" />
    </svg>
  );
}

export function IconChevron({ size = 16, style }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ ...base(size), ...style }}>
      <path d="m9 18 6-6-6-6" />
    </svg>
  );
}

export function IconTrash({ size = 15, style }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={{ ...base(size), ...style }}>
      <path d="M3 6h18M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2m2 0v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
      <path d="M10 11v6M14 11v6" />
    </svg>
  );
}

export function IconBook({ size = 15, style }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={{ ...base(size), ...style }}>
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20V3H6.5A2.5 2.5 0 0 0 4 5.5v14Z" />
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 22H20" />
    </svg>
  );
}

/** Anthropic 风格四芒星标记 */
export function BrandMark({ size = 22, style }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" style={{ ...base(size), ...style }}>
      <path d="M12 1.5c.4 4.3 1.7 5.6 6 6-4.3.4-5.6 1.7-6 6-.4-4.3-1.7-5.6-6-6 4.3-.4 5.6-1.7 6-6Z" />
      <path d="M18.5 13c.2 2.1.9 2.8 3 3-2.1.2-2.8.9-3 3-.2-2.1-.9-2.8-3-3 2.1-.2 2.8-.9 3-3Z" opacity="0.55" />
    </svg>
  );
}
