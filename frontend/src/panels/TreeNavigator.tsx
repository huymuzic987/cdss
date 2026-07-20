import { X } from 'lucide-react'
import { useState } from 'react'
import type { TreeSummary } from '../api/types'

const CATEGORIES: { label: string; match: (key: string, name: string) => boolean }[] = [
  {
    label: 'Diagnosis & Risk',
    match: (k, n) => /diagno|classif|risk/i.test(k + ' ' + n),
  },
  {
    label: 'Treatment',
    match: (k, n) => /threshold|essential|optimal|drug|combinat|bp.target/i.test(k + ' ' + n),
  },
  {
    label: 'Comorbidities',
    match: (k, n) => /coronary|ckd|kidney|diabetes|heart.fail|cardiac/i.test(k + ' ' + n),
  },
  {
    label: 'Special Conditions',
    match: (k, n) => /pregnan|emergency|resistant/i.test(k + ' ' + n),
  },
]

interface Props {
  trees: TreeSummary[]
  activeTreeKey: string | null
  onSelect: (key: string) => void
}

export function TreeNavigator({ trees, activeTreeKey, onSelect }: Props) {
  const [query, setQuery] = useState('')
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({})

  const toggleGroup = (label: string) =>
    setCollapsed((prev) => ({ ...prev, [label]: !prev[label] }))

  const trimmed = query.trim().toLowerCase()
  const filtered = trimmed
    ? trees.filter(
        (t) =>
          t.name_en.toLowerCase().includes(trimmed) ||
          t.tree_key.toLowerCase().includes(trimmed),
      )
    : null

  // Group trees into categories; uncategorized go to "Other"
  const categorized = CATEGORIES.map((cat) => ({
    label: cat.label,
    trees: trees.filter((t) => cat.match(t.tree_key, t.name_en)),
  })).filter((g) => g.trees.length > 0)

  const categorizedKeys = new Set(categorized.flatMap((g) => g.trees.map((t) => t.tree_key)))
  const other = trees.filter((t) => !categorizedKeys.has(t.tree_key))
  if (other.length > 0) categorized.push({ label: 'Other', trees: other })

  return (
    <div className="tree-nav">
      <div className="tree-nav-header">
        <span className="tree-nav-title">Clinical Guidelines</span>
      </div>

      <div className="tree-nav-search">
        <svg className="tree-nav-search-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <circle cx="11" cy="11" r="8"/>
          <path d="M21 21l-4.35-4.35"/>
        </svg>
        <input
          className="tree-nav-search-input"
          type="text"
          placeholder="Search trees..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        {query && (
          <button type="button" className="tree-nav-search-clear" onClick={() => setQuery('')} aria-label="Clear search">
            <X size={11} />
          </button>
        )}
      </div>

      <div className="tree-nav-body">
        {filtered ? (
          filtered.length === 0 ? (
            <div className="tree-nav-empty">No trees match "{query}"</div>
          ) : (
            filtered.map((t) => (
              <TreeNavItem key={t.tree_key} tree={t} active={t.tree_key === activeTreeKey} onSelect={onSelect} indent={false} />
            ))
          )
        ) : (
          categorized.map(({ label, trees: groupTrees }) => (
            <div key={label} className="tree-nav-group">
              <button
                type="button"
                className="tree-nav-group-header"
                onClick={() => toggleGroup(label)}
                aria-expanded={!collapsed[label]}
              >
                <svg
                  className={`tree-nav-chevron${collapsed[label] ? '' : ' open'}`}
                  width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d="M9 18l6-6-6-6"/>
                </svg>
                {label}
              </button>
              {!collapsed[label] && (
                <div className="tree-nav-group-items">
                  {groupTrees.map((t) => (
                    <TreeNavItem key={t.tree_key} tree={t} active={t.tree_key === activeTreeKey} onSelect={onSelect} indent />
                  ))}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  )
}

function TreeNavItem({
  tree,
  active,
  onSelect,
  indent,
}: {
  tree: TreeSummary
  active: boolean
  onSelect: (key: string) => void
  indent: boolean
}) {
  return (
    <button
      type="button"
      className={`tree-nav-item${active ? ' active' : ''}${indent ? ' indented' : ''}`}
      onClick={() => onSelect(tree.tree_key)}
      title={tree.name_en}
    >
      {tree.name_en}
    </button>
  )
}
