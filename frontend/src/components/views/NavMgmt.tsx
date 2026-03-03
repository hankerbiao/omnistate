import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Plus,
  ChevronRight,
  Navigation as NavIcon,
  Settings,
  Pencil,
  Trash2,
  Eye,
  EyeOff,
  Loader2,
  X,
} from 'lucide-react';
import { NavigationPage } from '../../types';

interface NavMgmtProps {
  navigationPages: NavigationPage[];
  currentUser: any;
  showForm: boolean;
  editingPage: NavigationPage | null;
  newPage: Partial<NavigationPage>;
  onBack: () => void;
  onShowForm: (show: boolean) => void;
  onNewPageChange: (page: Partial<NavigationPage>) => void;
  onCreatePage: () => void;
  onStartEditPage: (page: NavigationPage) => void;
  onSaveEditPage: (page: NavigationPage) => void;
  onCancelEdit: () => void;
  onEditFieldChange: (field: string, value: any) => void;
  onToggleActive: (view: string, isActive: boolean) => void;
  onDeletePage: (view: string) => void;
}

export const NavMgmt: React.FC<NavMgmtProps> = ({
  navigationPages,
  currentUser,
  showForm,
  editingPage,
  newPage,
  onBack,
  onShowForm,
  onNewPageChange,
  onCreatePage,
  onStartEditPage,
  onSaveEditPage,
  onCancelEdit,
  onEditFieldChange,
  onToggleActive,
  onDeletePage,
}) => {
  const isAdmin = Boolean(currentUser?.role_ids?.some((role: string) => role.toUpperCase().includes('ADMIN')));
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  const handleDeleteClick = (view: string) => {
    setDeleteConfirm(view);
  };

  const confirmDelete = (view: string) => {
    onDeletePage(view);
    setDeleteConfirm(null);
  };

  const cancelDelete = () => {
    setDeleteConfirm(null);
  };

  if (!isAdmin) {
    return (
      <div className="max-w-[1680px] mx-auto px-4 sm:px-6 py-8">
        <div className="flex items-center gap-4 mb-8">
          <button onClick={onBack} className="p-2 hover:bg-slate-100 rounded-xl transition-colors text-slate-500">
            <ChevronRight size={20} className="rotate-180" />
          </button>
          <div className="bg-slate-900 p-2 rounded-xl text-white shadow-lg shadow-slate-200">
            <NavIcon size={20} />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900">导航页面管理</h1>
            <p className="text-sm text-slate-500">管理系统导航页面配置</p>
          </div>
        </div>
        <div className="bg-white rounded-3xl border border-slate-100 shadow-xl shadow-slate-100/50 p-12 text-center">
          <div className="w-16 h-16 bg-rose-50 rounded-full flex items-center justify-center mx-auto mb-4">
            <Settings size={24} className="text-rose-500" />
          </div>
          <h3 className="text-lg font-bold text-slate-900 mb-2">权限不足</h3>
          <p className="text-sm text-slate-500">只有管理员才能访问导航管理功能</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-[1680px] mx-auto px-4 sm:px-6 py-8 space-y-8">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="p-2 hover:bg-slate-100 rounded-xl transition-colors text-slate-500">
            <ChevronRight size={20} className="rotate-180" />
          </button>
          <div className="bg-slate-900 p-2 rounded-xl text-white shadow-lg shadow-slate-200">
            <NavIcon size={20} />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900">导航页面管理</h1>
            <p className="text-sm text-slate-500">管理系统导航页面配置与权限</p>
          </div>
        </div>
        <div className="flex items-center gap-3 self-start lg:self-auto">
          <button
            onClick={() => {
              onShowForm(false);
              if (editingPage) onCancelEdit();
            }}
            className="flex items-center gap-2 px-4 py-2.5 bg-slate-900 text-white rounded-xl text-sm font-bold transition-all shadow-lg shadow-slate-900/20"
          >
            <Settings size={16} /> 管理导航
          </button>
          <button
            onClick={() => onShowForm(true)}
            className="flex items-center gap-2 px-4 py-2.5 bg-white text-slate-700 border border-slate-200 rounded-xl text-sm font-bold hover:border-slate-300 hover:bg-slate-50 transition-all active:scale-95"
          >
            <Plus size={16} /> 新建导航
          </button>
        </div>
      </div>

      <div className="bg-white rounded-3xl border border-slate-100 shadow-xl shadow-slate-100/50 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-50 flex justify-between items-center">
          <h3 className="font-bold text-slate-900">导航页面列表</h3>
          <span className="text-xs font-bold px-2 py-1 bg-slate-100 text-slate-500 rounded-lg">
            {(navigationPages || []).length} pages
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1180px] text-left border-collapse table-auto">
            <thead>
              <tr className="bg-slate-50/50 border-b border-slate-100">
                <th className="px-4 py-4 text-xs font-bold text-slate-400 uppercase tracking-wider w-44">View Code</th>
                <th className="px-4 py-4 text-xs font-bold text-slate-400 uppercase tracking-wider w-56">导航名称</th>
                <th className="px-4 py-4 text-xs font-bold text-slate-400 uppercase tracking-wider w-32">权限码</th>
                <th className="px-4 py-4 text-xs font-bold text-slate-400 uppercase tracking-wider w-[22rem]">描述</th>
                <th className="px-4 py-4 text-xs font-bold text-slate-400 uppercase tracking-wider w-24">排序</th>
                <th className="px-4 py-4 text-xs font-bold text-slate-400 uppercase tracking-wider w-24">状态</th>
                <th className="px-4 py-4 text-xs font-bold text-slate-400 uppercase tracking-wider w-56">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {(navigationPages || [])
                .sort((a, b) => (a.order || 0) - (b.order || 0))
                .map(page => (
                <tr key={page.view} className="hover:bg-slate-50/80 transition-colors group">
                  <td className="px-4 py-4 text-xs font-mono text-indigo-600 whitespace-nowrap">{page.view}</td>
                  <td className="px-4 py-4 text-sm font-bold text-slate-900">{page.label}</td>
                  <td className="px-4 py-4 text-xs text-slate-600 font-mono">
                    {page.permission || '-'}
                  </td>
                  <td className="px-4 py-4 text-sm text-slate-600 max-w-md truncate">
                    {page.description || '-'}
                  </td>
                  <td className="px-4 py-4 text-xs text-slate-500 font-mono">
                    {page.order || 0}
                  </td>
                  <td className="px-4 py-4">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-lg text-xs font-bold leading-relaxed ${
                      page.is_active && !page.is_deleted
                        ? 'bg-emerald-50 text-emerald-600'
                        : 'bg-slate-100 text-slate-400'
                    }`}>
                      {page.is_deleted ? '已删除' : page.is_active ? '启用' : '禁用'}
                    </span>
                  </td>
                  <td className="px-4 py-4">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => onToggleActive(page.view, !page.is_active)}
                        className="inline-flex items-center justify-center p-2 text-slate-600 hover:text-indigo-600 bg-slate-100 hover:bg-indigo-50 rounded-lg transition-all"
                        title={page.is_active ? '禁用' : '启用'}
                        aria-label={page.is_active ? '禁用' : '启用'}
                      >
                        {page.is_active ? <Eye size={16} /> : <EyeOff size={16} />}
                      </button>
                      <button
                        onClick={() => onStartEditPage(page)}
                        className="inline-flex items-center justify-center p-2 text-indigo-600 hover:text-indigo-700 bg-indigo-50 hover:bg-indigo-100 rounded-lg transition-all"
                        title="编辑导航"
                        aria-label="编辑导航"
                      >
                        <Pencil size={16} />
                      </button>
                      {!page.is_deleted && (
                        <button
                          onClick={() => handleDeleteClick(page.view)}
                          className="inline-flex items-center justify-center p-2 text-rose-600 hover:text-rose-700 bg-rose-50 hover:bg-rose-100 rounded-lg transition-all"
                          title="删除导航"
                          aria-label="删除导航"
                        >
                          <Trash2 size={16} />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create Form Modal */}
      <AnimatePresence>
        {showForm && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={() => onShowForm(false)}
              className="absolute inset-0 bg-slate-900/20 backdrop-blur-sm"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="relative w-full max-w-lg bg-white rounded-3xl shadow-2xl overflow-hidden"
            >
              <div className="px-8 py-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
                <h2 className="text-base font-bold text-slate-900">新建导航页面</h2>
                <button onClick={() => onShowForm(false)} className="text-slate-400 hover:text-slate-600 p-1 hover:bg-slate-100 rounded-lg transition-all">
                  <Plus size={24} className="rotate-45" />
                </button>
              </div>
              <div className="p-8 space-y-6">
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                    View Code <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={newPage.view || ''}
                    onChange={(e) => onNewPageChange({ ...newPage, view: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 text-sm focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all"
                    placeholder="例如: req_list"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                    导航名称 <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={newPage.label || ''}
                    onChange={(e) => onNewPageChange({ ...newPage, label: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 text-sm focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all"
                    placeholder="例如: 需求列表"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">权限码</label>
                  <input
                    type="text"
                    value={newPage.permission || ''}
                    onChange={(e) => onNewPageChange({ ...newPage, permission: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 text-sm focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all"
                    placeholder="例如: req:read"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">描述</label>
                  <textarea
                    value={newPage.description || ''}
                    onChange={(e) => onNewPageChange({ ...newPage, description: e.target.value })}
                    rows={3}
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 text-sm focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all resize-none"
                    placeholder="导航页面功能描述"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">排序序号</label>
                  <input
                    type="number"
                    value={newPage.order || 0}
                    onChange={(e) => onNewPageChange({ ...newPage, order: parseInt(e.target.value) || 0 })}
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 text-sm focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all"
                    placeholder="数值越小越靠前"
                  />
                </div>
              </div>
              <div className="px-8 py-6 bg-slate-50 border-t border-slate-100 flex gap-4">
                <button
                  onClick={() => onShowForm(false)}
                  className="flex-1 px-6 py-3 text-sm font-bold text-slate-600 hover:bg-white hover:shadow-sm border border-transparent hover:border-slate-200 rounded-xl transition-all"
                >
                  取消
                </button>
                <button
                  onClick={onCreatePage}
                  className="flex-1 px-6 py-3 bg-slate-900 text-white rounded-xl text-sm font-bold hover:bg-slate-800 transition-all shadow-lg hover:shadow-xl active:scale-95"
                >
                  确认创建
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Edit Form Modal */}
      <AnimatePresence>
        {editingPage && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={onCancelEdit}
              className="absolute inset-0 bg-slate-900/20 backdrop-blur-sm"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="relative w-full max-w-lg bg-white rounded-3xl shadow-2xl overflow-hidden"
            >
              <div className="px-8 py-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
                <h2 className="text-base font-bold text-slate-900">编辑导航页面</h2>
                <button onClick={onCancelEdit} className="text-slate-400 hover:text-slate-600 p-1 hover:bg-slate-100 rounded-lg transition-all">
                  <X size={20} />
                </button>
              </div>
              <div className="p-8 space-y-6">
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                    View Code
                  </label>
                  <input
                    type="text"
                    value={editingPage.view}
                    disabled
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 text-sm bg-slate-50 text-slate-500"
                  />
                  <p className="text-xs text-slate-400 mt-1">View Code 不可修改</p>
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">导航名称</label>
                  <input
                    type="text"
                    value={editingPage.label}
                    onChange={(e) => onEditFieldChange('label', e.target.value)}
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 text-sm focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">权限码</label>
                  <input
                    type="text"
                    value={editingPage.permission || ''}
                    onChange={(e) => onEditFieldChange('permission', e.target.value)}
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 text-sm focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">描述</label>
                  <textarea
                    value={editingPage.description || ''}
                    onChange={(e) => onEditFieldChange('description', e.target.value)}
                    rows={3}
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 text-sm focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all resize-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">排序序号</label>
                  <input
                    type="number"
                    value={editingPage.order || 0}
                    onChange={(e) => onEditFieldChange('order', parseInt(e.target.value) || 0)}
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 text-sm focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">状态</label>
                  <div className="flex gap-3">
                    <button
                      onClick={() => onEditFieldChange('is_active', true)}
                      className={`flex-1 px-4 py-3 rounded-xl text-sm font-bold border transition-all ${
                        editingPage.is_active
                          ? 'bg-emerald-50 text-emerald-600 border-emerald-200'
                          : 'bg-white text-slate-500 border-slate-200 hover:border-slate-300'
                      }`}
                    >
                      启用
                    </button>
                    <button
                      onClick={() => onEditFieldChange('is_active', false)}
                      className={`flex-1 px-4 py-3 rounded-xl text-sm font-bold border transition-all ${
                        !editingPage.is_active
                          ? 'bg-slate-200 text-slate-600 border-slate-300'
                          : 'bg-white text-slate-500 border-slate-200 hover:border-slate-300'
                      }`}
                    >
                      禁用
                    </button>
                  </div>
                </div>
              </div>
              <div className="px-8 py-6 bg-slate-50 border-t border-slate-100 flex gap-4">
                <button
                  onClick={onCancelEdit}
                  className="flex-1 px-6 py-3 text-sm font-bold text-slate-600 hover:bg-white hover:shadow-sm border border-transparent hover:border-slate-200 rounded-xl transition-all"
                >
                  取消
                </button>
                <button
                  onClick={() => onSaveEditPage(editingPage)}
                  className="flex-1 px-6 py-3 bg-slate-900 text-white rounded-xl text-sm font-bold hover:bg-slate-800 transition-all shadow-lg hover:shadow-xl active:scale-95"
                >
                  保存修改
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Delete Confirm Modal */}
      <AnimatePresence>
        {deleteConfirm && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={cancelDelete}
              className="absolute inset-0 bg-slate-900/20 backdrop-blur-sm"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="relative w-full max-w-md bg-white rounded-3xl shadow-2xl overflow-hidden"
            >
              <div className="px-8 py-6 border-b border-slate-100 flex items-center gap-3 bg-slate-50/50">
                <div className="w-12 h-12 bg-rose-50 rounded-full flex items-center justify-center">
                  <Trash2 size={24} className="text-rose-500" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-slate-900">确认删除</h2>
                  <p className="text-xs text-slate-500 mt-1">此操作不可撤销</p>
                </div>
              </div>
              <div className="p-8">
                <p className="text-sm text-slate-600 leading-relaxed">
                  您确定要删除导航页面 <span className="font-bold text-slate-900">"{deleteConfirm}"</span> 吗？
                  <br />
                  删除后，该导航页面将不再显示给用户。
                </p>
              </div>
              <div className="px-8 py-6 bg-slate-50 border-t border-slate-100 flex gap-4">
                <button
                  onClick={cancelDelete}
                  className="flex-1 px-6 py-3 text-sm font-bold text-slate-600 hover:bg-white hover:shadow-sm border border-transparent hover:border-slate-200 rounded-xl transition-all"
                >
                  取消
                </button>
                <button
                  onClick={() => confirmDelete(deleteConfirm)}
                  className="flex-1 px-6 py-3 bg-rose-500 text-white rounded-xl text-sm font-bold hover:bg-rose-600 transition-all shadow-lg hover:shadow-xl active:scale-95"
                >
                  确认删除
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};