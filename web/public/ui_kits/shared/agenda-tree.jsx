const AGENDA_TREE_BASE = [
  { group: "Opening", open: true, items: [
    { id: "agenda-1", label: "1", title: "Call to Order", page: 1 },
    { id: "agenda-2", label: "2", title: "Declaration of Conflict of Interest", page: 1 },
    { id: "agenda-3", label: "3", title: "Approval of Agenda", page: 1 },
    { id: "agenda-4", label: "4", title: "Adoption of Previous Draft Minutes of Council", page: 1, packagePage: 3, minutes: true },
    { id: "previous-minutes-2026-04-14", label: "4.1", title: "Regular Meeting of Council minutes, April 14, 2026", page: 3, packagePage: 3, minutes: true },
    { id: "agenda-5", label: "5", title: "Business Arising out of the Minutes", page: 1 },
    { id: "agenda-6", label: "6", title: "Council Inquiries to be taken Under Consideration", page: 1 },
  ]},
  { group: "Reports of Standing Committees", open: true, items: [
    { id: "agenda-7-1-planning-heritage", label: "7.1", title: "Planning & Heritage", page: 11, packagePage: 11, childGroup: "Planning & Heritage Items" },
    { id: "agenda-7-2", label: "7.2", title: "Environment & Sustainability", page: 2 },
    { id: "agenda-7-3", label: "7.3", title: "Finance, Audit, Tendering & Administration", page: 1 },
    { id: "agenda-7-4", label: "7.4", title: "Human Resources", page: 1 },
    { id: "agenda-7-5", label: "7.5", title: "Strategic Priorities, Communications & Intergovernmental Cooperation", page: 1 },
    { id: "agenda-7-6", label: "7.6", title: "Protective & Emergency Services", page: 2 },
    { id: "agenda-7-7", label: "7.7", title: "Parks, Recreation & Leisure Activities", page: 2 },
    { id: "agenda-7-8", label: "7.8", title: "Water & Sewer Utility", page: 2 },
    { id: "agenda-7-9", label: "7.9", title: "Economic, Tourism & Cultural Development", page: 2 },
    { id: "agenda-7-10", label: "7.10", title: "Public Works", page: 2 },
    { id: "agenda-7-11-new-business", label: "7.11", title: "New Business", page: 2, childGroup: "New Business Items" },
  ]},
  { group: "Close", open: false, items: [
    { id: "agenda-8", label: "8", title: "Closed Session Motion", page: 2 },
    { id: "agenda-9", label: "9", title: "Business Arising from Closed Session", page: 2 },
    { id: "agenda-10", label: "10", title: "Adjournment", page: 2 },
  ]},
];

const EXTRA_AGENDA_ITEMS = [
  { id: "resolution-pedestrian-mall-agreement", label: "7.1.1", title: "Pedestrian Mall Agreement resolution", page: 26, packagePage: 26, parentId: "agenda-7-1-planning-heritage" },
  { id: "resolution-planning-board-15-clonhaven-major-variance", label: "7.1.2", title: "15 Clonhaven Street major variance resolution", page: 49, packagePage: 49, parentId: "agenda-7-1-planning-heritage" },
  { id: "resolution-planning-board-307-patterson-public-consultation", label: "7.1.3", title: "307 Patterson Drive public consultation resolution", page: 56, packagePage: 56, parentId: "agenda-7-1-planning-heritage" },
  { id: "resolution-planning-board-pid-390534-1179670-public-consultation", label: "7.1.4", title: "Unaddressed PIDs 390534 and 1179670 public consultation resolution", page: 63, packagePage: 63, parentId: "agenda-7-1-planning-heritage" },
  { id: "resolution-planning-board-600-north-river-consolidation", label: "7.1.5", title: "600 North River Road consolidation resolution", page: 80, packagePage: 80, parentId: "agenda-7-1-planning-heritage" },
  { id: "bylaw-reading-ph-zd-2-110-231-brackley-point-road", label: "7.1.6", title: "231 Brackley Point Road rezoning second reading", page: 6, packagePage: 6, rezoning: true, parentId: "agenda-7-1-planning-heritage" },
  { id: "bylaw-reading-ph-zd-2-109-king-dorchester", label: "7.1.7", title: "King and Dorchester Streets rezoning second reading", page: 5, packagePage: 5, rezoning: true, parentId: "agenda-7-1-planning-heritage" },
  { id: "new-business-food-council-appointment", label: "7.11.1", title: "Food Council appointment resolution", page: 253, packagePage: 253, parentId: "agenda-7-11-new-business" },
];

function buildAgendaTree(payload) {
  const existingIds = new Set(EXTRA_AGENDA_ITEMS.map((item) => item.id));
  const packageChildren = (payload?.packageDocuments || [])
    .filter((document) => !existingIds.has(document.document_id))
    .filter((document) => {
      const type = document.document_type || "";
      const title = document.title || "";
      return type === "resolution" || type === "agenda_item_package" || /resolution|reading|bylaw|appointment/i.test(title);
    })
    .flatMap((document) => (document.agenda_item_ids || []).map((parentId) => ({
      id: document.document_id,
      label: "",
      title: document.title,
      page: document.page_start,
      packagePage: document.page_start,
      parentId,
    })));
  const children = [...EXTRA_AGENDA_ITEMS, ...packageChildren];
  return AGENDA_TREE_BASE.map((group) => ({
    ...group,
    items: group.items.map((item) => ({
      ...item,
      children: children.filter((child) => child.parentId === item.id),
    })),
  }));
}

function flattenAgendaItems(items) {
  return items.flatMap((item) => [item, ...flattenAgendaItems(item.children || [])]);
}

function allItems(payload) {
  return buildAgendaTree(payload).flatMap((group) => flattenAgendaItems(group.items));
}

function AgendaTreeItem({ item, selectedId, onSelect, titleOverrides = {} }) {
  const hasChildren = Boolean(item.children?.length);
  const title = titleOverrides[item.id] || item.title;
  const button = <button type="button" className={`tree-button ${selectedId === item.id ? "active" : ""}`} onClick={() => onSelect(item.id)}><span className="label">{item.label}</span><span className="title">{title}</span></button>;
  if (!hasChildren) return button;
  return <details className="tree-nested" open>
    <summary>{button}</summary>
    <div className="tree-children">{item.children.map((child) => <AgendaTreeItem item={child} selectedId={selectedId} onSelect={onSelect} titleOverrides={titleOverrides} key={child.id} />)}</div>
  </details>;
}

function AgendaTree({ audience, setAudience, selectedId, onSelect, payload, title = "Agenda Tree", embedded = false, titleOverrides = {} }) {
  const agendaTree = buildAgendaTree(payload);
  const content = <>
    {audience && setAudience && <div className="tabs" aria-label="Audience tabs">{["public", "council", "staff"].map((name) => <button type="button" key={name} className={audience === name ? "active" : ""} onClick={() => setAudience(name)}>{name[0].toUpperCase() + name.slice(1)}</button>)}</div>}
    <h2 className="section-title">{title}</h2>
    <div className="tree">{agendaTree.map((group) => <details className="tree-group" open={group.open} key={group.group}><summary>{group.group}</summary><div className="tree-items">{group.items.map((item) => <AgendaTreeItem item={item} selectedId={selectedId} onSelect={onSelect} titleOverrides={titleOverrides} key={item.id} />)}</div></details>)}</div>
  </>;
  return embedded ? content : <aside className="agenda-panel">{content}</aside>;
}

window.CouncilAgendaTree = { AgendaTree, allItems, buildAgendaTree };
