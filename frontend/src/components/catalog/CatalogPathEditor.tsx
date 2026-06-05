import React, { useCallback, useEffect, useId, useMemo, useRef, useState } from 'react';
import { api } from '../../services/api';
import { getCatalogLabs } from '../../services/catalogLabsCache';
import type { CatalogLab } from '../../types';
import { catalogStyles } from './catalogStyles';

export interface CatalogPathValue {
  labId: string;
  segments: string[];
}

interface CatalogPathEditorProps {
  value: CatalogPathValue;
  onChange: (value: CatalogPathValue) => void;
  /** When provided, skips fetching labs (shared with parent page). */
  labs?: CatalogLab[];
  disabled?: boolean;
  /** Lock Lab select when inherited from tree */
  lockLab?: boolean;
  /** Prefix segments cannot be edited or removed (from tree selection) */
  lockedPrefix?: string[];
  titlePreview?: string;
  showValidation?: boolean;
  compact?: boolean;
}

const SUGGEST_DEBOUNCE_MS = 280;

function useDebounced<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = window.setTimeout(() => setDebounced(value), ms);
    return () => window.clearTimeout(t);
  }, [value, ms]);
  return debounced;
}

const CatalogPathEditor: React.FC<CatalogPathEditorProps> = ({
  value,
  onChange,
  labs: labsProp,
  disabled = false,
  lockLab = false,
  lockedPrefix = [],
  titlePreview = '',
  showValidation = false,
  compact = false,
}) => {
  const baseId = useId();
  const [fetchedLabs, setFetchedLabs] = useState<CatalogLab[]>([]);
  const [labsFetchDone, setLabsFetchDone] = useState(labsProp !== undefined);
  const [suggestions, setSuggestions] = useState<string[][]>([]);
  const labs = labsProp ?? fetchedLabs;
  const loadingLabs = labsProp === undefined && !labsFetchDone;
  const [activeSegIndex, setActiveSegIndex] = useState<number | null>(null);
  const [highlightIdx, setHighlightIdx] = useState(0);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const debouncedSegments = useDebounced(value.segments, SUGGEST_DEBOUNCE_MS);
  const debouncedLabId = useDebounced(value.labId, SUGGEST_DEBOUNCE_MS);

  const lockedCount = lockedPrefix.length;

  const fetchSuggestions = useCallback(async (labId: string, segments: string[]) => {
    if (!labId) {
      setSuggestions([]);
      return;
    }
    const next: string[][] = [];
    for (let i = 0; i < segments.length; i++) {
      const parent = segments.slice(0, i);
      try {
        const resp = await api.getCatalogSuggestions(labId, parent);
        next[i] = resp.data?.segments || [];
      } catch {
        next[i] = [];
      }
    }
    try {
      const resp = await api.getCatalogSuggestions(labId, segments);
      next[segments.length] = resp.data?.segments || [];
    } catch {
      next[segments.length] = [];
    }
    setSuggestions(next);
  }, []);

  useEffect(() => {
    if (labsProp !== undefined) return;
    let cancelled = false;
    getCatalogLabs({ active_only: true })
      .then(items => {
        if (!cancelled) setFetchedLabs(items);
      })
      .catch(err => {
        console.error('Failed to load labs:', err);
        if (!cancelled) setFetchedLabs([]);
      })
      .finally(() => {
        if (!cancelled) setLabsFetchDone(true);
      });
    return () => { cancelled = true; };
  }, [labsProp]);

  useEffect(() => {
    if (debouncedLabId) {
      fetchSuggestions(debouncedLabId, debouncedSegments);
    } else {
      setSuggestions([]);
    }
  }, [debouncedLabId, debouncedSegments, fetchSuggestions]);

  useEffect(() => {
    const onDocClick = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setActiveSegIndex(null);
      }
    };
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, []);

  const selectedLab = labs.find(l => l.lab_id === value.labId);

  const filledSegments = useMemo(
    () => value.segments.map(s => s.trim()).filter(Boolean),
    [value.segments],
  );

  const breadcrumbParts = useMemo(() => {
    if (!selectedLab) return [] as string[];
    const parts = [selectedLab.name, ...filledSegments];
    const title = titlePreview.trim();
    if (title) parts.push(title);
    return parts;
  }, [selectedLab, filledSegments, titlePreview]);

  const hasValidPath = Boolean(value.labId) && filledSegments.length >= 1;
  const showPathError = showValidation && value.labId && filledSegments.length === 0;

  const handleLabChange = (labId: string) => {
    if (lockLab) return;
    if (labId !== value.labId) {
      const baseSegs = lockedCount > 0 ? [...lockedPrefix] : [''];
      onChange({ labId, segments: baseSegs });
      return;
    }
    onChange({ labId, segments: value.segments.length ? value.segments : [''] });
  };

  const handleSegmentChange = (index: number, segment: string) => {
    if (index < lockedCount) return;
    const next = [...value.segments];
    next[index] = segment;
    onChange({ ...value, segments: next });
  };

  const pickSuggestion = (index: number, name: string) => {
    handleSegmentChange(index, name);
    setActiveSegIndex(null);
  };

  const addSegment = () => {
    onChange({ ...value, segments: [...value.segments, ''] });
    setActiveSegIndex(value.segments.length);
  };

  const removeSegment = (index: number) => {
    if (index < lockedCount || value.segments.length <= 1) return;
    const next = value.segments.filter((_, i) => i !== index);
    onChange({ ...value, segments: next.length ? next : [''] });
  };

  const filteredSuggestions = (index: number): string[] => {
    const list = suggestions[index] || [];
    const q = (value.segments[index] || '').trim().toLowerCase();
    if (!q) return list;
    return list.filter(s => s.toLowerCase().includes(q));
  };

  const showDropdown = (index: number): boolean =>
    activeSegIndex === index && Boolean(value.labId) && !disabled && index >= lockedCount;

  const renderSegmentInput = (segment: string, index: number) => {
    const isLocked = index < lockedCount;
    const list = filteredSuggestions(index);
    const typed = segment.trim();
    const canCreate = typed && !list.some(s => s.toLowerCase() === typed.toLowerCase());

    return (
      <div
        key={index}
        style={{ ...styles.segmentEditorWrap, ...(isLocked ? styles.segmentLocked : {}) }}
        ref={showDropdown(index) ? dropdownRef : undefined}
      >
        {isLocked ? (
          <span style={{ ...catalogStyles.chip, ...catalogStyles.chipLocked }}>
            {segment}
          </span>
        ) : (
          <>
            <input
              id={`${baseId}-seg-${index}`}
              className="form-input"
              style={{
                ...styles.segmentInput,
                ...(showPathError && !segment.trim() ? styles.inputInvalid : {}),
              }}
              value={segment}
              placeholder={`路径段 ${index + 1}`}
              onChange={e => handleSegmentChange(index, e.target.value)}
              onFocus={() => {
                setActiveSegIndex(index);
                setHighlightIdx(0);
              }}
              onKeyDown={e => {
                if (!showDropdown(index)) return;
                if (e.key === 'ArrowDown') {
                  e.preventDefault();
                  setHighlightIdx(i => Math.min(i + 1, list.length + (canCreate ? 1 : 0) - 1));
                } else if (e.key === 'ArrowUp') {
                  e.preventDefault();
                  setHighlightIdx(i => Math.max(i - 1, 0));
                } else if (e.key === 'Enter' && list.length > 0) {
                  e.preventDefault();
                  const pick = list[highlightIdx] ?? list[0];
                  if (pick) pickSuggestion(index, pick);
                } else if (e.key === 'Escape') {
                  setActiveSegIndex(null);
                }
              }}
              disabled={disabled}
              autoComplete="off"
              aria-expanded={showDropdown(index) ? true : false}
              aria-controls={`${baseId}-suggest-${index}`}
            />
            {showDropdown(index) && (list.length > 0 || canCreate) && (
              <div id={`${baseId}-suggest-${index}`} style={catalogStyles.suggestionPanel} role="listbox">
                {list.map((s, i) => (
                  <button
                    key={s}
                    type="button"
                    role="option"
                    aria-selected={i === highlightIdx}
                    style={{
                      ...catalogStyles.suggestionItem,
                      ...(i === highlightIdx ? styles.suggestionHighlight : {}),
                    }}
                    onMouseDown={e => {
                      e.preventDefault();
                      pickSuggestion(index, s);
                    }}
                  >
                    {s}
                  </button>
                ))}
                {canCreate && (
                  <button
                    type="button"
                    role="option"
                    style={{
                      ...catalogStyles.suggestionItem,
                      ...styles.suggestionCreate,
                      ...(highlightIdx === list.length ? styles.suggestionHighlight : {}),
                    }}
                    onMouseDown={e => {
                      e.preventDefault();
                      pickSuggestion(index, typed);
                    }}
                  >
                    使用「{typed}」
                  </button>
                )}
              </div>
            )}
          </>
        )}
        {!isLocked && value.segments.length > lockedCount && (
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            style={styles.removeBtn}
            onClick={() => removeSegment(index)}
            disabled={disabled}
            aria-label={`删除路径段 ${index + 1}`}
          >
            ×
          </button>
        )}
      </div>
    );
  };

  return (
    <div style={{ ...styles.root, ...(compact ? styles.rootCompact : {}) }}>
      <div style={styles.field}>
        <label style={styles.fieldLabel} htmlFor={`${baseId}-lab`}>
          实验室 (Lab)
          <span style={styles.required}>*</span>
          {lockLab && <span style={styles.lockHint}>继承自目录树</span>}
        </label>
        <select
          id={`${baseId}-lab`}
          className="form-input form-select"
          style={styles.select}
          value={value.labId}
          onChange={e => handleLabChange(e.target.value)}
          disabled={disabled || loadingLabs || lockLab}
        >
          <option value="">{loadingLabs ? '加载中…' : '选择 Lab'}</option>
          {labs.map(lab => (
            <option key={lab.lab_id} value={lab.lab_id}>
              {lab.name} ({lab.code})
            </option>
          ))}
        </select>
        {!value.labId && showValidation && (
          <span style={styles.fieldError}>请选择实验室</span>
        )}
      </div>

      {value.labId && lockedCount > 0 && (
        <div style={styles.chipsRow} aria-label="已锁定路径前缀">
          <span style={{ ...catalogStyles.chip, ...catalogStyles.chipLab }}>{selectedLab?.name}</span>
          {lockedPrefix.map((seg, i) => (
            <React.Fragment key={`${seg}-${i}`}>
              <span style={styles.sep}>/</span>
              <span style={{ ...catalogStyles.chip, ...catalogStyles.chipLocked }}>{seg}</span>
            </React.Fragment>
          ))}
        </div>
      )}

      <div style={styles.pathBlock}>
        <div style={styles.pathHeader}>
          <span style={styles.pathTitle}>
            目录路径
            <span style={styles.required}>*</span>
          </span>
          {!compact && (
            <span style={styles.pathHint}>输入或从建议中选择 · 至少 1 段</span>
          )}
        </div>

        {!value.labId ? (
          <p style={styles.pathPlaceholder}>请先选择 Lab，再填写路径段</p>
        ) : (
          <div style={styles.segmentList}>
            {(lockedCount > 0
              ? value.segments.slice(lockedCount)
              : value.segments
            ).map((segment, offset) => {
              const index = lockedCount > 0 ? lockedCount + offset : offset;
              return renderSegmentInput(segment, index);
            })}
          </div>
        )}

        {showPathError && (
          <span style={styles.fieldError}>请填写至少一段目录路径</span>
        )}

        <button
          type="button"
          className="btn btn--secondary btn--sm"
          style={styles.addBtn}
          onClick={addSegment}
          disabled={disabled || !value.labId}
        >
          + 添加一级
        </button>
      </div>

      <div
        style={{
          ...catalogStyles.previewBar,
          ...(hasValidPath ? catalogStyles.previewBarActive : {}),
        }}
        aria-live="polite"
      >
        <span style={catalogStyles.labelCaps}>路径预览</span>
        {breadcrumbParts.length > 0 ? (
          <div style={styles.previewChips}>
            {breadcrumbParts.map((part, i) => (
              <React.Fragment key={`${part}-${i}`}>
                {i > 0 && <span style={styles.sep}>/</span>}
                <span
                  style={{
                    ...catalogStyles.chip,
                    ...(i === 0 ? catalogStyles.chipLab : {}),
                    ...(i === breadcrumbParts.length - 1 && titlePreview.trim()
                      ? styles.chipTitle
                      : {}),
                  }}
                >
                  {part}
                </span>
              </React.Fragment>
            ))}
          </div>
        ) : (
          <span style={styles.previewPlaceholder}>选择 Lab 并填写路径段后显示完整面包屑</span>
        )}
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  root: {
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-4)',
  },
  rootCompact: {
    gap: 'var(--space-3)',
  },
  field: {
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-2)',
  },
  fieldLabel: {
    fontSize: 12,
    fontWeight: 600,
    color: 'var(--text-secondary)',
    textTransform: 'uppercase',
    letterSpacing: '0.4px',
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-2)',
    flexWrap: 'wrap',
  },
  lockHint: {
    fontSize: 11,
    fontWeight: 500,
    color: 'var(--text-tertiary)',
    textTransform: 'none',
    letterSpacing: 0,
  },
  required: {
    color: 'var(--status-error)',
  },
  select: {
    cursor: 'pointer',
  },
  chipsRow: {
    display: 'flex',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: 'var(--space-1)',
    padding: 'var(--space-2) var(--space-3)',
    ...catalogStyles.cardInset,
  },
  sep: {
    color: 'var(--text-tertiary)',
    fontSize: 12,
    userSelect: 'none',
  },
  pathBlock: {
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-3)',
  },
  pathHeader: {
    display: 'flex',
    flexWrap: 'wrap',
    alignItems: 'baseline',
    gap: 'var(--space-2)',
  },
  pathTitle: {
    fontSize: 12,
    fontWeight: 600,
    color: 'var(--text-secondary)',
    textTransform: 'uppercase',
    letterSpacing: '0.4px',
  },
  pathHint: {
    fontSize: 12,
    color: 'var(--text-tertiary)',
  },
  pathPlaceholder: {
    margin: 0,
    padding: 'var(--space-3) var(--space-4)',
    fontSize: 13,
    color: 'var(--text-tertiary)',
    ...catalogStyles.cardInset,
    borderStyle: 'dashed',
  },
  segmentList: {
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-2)',
  },
  segmentEditorWrap: {
    position: 'relative',
    display: 'flex',
    gap: 'var(--space-2)',
    alignItems: 'center',
  },
  segmentLocked: {
    justifyContent: 'flex-start',
  },
  segmentInput: {
    flex: 1,
  },
  inputInvalid: {
    borderColor: 'var(--status-error)',
  },
  removeBtn: {
    flexShrink: 0,
    minWidth: 32,
  },
  addBtn: {
    alignSelf: 'flex-start',
  },
  fieldError: {
    fontSize: 12,
    color: 'var(--status-error)',
  },
  suggestionHighlight: {
    backgroundColor: 'var(--surface-hover)',
  },
  suggestionCreate: {
    color: 'var(--accent-primary)',
    fontWeight: 500,
    borderTop: '1px solid var(--border-subtle)',
  },
  previewChips: {
    display: 'flex',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: 'var(--space-1)',
  },
  previewPlaceholder: {
    fontSize: 13,
    color: 'var(--text-tertiary)',
  },
  chipTitle: {
    borderStyle: 'dashed',
    fontWeight: 600,
  },
};

export default CatalogPathEditor;
