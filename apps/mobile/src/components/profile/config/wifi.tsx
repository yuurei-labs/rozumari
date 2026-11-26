import { Button } from '@rozumari/ui/components/button'
import { Input } from '@rozumari/ui/components/input'
import { Typography } from '@rozumari/ui/components/typography'
import * as React from 'react'
import { View } from 'react-native'

import { useBLE } from '@/components/profile/config/_context'

export const BLEWifiConfig: React.FC = () => {
  const { config, send } = useBLE()

  const [ssid, setSsid] = React.useState('')
  const [password, setPassword] = React.useState('')

  const handleSave = async () => {
    const trimmedSsid = ssid.trim()
    if (!trimmedSsid) return
    await send(`wifi.${trimmedSsid}.${password}`)
  }

  if (!config) return null
  return (
    <View className='gap-4'>
      <View className='gap-1.5'>
        <Typography className='font-medium'>Wi-Fi Name (SSID)</Typography>
        <Input
          placeholder='Enter Wi-Fi SSID'
          value={ssid}
          onChangeText={setSsid}
          autoCapitalize='none'
          autoCorrect={false}
        />
      </View>

      <View className='gap-1.5'>
        <Typography className='font-medium'>Password</Typography>
        <Input
          placeholder='Enter Wi-Fi password'
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          autoCapitalize='none'
          autoCorrect={false}
        />
      </View>

      <Button disabled={!ssid.trim()} onPress={handleSave}>
        Save Changes
      </Button>
    </View>
  )
}
