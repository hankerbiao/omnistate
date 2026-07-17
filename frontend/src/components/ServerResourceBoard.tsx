import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Search, Server, MapPin, Cpu, Check, Folder, Layers, Eye, EyeOff, Loader2 } from 'lucide-react';
import { Dialog, DialogContent } from './ui/dialog';
import {
  fetchServerResources,
  SERVER_STATUS_LABEL,
  type ServerResource,
  type ServerStatus,
} from '../services/serverResourceService';

interface Props {
  /** 当前已回填的 BMC IP，用于高亮已选卡片 */
  currentBmcIp?: string;
  onClose: () => void;
  onSelect: (server: ServerResource) => void;
}

const STATUS_COLOR: Record<ServerStatus, { dot: string; text: string; bg: string }> = {
  online: { dot: '#3fb950', text: '#3fb950', bg: 'rgba(63,185,80,0.12)' },
  offline: { dot: '#f85149', text: '#f85149', bg: 'rgba(248,81,73,0.12)' },
  maintenance: { dot: '#d29922', text: '#d29922', bg: 'rgba(210,153,34,0.12)' },
};

/** 占用（正在执行任务）标识样式 */
const BUSY = { dot: '#a371f7', text: '#a371f7', bg: 'rgba(163,113,247,0.14)' };

const FILTERS: { key: ServerStatus | 'all'; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'online', label: '在线' },
  { key: 'offline', label: '离线' },
  { key: 'maintenance', label: '维护中' },
];

/** 单台服务器卡片 */
function ServerCard({
  server,
  isCurrent,
  onSelect,
}: {
  server: ServerResource;
  isCurrent: boolean;
  onSelect: (s: ServerResource) => void;
}) {
  const color = STATUS_COLOR[server.status];
  const [showPassword, setShowPassword] = useState(false);
  return (
    <div
      style={{
        border: `1px solid ${isCurrent ? 'var(--accent-primary)' : 'var(--border-subtle)'}`,
        borderRadius: 12, padding: 14,
        background: isCurrent ? 'color-mix(in srgb, var(--accent-primary) 6%, transparent)' : 'var(--bg-primary)',
        display: 'flex', flexDirection: 'column', gap: 10,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
          <Server size={16} style={{ color: 'var(--text-secondary)', flexShrink: 0 }} />
          <span style={{ fontSize: 13, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{server.hostname}</span>
        </div>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: 5, flexShrink: 0 }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 11, padding: '2px 8px', borderRadius: 10, background: color.bg, color: color.text }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: color.dot }} />
            {SERVER_STATUS_LABEL[server.status]}
          </span>
          {server.in_use && (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 11, padding: '2px 8px', borderRadius: 10, background: BUSY.bg, color: BUSY.text, fontWeight: 600 }}>
              <Loader2 size={11} style={{ animation: 'spin 1s linear infinite' }} />
              执行中
            </span>
          )}
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 12 }}>
        <div style={{ display: 'flex', gap: 8 }}>
          <span style={{ color: 'var(--text-tertiary)', width: 64, flexShrink: 0 }}>BMC IP</span>
          <span style={{ fontFamily: 'monospace', color: 'var(--text-primary)' }}>{server.bmc_ip}</span>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <span style={{ color: 'var(--text-tertiary)', width: 64, flexShrink: 0 }}>用户名</span>
          <span style={{ fontFamily: 'monospace', color: 'var(--text-primary)' }}>{server.bmc_username}</span>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <span style={{ color: 'var(--text-tertiary)', width: 64, flexShrink: 0 }}>密码</span>
          <span style={{ fontFamily: 'monospace', color: showPassword ? 'var(--text-primary)' : 'var(--text-tertiary)', letterSpacing: showPassword ? 0 : 1 }}>
            {showPassword ? server.bmc_password : '••••••••'}
          </span>
          <button
            type="button"
            onClick={() => setShowPassword((v) => !v)}
            title={showPassword ? '隐藏密码' : '查看明文密码'}
            aria-label={showPassword ? '隐藏密码' : '查看明文密码'}
            style={{
              display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
              background: 'none', border: 'none', cursor: 'pointer', padding: 2,
              color: 'var(--text-tertiary)', flexShrink: 0,
            }}
          >
            {showPassword ? <EyeOff size={13} /> : <Eye size={13} />}
          </button>
        </div>
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
        {server.in_use && server.current_task && (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 11, color: BUSY.text, background: BUSY.bg, padding: '2px 8px', borderRadius: 6 }}>
            <Loader2 size={11} style={{ animation: 'spin 1s linear infinite' }} /> {server.current_task.name}
          </span>
        )}
        {server.project && (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 11, color: 'var(--text-secondary)', background: 'var(--surface-tertiary)', padding: '2px 8px', borderRadius: 6 }}>
            <Folder size={11} /> {server.project}
          </span>
        )}
        {server.model && (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 11, color: 'var(--text-secondary)', background: 'var(--surface-tertiary)', padding: '2px 8px', borderRadius: 6 }}>
            <Cpu size={11} /> {server.model}
          </span>
        )}
        {server.location && (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 11, color: 'var(--text-secondary)', background: 'var(--surface-tertiary)', padding: '2px 8px', borderRadius: 6 }}>
            <MapPin size={11} /> {server.location}
          </span>
        )}
      </div>

      <button
        className="btn btn--primary"
        style={{ width: '100%', padding: '6px 0', fontSize: 13, fontWeight: 600, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}
        onClick={() => onSelect(server)}
        disabled={server.status === 'offline' || !!server.in_use}
        title={server.status === 'offline' ? '离线服务器不可选' : (server.in_use ? '服务器正在执行任务，暂不可用' : undefined)}
      >
        {isCurrent ? (<><Check size={14} /> 已选 · 重新回填</>) : (server.status === 'offline' ? '离线不可用' : (server.in_use ? '执行中 · 暂不可用' : '选择并回填'))}
      </button>
    </div>
  );
}

