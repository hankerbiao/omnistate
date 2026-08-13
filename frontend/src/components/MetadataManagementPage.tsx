import { useCallback, useEffect, useMemo, useState } from 'react';
import { Plus, Search, Pencil, PowerOff, X } from 'lucide-react';
import { api } from '../services/api';
import type { CreateTestCaseMetadataRequest, MetadataTypeDefinition, TestCaseMetadataOption } from '../types';

const emptyForm: CreateTestCaseMetadataRequest = { type_code: 'TEST_CATEGORY', code: '', name: '', description: '', color: '', sort_order: 0, is_active: true, is_default: false };

export default function MetadataManagementPage() {
  const [definitions, setDefinitions] = useState<MetadataTypeDefinition[]>([]);
  const [items, setItems] = useState<TestCaseMetadataOption[]>([]);
  const [activeType, setActiveType] = useState('TEST_CATEGORY');
  const [query, setQuery] = useState('');
  const [activeFilter, setActiveFilter] = useState('all');
  const [form, setForm] = useState<CreateTestCaseMetadataRequest>(emptyForm);
  const [editing, setEditing] = useState<TestCaseMetadataOption | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.listMetadata({ type_code: activeType, q: query || undefined, active: activeFilter === 'all' ? undefined : activeFilter === 'active' });
      setItems(response.data.items);
      if (!definitions.length) {
        const types = await api.listTestCaseMetadataTypes();
        setDefinitions(types.data.definitions);
      }
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载元数据失败');
    } finally { setLoading(false); }
  }, [activeFilter, activeType, definitions.length, query]);

  useEffect(() => { void load(); }, [load]);

  const currentDefinition = useMemo(() => definitions.find(item => item.type_code === activeType), [definitions, activeType]);
  const beginCreate = () => { setEditing(null); setFormOpen(true); setForm({ ...emptyForm, type_code: activeType, sort_order: items.length }); };
  const beginEdit = (item: TestCaseMetadataOption) => { setEditing(item); setFormOpen(true); setForm({ type_code: item.type_code, code: item.code, name: item.name, description: item.description || '', color: item.color || '', sort_order: item.sort_order, is_active: item.is_active, is_default: item.is_default }); };
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    try {
      if (editing) await api.updateMetadata(editing.id, { name: form.name, description: form.description, color: form.color, sort_order: form.sort_order, is_active: form.is_active, is_default: form.is_default });
      else await api.createMetadata(form);
      setForm({ ...emptyForm, type_code: activeType });
      setEditing(null);
      setFormOpen(false);
      await load();
    } catch (err) { setError(err instanceof Error ? err.message : '保存元数据失败'); }
  };
  const deactivate = async (item: TestCaseMetadataOption) => {
    if (!window.confirm(`停用“${item.name}”？历史用例仍会保留该值。`)) return;
    try { await api.deactivateMetadata(item.id); await load(); } catch (err) { setError(err instanceof Error ? err.message : '停用失败'); }
  };

  const enabledCount = items.filter(item => item.is_active).length;
  const referenceCount = items.reduce((total, item) => total + (item.usage_count ?? 0), 0);

  return <div className="metadata-page">
    <header className="metadata-page__header">
      <div>
        <div className="metadata-page__eyebrow">资产配置 / 选项字典</div>
        <h1>元数据管理</h1>
        <p>维护手工测试用例的标准分类、优先级、风险和标签</p>
      </div>
      <button type="button" className="btn btn--primary btn--sm" onClick={beginCreate}><Plus size={15} /> 新增选项</button>
    </header>

    <div className={`metadata-page__layout${formOpen ? ' metadata-page__layout--with-form' : ''}`}>
      <aside className="metadata-type-panel">
        <div className="metadata-type-panel__heading">
          <div><span>元数据类型</span><small>按类型管理选项</small></div>
          <span>{definitions.length}</span>
        </div>
        <nav aria-label="元数据类型">
          {definitions.map(definition => <button key={definition.type_code} type="button" className={`metadata-type-panel__item${activeType === definition.type_code ? ' is-active' : ''}`} onClick={() => { setActiveType(definition.type_code); setQuery(''); }}>
            <span>{definition.label}</span>{definition.required && <em>必填</em>}
          </button>)}
        </nav>
      </aside>

      <section className="metadata-content">
        <div className="metadata-content__heading">
          <div><h2>{currentDefinition?.label || '选项'}</h2><p>维护该类型下可供测试用例使用的标准选项</p></div>
          <div className="metadata-content__stats"><span><strong>{items.length}</strong> 项</span><span><strong>{enabledCount}</strong> 启用</span><span><strong>{referenceCount}</strong> 次引用</span></div>
        </div>
        <div className="metadata-toolbar">
          <label className="metadata-search"><Search size={15} /><span className="sr-only">搜索{currentDefinition?.label || '选项'}</span><input value={query} onChange={e => setQuery(e.target.value)} onKeyDown={e => e.key === 'Enter' && void load()} placeholder={`搜索${currentDefinition?.label || '选项'}名称或代码`} /></label>
          <select value={activeFilter} onChange={e => setActiveFilter(e.target.value)} aria-label="筛选状态"><option value="all">全部状态</option><option value="active">启用</option><option value="inactive">已停用</option></select>
        </div>
        {error && <div className="error-banner metadata-page__error">{error}</div>}
        <div className="metadata-table-wrap"><table className="metadata-table"><thead><tr><th>名称</th><th>代码</th><th>颜色</th><th>状态</th><th>引用次数</th><th className="metadata-table__actions-header">操作</th></tr></thead><tbody>
          {loading ? <tr><td colSpan={6} className="metadata-table__empty">加载中...</td></tr> : items.map(item => <tr key={item.id}>
            <td><div className="metadata-table__name"><strong>{item.name}</strong>{item.is_default && <span>默认</span>}</div>{item.description && <small>{item.description}</small>}</td>
            <td><code>{item.code}</code></td>
            <td>{item.color ? <span className="metadata-table__swatch" style={{ background: item.color }} title={item.color} /> : <span className="metadata-table__muted">未设置</span>}</td>
            <td><span className={`metadata-status${item.is_active ? ' is-active' : ''}`}>{item.is_active ? '启用' : '已停用'}</span></td>
            <td className="metadata-table__usage">{item.usage_count ?? 0}</td>
            <td><div className="metadata-table__actions"><button type="button" className="btn btn--secondary btn--sm metadata-icon-button" title="编辑选项" aria-label={`编辑${item.name}`} onClick={() => beginEdit(item)}><Pencil size={14} /></button>{item.is_active && <button type="button" className="btn btn--secondary btn--sm metadata-icon-button metadata-icon-button--deactivate" title="停用选项" aria-label={`停用${item.name}`} onClick={() => void deactivate(item)}><PowerOff size={14} /></button>}</div></td>
          </tr>)}
          {!loading && items.length === 0 && <tr><td colSpan={6} className="metadata-table__empty"><strong>暂无匹配选项</strong><span>可以尝试调整搜索条件，或新增一个选项</span></td></tr>}
        </tbody></table></div>
      </section>

      {formOpen && <form onSubmit={submit} className="metadata-form">
        <div className="metadata-form__header"><div><span className="metadata-page__eyebrow">{editing ? '编辑数据' : '新增数据'}</span><h2>{editing ? '编辑选项' : '新增选项'}</h2></div><button type="button" className="metadata-form__close" onClick={() => { setEditing(null); setFormOpen(false); }} title="关闭" aria-label="关闭表单"><X size={17} /></button></div>
        <p className="metadata-form__hint">{editing ? '更新名称、描述或状态，代码保持不变。' : `为“${currentDefinition?.label || '当前类型'}”添加一个可复用的标准选项。`}</p>
        <label>类型<select value={form.type_code} disabled={Boolean(editing)} onChange={e => setForm({ ...form, type_code: e.target.value })}>{definitions.map(def => <option key={def.type_code} value={def.type_code}>{def.label}</option>)}</select></label>
        <label>代码<input value={form.code} disabled={Boolean(editing)} onChange={e => setForm({ ...form, code: e.target.value.toUpperCase() })} placeholder="例如 FUNCTIONAL" required /><small>用于接口和数据存储，创建后不可修改。</small></label>
        <label>名称<input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="例如 功能" required /></label>
        <label>描述<textarea value={form.description || ''} onChange={e => setForm({ ...form, description: e.target.value })} rows={3} placeholder="补充该选项的使用范围（可选）" /></label>
        <div className="metadata-form__field-row"><label>颜色<input className="metadata-form__color" type="color" value={form.color || '#64748b'} onChange={e => setForm({ ...form, color: e.target.value })} /></label><label>排序<input type="number" min={0} value={form.sort_order ?? 0} onChange={e => setForm({ ...form, sort_order: Number(e.target.value) })} /></label></div>
        <label className="metadata-form__checkbox"><input type="checkbox" checked={Boolean(form.is_default)} onChange={e => setForm({ ...form, is_default: e.target.checked })} /><span><strong>默认选项</strong><small>新建用例时优先使用</small></span></label>
        <label className="metadata-form__checkbox"><input type="checkbox" checked={form.is_active !== false} onChange={e => setForm({ ...form, is_active: e.target.checked })} /><span><strong>启用此选项</strong><small>停用后不会出现在新用例中</small></span></label>
        <div className="metadata-form__actions"><button type="button" className="btn btn--secondary btn--sm" onClick={() => { setEditing(null); setFormOpen(false); setForm({ ...emptyForm, type_code: activeType }); }}>取消</button><button type="submit" className="btn btn--primary btn--sm">保存选项</button></div>
      </form>}
    </div>
  </div>;
}
