import { beforeEach, describe, expect, it, vi } from 'vitest'

import { $onboardingPhase } from './onboarding-phase'
import { $onboardingDecided, $onboardingSurfaceClear } from './onboarding-presence'
import { $onboardingEnded, decideOnboarding, noteSetupBeatResult, startOnboarding } from './onboarding-run'
import { $connection } from './session'

const ensureProfile = async (): Promise<void> => undefined

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
})

describe('onboarding run', () => {
  it('opens the onboarding chat when due and never shows a clear moment before it', async () => {
    const clear: boolean[] = []
    const stop = $onboardingSurfaceClear.subscribe(value => clear.push(value))
    const { calls, request } = backend({ eligible: true, run: true })
    const resume = vi.fn(async () => undefined)

    await decideOnboarding(request, resume, { ensureProfile })
    stop()

    expect(calls).toEqual(['onboarding.state', 'onboarding.start'])
    expect(resume).toHaveBeenCalledWith('st-1', true)
    expect($onboardingDecided.get()).toBe(true)
    expect(clear).not.toContain(true)
  })

  it('ends once on the model finishing, and frees the first-run surfaces', async () => {
    const { request } = backend({ eligible: true, run: true })

    await startOnboarding(request, vi.fn(async () => undefined), { ensureProfile })
    noteSetupBeatResult({ completed: true })
    noteSetupBeatResult({ skipped_all: true })

    expect($onboardingPhase.get()).toBe('done')
    expect($onboardingEnded.get()).toBe('done')
    expect($onboardingSurfaceClear.get()).toBe(true)
  })
})
