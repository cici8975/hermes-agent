'use client'

import type { SetupBeat } from '@hermes/shared'

import { WIDGET_SHELL_CLASS } from '@/components/chat/widget-shell'
import { LAYOUTS_AREA } from '@/components/pane-shell/tree/presets'
import { useContributions } from '@/contrib/react/use-contributions'
import { useI18n } from '@/i18n'
import { cn } from '@/lib/utils'
import type { SetupBeatAnswer, SetupBeatToolResult } from '@/store/setup-beat'
import { accentName } from '@/themes/accents'

export const SETUP_BEAT_SHELL_CLASS = cn(
  WIDGET_SHELL_CLASS,
  'my-1.5 text-[length:var(--conversation-text-font-size)] text-(--ui-text-primary)'
)

export const SETUP_BEAT_LABEL_CLASS = 'text-[0.6875rem] leading-4 text-(--ui-text-tertiary)'

/** What a settled card shows: the beat's pick, or how the card closed without one. */
export type SetupBeatOutcome =
  | { answer: SetupBeatAnswer; beat: SetupBeat; kind: 'answer' }
  | { beat: SetupBeat | null; kind: 'said' | 'skipped_all' | 'timed_out' }

/** The receipt a setup_beat result calls for; null for a result that showed no card (a value given in
 *  words, a skip, `done`), which draws nothing. */
export function setupBeatOutcome(result: SetupBeatToolResult): null | SetupBeatOutcome {
  const beat = result.beat ?? null

  if (result.skipped_all) {
    return { beat, kind: 'skipped_all' }
  }

  if (!beat) {
    return null
  }

  if (result.answer) {
    return { answer: result.answer, beat, kind: 'answer' }
  }

  if (result.said !== undefined) {
    return { beat, kind: 'said' }
  }

  return result.timed_out ? { beat, kind: 'timed_out' } : null
}

interface AnswerNames {
  layout: (id: string) => string
  none: string
  themeAccent: string
}

function answerText(beat: SetupBeat, answer: SetupBeatAnswer, names: AnswerNames): string {
  switch (beat) {
    case 'theme':
      return answer.accent ? accentName(answer.accent) : names.themeAccent

    case 'layout':
      return names.layout(answer.layout ?? '')

    case 'connectors':
    case 'plugins': {
      const picked = (beat === 'connectors' ? answer.connected : answer.installed) ?? []

      return picked.length > 0 ? picked.join(', ') : names.none
    }

    case 'name':
      return answer.name ?? ''

    case 'tour':
      return answer.label ?? answer.tour ?? ''

    case 'build':
      return answer.label ?? answer.build ?? ''
  }
}

/** One line where the choice happened: the beat, then what was picked or how the card closed. */
export function SetupBeatReceipt({ outcome }: { outcome: SetupBeatOutcome }) {
  const { t } = useI18n()
  const copy = t.firstRun
  const presets = useContributions(LAYOUTS_AREA)

  const closed = { said: copy.answeredInChat, skipped_all: copy.skippedAll, timed_out: copy.noAnswer }

  const text =
    outcome.kind === 'answer'
      ? answerText(outcome.beat, outcome.answer, {
          layout: id => presets.find(preset => preset.id === id)?.title ?? id,
          none: copy.noneChosen,
          themeAccent: t.assistant.themePicker.themeAccent
        })
      : closed[outcome.kind]

  return (
    <div className={cn(SETUP_BEAT_SHELL_CLASS, 'flex flex-wrap items-center gap-x-2')} data-setup-beat-settled="">
      {outcome.beat && outcome.kind !== 'skipped_all' && (
        <span className="text-(--ui-text-tertiary)">{copy.beats[outcome.beat]}</span>
      )}
      <span className={cn(outcome.kind !== 'answer' && 'italic text-(--ui-text-tertiary)')}>{text}</span>
    </div>
  )
}
