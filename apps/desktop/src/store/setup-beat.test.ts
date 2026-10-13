import type { ServerRequest } from '@hermes/shared'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { setupBeatOutcome } from '@/components/assistant-ui/setup-beat/receipt'

import { answerParkedCard } from './parked-card-answers'
import { rememberServerRequest, resetServerRequestsForTests } from './server-requests'
import { $setupBeatRequests, clearSetupBeat, parkSetupBeat } from './setup-beat'

function parkNameCard(requestId: string) {
  const respond = vi.fn()

  const request: ServerRequest = { fail: vi.fn(), id: requestId, method: 'setup_beat', params: { session_id: 'rt-1' }, respond }

  rememberServerRequest(request)
  parkSetupBeat({ beat: 'name', card: {}, question: 'What should I call you?', requestId, sessionId: 'rt-1' })

  return respond
}

afterEach(() => {
  resetServerRequestsForTests()
  $setupBeatRequests.set({})
})

describe('setup_beat card', () => {
  it('takes composer text as the user words and closes, and a stale cancel leaves a newer card', () => {
    parkNameCard('srq-1')
    clearSetupBeat('srq-old', 'rt-1')
    expect($setupBeatRequests.get()['rt-1']?.requestId).toBe('srq-1')

    const respond = parkNameCard('srq-2')

    expect(answerParkedCard('rt-1', '  Sid  ')).toBe(true)
    expect(respond).toHaveBeenCalledWith({ said: 'Sid' })
    expect($setupBeatRequests.get()['rt-1']).toBeUndefined()
    expect(answerParkedCard('rt-1', 'again')).toBe(false)
  })

  it('collapses every way a card can close to a receipt, and draws nothing for a card-less call', () => {
    expect(setupBeatOutcome({ answer: { name: 'Sid' }, beat: 'name' })).toMatchObject({ kind: 'answer' })
    expect(setupBeatOutcome({ beat: 'theme', said: 'make it violet' })).toMatchObject({ kind: 'said' })
    expect(setupBeatOutcome({ beat: 'layout', timed_out: true })).toMatchObject({ kind: 'timed_out' })
    expect(setupBeatOutcome({ skipped_all: true })).toMatchObject({ kind: 'skipped_all' })
    expect(setupBeatOutcome({ completed: true })).toBeNull()
  })
})
