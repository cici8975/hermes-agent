'use client'

import type { SetupBeat } from '@hermes/shared'

import { WIDGET_SHELL_CLASS } from '@/components/chat/widget-shell'
import { LAYOUTS_AREA } from '@/components/pane-shell/tree/presets'
import { useContributions } from '@/contrib/react/use-contributions'
import { useI18n } from '@/i18n'
import { connectorText, recordOf } from '@/lib/connector-tools'
import { cn } from '@/lib/utils'
import { accentName } from '@/themes/accents'

export const SETUP_BEAT_SHELL_CLASS = cn(
  WIDGET_SHELL_CLASS,
  'my-1.5 text-[length:var(--conversation-text-font-size)] text-(--ui-text-primary)'
)

export const SETUP_BEAT_LABEL_CLASS = 'text-[0.6875rem] leading-4 text-(--ui-text-tertiary)'

const BEATS: readonly SetupBeat[] = ['name', 'theme', 'layout', 'connectors', 'plugins', 'tour', 'build']

/** What a settled card shows: the beat's pick, or how the card closed without one. */
export type SetupBeatOutcome =
  | { answer: Record<string, unknown>; beat: SetupBeat; kind: 'answer' }
  | { beat: SetupBeat | null; kind: 'said' | 'skipped_all' | 'timed_out' }

/** The receipt a setup_beat result calls for; null for a result that showed no card (a value given in
 *  words, a skip, `done`), which draws nothing. */
export function setupBeatOutcome(result: unknown): null | SetupBeatOutcome {
  const row = resultRow(result)
  const beat = BEATS.find(candidate => candidate === row.beat) ?? null

  if (row.skipped_all === true) {
    return { beat, kind: 'skipped_all' }
  }

  if (!beat) {
    return null
  }

  if (typeof row.answer === 'object' && row.answer !== null) {
    return { answer: recordOf(row.answer), beat, kind: 'answer' }
  }

  if (typeof row.said === 'string') {
    return { beat, kind: 'said' }
  }

  return row.timed_out === true ? { beat, kind: 'timed_out' } : null
}

const resultRow = (result: unknown) => recordOf(typeof result === 'string' ? parseJson(result) : result)

/** A refused call (`{error}`): shown as the plain tool row so the failure stays readable. */
export const setupBeatFailed = (result: unknown): boolean => typeof resultRow(result).error === 'string'

function parseJson(text: string): unknown {
  try {
    return JSON.parse(text)
  } catch {
    return null
  }
}

const listOf = (value: unknown): string[] =>
  Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []

function answerText(beat: SetupBeat, answer: Record<string, unknown>, names: AnswerNames): string {
  if (beat === 'theme') {
    return answer.accent === null ? names.themeAccent : accentName(connectorText(answer.accent) ?? '')
  }

  if (beat === 'layout') {
    return names.layout(connectorText(answer.layout) ?? '')
  }

  if (beat === 'connectors' || beat === 'plugins') {
    const picked = listOf(beat === 'connectors' ? answer.connected : answer.installed)

    return picked.length > 0 ? picked.join(', ') : names.none
  }

  return connectorText(answer.label) ?? connectorText(answer[beat]) ?? ''
}

interface AnswerNames {
  layout: (id: string) => string
  none: string
  themeAccent: string
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
