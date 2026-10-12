/**
 * Open `theme.pick` requests (the set_theme picker card), one per session.
 *
 * The card in the tool row reads this to draw the picker; a pick applies the
 * value at once and answers the request with what was applied. The backend's
 * `request.cancel` (timeout, Stop) clears the entry by request id, so a late
 * cancel never erases a newer card the same session raised.
 */

import type { ThemePicker, ThemePickResult } from '@hermes/shared'
import { atom } from 'nanostores'

import { type AppearanceValues, applyAppearance } from './appearance-apply'
import { respondToServerRequest } from './server-requests'

export interface ThemePickRequest {
  picker: ThemePicker
  requestId: string
  sessionId: string
}

export const $themePicks = atom<Record<string, ThemePickRequest>>({})

export function parkThemePick(request: ThemePickRequest): void {
  $themePicks.set({ ...$themePicks.get(), [request.sessionId]: request })
}

/** Drop the card for `requestId`; a no-op when the session's card is a newer one. */
export function clearThemePick(requestId: string, sessionId: string): boolean {
  const { [sessionId]: current, ...others } = $themePicks.get()

  if (current?.requestId !== requestId) {
    return false
  }

  $themePicks.set(others)

  return true
}

function answer(sessionId: string, result: ThemePickResult): boolean {
  const request = $themePicks.get()[sessionId]

  if (!request) {
    return false
  }

  clearThemePick(request.requestId, sessionId)

  return respondToServerRequest(request.requestId, { ...result })
}

/** Apply the user's pick and answer the session's card with it. False when no card waits or the value is unknown. */
export function pickTheme(sessionId: string, values: AppearanceValues): boolean {
  const applied = applyAppearance(values)

  return applied.success && answer(sessionId, { picked: applied.applied })
}

export function cancelThemePick(sessionId: string): boolean {
  return answer(sessionId, { cancelled: true })
}
