'use client'

import { useStore } from '@nanostores/react'

import { isLayoutNode } from '@/components/pane-shell/tree/model'
import { layoutPresetResting, LAYOUTS_AREA } from '@/components/pane-shell/tree/presets'
import { TreeThumbnail } from '@/components/pane-shell/tree/renderer/layout-picker'
import { $activePresetId } from '@/components/pane-shell/tree/store'
import { useContributions } from '@/contrib/react/use-contributions'
import { useI18n } from '@/i18n'
import { selectableCardClass } from '@/lib/selectable-card'
import { cn } from '@/lib/utils'

export interface LayoutPickerCardProps {
  onPick: (preset: string) => void
}

/** Basic is the Simple shell's sidebar-left; Elite is the Advanced terminal deck. */
const CHOICES = [
  { id: 'sidebar-left', name: 'basic', detail: 'basicDetail' },
  { id: 'terminal-deck', name: 'elite', detail: 'eliteDetail' }
] as const

/** The two first-run layouts as the layout picker's own preset cards; a card click is the pick. */
export function LayoutPickerCard({ onPick }: LayoutPickerCardProps) {
  const copy = useI18n().t.assistant.themePicker
  const presets = useContributions(LAYOUTS_AREA)
  const activeId = useStore($activePresetId)

  return (
    <div className="grid grid-cols-2 gap-3 p-1" role="group">
      {CHOICES.map(choice => {
        const tree = presets.find(preset => preset.id === choice.id)?.data
        const active = choice.id === activeId

        return (
          <button
            aria-pressed={active}
            className={cn(selectableCardClass({ active, prominent: true }), 'flex flex-col gap-2 p-2 text-left')}
            key={choice.id}
            onClick={() => onPick(choice.id)}
            type="button"
          >
            <span className="flex h-20 w-full">
              {isLayoutNode(tree) && <TreeThumbnail node={tree} resting={layoutPresetResting(choice.id)} />}
            </span>
            <span className="flex flex-col gap-0.5">
              <span className={cn('text-xs font-medium', active ? 'text-foreground' : 'text-(--ui-text-secondary)')}>
                {copy[choice.name]}
              </span>
              <span className="text-[0.68rem] text-(--ui-text-tertiary)">{copy[choice.detail]}</span>
            </span>
          </button>
        )
      })}
    </div>
  )
}
