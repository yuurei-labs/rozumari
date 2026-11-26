import { useFocusEffect } from 'expo-router'
import { useCallback } from 'react'
import { KeyboardAvoidingView, Platform, ScrollView } from 'react-native'

import { BLEProvider, useBLE } from '@/components/profile/config/_context'
import { BLEConnection } from '@/components/profile/config/connection'
import { BLEGeneralConfig } from '@/components/profile/config/general'
import { BLETimeoutConfig } from '@/components/profile/config/timeout'
import { BLEWifiConfig } from '@/components/profile/config/wifi'

function ConfigContent() {
  const { status, config, disconnect } = useBLE()

  useFocusEffect(
    useCallback(
      () => () => status === 'connected' && disconnect(),
      [status, disconnect]
    )
  )

  const configKey = config ? JSON.stringify(config) : 'default'

  return (
    <KeyboardAvoidingView
      className='flex-1'
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
    >
      <ScrollView
        className='flex-1 p-4'
        contentContainerClassName='grow flex-col gap-6 pb-6'
        keyboardShouldPersistTaps='handled'
      >
        <BLEConnection />

        <BLEGeneralConfig key={`${configKey}-general`} />

        <BLETimeoutConfig key={`${configKey}-timeout`} />

        <BLEWifiConfig key={`${configKey}-wifi`} />
      </ScrollView>
    </KeyboardAvoidingView>
  )
}

export default function ProfileConfigScreen() {
  return (
    <BLEProvider>
      <ConfigContent />
    </BLEProvider>
  )
}