/**
 * 服务器资源看板（由父组件在打开时挂载，关闭时卸载，因此使用初始 state 即可）。
 * 布局：左侧项目导航（潮白河 / 蓟运河 / 永定河 / 全部），右侧搜索 + 状态筛选 + 卡片网格。
 */
const ServerResourceBoard: React.FC<Props> = ({ currentBmcIp, onClose, onSelect }) => {
  const [servers, setServers] = useState<ServerResource[]>([]);
  const [loading, setLoading] = useState(true);
  const [keyword, setKeyword] = useState('');
  const [statusFilter, setStatusFilter] = useState<ServerStatus | 'all'>('all');
  const [selectedProject, setSelectedProject] = useState<string>('all');

  useEffect(() => {
    let active = true;
    fetchServerResources()
      .then((data) => { if (active) setServers(data); })
      .catch(() => { if (active) setServers([]); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  // 项目列表 + 各项目服务器总数（不受状态/关键词筛选影响）
  const projectList = useMemo(() => {
    const map = new Map<string, number>();
    servers.forEach((s) => {
      const k = s.project || '未分类';
      map.set(k, (map.get(k) || 0) + 1);
    });
    return Array.from(map.entries()).sort((a, b) => a[0].localeCompare(b[0], 'zh'));
  }, [servers]);

  const filtered = servers.filter((s) => {
    if (selectedProject !== 'all' && (s.project || '未分类') !== selectedProject) return false;
    if (statusFilter !== 'all' && s.status !== statusFilter) return false;
    if (!keyword.trim()) return true;
    const kw = keyword.trim().toLowerCase();
    return (
      s.hostname.toLowerCase().includes(kw) ||
      s.bmc_ip.toLowerCase().includes(kw) ||
      (s.model || '').toLowerCase().includes(kw) ||
      (s.location || '').toLowerCase().includes(kw) ||
      (s.project || '').toLowerCase().includes(kw)
    );
  });

  // 「全部项目」时按项目分组；选中具体项目时直接展示该组
  const groups = useMemo(() => {
    if (selectedProject !== 'all') return [[selectedProject, filtered]] as [string, ServerResource[]][];
    const map = new Map<string, ServerResource[]>();
    for (const s of filtered) {
      const key = s.project || '未分类';
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(s);
    }
    return Array.from(map.entries());
  }, [filtered, selectedProject]);

  const handleSelect = useCallback((s: ServerResource) => {
    onSelect(s);
  }, [onSelect]);

  return (
    <Dialog open onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="sm:max-w-[820px]" style={{ padding: 0, overflow: 'hidden' }}>
        {/* Header */}
        <div style={{ padding: '16px 20px 12px', borderBottom: '1px solid var(--border-subtle)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Server size={18} style={{ color: 'var(--accent-primary)' }} />
            <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>服务器资源看板</h3>
            <span style={{ fontSize: 10, padding: '1px 8px', borderRadius: 4, background: 'rgba(210,153,34,0.14)', color: '#d29922', fontWeight: 600 }}>Mock 数据</span>
          </div>
          <p style={{ margin: '6px 0 0', fontSize: 12, color: 'var(--text-tertiary)' }}>
            由 TMMS 服务提供可用服务器的 BMC 信息，选择一台即可回填下发参数；按河系项目分类浏览。
          </p>
        </div>

        {/* 主体：左侧项目导航 + 右侧列表 */}
        <div style={{ display: 'flex', height: '60vh' }}>
          {/* 侧边栏：项目导航 */}
          <aside style={{
            width: 184, flexShrink: 0, borderRight: '1px solid var(--border-subtle)',
            background: 'var(--surface-secondary, var(--bg-primary))', padding: 12, overflowY: 'auto',
            display: 'flex', flexDirection: 'column', gap: 4,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.4px', padding: '0 6px 6px' }}>
              <Layers size={12} /> 项目
            </div>
            <button
              onClick={() => setSelectedProject('all')}
              style={navItemStyle(selectedProject === 'all')}
            >
              <Folder size={14} />
              <span style={{ flex: 1, textAlign: 'left' }}>全部项目</span>
              <span style={navCountStyle(selectedProject === 'all')}>{servers.length}</span>
            </button>
            {projectList.map(([name, count]) => (
              <button
                key={name}
                onClick={() => setSelectedProject(name)}
                style={navItemStyle(selectedProject === name)}
              >
                <Folder size={14} />
                <span style={{ flex: 1, textAlign: 'left', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{name}</span>
                <span style={navCountStyle(selectedProject === name)}>{count}</span>
              </button>
            ))}
          </aside>

          {/* 右侧：工具栏 + 卡片区 */}
          <main style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}>
            {/* 工具栏 */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '12px 16px', flexWrap: 'wrap', borderBottom: '1px solid var(--border-subtle)' }}>
              <div style={{ position: 'relative', flex: 1, minWidth: 180 }}>
                <Search size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-tertiary)' }} />
                <input
                  className="form-input"
                  style={{ width: '100%', paddingLeft: 30, fontSize: 13 }}
                  placeholder="搜索主机名 / BMC IP / 机型 / 位置 / 项目"
                  value={keyword}
                  onChange={(e) => setKeyword(e.target.value)}
                />
              </div>
              <div style={{ display: 'flex', gap: 6 }}>
                {FILTERS.map((f) => (
                  <button
                    key={f.key}
                    onClick={() => setStatusFilter(f.key)}
                    style={{
                      padding: '5px 12px', fontSize: 12, borderRadius: 16, cursor: 'pointer',
                      border: '1px solid var(--border-subtle)',
                      background: statusFilter === f.key ? 'var(--accent-primary)' : 'var(--bg-primary)',
                      color: statusFilter === f.key ? '#fff' : 'var(--text-secondary)',
                      fontWeight: statusFilter === f.key ? 600 : 400,
                    }}
                  >
                    {f.label}
                  </button>
                ))}
              </div>
            </div>

            {/* 卡片区 */}
            <div style={{ flex: 1, padding: '12px 16px', overflowY: 'auto' }}>
              {loading ? (
                <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 13 }}>加载服务器资源...</div>
              ) : filtered.length === 0 ? (
                <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 13 }}>未找到匹配的服务器资源</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  {groups.map(([project, list]) => (
                    <div key={project}>
                      {selectedProject === 'all' && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, margin: '0 0 10px' }}>
                          <Folder size={14} style={{ color: 'var(--text-secondary)' }} />
                          <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{project}</span>
                          <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{list.length} 台</span>
                          <div style={{ flex: 1, height: 1, background: 'var(--border-subtle)' }} />
                        </div>
                      )}
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 12 }}>
                        {list.map((s) => (
                          <ServerCard
                            key={s.id}
                            server={s}
                            isCurrent={!!currentBmcIp && currentBmcIp === s.bmc_ip}
                            onSelect={handleSelect}
                          />
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </main>
        </div>
      </DialogContent>
    </Dialog>
  );
};

/** 侧边栏导航项样式 */
function navItemStyle(active: boolean): React.CSSProperties {
  return {
    display: 'flex', alignItems: 'center', gap: 8,
    padding: '8px 10px', borderRadius: 8, cursor: 'pointer', fontSize: 13,
    border: '1px solid transparent',
    background: active ? 'var(--accent-primary)' : 'transparent',
    color: active ? '#fff' : 'var(--text-secondary)',
    fontWeight: active ? 600 : 400,
  };
}

function navCountStyle(active: boolean): React.CSSProperties {
  return {
    fontSize: 11, padding: '0 6px', borderRadius: 8, minWidth: 20, textAlign: 'center',
    background: active ? 'rgba(255,255,255,0.22)' : 'var(--surface-tertiary)',
    color: active ? '#fff' : 'var(--text-tertiary)',
  };
}

export default ServerResourceBoard;
