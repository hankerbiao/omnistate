import type { PageType, NavSection } from '../types/app'
import type { NavItemWithIcon } from '../config/navigation'

interface SidebarProps {
  currentPage: PageType
  onNavigate: (page: PageType) => void
  visibleItems: NavItemWithIcon[]
  sections: NavSection[]
}

const Sidebar: React.FC<SidebarProps> = ({ currentPage, onNavigate, visibleItems, sections }) => {
  const visibleKeys = new Set(visibleItems.map(item => item.key))
  const itemByKey = new Map(visibleItems.map(item => [item.key, item]))

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
        {sections.map(section => {
          const sectionItems = section.keys
            .filter(key => visibleKeys.has(key))
            .map(key => itemByKey.get(key)!)

          if (sectionItems.length === 0) return null

          return (
            <div key={section.label} className="sidebar__section">
              <span className="sidebar__section-label">{section.label}</span>
              {sectionItems.map(item => {
                const active = currentPage === item.key
                const Icon = item.icon
                return (
                  <button
                    key={item.key}
                    type="button"
                    className={`sidebar__item${active ? ' sidebar__item--active' : ''}`}
                    onClick={() => onNavigate(item.key)}
                    aria-current={active ? 'page' : undefined}
                  >
                    <span className="sidebar__icon" aria-hidden>
                      <Icon size={16} />
                    </span>
                    <span>{item.label}</span>
                  </button>
                )
              })}
            </div>
          )
        })}
      </nav>

      <div className="sidebar__footer">DML V4 · 研发运营</div>
    </aside>
  )
}

export default Sidebar
