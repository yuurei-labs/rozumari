import { Button } from '@rozumari/ui/components/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@rozumari/ui/components/select'
import { useTranslation } from 'react-i18next'
import { View } from 'react-native'

import { useBLE } from '@/components/profile/config/_context'

export const BLEConnection: React.FC = () => {
  const { t } = useTranslation(['common', 'pill-box', 'profile'])
  const { status, startScan, devices, device, setDevice, connect, disconnect } =
    useBLE()

  return (
    <View className='flex-col gap-4'>
      <Select
        value={device}
        onValueChange={setDevice}
        items={devices.map((dev) => ({
          value: dev.id,
          label: dev.name ?? t('pill-box:details.device.unnamed_device'),
        }))}
      >
        <SelectTrigger disabled={status !== 'idle'}>
          <SelectValue
            placeholder={t('profile:config.device.selector.placeholder')}
          />
        </SelectTrigger>

        <SelectContent title={t('profile:config.device.selector.title')}>
          {devices.map((dev) => (
            <SelectItem key={dev.id} value={dev.id}>
              {dev.name ?? t('pill-box:details.device.unnamed_device')} (
              {dev.id})
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {status !== 'connected' && (
        <View className='flex-row gap-4'>
          <Button
            variant='outline'
            className='flex-1'
            disabled={status !== 'idle'}
            onPress={startScan}
          >
            {status === 'scanning'
              ? t('profile:config.actions.scanning')
              : t('profile:config.actions.scan')}
          </Button>
          <Button
            className='flex-1'
            disabled={status === 'connecting'}
            onPress={connect}
          >
            {status === 'connecting'
              ? t('profile:config.actions.connecting')
              : t('profile:config.actions.connect')}
          </Button>
        </View>
      )}

      {status === 'connected' && (
        <Button variant='destructive' onPress={disconnect}>
          {t('profile:config.actions.disconnect')}
        </Button>
      )}
    </View>
  )
}
