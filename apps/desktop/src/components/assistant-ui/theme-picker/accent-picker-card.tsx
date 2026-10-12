'use client'

import { useState } from 'react'

import { AccentSwatch } from '@/components/ui/accent-swatch'
import { Codicon } from '@/components/ui/codicon'
import { useI18n } from '@/i18n'
import { useTheme } from '@/themes'
import { accentsFor, CUSTOM_ACCENT_PREFIX, NOUS_ACCENT } from '@/themes/accents'

export interface AccentPickerCardProps {
  /** A swatch id, `custom:#rrggbb`, or null for the theme's own accent (Nous blue). */
  onPick: (accent: null | string) => void
}

/** The eight accent swatches plus a custom colour well; a swatch click is the pick. */
export function AccentPickerCard({ onPick }: AccentPickerCardProps) {
  const { t } = useI18n()
  const { renderedMode } = useTheme()
  const [custom, setCustom] = useState<null | string>(null)

  return (
    <div className="flex flex-wrap items-center gap-2.5 p-1" role="group">
      {accentsFor(renderedMode === 'dark').map(swatch => (
        <AccentSwatch
          active={false}
          hex={swatch.hex}
          key={swatch.id}
          name={swatch.name}
          onPick={() => onPick(swatch.id === 'nous' ? null : swatch.id)}
        />
      ))}
      <AccentSwatch
        active={custom !== null}
        hex={custom ?? NOUS_ACCENT}
        name={t.assistant.themePicker.customColor}
        onColorChange={setCustom}
      />
      {custom !== null && (
        <button
          aria-label={t.assistant.themePicker.customColor}
          className="grid size-7 place-items-center rounded-full border border-(--ui-stroke-tertiary) text-(--ui-text-secondary) hover:bg-(--chrome-action-hover)"
          onClick={() => onPick(`${CUSTOM_ACCENT_PREFIX}${custom.toLowerCase()}`)}
          type="button"
        >
          <Codicon name="check" size="0.875rem" />
        </button>
      )}
    </div>
  )
}
