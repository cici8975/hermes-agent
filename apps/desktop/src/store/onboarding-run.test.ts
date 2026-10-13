import { beforeEach, describe, expect, it, vi } from 'vitest'

import { $onboardingPhase } from './onboarding-phase'
import { $onboardingDecided, $onboardingSurfaceClear } from './onboarding-presence'
import {
  $onboardingEnded,
  $onboardingSettleFrom,
  decideOnboarding,
  noteSetupBeatResult,
  startOnboarding
} from './onboarding-run'
import { $connection, $selectedStoredSessionId } from './session'

const ensureProfile = async (): Promise<void> => undefined

// What resumeSession does for the test: the stored chat becomes the one on screen.
const resume = vi.fn(async (storedId: string) => $selectedStoredSessionId.set(storedId))

function backend(state: { eligible: boolean; run: boolean }) {
  const calls: string[] = []
  const started = { resumed: false, session_id: 'rt-1', stored_session_id: 'st-1' }

  const request = async <T,>(method: string): Promise<T> => {
    calls.push(method)

    // SAFETY: the fake answers onboarding.state and onboarding.start with their contract result shapes.
    return (method === 'onboarding.state' ? state : started) as T
  }

  return { calls, request }
}

beforeEach(() => {
  // SAFETY: factsSource reads only `mode`; a local connection skips the machine comparison.
  $connection.set({ mode: 'local' } as never)
  $onboardingPhase.set('idle')
  $onboardingEnded.set(null)
  $onboardingSettleFrom.set(null)
  $selectedStoredSessionId.set(null)
})

describe('onboarding run', () => {
  it('opens the onboarding chat when due and never shows a clear moment before it', async () => {
    const clear: boolean[] = []
    const stop = $onboardingSurfaceClear.subscribe(value => clear.push(value))
    const { calls, request } = backend({ eligible: true, run: true })

    await decideOnboarding(request, resume, { ensureProfile })
    stop()

    expect(calls).toEqual(['onboarding.state', 'onboarding.start'])
    expect(resume).toHaveBeenCalledWith('st-1', true)
    expect($onboardingDecided.get()).toBe(true)
    expect(clear).not.toContain(true)
  })

  it('ends once on the model finishing, and frees the first-run surfaces', async () => {
    const { request } = backend({ eligible: true, run: true })

    await startOnboarding(request, resume, { ensureProfile })
    noteSetupBeatResult({ completed: true })
    noteSetupBeatResult({ skipped_all: true })

    expect($onboardingPhase.get()).toBe('done')
    expect($onboardingEnded.get()).toBe('done')
    expect($onboardingSurfaceClear.get()).toBe(true)
  })

  it('frees the first-run surfaces in another chat mid-run and arms the end-of-onboarding wait', async () => {
    const { request } = backend({ eligible: true, run: true })

    await startOnboarding(request, resume, { ensureProfile })
    expect($onboardingSurfaceClear.get()).toBe(false)

    $selectedStoredSessionId.set('another-chat')

    expect($onboardingPhase.get()).toBe('shown')
    expect($onboardingSurfaceClear.get()).toBe(true)
    expect($onboardingSettleFrom.get()).not.toBeNull()
  })
})
