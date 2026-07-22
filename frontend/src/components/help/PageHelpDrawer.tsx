import { X } from 'lucide-react';
import type { HelpSectionDoc, PageHelpDoc } from '../../help/pageHelpDocs';

interface PageHelpDrawerProps {
  doc: PageHelpDoc;
  sectionDoc?: HelpSectionDoc;
  onClose: () => void;
}

interface HelpListProps {
  title: string;
  items: string[];
}

function HelpList({ title, items }: HelpListProps) {
  return (
    <section className="page-help__section">
      <h3>{title}</h3>
      <ul>
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

export default function PageHelpDrawer({ doc, sectionDoc, onClose }: PageHelpDrawerProps) {
  return (
    <>
      <div className="drawer-overlay page-help__overlay" onClick={onClose} aria-hidden="true" />
      <aside className="drawer drawer--right page-help" role="dialog" aria-modal="true" aria-labelledby="page-help-title">
        <div className="drawer__header page-help__header">
          <div>
            <p className="page-help__eyebrow">页面说明</p>
            <h2 id="page-help-title" className="drawer__title page-help__title">{doc.title}</h2>
            <p className="drawer__subtitle page-help__subtitle">{doc.summary}</p>
          </div>
          <button type="button" className="drawer__close" onClick={onClose} aria-label="关闭页面说明">
            <X size={16} />
          </button>
        </div>

        <div className="drawer__body page-help__body">
          {sectionDoc && (
            <section className="page-help__section page-help__section--overview">
              <div className="page-help__section-label">分组概览</div>
              <h3>{sectionDoc.title}</h3>
              <p>{sectionDoc.summary}</p>
              <div className="page-help__chips">
                {sectionDoc.pages.map((page) => (
                  <span key={page} className="page-help__chip">{page}</span>
                ))}
              </div>
            </section>
          )}

          <HelpList title="适用场景" items={doc.scenarios} />
          <HelpList title="页面区域" items={doc.areas} />
          <HelpList title="核心操作" items={doc.actions} />
          <HelpList title="常见流程" items={doc.workflows} />
          <HelpList title="注意事项" items={doc.notes} />
          <HelpList title="关联页面" items={doc.relatedPages} />
        </div>
      </aside>
    </>
  );
}
