import React, { useState } from 'react';
import { motion } from 'motion/react';
import {
  Server,
  User,
  Lock,
  Eye,
  EyeOff,
  AlertCircle,
  Cpu,
} from 'lucide-react';

interface LoginProps {
  loginForm: {
    user_id: string;
    password: string;
    rememberMe: boolean;
  };
  showPassword: boolean;
  loginError: string;
  onLoginFormChange: (form: { user_id: string; password: string; rememberMe: boolean }) => void;
  onShowPasswordChange: (show: boolean) => void;
  onLogin: () => boolean;
  onQuickLogin: (user_id: string) => void;
}

// Platform Preview Component
const PlatformPreview = () => (
  <div className="relative">
    <div className="absolute -inset-3 bg-gradient-to-r from-cyan-300/30 via-blue-300/30 to-indigo-300/30 blur-2xl" />

    <div className="relative rounded-3xl border border-slate-700/80 bg-slate-900/95 p-5 shadow-2xl">
      <div className="mb-5 flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs text-slate-300">
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
          Quality Command Center
        </div>
        <span className="rounded-full border border-emerald-400/30 bg-emerald-400/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-300">
          Live
        </span>
      </div>

      <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
        {[
          { label: '活动需求', value: '26', tone: 'from-cyan-400 to-blue-500' },
          { label: '执行中任务', value: '11', tone: 'from-blue-400 to-indigo-500' },
          { label: '自动化通过', value: '98%', tone: 'from-emerald-400 to-teal-500' },
        ].map((item, idx) => (
          <motion.div
            key={item.label}
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 + idx * 0.1 }}
            className="rounded-xl border border-slate-700 bg-slate-800/70 p-3"
          >
            <p className="text-[11px] text-slate-400">{item.label}</p>
            <p className={`mt-1 text-lg font-bold bg-gradient-to-r ${item.tone} bg-clip-text text-transparent`}>
              {item.value}
            </p>
          </motion.div>
        ))}
      </div>

      <div className="rounded-2xl border border-slate-700 bg-slate-800/60 p-4">
        <p className="text-xs font-semibold text-slate-300">测试流转</p>
        <div className="mt-3 flex flex-wrap items-center gap-2 sm:flex-nowrap">
          {['需求解析', '用例设计', '自动回归'].map((step, idx) => (
            <React.Fragment key={step}>
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.6 + idx * 0.12 }}
                className="rounded-lg border border-slate-600 bg-slate-900/80 px-2.5 py-1.5 text-[11px] text-slate-200"
              >
                {step}
              </motion.div>
              {idx < 2 && (
                <motion.div
                  animate={{ opacity: [0.35, 1, 0.35] }}
                  transition={{ duration: 1.8, repeat: Infinity, delay: idx * 0.2 }}
                  className="hidden h-px flex-1 bg-gradient-to-r from-cyan-400/30 via-cyan-300 to-cyan-400/30 sm:block"
                />
              )}
            </React.Fragment>
          ))}
        </div>
      </div>

      <div className="mt-4 space-y-2">
        {[
          { title: 'DDR5 高温回归', status: '通过率 98.6%' },
          { title: 'NVMe 峰值性能', status: '结果已归档' },
          { title: 'BMC 兼容性验证', status: '等待评审' },
        ].map((task, idx) => (
          <motion.div
            key={task.title}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.9 + idx * 0.1 }}
            className="flex items-center justify-between rounded-lg border border-slate-700/80 bg-slate-800/40 px-3 py-2"
          >
            <span className="text-xs text-slate-200">{task.title}</span>
            <span className="text-[11px] text-slate-400">{task.status}</span>
          </motion.div>
        ))}
      </div>
    </div>

    <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
      {['DELL', 'HPE', 'Lenovo', 'Supermicro'].map((vendor, idx) => (
        <motion.div
          key={vendor}
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 1.2 + idx * 0.06 }}
          className="rounded-lg border border-slate-200 bg-white/80 px-2 py-1.5 text-center shadow-sm backdrop-blur-sm"
        >
          <span className="text-[10px] font-bold tracking-wide text-slate-600">{vendor}</span>
        </motion.div>
      ))}
    </div>
  </div>
);

