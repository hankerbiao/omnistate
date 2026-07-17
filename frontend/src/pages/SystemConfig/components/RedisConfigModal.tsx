import { useState, useEffect } from 'react';
import { api } from '../../../services/api';
import type { SystemConfig } from '../../../types';

interface RedisConfigModalProps {
  visible: boolean;
  configs: SystemConfig[];        // redis.* 配置项列表
  onClose: () => void;
  onSaved: () => void;
}

interface RedisFormData {
  sentinel_hosts: string;
  master_name: string;
  username: string;
  password: string;
  db: string;
  socket_timeout: string;
  max_connections: string;
  service_registry_key: string;
}

const FIELD_LABELS: Record<keyof RedisFormData, string> = {
  sentinel_hosts: 'Sentinel 节点',
  master_name: 'Master 名称',
  username: '用户名',
  password: '密码',
  db: '数据库编号',
  socket_timeout: 'Socket 超时 (秒)',
  max_connections: '最大连接数',
  service_registry_key: '服务注册 Key 前缀',
};

const FIELD_PLACEHOLDERS: Record<keyof RedisFormData, string> = {
  sentinel_hosts: 'host:port, 多个以逗号分隔',
  master_name: 'redis_master',
  username: '',
  password: '',
  db: '0',
  socket_timeout: '2',
  max_connections: '100',
  service_registry_key: 'dmlv4:service_registry',
};

const FIELD_TYPES: Record<keyof RedisFormData, 'text' | 'password' | 'number'> = {
  sentinel_hosts: 'text',
  master_name: 'text',
  username: 'text',
  password: 'password',
  db: 'number',
  socket_timeout: 'number',
  max_connections: 'number',
  service_registry_key: 'text',
};

function getConfigValue(configs: SystemConfig[], key: string, defaultValue: string): string {
  return configs.find(c => c.config_key === key)?.config_value ?? defaultValue;
}

/** 将 JSON 数组字符串转为逗号分隔的显示文本 */
function formatHosts(jsonStr: string): string {
  try {
    const arr = JSON.parse(jsonStr);
    return Array.isArray(arr) ? arr.join(', ') : jsonStr;
  } catch {
    return jsonStr;
  }
}

/** 将逗号分隔的文本转为 JSON 数组字符串 */
function parseHosts(text: string): string {
  const items = text
    .split(/[,\s]+/)
    .map(s => s.trim())
    .filter(Boolean);
  return JSON.stringify(items);
}

const RedisConfigModal: React.FC<RedisConfigModalProps> = ({ visible, configs, onClose, onSaved }) => {
  const [form, setForm] = useState<RedisFormData>({
    sentinel_hosts: '',
    master_name: '',
    username: '',
    password: '',
    db: '0',
    socket_timeout: '2',
    max_connections: '100',
    service_registry_key: 'dmlv4:service_registry',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 弹窗打开时，从当前 configs 初始化表单
  useEffect(() => {
    if (!visible) return;
    const hostsRaw = getConfigValue(configs, 'redis.sentinel_hosts', '["localhost:26379"]');
    setForm({
      sentinel_hosts: formatHosts(hostsRaw),
      master_name: getConfigValue(configs, 'redis.master_name', 'redis_master'),
      username: getConfigValue(configs, 'redis.username', ''),
      password: getConfigValue(configs, 'redis.password', ''),
      db: getConfigValue(configs, 'redis.db', '0'),
      socket_timeout: getConfigValue(configs, 'redis.socket_timeout', '2'),
      max_connections: getConfigValue(configs, 'redis.max_connections', '100'),
      service_registry_key: getConfigValue(configs, 'redis.service_registry_key', 'dmlv4:service_registry'),
    });
    setError(null);
  }, [visible, configs]);

  const handleChange = (field: keyof RedisFormData, value: string) => {
    setForm(prev => ({ ...prev, [field]: value }));
    setError(null);
  };

  const handleSave = async () => {
    // 基本验证
    if (!form.sentinel_hosts.trim()) {
      setError('Sentinel 节点不能为空');
      return;
    }
    if (!form.master_name.trim()) {
      setError('Master 名称不能为空');
      return;
    }
    const dbNum = parseInt(form.db);
    if (isNaN(dbNum) || dbNum < 0) {
      setError('数据库编号必须 >= 0');
      return;
    }
    const timeout = parseInt(form.socket_timeout);
    if (isNaN(timeout) || timeout < 1) {
      setError('Socket 超时必须 >= 1');
      return;
    }
    const maxConn = parseInt(form.max_connections);
    if (isNaN(maxConn) || maxConn < 1) {
      setError('最大连接数必须 >= 1');
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await api.batchUpdateSystemConfigs({
        items: [
          { config_key: 'redis.sentinel_hosts', config_value: parseHosts(form.sentinel_hosts) },
          { config_key: 'redis.master_name', config_value: form.master_name.trim() },
          { config_key: 'redis.username', config_value: form.username.trim() },
          { config_key: 'redis.password', config_value: form.password },
          { config_key: 'redis.db', config_value: form.db },
          { config_key: 'redis.socket_timeout', config_value: form.socket_timeout },
          { config_key: 'redis.max_connections', config_value: form.max_connections },
          { config_key: 'redis.service_registry_key', config_value: form.service_registry_key.trim() },
        ],
        remark: '从 Redis 配置弹窗编辑',
      });
      onSaved();
      onClose();
    } catch (err: any) {
      setError('保存失败: ' + (err.message || '未知错误'));
    } finally {
      setSaving(false);
    }
  };

  if (!visible) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content redis-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Redis 配置</h3>
          <button type="button" className="modal-close" onClick={onClose}>×</button>
        </div>

        <div className="modal-body">
          {error && (
            <div className="error-banner">
              <span>⚠ {error}</span>
              <button type="button" onClick={() => setError(null)}>×</button>
            </div>
          )}

          <div className="redis-modal__hint">
            修改 Redis 配置后需要<strong>重启服务</strong>才能生效
          </div>

          {(Object.keys(FIELD_LABELS) as (keyof RedisFormData)[]).map(field => (
            <div className="form-field" key={field}>
              <label className="form-field__label">{FIELD_LABELS[field]}</label>
              <input
                type={FIELD_TYPES[field]}
                className="form-input"
                value={form[field]}
                onChange={e => handleChange(field, e.target.value)}
                placeholder={FIELD_PLACEHOLDERS[field]}
                min={field === 'db' || field === 'socket_timeout' || field === 'max_connections' ? 0 : undefined}
              />
              {field === 'sentinel_hosts' && (
                <span className="form-hint">格式: host1:port1, host2:port2 (逗号或空格分隔)</span>
              )}
            </div>
          ))}
        </div>

        <div className="modal-footer">
          <button type="button" className="btn btn--ghost" onClick={onClose}>取消</button>
          <button type="button" className="btn btn--primary" onClick={handleSave} disabled={saving}>
            {saving ? '保存中...' : '保存'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default RedisConfigModal;
