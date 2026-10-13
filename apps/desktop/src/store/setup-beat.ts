/**
 * Open `setup_beat` requests: the onboarding chat's card for one beat, one per session.
 *
 * The setup_beat tool row reads this to draw the beat's card. A pick answers the request with
 * `{answer}`; composer text answers it with `{said}` (the backend treats words on the name card as
 * the name). The backend's `request.cancel` (timeout, Stop, Skip setup) clears the entry by request
 * id, so a late cancel never erases a newer card the same session raised.
 */

import type { ToolCallMessagePart } from '@assistant-ui/react'
import type { SetupBeat } from '@hermes/shared'
import { atom } from 'nanostores'

import { recordOf } from '@/lib/connector-tools'

import { registerParkedCardAnswer } from './parked-card-answers'
import { respondToServerRequest } from './server-requests'

export interface BeatOption {
  id: string
  label: string
}

/** A beat's card data (`agent/onboarding_flow.py::BEATS`, `tools/setup_beat_tool.py::_card`): name `{suggested?}`
 *  (the account's full name), layout/tour/build `{options}`, connectors `{suggested}` (slugs), plugins `{plugins}`. */
export interface SetupBeatCard {
  options?: BeatOption[]
  plugins?: string[]
  suggested?: string | string[]
}

/** The picks a card answers with, per beat (`SetupBeatResult.answer`). Tour and build add the option's label. */
export interface SetupBeatAnswer {
  accent?: null | string
  build?: string
  connected?: string[]
  installed?: string[]
  label?: string
  layout?: string
  name?: string
  newly_connected?: string[]
  tour?: string
}

/** What `tools/setup_beat_tool.py` returns to the model, as the transcript's tool row carries it. */
export interface SetupBeatToolResult {
  answer?: SetupBeatAnswer
  beat?: SetupBeat
  completed?: boolean
  error?: string
  said?: string
  skipped_all?: boolean
  timed_out?: boolean
}

/** A setup_beat tool row's result: the object a live row carries, or the JSON text of a reloaded one. */
export function setupBeatResult(result: ToolCallMessagePart['result']): SetupBeatToolResult {
  // SAFETY: tools/setup_beat_tool.py::_result builds every result from an agent/onboarding_flow.py step.
  return recordOf(result) as SetupBeatToolResult
}

export interface SetupBeatRequest {
  beat: SetupBeat
  card: SetupBeatCard
  question: string
  requestId: string
  sessionId: string
}

export const $setupBeatRequests = atom<Record<string, SetupBeatRequest>>({})

export function parkSetupBeat(request: SetupBeatRequest): void {
  $setupBeatRequests.set({ ...$setupBeatRequests.get(), [request.sessionId]: request })
}

/** Drop the card for `requestId`; a no-op when the session's card is a newer one. */
export function clearSetupBeat(requestId: string, sessionId: string): boolean {
  const { [sessionId]: current, ...others } = $setupBeatRequests.get()

  if (current?.requestId !== requestId) {
    return false
  }

  $setupBeatRequests.set(others)

  return true
}

function respond(sessionId: string, result: { answer: SetupBeatAnswer } | { said: string }): boolean {
  const request = $setupBeatRequests.get()[sessionId]

  if (!request) {
    return false
  }

  clearSetupBeat(request.requestId, sessionId)

  return respondToServerRequest(request.requestId, { ...result })
}

/** Answer the session's card with the beat's picks. False when no card waits. */
export function answerSetupBeat(sessionId: string, answer: SetupBeatAnswer): boolean {
  return respond(sessionId, { answer })
}

/** Composer text typed while a card waits answers it as the user's words. */
export function sayToSetupBeat(sessionId: string, text: string): boolean {
  return Boolean(text.trim()) && respond(sessionId, { said: text.trim() })
}

registerParkedCardAnswer('setup_beat', sayToSetupBeat)
