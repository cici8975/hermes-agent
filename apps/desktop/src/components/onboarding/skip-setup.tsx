import { useStore } from '@nanostores/react'

import { useGatewayRequest } from '@/app/gateway/hooks/use-gateway-request'
import { Tip } from '@/components/ui/tooltip'
import { useI18n } from '@/i18n'
import { $onboardingSession, skipOnboarding } from '@/store/onboarding-run'

/** Skip setup, shown in the composer of the onboarding chat only. */
export function OnboardingSkip({ sessionId }: { sessionId: null | string }) {
  const session = useStore($onboardingSession)

  if (!session || !sessionId || session.runtimeId !== sessionId) {
    return null
  }

  return <SkipButton runtimeId={session.runtimeId} />
}

// Split out so the gateway hook mounts only in the onboarding chat, not in every composer.
function SkipButton({ runtimeId }: { runtimeId: string }) {
  const { t } = useI18n()
  const { requestGateway } = useGatewayRequest()

  return (
    <Tip label={t.firstRun.skipTip}>
      <button
        className="ml-auto text-[11px] text-(--ui-text-quaternary) transition-colors hover:text-(--ui-text-secondary)"
        onClick={() => void skipOnboarding(requestGateway, runtimeId)}
        type="button"
      >
        {t.firstRun.skip}
      </button>
    </Tip>
  )
}
