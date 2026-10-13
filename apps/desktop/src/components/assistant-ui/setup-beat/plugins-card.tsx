'use client'

import type { CatalogPluginPresence, PluginsManageResult } from '@hermes/shared'
import { useStore } from '@nanostores/react'
import { useQuery } from '@tanstack/react-query'

import { useSessionView } from '@/app/chat/session-view'
import { useConnectionOwner } from '@/components/assistant-ui/use-connection-owner'
import { Button } from '@/components/ui/button'
import { Chip } from '@/components/ui/chip'
import { useI18n } from '@/i18n'
import { lookupPluginCatalogEntry } from '@/lib/plugin-catalog'
import { $agentPlugins } from '@/store/agent-plugins'
import type { ConnectionOwner } from '@/store/connection-request'
import { requestGatewayForAgent } from '@/store/gateway'
import { openCatalogPluginInstall } from '@/store/plugin-catalog-install'

const pluginNames = (card: Record<string, unknown>): string[] =>
  Array.isArray(card.plugins) ? card.plugins.filter((name): name is string => typeof name === 'string') : []

async function readPresence(owner: ConnectionOwner, names: string[]): Promise<CatalogPluginPresence[]> {
  const result = await requestGatewayForAgent<PluginsManageResult>(owner.connectionId, owner.profile, 'plugins.manage', {
    action: 'presence',
    names
  })

  return result.presence ?? []
}

async function openInstall(name: string, profile: string): Promise<void> {
  const lookup = await lookupPluginCatalogEntry(name)

  if (lookup.ok) {
    openCatalogPluginInstall(lookup.entry, profile)
  }
}

/** The plugins this OS runs, from the card payload; Install opens the reviewed install dialog in place,
 *  Continue answers with the ones installed. */
export function PluginsCard({
  card,
  onContinue
}: {
  card: Record<string, unknown>
  onContinue: (installed: string[]) => void
}) {
  const { t } = useI18n()
  const copy = t.firstRun
  const storedId = useStore(useSessionView().$storedId)
  const owner = useConnectionOwner(storedId, true)
  const names = pluginNames(card)
  const plugins = useStore($agentPlugins)

  const presence = useQuery({
    enabled: Boolean(owner) && names.length > 0,
    queryFn: () => readPresence(owner!, names),
    queryKey: ['onboarding', 'plugins.presence', owner?.connectionId, owner?.profile, ...names],
    staleTime: Infinity
  })

  const installed = new Set(
    plugins.flatMap(row => [row.catalog_name, row.name]).filter((name): name is string => Boolean(name))
  )

  const rows = presence.data ?? []

  return (
    <div className="grid gap-3">
      {presence.isPending && names.length > 0 ? (
        <p className="text-xs text-(--ui-text-tertiary)" role="status">
          {copy.loading}
        </p>
      ) : rows.length === 0 ? (
        <p className="text-xs text-(--ui-text-tertiary)">{copy.noPlugins}</p>
      ) : (
        <div className="grid grid-cols-2 gap-2 p-1">
          {rows.map(row => {
            const on = installed.has(row.name)

            return (
              <Chip
                className="w-full"
                key={row.name}
                label={row.title || row.name}
                on={on}
                onToggle={() => {
                  if (!on && owner) {
                    void openInstall(row.name, owner.profile)
                  }
                }}
                sub={on ? copy.installed : row.sentence || copy.install}
              />
            )
          })}
        </div>
      )}
      <div>
        <Button
          onClick={() => onContinue(names.filter(name => installed.has(name)))}
          size="xs"
          variant="textStrong"
        >
          {t.common.continue}
        </Button>
      </div>
    </div>
  )
}
