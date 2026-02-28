import React from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Plus,
  ChevronRight,
  User,
  Settings,
  Pencil,
  Shield,
  Loader2,
  X,
} from 'lucide-react';
import { User as UserType, ROLES } from '../../constants/config';

interface NavigationOption {
  view: string;
  label: string;
  permission: string;
  description?: string;
}

interface UserMgmtProps {
  users: UserType[];
  currentUser: UserType | null;
  showUserForm: boolean;
  editingUser: UserType | null;
  newUser: Partial<UserType>;
  onBack: () => void;
  onShowUserForm: (show: boolean) => void;
  onNewUserChange: (user: Partial<UserType>) => void;
  onCreateUser: () => void;
  onStartEditUser: (user: UserType) => void;
  onSaveEditUser: (user: UserType) => void;
  onCancelEdit: () => void;
  onEditFieldChange: (field: string, value: any) => void;
  navigationOptions: NavigationOption[];
  editingNavigationUser: UserType | null;
  editingNavigationViews: string[];
  isSavingNavigation: boolean;
  onStartEditNavigation: (user: UserType) => void;
  onToggleEditNavigationView: (view: string) => void;
  onSaveEditNavigation: () => void;
  onCancelEditNavigation: () => void;
}

export const UserMgmt: React.FC<UserMgmtProps> = ({
  users,
  currentUser,
  showUserForm,
  editingUser,
  newUser,
  onBack,
  onShowUserForm,
  onNewUserChange,
  onCreateUser,
  onStartEditUser,
  onSaveEditUser,
  onCancelEdit,
  onEditFieldChange,
  navigationOptions,
  editingNavigationUser,
  editingNavigationViews,
  isSavingNavigation,
  onStartEditNavigation,
  onToggleEditNavigationView,
  onSaveEditNavigation,
  onCancelEditNavigation,
}) => {
  const isAdmin = Boolean(currentUser?.role_ids.some(role => String(role).toUpperCase().includes('ADMIN')));

  return (
    <div className="max-w-[1680px] mx-auto px-4 sm:px-6 py-8 space-y-8">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="p-2 hover:bg-slate-100 rounded-xl transition-colors text-slate-500">
            <ChevronRight size={20} className="rotate-180" />
          </button>
          <div className="bg-slate-900 p-2 rounded-xl text-white shadow-lg shadow-slate-200">
            <User size={20} />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900">用户与权限管理</h1>
            <p className="text-sm text-slate-500">管理系统用户、角色分配及权限设置</p>
          </div>
        </div>
        <div className="flex items-center gap-3 self-start lg:self-auto">
          <button
            onClick={() => {
              onShowUserForm(false);
              if (editingUser) onCancelEdit();
            }}
            className="flex items-center gap-2 px-4 py-2.5 bg-slate-900 text-white rounded-xl text-sm font-bold transition-all shadow-lg shadow-slate-900/20"
          >
            <Settings size={16} /> 管理用户
          </button>
          <button
            onClick={() => onShowUserForm(true)}
            className="flex items-center gap-2 px-4 py-2.5 bg-white text-slate-700 border border-slate-200 rounded-xl text-sm font-bold hover:border-slate-300 hover:bg-slate-50 transition-all active:scale-95"
          >
            <Plus size={16} /> 新建用户
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
        {/* User List */}
        <div className="xl:col-span-9">
          <div className="bg-white rounded-3xl border border-slate-100 shadow-xl shadow-slate-100/50 overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-50 flex justify-between items-center">
              <h3 className="font-bold text-slate-900">用户列表</h3>
              <span className="text-xs font-bold px-2 py-1 bg-slate-100 text-slate-500 rounded-lg">{users.length} users</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[1180px] text-left border-collapse table-auto">
                <thead>
                  <tr className="bg-slate-50/50 border-b border-slate-100">
                    <th className="px-4 py-4 text-xs font-bold text-slate-400 uppercase tracking-wider w-44">用户 ID</th>
                    <th className="px-4 py-4 text-xs font-bold text-slate-400 uppercase tracking-wider w-44">用户名</th>
                    <th className="px-4 py-4 text-xs font-bold text-slate-400 uppercase tracking-wider w-[22rem]">邮箱</th>
                    <th className="px-4 py-4 text-xs font-bold text-slate-400 uppercase tracking-wider">角色</th>
                    <th className="px-4 py-4 text-xs font-bold text-slate-400 uppercase tracking-wider w-24">状态</th>
                    <th className="px-4 py-4 text-xs font-bold text-slate-400 uppercase tracking-wider w-56">操作</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                  {users.map(user => (
                    <tr key={user.user_id} className="hover:bg-slate-50/80 transition-colors group">
                      <td className="px-4 py-4 text-xs font-mono text-slate-500 whitespace-nowrap">{user.user_id}</td>
                      <td className="px-4 py-4 text-sm font-bold text-slate-900">{user.username}</td>
                      <td className="px-4 py-4 text-sm text-slate-600 break-all">{user.email}</td>
                      <td className="px-4 py-4">
                        <div className="flex flex-wrap gap-1">
                          {user.role_ids.map(rid => (
                            <span key={rid} className="px-1.5 py-0.5 bg-indigo-50 text-indigo-600 rounded text-xs font-bold whitespace-nowrap">
                              {ROLES.find(r => r.id === rid)?.name || rid}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="px-4 py-4">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-lg text-xs font-bold leading-relaxed ${
                          user.status === 'ACTIVE' ? 'bg-emerald-50 text-emerald-600' : 'bg-slate-100 text-slate-400'
                        }`}>
                          {user.status === 'ACTIVE' ? '启用' : '禁用'}
                        </span>
                      </td>
                      <td className="px-4 py-4">
                        {isAdmin ? (
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => onStartEditUser(user)}
                              className="inline-flex items-center justify-center p-2 text-indigo-600 hover:text-indigo-700 bg-indigo-50 hover:bg-indigo-100 rounded-lg transition-all"
                              title="修改用户信息"
                              aria-label="修改用户信息"
                            >
                              <Pencil size={16} />
                            </button>
                            <button
                              onClick={() => onStartEditNavigation(user)}
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold text-slate-600 hover:text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-all whitespace-nowrap"
                              title="管理导航权限"
                            >
                              <Shield size={14} />
                              导航权限
                            </button>
                          </div>
                        ) : (
                          <span className="inline-flex items-center px-2.5 py-1 text-xs font-medium text-slate-400 bg-slate-100 rounded-lg whitespace-nowrap">
                            仅管理员可修改
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Role Definitions */}
        <div className="xl:col-span-3 space-y-6">
          <div className="bg-white rounded-3xl border border-slate-100 shadow-xl shadow-slate-100/50 p-6">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-6">角色定义</h3>
            <div className="space-y-4">
              {ROLES.map(role => (
                <div key={role.id} className="p-4 rounded-2xl border border-slate-100 bg-slate-50/30 hover:bg-slate-50 transition-colors">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm font-bold text-slate-900">{role.name}</span>
                    <span className="text-xs font-mono text-slate-400 bg-white px-1.5 py-0.5 rounded border border-slate-100">{role.id}</span>
                  </div>
                  <p className="text-xs text-slate-500 mb-3 leading-relaxed">{role.description}</p>
                  <div className="flex flex-wrap gap-1.5">
                    {role.permissions.map(p => (
                      <span key={p} className="px-1.5 py-0.5 bg-white border border-slate-200 rounded-md text-[10px] text-slate-500 font-mono">
                        {p}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* User Creation Modal */}
      <AnimatePresence>
        {showUserForm && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={() => onShowUserForm(false)}
              className="absolute inset-0 bg-slate-900/20 backdrop-blur-sm"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="relative w-full max-w-lg bg-white rounded-3xl shadow-2xl overflow-hidden"
            >
              <div className="px-8 py-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
                <h2 className="text-base font-bold text-slate-900">新建用户</h2>
                <button onClick={() => onShowUserForm(false)} className="text-slate-400 hover:text-slate-600 p-1 hover:bg-slate-100 rounded-lg transition-all">
                  <Plus size={24} className="rotate-45" />
                </button>
              </div>
              <div className="p-8 space-y-6">
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">用户名</label>
                  <input
                    type="text"
                    value={newUser.username || ''}
                    onChange={(e) => onNewUserChange({ ...newUser, username: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 text-sm focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all"
                    placeholder="例如: alice"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">邮箱地址</label>
                  <input
                    type="email"
                    value={newUser.email || ''}
                    onChange={(e) => onNewUserChange({ ...newUser, email: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 text-sm focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all"
                    placeholder="alice@example.com"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">角色分配</label>
                  <div className="grid grid-cols-2 gap-3">
                    {ROLES.map(role => (
                      <button
                        key={role.id}
                        onClick={() => {
                          const current = newUser.role_ids || [];
                          const next = current.includes(role.id)
                            ? current.filter(id => id !== role.id)
                            : [...current, role.id];
                          onNewUserChange({ ...newUser, role_ids: next });
                        }}
                        className={`px-4 py-3 rounded-xl text-xs font-bold border transition-all text-left flex flex-col gap-1 ${
                          newUser.role_ids?.includes(role.id)
                            ? 'bg-slate-900 text-white border-slate-900 shadow-lg shadow-slate-900/20'
                            : 'bg-white text-slate-500 border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                        }`}
                      >
                        <span className="text-sm">{role.name}</span>
                        <span className={`text-[10px] font-normal ${newUser.role_ids?.includes(role.id) ? 'text-slate-400' : 'text-slate-400'}`}>{role.description}</span>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
              <div className="px-8 py-6 bg-slate-50 border-t border-slate-100 flex gap-4">
                <button
                  onClick={() => onShowUserForm(false)}
                  className="flex-1 px-6 py-3 text-sm font-bold text-slate-600 hover:bg-white hover:shadow-sm border border-transparent hover:border-slate-200 rounded-xl transition-all"
                >
                  取消
                </button>
                <button
                  onClick={onCreateUser}
                  className="flex-1 px-6 py-3 bg-slate-900 text-white rounded-xl text-sm font-bold hover:bg-slate-800 transition-all shadow-lg hover:shadow-xl active:scale-95"
                >
                  确认创建
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Edit User Modal */}
      <AnimatePresence>
        {editingUser && (
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
                <h2 className="text-base font-bold text-slate-900">编辑用户</h2>
                <button onClick={onCancelEdit} className="text-slate-400 hover:text-slate-600 p-1 hover:bg-slate-100 rounded-lg transition-all">
                  <X size={20} />
                </button>
              </div>
              <div className="p-8 space-y-6">
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">用户名</label>
                  <input
                    type="text"
                    value={editingUser.username}
                    onChange={(e) => onEditFieldChange('username', e.target.value)}
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 text-sm focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">邮箱地址</label>
                  <input
                    type="email"
                    value={editingUser.email}
                    onChange={(e) => onEditFieldChange('email', e.target.value)}
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 text-sm focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">状态</label>
                  <div className="flex gap-3">
                    <button
                      onClick={() => onEditFieldChange('status', 'ACTIVE')}
                      className={`flex-1 px-4 py-3 rounded-xl text-sm font-bold border transition-all ${
                        editingUser.status === 'ACTIVE'
                          ? 'bg-emerald-50 text-emerald-600 border-emerald-200'
                          : 'bg-white text-slate-500 border-slate-200 hover:border-slate-300'
                      }`}
                    >
                      启用
                    </button>
                    <button
                      onClick={() => onEditFieldChange('status', 'INACTIVE')}
                      className={`flex-1 px-4 py-3 rounded-xl text-sm font-bold border transition-all ${
                        editingUser.status === 'INACTIVE'
                          ? 'bg-slate-200 text-slate-600 border-slate-300'
                          : 'bg-white text-slate-500 border-slate-200 hover:border-slate-300'
                      }`}
                    >
                      禁用
                    </button>
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">角色分配</label>
                  <div className="grid grid-cols-2 gap-3">
                    {ROLES.map(role => (
                      <button
                        key={role.id}
                        onClick={() => {
                          const current = editingUser.role_ids || [];
                          const next = current.includes(role.id)
                            ? current.filter(id => id !== role.id)
                            : [...current, role.id];
                          onEditFieldChange('role_ids', next);
                        }}
                        className={`px-4 py-3 rounded-xl text-xs font-bold border transition-all text-left flex flex-col gap-1 ${
                          editingUser.role_ids?.includes(role.id)
                            ? 'bg-slate-900 text-white border-slate-900 shadow-lg shadow-slate-900/20'
                            : 'bg-white text-slate-500 border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                        }`}
                      >
                        <span className="text-sm">{role.name}</span>
                        <span className={`text-[10px] font-normal ${editingUser.role_ids?.includes(role.id) ? 'text-slate-400' : 'text-slate-400'}`}>{role.description}</span>
                      </button>
                    ))}
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
                  onClick={() => onSaveEditUser(editingUser)}
                  className="flex-1 px-6 py-3 bg-slate-900 text-white rounded-xl text-sm font-bold hover:bg-slate-800 transition-all shadow-lg hover:shadow-xl active:scale-95"
                >
                  保存修改
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Navigation Permission Modal */}
      <AnimatePresence>
        {editingNavigationUser && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={onCancelEditNavigation}
              className="absolute inset-0 bg-slate-900/20 backdrop-blur-sm"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="relative w-full max-w-xl bg-white rounded-3xl shadow-2xl overflow-hidden"
            >
              <div className="px-8 py-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
                <div>
                  <h2 className="text-base font-bold text-slate-900">导航访问权限</h2>
                  <p className="text-xs text-slate-500 mt-1">
                    用户：{editingNavigationUser.username}（{editingNavigationUser.user_id}）
                  </p>
                </div>
                <button onClick={onCancelEditNavigation} className="text-slate-400 hover:text-slate-600 p-1 hover:bg-slate-100 rounded-lg transition-all">
                  <X size={20} />
                </button>
              </div>

              <div className="p-8 space-y-4">
                {navigationOptions.map(option => {
                  const checked = editingNavigationViews.includes(option.view);
                  return (
                    <button
                      key={option.view}
                      onClick={() => onToggleEditNavigationView(option.view)}
                      className={`w-full text-left p-4 rounded-2xl border transition-all ${
                        checked
                          ? 'border-indigo-200 bg-indigo-50/60'
                          : 'border-slate-200 bg-white hover:bg-slate-50'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <div className="text-sm font-bold text-slate-900">{option.label}</div>
                          <div className="text-xs text-slate-500 mt-1">{option.description || option.permission}</div>
                        </div>
                        <span className={`inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-bold ${
                          checked ? 'bg-indigo-100 text-indigo-700' : 'bg-slate-100 text-slate-500'
                        }`}>
                          {checked ? '已授权' : '未授权'}
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>

              <div className="px-8 py-6 bg-slate-50 border-t border-slate-100 flex gap-4">
                <button
                  onClick={onCancelEditNavigation}
                  disabled={isSavingNavigation}
                  className="flex-1 px-6 py-3 text-sm font-bold text-slate-600 hover:bg-white hover:shadow-sm border border-transparent hover:border-slate-200 rounded-xl transition-all disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  取消
                </button>
                <button
                  onClick={onSaveEditNavigation}
                  disabled={isSavingNavigation}
                  className="flex-1 px-6 py-3 bg-slate-900 text-white rounded-xl text-sm font-bold hover:bg-slate-800 transition-all shadow-lg hover:shadow-xl active:scale-95 disabled:opacity-70 disabled:cursor-not-allowed inline-flex items-center justify-center gap-2"
                >
                  {isSavingNavigation && <Loader2 size={16} className="animate-spin" />}
                  保存权限
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};
