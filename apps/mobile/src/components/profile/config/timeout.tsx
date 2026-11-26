import { Button } from '@rozumari/ui/components/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@rozumari/ui/components/select'
import { Typography } from '@rozumari/ui/components/typography'
import * as React from 'react'
import { useTranslation } from 'react-i18next'
import { View } from 'react-native'

import { useBLE } from '@/components/profile/config/_context'

type TimeoutKey = 'drop' | 'open' | 'close'

const MINUTE_OPTIONS = Array.from({ length: 13 }, (_, i) => {
  const val = i * 5
  return {
    value: String(val),
    label: `${String(val).padStart(2, '0')} min`,
  }
})

const SECOND_OPTIONS = Array.from({ length: 12 }, (_, i) => {
  const val = i * 5
  return {
    value: String(val),
    label: `${String(val).padStart(2, '0')} sec`,
  }
})

export const BLETimeoutConfig: React.FC = () => {
  const { t } = useTranslation(['common', 'profile'])
  const { config, send } = useBLE()

  const [drop, setDrop] = React.useState<number>(config?.timeout.drop ?? 5)
  const [open, setOpen] = React.useState<number>(config?.timeout.open ?? 10)
  const [close, setClose] = React.useState<number>(config?.timeout.close ?? 10)

  const updateDuration = (
    key: TimeoutKey,
    newMins: number,
    newSecs: number
  ) => {
    const clampedMins = Math.min(60, Math.max(0, newMins))
    const clampedSecs =
      clampedMins === 60 ? 0 : Math.min(59, Math.max(0, newSecs))
    const total = clampedMins * 60 + clampedSecs

    if (key === 'drop') setDrop(total)
    else if (key === 'open') setOpen(total)
    else if (key === 'close') setClose(total)
  }

  const renderTimeoutField = (
    label: string,
    key: TimeoutKey,
    valueInSeconds: number
  ) => {
    const mins = Math.min(60, Math.floor(valueInSeconds / 60))
    const secs = mins === 60 ? 0 : valueInSeconds % 60
    const secOptions = mins === 60 ? SECOND_OPTIONS.slice(0, 1) : SECOND_OPTIONS

    return (
      <View className='gap-1.5'>
        <Typography className='font-medium'>{label}</Typography>

        <View className='flex-row items-center gap-2'>
          <View className='flex-1'>
            <Select
              value={String(mins)}
              onValueChange={(val) =>
                updateDuration(key, Number(val ?? 0), secs)
              }
              items={MINUTE_OPTIONS}
            >
              <SelectTrigger>
                <SelectValue placeholder='MM' />
              </SelectTrigger>
              <SelectContent>
                {MINUTE_OPTIONS.map((m) => (
                  <SelectItem key={m.value} value={m.value}>
                    {m.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </View>

          <Typography className='font-bold'>:</Typography>

          <View className='flex-1'>
            <Select
              value={String(secs)}
              onValueChange={(val) =>
                updateDuration(key, mins, Number(val ?? 0))
              }
              items={secOptions}
            >
              <SelectTrigger>
                <SelectValue placeholder='SS' />
              </SelectTrigger>
              <SelectContent>
                {secOptions.map((s) => (
                  <SelectItem key={s.value} value={s.value}>
                    {s.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </View>
        </View>
      </View>
    )
  }

  if (!config) return null
  return (
    <View className='gap-4'>
      {renderTimeoutField(t('profile:config.timeout.drop.title'), 'drop', drop)}
      {renderTimeoutField(t('profile:config.timeout.open.title'), 'open', open)}
      {renderTimeoutField(
        t('profile:config.timeout.close.title'),
        'close',
        close
      )}

      <Button onPress={() => send(`timeout.${drop}.${open}.${close}`)}>
        {t('common:save_changes')}
      </Button>
    </View>
  )
}
