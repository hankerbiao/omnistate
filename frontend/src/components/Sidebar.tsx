import type { PageType, NavItem } from '../types/app'

interface SidebarProps {
  currentPage: PageType
  onNavigate: (page: PageType) => void
  visibleItems: NavItem[]
}

const Sidebar: React.FC<SidebarProps> = ({ currentPage, onNavigate, visibleItems }) => {
  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <div className="sidebar__logo" aria-hidden>TH</div>
        <div>
          <div className="sidebar__title">TestHub</div>
          <div className="sidebar__version">测试运营平台</div>
        </div>
      </div>

      <nav className="sidebar__nav" aria-label="主导航">
        <span className="sidebar__section-label">工作区</span>
        {visibleItems.map(item => {
          const active = currentPage === item.key
          return (
            <button
              key={item.key}
              type="button"
              className={`sidebar__item${active ? ' sidebar__item--active' : ''}`}
              onClick={() => onNavigate(item.key)}
              aria-current={active ? 'page' : undefined}
            >
              <span className="sidebar__icon" aria-hidden>{item.icon}</span>
              <span>{item.label}</span>
            </button>
          )
        })}
      </nav>

      <div className="sidebar__footer">DML V4 · 研发运营</div>
    </aside>
  )
}

export default Sidebar
