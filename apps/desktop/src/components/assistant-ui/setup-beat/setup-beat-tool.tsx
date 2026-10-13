'use client'

import type { ToolCallMessagePartProps } from '@assistant-ui/react'
import type { SetupBeat } from '@hermes/shared'
import { useStore } from '@nanostores/react'
import { type ReactNode, useState } from 'react'

import { useSessionView } from '@/app/chat/session-view'
import { ConnectorDirectoryCard } from '@/components/assistant-ui/connector-directory-card'
import { AccentPickerCard } from '@/components/assistant-ui/theme-picker/accent-picker-card'
import { LayoutPickerCard } from '@/components/assistant-ui/theme-picker/layout-picker-card'
import { cn } from '@/lib/utils'
import { applyAppearance } from '@/store/appearance-apply'
import { $setupBeatRequests, answerSetupBeat, type SetupBeatRequest } from '@/store/setup-beat'

import { ToolFallback } from '../tool/fallback'

import { beatOptions, NameCard, OptionsCard } from './beat-cards'
import { PluginsCard } from './plugins-card'
import {
  SETUP_BEAT_LABEL_CLASS,
  SETUP_BEAT_SHELL_CLASS,
  setupBeatFailed,
  type SetupBeatOutcome,
  setupBeatOutcome,
  SetupBeatReceipt
} from './receipt'

/** The card body for one beat; `answer` sends the beat's picks and settles the card. */
function BeatBody({ answer, request }: { answer: (picks: Record<string, unknown>) => void; request: SetupBeatRequest }) {
  const { card } = request

  switch (request.beat) {
    case 'name':
      return (
        <NameCard
          onName={name => answer({ name })}
          suggested={typeof card.suggested === 'string' ? card.suggested : undefined}
        />
      )

    case 'theme':
      return (
        <AccentPickerCard
          onPick={accent => {
            if (applyAppearance({ accent: accent ?? 'theme' }).success) {
              answer({ accent })
            }
          }}
        />
      )

    case 'layout':
      return (
        <LayoutPickerCard
          onPick={layout => {
            if (applyAppearance({ layout }).success) {
              answer({ layout })
            }
          }}
        />
      )

    case 'plugins':
      return <PluginsCard card={card} onContinue={installed => answer({ installed })} />

    case 'tour':

    case 'build':
      return (
        <OptionsCard
          onPick={option => answer({ [request.beat]: option.id, label: option.label })}
          options={beatOptions(card)}
        />
      )

    case 'connectors':
      return null
  }
}

function suggestedSlugs(card: Record<string, unknown>): string[] {
  return Array.isArray(card.suggested) ? card.suggested.filter((slug): slug is string => typeof slug === 'string') : []
}

function BeatShell({ beat, children, question }: { beat: SetupBeat; children: ReactNode; question: string }) {
  return (
    <div className={cn(SETUP_BEAT_SHELL_CLASS, 'grid gap-3')} data-setup-beat={beat}>
      {question && <span className={SETUP_BEAT_LABEL_CLASS}>{question}</span>}
      {children}
    </div>
  )
}

/** The setup_beat tool row: the beat's card while its request waits, then a one-line receipt where the
 *  choice happened. A card closed by words in the composer or by the deadline collapses the same way. */
export function SetupBeatTool(props: ToolCallMessagePartProps) {
  const sessionId = useStore(useSessionView().$runtimeId)
  const requests = useStore($setupBeatRequests)
  const [settled, setSettled] = useState<null | SetupBeatOutcome>(null)

  if (props.result !== undefined) {
    if (setupBeatFailed(props.result)) {
      return <ToolFallback {...props} />
    }

    const outcome = setupBeatOutcome(props.result)

    return outcome ? <SetupBeatReceipt outcome={outcome} /> : null
  }

  // Answered: the card is gone from the store a beat before tool.complete brings the result.
  if (settled) {
    return <SetupBeatReceipt outcome={settled} />
  }

  const request = sessionId ? requests[sessionId] : undefined

  if (!sessionId || !request) {
    return null
  }

  const answer = (picks: Record<string, unknown>) => {
    if (answerSetupBeat(sessionId, picks)) {
      setSettled({ answer: picks, beat: request.beat, kind: 'answer' })
    }
  }

  if (request.beat === 'connectors') {
    return (
      <div className="grid gap-1" data-setup-beat="connectors">
        {request.question && <span className={cn(SETUP_BEAT_LABEL_CLASS, 'px-3.5')}>{request.question}</span>}
        <ConnectorDirectoryCard
          onContinue={({ connected, newly_connected }) => answer({ connected, newly_connected })}
          suggested={suggestedSlugs(request.card)}
        />
      </div>
    )
  }

  return (
    <BeatShell beat={request.beat} question={request.question}>
      <BeatBody answer={answer} request={request} />
    </BeatShell>
  )
}
