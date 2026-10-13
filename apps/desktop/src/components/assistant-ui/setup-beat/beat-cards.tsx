'use client'

import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Chip } from '@/components/ui/chip'
import { Input } from '@/components/ui/input'
import { useI18n } from '@/i18n'
import type { BeatOption } from '@/store/setup-beat'

/** A text box for the name. The OS account's full name is offered as a row and is sent only when picked. */
export function NameCard({ onName, suggested }: { onName: (name: string) => void; suggested?: string }) {
  const { t } = useI18n()
  const [name, setName] = useState('')
  const typed = name.trim()

  return (
    <div className="grid gap-2">
      {suggested && <Chip label={t.firstRun.useName(suggested)} on={false} onToggle={() => onName(suggested)} variant="pill" />}
      <form
        className="flex items-center gap-2"
        onSubmit={event => {
          event.preventDefault()

          if (typed) {
            onName(typed)
          }
        }}
      >
        <Input
          aria-label={t.firstRun.namePlaceholder}
          autoFocus
          className="flex-1"
          onChange={event => setName(event.target.value)}
          placeholder={t.firstRun.namePlaceholder}
          value={name}
        />
        <Button disabled={!typed} size="xs" type="submit" variant="textStrong">
          {t.common.continue}
        </Button>
      </form>
    </div>
  )
}

/** The backend's options for tour and build, one pill each; a click is the pick. */
export function OptionsCard({ onPick, options }: { onPick: (option: BeatOption) => void; options: BeatOption[] }) {
  return (
    <div className="flex flex-wrap gap-2" role="group">
      {options.map(option => (
        <Chip key={option.id} label={option.label} on={false} onToggle={() => onPick(option)} variant="pill" />
      ))}
    </div>
  )
}
