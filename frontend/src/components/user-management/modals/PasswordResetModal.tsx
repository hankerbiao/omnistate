/**
 * PasswordResetModal — shadcn Dialog for resetting user password.
 */
import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

interface PasswordResetModalProps {
  open: boolean;
  username: string;
  onClose: () => void;
  resetting: boolean;
  onReset: (password: string) => void;
  error?: string | null;
}

export function PasswordResetModal({ open, username, onClose, resetting, onReset, error }: PasswordResetModalProps) {
  const [password, setPassword] = useState('');

  const handleSubmit = () => {
    if (password.trim().length < 6) return;
    onReset(password.trim());
  };

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="sm:max-w-[400px]">
        <DialogHeader>
          <DialogTitle>重置密码</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <p className="text-sm text-[var(--text-secondary)]">为用户 <strong>{username}</strong> 设置新密码</p>
          {error && <p className="text-sm text-[var(--status-error)]">{error}</p>}
          <div className="space-y-1.5">
            <Label>新密码 *</Label>
            <Input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="至少6位"
              autoFocus
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" size="sm" onClick={onClose}>取消</Button>
          <Button size="sm" onClick={handleSubmit} disabled={resetting || password.trim().length < 6}>
            {resetting ? '重置中...' : '确认重置'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
