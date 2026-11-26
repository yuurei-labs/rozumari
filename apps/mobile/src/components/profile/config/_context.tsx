import type {
  Device,
  Subscription,
  BleManager as TBleManager,
} from 'react-native-ble-plx'

import { toast } from '@rozumari/ui/components/toast'
import * as Base64 from 'effect/encoding/Base64'
import * as React from 'react'
import { State } from 'react-native-ble-plx'

import { BLE_RX_UUID, BLE_SERVICE_UUID, BLE_TX_UUID } from '@/lib/constants'

const globalForBle = globalThis as unknown as {
  __bleManager?: TBleManager | null
}

function getBleManager(): TBleManager | null {
  if (!globalForBle.__bleManager) {
    try {
      // oxlint-disable-next-line node/global-require unicorn/prefer-module
      const { BleManager: _BleManager } = require('react-native-ble-plx') as {
        BleManager: typeof TBleManager
      }
      globalForBle.__bleManager = new _BleManager()
    } catch {
      globalForBle.__bleManager = null
    }
  }
  return globalForBle.__bleManager ?? null
}

interface BLEContextValue {
  status: 'idle' | 'scanning' | 'connecting' | 'connected'
  devices: Device[]
  device: string | null
  setDevice: React.Dispatch<React.SetStateAction<string | null>>
  startScan: () => Promise<void>
  stopScan: () => Promise<void>
  connect: () => Promise<Device | null>
  disconnect: () => Promise<void>
  send: (payload: string | Record<string, unknown>) => Promise<boolean>

  config: Config | null
}

interface Config {
  general: { syncTime: '04:00:00'; timezone: 7; language: 'vi' }
  timeout: { drop: 5; close: 10; open: 10 }
}

interface BLENotifyPayload {
  type: 'success' | 'error'
  content: string
}

const BLEContext = React.createContext<BLEContextValue | null>(null)

const useBLE = () => {
  const ctx = React.use(BLEContext)
  if (!ctx) throw new Error('useBLE must be used within a BLEProvider')
  return ctx
}

function BLEProvider({ children }: Readonly<{ children: React.ReactNode }>) {
  const [status, setStatus] = React.useState<BLEContextValue['status']>('idle')
  const [devices, setDevices] = React.useState<Device[]>([])
  const [device, setDevice] = React.useState<string | null>(null)
  const [config, setConfig] = React.useState<Config | null>(null)

  const scanTimeoutRef = React.useRef<ReturnType<typeof setTimeout> | null>(
    null
  )
  const disconnectSubRef = React.useRef<Subscription | null>(null)
  const txMonitorSubRef = React.useRef<Subscription | null>(null)

  const stopScan = React.useCallback(async () => {
    const ble = getBleManager()
    if (!ble) return

    if (scanTimeoutRef.current) {
      clearTimeout(scanTimeoutRef.current)
      scanTimeoutRef.current = null
    }

    await ble.stopDeviceScan()
    setStatus((current) => (current === 'scanning' ? 'idle' : current))
  }, [])

  const startScan = React.useCallback(async () => {
    const ble = getBleManager()
    if (!ble || status === 'connected' || status === 'connecting') return

    setDevices([])
    setStatus('scanning')

    const state = await ble.state()
    if (state !== State.PoweredOn) return setStatus('idle')

    await ble.startDeviceScan(
      null,
      { allowDuplicates: false, scanMode: 2 },
      (error, dev) => {
        if (error) return setStatus('idle')
        if (!dev) return

        setDevices((curr) => {
          if (curr.some(({ id }) => id === dev.id)) return curr
          return [...curr, dev]
        })
      }
    )

    scanTimeoutRef.current = setTimeout(() => {
      void stopScan()
    }, 5000)
  }, [status, stopScan])

  const connect = React.useCallback(async () => {
    const ble = getBleManager()
    if (!ble || ['connecting', 'connected'].includes(status) || !device)
      return null

    if (status === 'scanning') await stopScan()
    setStatus('connecting')

    try {
      const dev = await ble.connectToDevice(device, {
        requestMTU: 256,
        timeout: 10_000,
      })

      const readyDev = await dev.discoverAllServicesAndCharacteristics()

      const services = await readyDev.services()
      const hasTargetService = services.some(
        (s) => s.uuid.toLowerCase() === BLE_SERVICE_UUID.toLowerCase()
      )
      if (!hasTargetService) {
        await ble.cancelDeviceConnection(device)
        setStatus('idle')
        return null
      }

      txMonitorSubRef.current?.remove()
      txMonitorSubRef.current = readyDev.monitorCharacteristicForService(
        BLE_SERVICE_UUID,
        BLE_TX_UUID,
        // oxlint-disable-next-line promise/prefer-await-to-callbacks
        (error, characteristic) => {
          if (error || !characteristic?.value) return

          const decoded = Base64.decode(characteristic.value)
          if (decoded._tag === 'Failure') return

          const _raw = String.fromCodePoint(...decoded.success)
          try {
            const data = JSON.parse(_raw) as Config | BLENotifyPayload
            if ('general' in data && 'timeout' in data) setConfig(data)
            if ('type' in data && 'content' in data)
              toast[data.type](data.content)
          } catch {
            toast.show(_raw)
          }
        }
      )

      disconnectSubRef.current?.remove()
      disconnectSubRef.current = ble.onDeviceDisconnected(
        device,
        (_error, _disconnectedDevice) => {
          txMonitorSubRef.current?.remove()
          txMonitorSubRef.current = null
          disconnectSubRef.current?.remove()
          disconnectSubRef.current = null
          setStatus('idle')
        }
      )

      setStatus('connected')
      return readyDev
    } catch {
      setStatus('idle')
      return null
    }
  }, [stopScan, status, device])

  const send = React.useCallback(
    async (payload: string | Record<string, unknown>): Promise<boolean> => {
      const ble = getBleManager()
      if (!ble || status !== 'connected' || !device) return false

      try {
        const raw =
          typeof payload === 'string' ? payload : JSON.stringify(payload)
        const base64Data = Base64.encode(raw)

        await ble.writeCharacteristicWithResponseForDevice(
          device,
          BLE_SERVICE_UUID,
          BLE_RX_UUID,
          base64Data
        )
        return true
      } catch {
        return false
      }
    },
    [status, device]
  )

  const disconnect = React.useCallback(async () => {
    const ble = getBleManager()
    if (!ble || status !== 'connected' || !device) return

    try {
      txMonitorSubRef.current?.remove()
      txMonitorSubRef.current = null
      disconnectSubRef.current?.remove()
      disconnectSubRef.current = null

      const isConnected = await ble.isDeviceConnected(device)
      if (isConnected) await ble.cancelDeviceConnection(device)
      setConfig(null)
    } catch {
      // noop
    } finally {
      setStatus('idle')
    }
  }, [status, device])

  React.useEffect(
    () => () => {
      txMonitorSubRef.current?.remove()
      disconnectSubRef.current?.remove()
    },
    []
  )

  const memoizedValue = React.useMemo(
    () => ({
      status,
      devices,

      device,
      setDevice,

      startScan,
      stopScan,

      connect,
      disconnect,
      send,

      config,
    }),
    [
      status,
      devices,
      device,
      startScan,
      stopScan,
      connect,
      disconnect,
      send,
      config,
    ]
  )

  return <BLEContext value={memoizedValue}>{children}</BLEContext>
}

export { BLEProvider, useBLE }
