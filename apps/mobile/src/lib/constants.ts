export const REFRESH_TOKEN_KEY = 'auth.refreshToken'
export const ACCESS_TOKEN_KEY = 'auth.accessToken'

export const THEME_KEY = 'config.theme'
export const LANGUAGE_KEY = 'config.language'

export const BLE_SERVICE_UUID = '20D2C743-9DFC-4FC8-B58F-14686A0A66A5'
export const BLE_RX_UUID = '28363331-A0EA-4954-9E39-3CA259D85EFF'
export const BLE_TX_UUID = '21F3B000-609B-498B-9079-86AE7AE31A28'

export const SUPPORTED_PROVIDERS = [
  { id: 'facebook', name: 'Facebook' },
  { id: 'github', name: 'Github' },
  { id: 'google', name: 'Google' },
  { id: 'twitter', name: 'Twitter' },
] as const
