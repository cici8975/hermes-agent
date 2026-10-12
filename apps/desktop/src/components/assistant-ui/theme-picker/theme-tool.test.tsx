import type { ToolCallMessagePartProps } from '@assistant-ui/react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { atom } from 'nanostores'
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest'

import { PRIMARY_SESSION_VIEW, type SessionView, SessionViewProvider } from '@/app/chat/session-view'
import { registerLayoutPresets } from '@/app/contrib/layout-presets'
import { I18nProvider } from '@/i18n'
import { rememberServerRequest, resetServerRequestsForTests } from '@/store/server-requests'
import { $themePicks, parkThemePick } from '@/store/theme-pick'
import { ThemeProvider } from '@/themes/context'

import { ThemeTool } from './theme-tool'

const SESSION = 'theme-session'

const view: SessionView = { ...PRIMARY_SESSION_VIEW, $runtimeId: atom(SESSION), $storedId: atom('stored-theme') }

function renderRow(props: Partial<ToolCallMessagePartProps>) {
  // SAFETY: ThemeTool reads only args, result, toolName and toolCallId; the rest of the part API is unused.
  const row = { args: {}, toolCallId: 'call-1', toolName: 'set_theme', ...props } as ToolCallMessagePartProps

  return render(
    <I18nProvider configClient={null} initialLocale="en">
      <ThemeProvider>
        <SessionViewProvider value={view}>
          <ThemeTool {...row} />
        </SessionViewProvider>
      </ThemeProvider>
    </I18nProvider>
  )
}

function park(picker: 'accent' | 'layout') {
  const respond = vi.fn()

  rememberServerRequest({ fail: vi.fn(), id: 'srq-7', method: 'theme.pick', params: {}, respond })
  parkThemePick({ picker, requestId: 'srq-7', sessionId: SESSION })

  return respond
}

describe('ThemeTool', () => {
  beforeAll(() => {
    registerLayoutPresets()
  })

  afterEach(() => {
    cleanup()
    $themePicks.set({})
    resetServerRequestsForTests()
  })

  it('answers the waiting card with the swatch the user clicked, then shows the receipt', () => {
    const respond = park('accent')

    renderRow({ args: { picker: 'accent' } })
    fireEvent.click(screen.getByRole('button', { name: 'Ultraviolet' }))

    expect(respond).toHaveBeenCalledWith({ picked: { accent: 'violet' } })
    expect(screen.getByText('Ultraviolet').closest('[data-theme-settled]')).not.toBeNull()
  })

  it('draws the layout card for a call made through the tool_call bridge', () => {
    const respond = park('layout')

    renderRow({
      args: { calls: [{ arguments: { picker: 'layout' }, name: 'set_theme' }] },
      toolName: 'tool_call'
    })
    fireEvent.click(screen.getByRole('button', { name: /Elite/ }))

    expect(respond).toHaveBeenCalledWith({ picked: { layout: 'terminal-deck' } })
  })
})
