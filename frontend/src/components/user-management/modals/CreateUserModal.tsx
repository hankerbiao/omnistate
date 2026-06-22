/**
 * CreateUserModal — shadcn Dialog for creating a new user.
 */
import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

interface Role { role_id: string; name: string; }
interface NewUserData { user_id: string; username: string; password: string; email: string; role_ids: string[]; }

interface CreateUserModalProps {
  open: boolean;
  onClose: () => void;
  roles: Role[];
  creating: boolean;
  onCreateUser: (data: NewUserData) => void;
}

export function CreateUserModal({ open, onClose, roles, creating, onCreateUser }: CreateUserModalProps) {
  const [newUser, setNewUser] = useState<NewUserData>({ user_id: '', username: '', password: '', email: '', role_ids: [] });

  const handleSubmit = () => {
    if (!newUser.user_id.trim() || !newUser.username.trim() || !newUser.password.trim()) return;
    onCreateUser(newUser);
  };

  const toggleRole = (roleId: string) => {
    setNewUser(prev => ({
      ...prev,
      role_ids: prev.role_ids.includes(roleId)
        ? prev.role_ids.filter(id => id !== roleId)
        : [...prev.role_ids, roleId],
    }));
  };

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="sm:max-w-[480px]">
        <DialogHeader>
          <DialogTitle>新建用户</DialogTitle>
        </DialogHeader>

        <div className="flex flex-col gap-4">
          <div className="space-y-1.5">
            <Label>用户ID *</Label>
            <Input value={newUser.user_id} onChange={e => setNewUser(p => ({ ...p, user_id: e.target.value }))} placeholder="登录用ID" autoFocus />
          </div>
          <div className="space-y-1.5">
            <Label>用户名 *</Label>
            <Input value={newUser.username} onChange={e => setNewUser(p => ({ ...p, username: e.target.value }))} placeholder="显示名称" />
          </div>
          <div className="space-y-1.5">
            <Label>密码 *</Label>
            <Input type="password" value={newUser.password} onChange={e => setNewUser(p => ({ ...p, password: e.target.value }))} placeholder="至少6位" />
          </div>
          <div className="space-y-1.5">
            <Label>邮箱</Label>
            <Input type="email" value={newUser.email} onChange={e => setNewUser(p => ({ ...p, email: e.target.value }))} placeholder="可选" />
          </div>
          <div className="space-y-1.5">
            <Label>初始角色</Label>
            <div className="flex flex-col gap-1 max-h-[200px] overflow-y-auto">
              {roles.map(role => {
                const selected = newUser.role_ids.includes(role.role_id);
                return (
                  <label key={role.role_id}
                    className="flex items-center gap-2 px-3 py-2 rounded-md border cursor-pointer text-sm"
                    style={{ border: selected ? '1px solid var(--accent-primary)' : '1px solid var(--border-subtle)', background: selected ? 'var(--status-info-bg)' : 'transparent' }}
                    onClick={() => toggleRole(role.role_id)}
                  >
                    <input type="checkbox" checked={selected} onChange={() => toggleRole(role.role_id)} style={{ accentColor: 'var(--accent-primary)' }} />
                    <span>{role.name}</span>
                  </label>
                );
              })}
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="ghost" size="sm" onClick={onClose}>取消</Button>
          <Button size="sm" onClick={handleSubmit} disabled={creating || !newUser.user_id.trim() || !newUser.username.trim() || !newUser.password}>
            {creating ? '创建中...' : '创建'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export type { NewUserData };
