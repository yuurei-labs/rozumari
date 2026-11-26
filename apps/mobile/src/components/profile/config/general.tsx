import DateTimePicker from '@react-native-community/datetimepicker'
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
import { Platform, View } from 'react-native'

import { useBLE } from '@/components/profile/config/_context'

function parseTimeStringToDate(timeStr: string): Date {
  const [hh = '04', mm = '00'] = timeStr.split(':')
  const d = new Date()
  d.setHours(Number(hh) || 0, Number(mm) || 0, 0, 0)
  return d
}

function formatDateToSyncTime(date: Date): string {
  const hh = String(date.getHours()).padStart(2, '0')
  const mm = String(date.getMinutes()).padStart(2, '0')
  return `${hh}:${mm}:00`
}

export const BLEGeneralConfig: React.FC = () => {
  const { config, send } = useBLE()

  const [syncTime, setSyncTime] = React.useState<string>(
    config?.general.syncTime ?? '04:00:00'
  )
  const [timezone, setTimezone] = React.useState<number>(
    config?.general.timezone ?? 7
  )
  const [language, setLanguage] = React.useState<string | null>(
    config?.general.language ?? 'vi'
  )
  const [showTimePicker, setShowTimePicker] = React.useState(false)

  const pickerDateValue = React.useMemo(
    () => parseTimeStringToDate(syncTime),
    [syncTime]
  )

  if (!config) return null
  return (
    <View className='gap-4'>
      <View className='gap-1.5'>
        <Typography className='font-medium'>Sync Time</Typography>
        <Button variant='outline' onPress={() => setShowTimePicker(true)}>
          {syncTime}
        </Button>

        {showTimePicker && (
          <DateTimePicker
            value={pickerDateValue}
            mode='time'
            is24Hour
            minuteInterval={30}
            display={Platform.OS === 'ios' ? 'spinner' : 'default'}
            onValueChange={(_, date) => {
              if (Platform.OS === 'android') setShowTimePicker(false)
              setSyncTime(formatDateToSyncTime(date))
            }}
            onDismiss={() => setShowTimePicker(false)}
            onNeutralButtonPress={() => setShowTimePicker(false)}
          />
        )}
      </View>

      <View className='gap-1.5'>
        <Typography className='font-medium'>Timezone</Typography>
        <Select
          value={String(timezone)}
          onValueChange={(val) => setTimezone(Number(val))}
          items={TIMEZONE_OPTIONS.map((tz) => ({
            value: String(tz.value),
            label: tz.label,
          }))}
        >
          <SelectTrigger>
            <SelectValue placeholder='Select timezone' />
          </SelectTrigger>
          <SelectContent>
            {TIMEZONE_OPTIONS.map((tz) => (
              <SelectItem key={tz.value} value={String(tz.value)}>
                {tz.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </View>

      <View className='gap-1.5'>
        <Typography className='font-medium'>Language</Typography>
        <Select
          value={language}
          onValueChange={setLanguage}
          items={LANGUAGE_OPTIONS}
        >
          <SelectTrigger>
            <SelectValue placeholder='Select language' />
          </SelectTrigger>
          <SelectContent>
            {LANGUAGE_OPTIONS.map((lang) => (
              <SelectItem key={lang.value} value={lang.value}>
                {lang.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </View>

      <Button
        onPress={() => send(`general.${timezone}.${syncTime}.${language}`)}
      >
        Save Changes
      </Button>
    </View>
  )
}

const TIMEZONE_OPTIONS = [
  { value: -12, label: 'Etc/GMT+12 (UTC-12)' },
  { value: -11, label: 'Pacific/Midway (UTC-11)' },
  { value: -10, label: 'Pacific/Honolulu (UTC-10)' },
  { value: -9, label: 'America/Anchorage (UTC-9)' },
  { value: -8, label: 'America/Los Angeles (UTC-8)' },
  { value: -7, label: 'America/Denver (UTC-7)' },
  { value: -6, label: 'America/Chicago (UTC-6)' },
  { value: -5, label: 'America/New York (UTC-5)' },
  { value: -4, label: 'America/Halifax (UTC-4)' },
  { value: -3, label: 'America/Sao Paulo (UTC-3)' },
  { value: -2, label: 'Atlantic/South Georgia (UTC-2)' },
  { value: -1, label: 'Atlantic/Azores (UTC-1)' },
  { value: 0, label: 'Europe/London (UTC+0)' },
  { value: 1, label: 'Europe/Berlin (UTC+1)' },
  { value: 2, label: 'Europe/Athens (UTC+2)' },
  { value: 3, label: 'Europe/Moscow (UTC+3)' },
  { value: 4, label: 'Asia/Dubai (UTC+4)' },
  { value: 5, label: 'Asia/Karachi (UTC+5)' },
  { value: 6, label: 'Asia/Dhaka (UTC+6)' },
  { value: 7, label: 'Asia/Ho Chi Minh (UTC+7)' },
  { value: 8, label: 'Asia/Singapore (UTC+8)' },
  { value: 9, label: 'Asia/Tokyo (UTC+9)' },
  { value: 10, label: 'Australia/Sydney (UTC+10)' },
  { value: 11, label: 'Pacific/Noumea (UTC+11)' },
  { value: 12, label: 'Pacific/Auckland (UTC+12)' },
  { value: 13, label: 'Pacific/Tongatapu (UTC+13)' },
  { value: 14, label: 'Pacific/Kiritimati (UTC+14)' },
] as const

const LANGUAGE_OPTIONS = [
  { value: 'vi', label: 'Tiếng Việt' },
  { value: 'en', label: 'English' },
] as const
