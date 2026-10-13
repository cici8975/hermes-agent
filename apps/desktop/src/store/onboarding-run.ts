/**
 * First-run onboarding as this window runs it: one chat in the default profile, opened by the
 * backend's `onboarding.start`, ended by the model (`setup_beat(beat="done")`) or by Skip setup.
 *
 * This module is the one writer of `$onboardingPhase` and of the `onboarding` presence surface, so
 * the two never disagree: the surface is open exactly while the phase is `shown`. The backend owns
 * whether onboarding is due (`onboarding.state`) and writes the install-level flag when a run ends.
 */

import type { MachineFactsResult, OnboardingRunStateResult, OnboardingStartResult } from '@hermes/shared'
import { atom } from 'nanostores'

import { getRuntimeI18nLocale } from '@/i18n/runtime'
import type { GatewayRequester } from '@/lib/yolo-session'

import { $onboardingPhase } from './onboarding-phase'
import { markOnboardingDecided, setOnboardingSurfaceActive } from './onboarding-presence'
import { ensureGatewayProfile } from './profile'
import { $connection } from './session'
import type { SetupBeatToolResult } from './setup-beat'

export type OnboardingRequest = GatewayRequester

/** Opens a stored session on screen, replacing the route (`useSessionActions().resumeSession`). */
export type OnboardingResume = (storedId: string, replaceRoute?: boolean) => Promise<void>

export interface OnboardingSession {
  runtimeId: string
  storedId: string
}

/** The onboarding chat while a run is on screen in this window. */
export const $onboardingSession = atom<null | OnboardingSession>(null)

/** How the last run in this window ended; the end-of-onboarding surfaces wake on it. */
export const $onboardingEnded = atom<'done' | 'skipped' | null>(null)

// The backend runs onboarding in its root profile whichever profile the app was on.
const ONBOARDING_PROFILE = 'default'

$onboardingPhase.subscribe(phase => setOnboardingSurfaceActive('onboarding', phase === 'shown'))

/** Same machine as this app (`local`), or a backend somewhere else (`remote`). A local connection is
 *  this machine; any other compares the backend's OS and architecture with Electron's. */
async function factsSource(request: OnboardingRequest): Promise<'local' | 'remote'> {
  if ($connection.get()?.mode === 'local') {
    return 'local'
  }

  const [profile, facts] = await Promise.all([
    window.hermesDesktop?.getMachineProfile?.().catch(() => null),
    request<MachineFactsResult>('machine.facts').catch(() => null)
  ])

  const arch = (value: null | string | undefined) => (value === 'x64' || value === 'amd64' ? 'x86_64' : value)

  const same =
    Boolean(profile && facts) &&
    profile?.platform === facts?.machine.os_family &&
    arch(profile?.arch) === arch(facts?.machine.native_arch)

  return same ? 'local' : 'remote'
}

interface StartOptions {
  /** Points the window's gateway at the profile onboarding runs in (`store/profile.ts::ensureGatewayProfile`). */
  ensureProfile?: (profile: string) => Promise<void>
  rerun?: boolean
}

/** Open the onboarding chat (a new one for a rerun, else the run in progress or a new one). */
export async function startOnboarding(
  request: OnboardingRequest,
  resume: OnboardingResume,
  { ensureProfile = ensureGatewayProfile, rerun = false }: StartOptions = {}
): Promise<boolean> {
  $onboardingPhase.set('shown')
  $onboardingEnded.set(null)

  try {
    await ensureProfile(ONBOARDING_PROFILE)

    const started = await request<OnboardingStartResult>('onboarding.start', {
      facts_source: await factsSource(request),
      locale: getRuntimeI18nLocale(),
      rerun
    })

    $onboardingSession.set({ runtimeId: started.session_id, storedId: started.stored_session_id })
    await resume(started.stored_session_id, true)

    return true
  } catch (error) {
    console.warn('[onboarding] could not start', error)
    $onboardingSession.set(null)
    $onboardingPhase.set('failed')

    return false
  }
}

let decision: null | Promise<void> = null

/**
 * The main window's boot check, once per launch: open onboarding when the backend says it is due on
 * this install and the free tier can drive it. First-run surfaces wait until this has answered; the
 * presence surface is set before the answer is published, so they never see a clear moment in between.
 */
export function decideOnboarding(
  request: OnboardingRequest,
  resume: OnboardingResume,
  options?: StartOptions
): Promise<void> {
  decision ??= readAndStart(request, resume, options)

  return decision
}


async function readAndStart(request: OnboardingRequest, resume: OnboardingResume, options?: StartOptions): Promise<void> {
  try {
    const state = await request<OnboardingRunStateResult>('onboarding.state')

    if (state.run && state.eligible) {
      await startOnboarding(request, resume, options)
    }
  } catch (error) {
    console.warn('[onboarding] state could not be read', error)
  } finally {
    markOnboardingDecided()
  }
}

/** The run ended: the model finished it or the user skipped. Later calls for the same run do nothing. */
export function endOnboarding(outcome: 'done' | 'skipped'): void {
  if ($onboardingPhase.get() !== 'shown') {
    return
  }

  $onboardingPhase.set(outcome)
  $onboardingEnded.set(outcome)
  $onboardingSession.set(null)
}

/** Skip setup: the backend ends the run and closes the card that waits. */
export async function skipOnboarding(request: OnboardingRequest, runtimeId: string): Promise<void> {
  try {
    await request('onboarding.skip', { session_id: runtimeId })
  } catch (error) {
    console.warn('[onboarding] skip failed', error)
  }

  endOnboarding('skipped')
}

/** A `setup_beat` result that ends the run: `completed` (the model said done) or `skipped_all`. */
export function noteSetupBeatResult(result: SetupBeatToolResult): void {
  if (result.completed) {
    endOnboarding('done')
  } else if (result.skipped_all) {
    endOnboarding('skipped')
  }
}
