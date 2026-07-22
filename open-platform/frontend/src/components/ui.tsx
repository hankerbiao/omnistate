// 通用 UI 组件
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";
import { IconCopy, IconCheck } from "./icons";
import "./ui.css";

/* ---------------- Button ---------------- */
type BtnVariant = "primary" | "secondary" | "ghost" | "danger";
export function Button({
  children,
  variant = "primary",
  size,
  onClick,
  disabled,
  type = "button",
}: {
  children: ReactNode;
  variant?: BtnVariant;
  size?: "sm";
  onClick?: () => void;
  disabled?: boolean;
  type?: "button" | "submit";
}) {
  return (
    <button
      type={type}
      className={`btn btn-${variant}${size === "sm" ? " btn-sm" : ""}`}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  );
}

/* ---------------- Badge ---------------- */
export function Badge({
  children,
  tone = "muted",
  dot = false,
}: {
  children: ReactNode;
  tone?: "success" | "error" | "warning" | "muted" | "live" | "test";
  dot?: boolean;
}) {
  return (
    <span className={`badge badge-${tone}`}>
      {dot && <span className="badge-dot" />}
      {children}
    </span>
  );
}

export function MethodTag({ method }: { method: string }) {
  return <span className={`method method-${method}`}>{method}</span>;
}

/* ---------------- Switch ---------------- */
export function Switch({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: (value: boolean) => void;
  label?: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      className={`switch${checked ? " on" : ""}`}
      onClick={() => onChange(!checked)}
    >
      <span className="switch-thumb" />
    </button>
  );
}

/* ---------------- Card ---------------- */
export function Card({
  children,
  variant,
  style,
}: {
  children: ReactNode;
  variant?: "cream" | "dark";
  style?: React.CSSProperties;
}) {
  const cls = variant === "cream" ? "card card-cream" : variant === "dark" ? "card-dark" : "card";
  return (
    <div className={cls} style={style}>
      {children}
    </div>
  );
}

/* ---------------- Modal ---------------- */
export function Modal({
  title,
  onClose,
  children,
  footer,
  width,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  width?: number;
}) {
  const titleId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const previouslyFocused = document.activeElement as HTMLElement | null;
    const dialog = dialogRef.current;
    const focusable = dialog?.querySelector<HTMLElement>(
      'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [href], [tabindex]:not([tabindex="-1"])',
    );
    focusable?.focus();

    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
        return;
      }
      if (event.key !== "Tab" || !dialog) return;
      const elements = Array.from(
        dialog.querySelectorAll<HTMLElement>(
          'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [href], [tabindex]:not([tabindex="-1"])',
        ),
      );
      if (elements.length === 0) return;
      const first = elements[0];
      const last = elements[elements.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    const previousBodyOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = previousBodyOverflow;
      previouslyFocused?.focus();
    };
  }, [onClose]);

  const modal = (
    <div className="modal-overlay" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <div
        ref={dialogRef}
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        style={width ? { maxWidth: width } : undefined}
      >
        <div className="modal-header">
          <h3 id={titleId} className="title-md">{title}</h3>
          <button className="modal-close" onClick={onClose} aria-label="关闭">
            ×
          </button>
        </div>
        <div className="modal-body">{children}</div>
        {footer && <div className="modal-footer">{footer}</div>}
      </div>
    </div>
  );

  return createPortal(modal, document.body);
}

/* ---------------- Spinner / Empty ---------------- */
export function Loading({ label = "正在加载数据" }: { label?: string }) {
  return (
    <div className="loading-wrap" role="status" aria-live="polite">
      <div className="spinner" aria-hidden="true" />
      <span className="body-sm text-muted">{label}…</span>
    </div>
  );
}

export function Empty({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="empty">
      <div className="title-sm" style={{ color: "var(--muted)" }}>
        {title}
      </div>
      {hint && <div className="body-sm text-muted-soft" style={{ marginTop: 6 }}>{hint}</div>}
    </div>
  );
}

/* ---------------- CopyButton ---------------- */
export function CopyButton({ text, label }: { text: string; label?: string }) {
  const { push } = useToast();
  const [done, setDone] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setDone(true);
      push("已复制到剪贴板", "success");
      setTimeout(() => setDone(false), 1500);
    } catch {
      push("复制失败，请手动选择并复制", "error");
    }
  };
  return (
    <button className="copy-inline" onClick={copy} aria-label={label ?? "复制内容"}>
      {done ? <IconCheck /> : <IconCopy />}
      {label && <span style={{ marginLeft: 4 }}>{label}</span>}
    </button>
  );
}

/* ---------------- CodeBlock（含极简 JSON 高亮） ---------------- */
function highlight(code: string): ReactNode[] {
  const tokens: ReactNode[] = [];
  const regex = /("(?:[^"\\]|\\.)*"\s*:)|("(?:[^"\\]|\\.)*")|(\b-?\d+\.?\d*\b)|([{}[\],])/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let i = 0;
  while ((m = regex.exec(code)) !== null) {
    if (m.index > last) tokens.push(code.slice(last, m.index));
    if (m[1]) tokens.push(<span key={i++} className="tok-key">{m[1]}</span>);
    else if (m[2]) tokens.push(<span key={i++} className="tok-str">{m[2]}</span>);
    else if (m[3]) tokens.push(<span key={i++} className="tok-num">{m[3]}</span>);
    else if (m[4]) tokens.push(<span key={i++} className="tok-punc">{m[4]}</span>);
    last = regex.lastIndex;
  }
  if (last < code.length) tokens.push(code.slice(last));
  return tokens;
}

export function CodeBlock({ code, language }: { code: string; language?: "json" | "bash" | "text" }) {
  return (
    <div className="code-block">
      <CopyButtonDark text={code} />
      <pre>{language === "json" ? highlight(code) : code}</pre>
    </div>
  );
}

function CopyButtonDark({ text }: { text: string }) {
  const { push } = useToast();
  const [done, setDone] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setDone(true);
      push("已复制", "success");
      setTimeout(() => setDone(false), 1500);
    } catch {
      push("复制失败，请手动选择并复制", "error");
    }
  };
  return (
    <button className="code-copy" onClick={copy} aria-label="复制代码">
      {done ? "已复制" : "复制"}
    </button>
  );
}

/* ---------------- Toast Context ---------------- */
type ToastTone = "success" | "error" | "info";
interface ToastItem {
  id: number;
  msg: string;
  tone: ToastTone;
}
interface ToastCtx {
  push: (msg: string, tone?: ToastTone) => void;
}
const ToastContext = createContext<ToastCtx>({ push: () => {} });
export const useToast = () => useContext(ToastContext);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const push = useCallback((msg: string, tone: ToastTone = "info") => {
    const id = Date.now() + Math.random();
    setItems((prev) => [...prev, { id, msg, tone }]);
    setTimeout(() => setItems((prev) => prev.filter((t) => t.id !== id)), 2600);
  }, []);
  return (
    <ToastContext.Provider value={{ push }}>
      {children}
      <div className="toast-stack" aria-live="polite" aria-atomic="true">
        {items.map((t) => (
          <div key={t.id} className={`toast toast-${t.tone}`} role={t.tone === "error" ? "alert" : "status"}>
            <span className="toast-icon" aria-hidden="true" />
            {t.msg}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
