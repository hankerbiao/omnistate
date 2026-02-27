import { useState } from "react";
import "./Sidebar.css";

interface NavItem {
  id: string;
  label: string;
  icon?: React.ReactNode;
}

interface NavGroup {
  id: string;
  title: string;
  items: NavItem[];
}

interface SidebarProps {
  activeModule: string;
  activePage: string;
  onNavigate: (moduleId: string, pageId: string) => void;
}

const NAV_GROUPS: NavGroup[] = [
  {
    id: "workflow",
    title: "流程管理",
    items: [
      { id: "all", label: "全部事项" },
      { id: "requirement", label: "需求开发" },
      { id: "test_case", label: "测试用例" },
    ],
  },
  {
    id: "testing",
    title: "测试工具",
    items: [
      { id: "coming-soon", label: "即将上线..." },
    ],
  },
  {
    id: "reports",
    title: "报告分析",
    items: [
      { id: "coming-soon", label: "即将上线..." },
    ],
  },
];

function Sidebar({ activeModule, activePage, onNavigate }: SidebarProps) {
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(
    new Set(["workflow"])
  );

  const toggleGroup = (groupId: string) => {
    const newExpanded = new Set(expandedGroups);
    if (newExpanded.has(groupId)) {
      newExpanded.delete(groupId);
    } else {
      newExpanded.add(groupId);
    }
    setExpandedGroups(newExpanded);
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="logo-placeholder">W</div>
        <h1>测试工作台</h1>
      </div>

      <nav className="sidebar-nav">
        {NAV_GROUPS.map((group) => (
          <div key={group.id} className="nav-group">
            <button
              className="nav-group-title"
              onClick={() => toggleGroup(group.id)}
            >
              <span className="nav-group-text">{group.title}</span>
              <span
                className={`nav-group-arrow ${
                  expandedGroups.has(group.id) ? "expanded" : ""
                }`}
              >
                <svg
                  width="12"
                  height="12"
                  viewBox="0 0 12 12"
                  fill="none"
                >
                  <path
                    d="M3 4.5L6 7.5L9 4.5"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </span>
            </button>
            {expandedGroups.has(group.id) && (
              <div className="nav-group-items">
                {group.items.map((item) => (
                  <button
                    key={item.id}
                    className={`nav-item ${
                      activeModule === group.id && activePage === item.id
                        ? "active"
                        : ""
                    }`}
                    onClick={() => onNavigate(group.id, item.id)}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="version-info">v1.0.0</div>
      </div>
    </aside>
  );
}

export default Sidebar;