export const Login: React.FC<LoginProps> = ({
  loginForm,
  showPassword,
  loginError,
  onLoginFormChange,
  onShowPasswordChange,
  onLogin,
  onQuickLogin,
}) => {
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = () => {
    setIsLoading(true);
    setTimeout(() => {
      onLogin();
      setIsLoading(false);
    }, 500);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 flex relative overflow-hidden">
      {/* Background Decorations */}
      <div className="absolute inset-0 overflow-hidden">
        {/* Floating geometric shapes */}
        <motion.div
          animate={{
            y: [0, -20, 0],
            rotate: [0, 5, 0],
          }}
          transition={{
            duration: 6,
            repeat: Infinity,
            ease: "easeInOut",
          }}
          className="absolute top-20 left-20 w-32 h-32 bg-blue-200/30 rounded-full blur-xl"
        />
        <motion.div
          animate={{
            y: [0, 30, 0],
            rotate: [0, -10, 0],
          }}
          transition={{
            duration: 8,
            repeat: Infinity,
            ease: "easeInOut",
            delay: 1,
          }}
          className="absolute bottom-32 right-32 w-40 h-40 bg-indigo-200/30 rounded-full blur-xl"
        />
        <motion.div
          animate={{
            x: [0, 15, 0],
            y: [0, -25, 0],
          }}
          transition={{
            duration: 7,
            repeat: Infinity,
            ease: "easeInOut",
            delay: 2,
          }}
          className="absolute top-1/2 left-1/3 w-24 h-24 bg-cyan-200/30 rounded-full blur-xl"
        />

        {/* Subtle grid pattern */}
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: `
              linear-gradient(blue 1px, transparent 1px),
              linear-gradient(90deg, blue 1px, transparent 1px)
            `,
            backgroundSize: '60px 60px',
          }}
        />
      </div>

      <div className="relative z-10 mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-8 px-4 py-6 sm:px-6 lg:flex-row lg:items-start lg:gap-12 lg:px-8 lg:py-10">
        {/* Left Section - Branding & Features */}
        <div className="order-2 flex w-full flex-col justify-start lg:order-1 lg:w-6/12 lg:pr-4 xl:w-7/12 xl:pr-10">
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6 }}
            className="mb-6"
          >
            <div className="inline-flex items-center gap-2 rounded-full border border-blue-200/70 bg-white/70 px-3 py-1 text-[11px] font-semibold text-blue-700 backdrop-blur-sm">
              <span className="h-2 w-2 rounded-full bg-blue-500" />
              Server Validation Studio
            </div>
            <div className="mt-5 flex flex-col items-start gap-4 sm:flex-row">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-700 shadow-xl shadow-blue-500/30">
                <Server size={32} className="text-white" />
              </div>
              <div className="pt-1">
                <h1 className="bg-gradient-to-r from-blue-600 to-indigo-700 bg-clip-text text-2xl font-bold text-transparent sm:text-3xl">
                  全新 DML V4
                </h1>
                <p className="mt-2 max-w-xl text-sm leading-relaxed text-slate-600">
                  统一管理测试需求、用例设计、自动化执行与评审闭环，并引入 AI 辅助生成与分析能力，显著降低跨系统切换和沟通成本。
                </p>
              </div>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="max-w-xl"
          >
            <PlatformPreview />
          </motion.div>
        </div>

        {/* Right Section - Login Form */}
        <div className="order-1 flex w-full items-start justify-center lg:order-2 lg:w-6/12 lg:items-center xl:w-5/12">
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="w-full max-w-md rounded-3xl border border-slate-200/50 bg-white/80 p-6 shadow-2xl backdrop-blur-xl sm:p-8"
          >
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
              className="mb-6 text-center"
            >
              <h2 className="mb-2 text-2xl font-bold text-slate-800">欢迎回来</h2>
              <p className="text-sm text-slate-500">登录您的测试管理平台</p>
            </motion.div>

            <div className="space-y-4">
              {/* User ID */}
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.6 }}
              >
                <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-slate-700">
                  用户ID
                </label>
                <div className="relative">
                  <User className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                  <input
                    type="text"
                    value={loginForm.user_id}
                    onChange={(e) => onLoginFormChange({ ...loginForm, user_id: e.target.value })}
                    className="w-full rounded-xl border border-slate-200 py-3 pl-12 pr-4 text-sm text-slate-800 placeholder-slate-400 outline-none transition-all hover:border-slate-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
                    placeholder="请输入用户ID"
                    onKeyDown={(e) => e.key === 'Enter' && handleLogin()}
                  />
                </div>
              </motion.div>

              {/* Password */}
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.7 }}
              >
                <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-slate-700">
                  密码
                </label>
                <div className="relative">
                  <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={loginForm.password}
                    onChange={(e) => onLoginFormChange({ ...loginForm, password: e.target.value })}
                    className="w-full rounded-xl border border-slate-200 py-3 pl-12 pr-12 text-sm text-slate-800 placeholder-slate-400 outline-none transition-all hover:border-slate-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
                    placeholder="请输入密码"
                    onKeyDown={(e) => e.key === 'Enter' && handleLogin()}
                  />
                  <button
                    type="button"
                    onClick={() => onShowPasswordChange(!showPassword)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 transition-colors hover:text-slate-600"
                  >
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </motion.div>

              {/* Remember Me & Forgot */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.8 }}
                className="flex items-center justify-between"
              >
                <label className="group flex cursor-pointer items-center gap-2">
                  <input
                    type="checkbox"
                    checked={loginForm.rememberMe}
                    onChange={(e) => onLoginFormChange({ ...loginForm, rememberMe: e.target.checked })}
                    className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="text-xs text-slate-600 transition-colors group-hover:text-slate-800">记住我</span>
                </label>
                <button className="text-xs font-medium text-blue-600 transition-colors hover:text-blue-700">
                  忘记密码?
                </button>
              </motion.div>

              {/* Error Message */}
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: loginError ? 1 : 0, height: loginError ? 'auto' : 0 }}
                transition={{ delay: 0.9 }}
              >
                {loginError && (
                  <div className="flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-600">
                    <AlertCircle size={16} />
                    {loginError}
                  </div>
                )}
              </motion.div>

              {/* Login Button */}
              <motion.button
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1 }}
                onClick={handleLogin}
                disabled={isLoading}
                className="group relative mt-2 w-full overflow-hidden rounded-xl bg-gradient-to-r from-blue-600 to-indigo-700 py-3.5 text-sm font-bold text-white shadow-lg transition-all hover:from-blue-700 hover:to-indigo-800 hover:shadow-xl active:scale-[0.98]"
              >
                <span className={`relative z-10 ${isLoading ? 'opacity-0' : 'opacity-100'}`}>
                  立即登录
                </span>
                {isLoading && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="absolute inset-0 flex items-center justify-center"
                  >
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                      className="h-5 w-5 rounded-full border-2 border-white/30 border-t-white"
                    />
                  </motion.div>
                )}
                <motion.div
                  initial={{ x: '-100%' }}
                  whileHover={{ x: 0 }}
                  className="absolute inset-0 translate-x-full bg-white/10 transition-transform duration-300 group-hover:translate-x-0"
                />
              </motion.button>
            </div>

            {/* Demo Accounts */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 1.1 }}
              className="mt-6 border-t border-slate-200 pt-6"
            >
              <p className="mb-3 text-center text-xs text-slate-500">🚀 快速体验演示账户</p>
              <div className="grid grid-cols-2 gap-2">
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => onQuickLogin('admin')}
                  className="flex items-center justify-center gap-1.5 rounded-lg border border-blue-200 bg-gradient-to-r from-blue-50 to-indigo-50 px-3 py-2.5 text-xs font-medium text-blue-700 transition-all hover:from-blue-100 hover:to-indigo-100"
                >
                  <Cpu size={12} />
                  管理员
                </motion.button>
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => onQuickLogin('alice')}
                  className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-xs font-medium text-slate-700 transition-all hover:bg-slate-100"
                >
                  Alice
                </motion.button>
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => onQuickLogin('bob')}
                  className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-xs font-medium text-slate-700 transition-all hover:bg-slate-100"
                >
                  Bob
                </motion.button>
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => onQuickLogin('eng_zhang_san')}
                  className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-xs font-medium text-slate-700 transition-all hover:bg-slate-100"
                >
                  工程师
                </motion.button>
              </div>
            </motion.div>

            {/* Footer */}
            <motion.footer
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 1.3 }}
              className="mt-6 border-t border-slate-100 pt-4 text-[11px] text-slate-400"
            >
              <div className="flex items-center justify-center gap-1.5 text-slate-500">
                <Server size={12} />
                <span>© 2026 Server Test Designer</span>
              </div>
              <div className="mt-2 flex flex-wrap items-center justify-center gap-x-3 gap-y-1">
                <span>Version v1.0.0</span>
                <span>技术支持: 联系系统管理员</span>
                <span>服务时间: 周一至周五 09:00-18:00</span>
              </div>
              <p className="mt-2 text-center text-slate-400">
                登录即表示同意内部测试平台使用规范与审计策略
              </p>
            </motion.footer>
          </motion.div>
        </div>
      </div>
    </div>
  );
};
