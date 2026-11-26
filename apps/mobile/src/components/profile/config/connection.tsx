import { Button } from '@rozumari/ui/components/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@rozumari/ui/components/select'
import { View } from 'react-native'

import { useBLE } from '@/components/profile/config/_context'

export const BLEConnection: React.FC = () => {
  const { status, startScan, devices, device, setDevice, connect, disconnect } =
    useBLE()

  return (
    <View className='flex-col gap-4'>
      <Select
        value={device}
        onValueChange={setDevice}
        items={devices.map((dev) => ({
          value: dev.id,
          label: `${dev.name} (${dev.id})`,
        }))}
      >
        <SelectTrigger disabled={status !== 'idle'}>
          <SelectValue />
        </SelectTrigger>

        <SelectContent>
          {devices.map((dev) => (
            <SelectItem key={dev.id} value={dev.id}>
              {dev.name} ({dev.id})
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
            Scan
          </Button>
          <Button
            className='flex-1'
            disabled={status === 'connecting'}
            onPress={connect}
          >
            Connect
          </Button>
        </View>
      )}

      {status === 'connected' && (
        <Button variant='destructive' onPress={disconnect}>
          Disconnect
        </Button>
      )}
    </View>
  )
}
