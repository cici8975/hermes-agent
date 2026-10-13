import { useState } from 'react'

import { useGatewayRequest } from '@/app/gateway/hooks/use-gateway-request'
import { sessionRoute } from '@/app/routes'
import { Button } from '@/components/ui/button'
import { useI18n } from '@/i18n'
import { isOnboardingEnabled } from '@/lib/onboarding-enabled'
import { notifyError } from '@/store/notifications'
import { startOnboarding } from '@/store/onboarding-run'
import { requestRoute } from '@/store/recovery-requests'

import { ListRow } from './primitives'

/** Advanced → Run onboarding again. Only builds with the guided first run show it. */
export function OnboardingSettings() {
  return isOnboardingEnabled() ? <RerunOnboardingRow /> : null
}

function RerunOnboardingRow() {
  const copy = useI18n().t.firstRun.rerun
  const { requestGateway } = useGatewayRequest()
  const [starting, setStarting] = useState(false)

  const rerun = async () => {
    setStarting(true)

    const started = await startOnboarding(requestGateway, async storedId => requestRoute(sessionRoute(storedId)), {
      rerun: true
    })

    setStarting(false)

    if (!started) {
      notifyError(null, copy.failed)
    }
  }

  return (
    <ListRow
      action={
        <Button disabled={starting} onClick={() => void rerun()} size="sm" variant="outline">
          {copy.action}
        </Button>
      }
      description={copy.description}
      title={copy.title}
    />
  )
}
