import type { CSSProperties } from 'react'

import { selectableClass } from '@/components/onboarding-chat/chip'
import { IS_MAC } from '@/lib/keybinds/combo'
import { cn } from '@/lib/utils'
import type { InterfaceMode } from '@/store/interface-mode'

const CONNECTOR_LEAD_ORDER = [
  'gmail',
  'googlecalendar',
  'googledrive',
  'googledocs',
  'googlesheets',
  'outlook',
  'slack',
  'notion',
  'linear',
  'jira',
  'figma',
  'todoist'
]

const CONNECTOR_PICKER_HIDDEN = new Set(['discord', 'discordbot', 'microsoft_teams'])

export function orderConnectorPicks<T extends { connector: string; enabled?: boolean }>(rows: T[]): T[] {
  const rank = new Map(CONNECTOR_LEAD_ORDER.map((slug, index) => [slug, index]))

  return rows
    .filter(row => row.enabled !== false && !CONNECTOR_PICKER_HIDDEN.has(row.connector))
    .sort((a, b) => {
      const ra = rank.get(a.connector) ?? Number.POSITIVE_INFINITY
      const rb = rank.get(b.connector) ?? Number.POSITIVE_INFINITY

      return ra - rb || a.connector.localeCompare(b.connector)
    })
}

type MiniNode = 1 | { dir: 'column' | 'row'; children: MiniNode[]; weights: number[] }

const ELITE_LAYOUT_ID = 'terminal-deck'

export const LAYOUTS: Array<{ description: string; id: string; mode: InterfaceMode; name: string; tree: MiniNode }> = [
  {
    description: 'For talking to Hermes.',
    id: 'sidebar-left',
    mode: 'simple',
    name: 'Basic',
    tree: { children: [1, 1], dir: 'row', weights: [1, 4.6] }
  },
  {
    description: 'For developers: terminal, files, diffs.',
    id: ELITE_LAYOUT_ID,
    mode: 'advanced',
    name: 'Elite',
    tree: {
      children: [{ children: [1, 1, 1], dir: 'row', weights: [1, 3.2, 1.2] }, 1],
      dir: 'column',
      weights: [3, 1]
    }
  }
]

function MiniTree({ node }: { node: MiniNode }) {
  if (node === 1) {
    return <div className="min-h-0 min-w-0 flex-1 rounded-[3px] bg-foreground/15" />
  }

  return (
    <div className={cn('flex min-h-0 min-w-0 flex-1 gap-1', node.dir === 'row' ? 'flex-row' : 'flex-col')}>
      {node.children.map((child, i) => (
        <div className="flex min-h-0 min-w-0" key={i} style={{ flex: `${node.weights[i]} ${node.weights[i]} 0px` }}>
          <MiniTree node={child} />
        </div>
      ))}
    </div>
  )
}

function MiniWindowButtons() {
  if (IS_MAC) {
    return (
      <span aria-hidden className="flex gap-1">
        <span className="size-1.5 rounded-full bg-[#ff5f57]" />
        <span className="size-1.5 rounded-full bg-[#febc2e]" />
        <span className="size-1.5 rounded-full bg-[#28c840]" />
      </span>
    )
  }

  return (
    <span aria-hidden className="flex items-center justify-end gap-1.5 text-foreground/40">
      <span className="h-px w-1.5 bg-current" />
      <span className="size-1.5 border border-current" />
      <span className="relative size-1.5">
        <span className="absolute top-1/2 left-0 h-px w-full rotate-45 bg-current" />
        <span className="absolute top-1/2 left-0 h-px w-full -rotate-45 bg-current" />
      </span>
    </span>
  )
}

export function LayoutPreviewCard({
  active,
  description,
  name,
  onSelect,
  previewStyle,
  tree
}: {
  active: boolean
  description?: string
  name: string
  onSelect: () => void
  previewStyle?: CSSProperties
  tree: MiniNode
}) {
  return (
    <button aria-pressed={active} className="group flex flex-col items-center gap-2" onClick={onSelect} type="button">
      <span
        className={cn('flex aspect-[10/7] w-full flex-col gap-1.5 rounded-[8px] p-2', selectableClass(active))}
        style={previewStyle}
      >
        <MiniWindowButtons />
        <span className="flex min-h-0 flex-1">
          <MiniTree node={tree} />
        </span>
      </span>
      <span className="flex flex-col items-center gap-0.5">
        <span className={cn('text-xs', active ? 'text-foreground' : 'text-muted-foreground')}>{name}</span>
        {description && <span className="text-[0.68rem] text-muted-foreground/70">{description}</span>}
      </span>
    </button>
  )
}
