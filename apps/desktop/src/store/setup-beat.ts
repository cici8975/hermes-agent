/**
 * Open `setup_beat` requests: the onboarding chat's card for one beat, one per session.
 *
 * The setup_beat tool row reads this to draw the beat's card. A pick answers the request with
 * `{answer}`; composer text answers it with `{said}` (the backend treats words on the name card as
 * the name). The backend's `request.cancel` (timeout, Stop, Skip setup) clears the entry by request
 * id, so a late cancel never erases a newer card the same session raised.
 */

import type { SetupBeat } from '@hermes/shared'
import { atom } from 'nanostores'

import { registerParkedCardAnswer } from './parked-card-answers'
import { respondToServerRequest } from './server-requests'

export interface SetupBeatRequest {
  beat: SetupBeat
  /** The beat's data from `agent/onboarding_flow.py::BEATS` (options, suggested slugs, plugin names). */
  card: Record<string, unknown>
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

function respond(sessionId: string, result: { answer: Record<string, unknown> } | { said: string }): boolean {
  const request = $setupBeatRequests.get()[sessionId]

  if (!request) {
    return false
  }

  clearSetupBeat(request.requestId, sessionId)

  return respondToServerRequest(request.requestId, result)
}

/** Answer the session's card with the beat's picks. False when no card waits. */
export function answerSetupBeat(sessionId: string, answer: Record<string, unknown>): boolean {
  return respond(sessionId, { answer })
}

/** Composer text typed while a card waits answers it as the user's words. */
export function sayToSetupBeat(sessionId: string, text: string): boolean {
  return Boolean(text.trim()) && respond(sessionId, { said: text.trim() })
}

registerParkedCardAnswer('setup_beat', sayToSetupBeat)
