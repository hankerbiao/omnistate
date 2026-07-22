import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles/theme.css";
import { Layout, type PageKey } from "./components/Layout";
import { ToastProvider } from "./components/ui";
import { Overview } from "./pages/Overview";
import { UserPermissions } from "./pages/UserPermissions";
import { UserQuota } from "./pages/UserQuota";
import { ApiKeys } from "./pages/ApiKeys";
import { ApiDebugger } from "./pages/ApiDebugger";
import { Capabilities } from "./pages/Capabilities";
import { Logs } from "./pages/Logs";
import { Mcp } from "./pages/Mcp";
import { UsageGuide } from "./pages/UsageGuide";
import { Home } from "./pages/Home";
import { ForceChangePassword } from "./pages/ForceChangePassword";
import { api } from "./services/api";
import type { MockUser } from "./types";

const FALLBACK_USER: MockUser = {
  id: "loading",
  username: null,
  name: "加载中",
  email: "loading@dml.local",
  role: "admin",
  team: "开放平台",
  avatar: "开",
  allowedCapabilityIds: [],
  quota: { enabled: true, monthlyLimit: 0, rpmLimit: 0, concurrency: 0 },
  mustChangePassword: false,
};

const PAGE_KEYS: PageKey[] = ["overview", "guide", "users", "quota", "keys", "capabilities", "debugger", "logs", "mcp"];

function getPageFromHash(): PageKey {
  const candidate = window.location.hash.replace("#/", "");
  return PAGE_KEYS.includes(candidate as PageKey) ? (candidate as PageKey) : "overview";
}

function saveSession(user: MockUser) {
  window.localStorage.setItem("dml-open-platform-user", user.id);
  window.localStorage.setItem("dml-open-platform-session-user", JSON.stringify(user));
}

function readSessionUser(): MockUser | null {
  const raw = window.localStorage.getItem("dml-open-platform-session-user");
  if (!raw) return null;
  try {
    return JSON.parse(raw) as MockUser;
  } catch {
    return null;
  }
}

function App() {
  const [page, setPage] = useState<PageKey>(getPageFromHash);
  const [users, setUsers] = useState<MockUser[]>([FALLBACK_USER]);
  const [user, setUser] = useState<MockUser | null>(null);
  const [booting, setBooting] = useState(true);
  const [showHome, setShowHome] = useState(() => !window.location.hash || window.location.hash === "#/home");

  useEffect(() => {
    if (user) api.setConsoleUserId(user.id);
  }, [user]);

  useEffect(() => {
    const onHashChange = () => {
      if (window.location.hash === "#/home") {
        setShowHome(true);
        return;
      }
      setShowHome(false);
      setPage(getPageFromHash());
    };
    window.addEventListener("hashchange", onHashChange);
    if (!window.location.hash) window.history.replaceState(null, "", "#/home");
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  useEffect(() => {
    const savedId = window.localStorage.getItem("dml-open-platform-user");
    const savedUser = readSessionUser();
    if (!savedId) {
      setBooting(false);
      return;
    }
    api.setConsoleUserId(savedId);
    if (!savedUser || savedUser.id !== savedId) {
      window.localStorage.removeItem("dml-open-platform-user");
      window.localStorage.removeItem("dml-open-platform-session-user");
      setBooting(false);
      return;
    }
    setUser(savedUser);
    setUsers([savedUser]);
    if (savedUser.role === "admin") api.listUsers().then(setUsers).catch(() => setUsers([savedUser]));
    setBooting(false);
  }, []);

  const navigate = (nextPage: PageKey) => {
    if (nextPage === page) return;
    window.location.hash = `/${nextPage}`;
  };

  const changeUser = (nextUser: MockUser) => {
    api.setConsoleUserId(nextUser.id);
    setUser(nextUser);
    saveSession(nextUser);
    if (nextUser.role !== "admin" && (page === "users" || page === "quota")) navigate("overview");
  };

  const updateUser = (updatedUser: MockUser) => {
    setUsers((current) => current.map((item) => item.id === updatedUser.id ? updatedUser : item));
    if (user?.id === updatedUser.id) setUser(updatedUser);
  };

  const addUser = (createdUser: MockUser) => {
    setUsers((current) => [...current.filter((item) => item.id !== "loading"), createdUser]);
  };


  const handleLogin = (loggedInUser: MockUser) => {
    setUser(loggedInUser);
    saveSession(loggedInUser);
    setShowHome(false);
    window.location.hash = "/overview";
    if (loggedInUser.role === "admin") api.listUsers().then(setUsers).catch(() => setUsers([loggedInUser]));
    else setUsers([loggedInUser]);
  };

  const handlePasswordChanged = (updatedUser: MockUser) => {
    setUser(updatedUser);
    saveSession(updatedUser);
    if (updatedUser.role === "admin") api.listUsers().then(setUsers).catch(() => setUsers([updatedUser]));
    else setUsers([updatedUser]);
  };

  const handleLogout = () => {
    window.localStorage.removeItem("dml-open-platform-user");
    window.localStorage.removeItem("dml-open-platform-session-user");
    setUser(null);
    setUsers([FALLBACK_USER]);
    api.setConsoleUserId("user_admin");
  };

  if (booting) return <ToastProvider><div className="login-shell"><span className="body-sm text-muted">正在进入控制台...</span></div></ToastProvider>;
  if (showHome) {
    return (
      <ToastProvider>
        <Home
          user={user}
          onEnter={() => {
            setShowHome(false);
            window.location.hash = "/overview";
          }}
          onLogin={handleLogin}
        />
      </ToastProvider>
    );
  }
  if (!user) return <ToastProvider><Home user={null} onEnter={() => undefined} onLogin={handleLogin} /></ToastProvider>;
  if (user.mustChangePassword) {
    return (
      <ToastProvider>
        <ForceChangePassword user={user} onChanged={handlePasswordChanged} onLogout={handleLogout} />
      </ToastProvider>
    );
  }

  return (
    <ToastProvider>
      <Layout page={page} onNavigate={navigate} user={user} users={users} onUserChange={changeUser} onLogout={handleLogout}>
        {page === "overview" && <Overview user={user} />}
        {page === "guide" && <UsageGuide />}
        {page === "users" && user.role === "admin" && <UserPermissions users={users} onUpdateUser={updateUser} onCreateUser={addUser} />}
        {page === "quota" && user.role === "admin" && <UserQuota users={users} onUpdateUser={updateUser} />}
        {page === "keys" && <ApiKeys user={user} />}
        {page === "capabilities" && <Capabilities user={user} />}
        {page === "debugger" && <ApiDebugger user={user} />}
        {page === "logs" && <Logs user={user} />}
        {page === "mcp" && <Mcp />}
      </Layout>
    </ToastProvider>
  );
}

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("找不到 #root 挂载节点");
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
