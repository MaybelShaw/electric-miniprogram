import { BASE_URL } from './request'

const API_ORIGIN = BASE_URL.replace(/\/api\/?$/, '').replace(/\/$/, '')
const ALLOW_REMOTE_MEDIA = process.env.TARO_APP_ALLOW_REMOTE_MEDIA === 'true'

function getHttpHost(value: string) {
  return value.replace(/^https?:\/\//i, '').split(/[/:?#]/)[0].toLowerCase()
}

function getHttpOrigin(value: string) {
  const match = value.match(/^https?:\/\/[^/?#]+/i)
  return match ? match[0].replace(/\/$/, '').toLowerCase() : ''
}

function isPrivateHost(host: string) {
  return (
    host === 'localhost' ||
    host === '127.0.0.1' ||
    host === '0.0.0.0' ||
    host === '::1' ||
    host === 'tmp' ||
    /^10\./.test(host) ||
    /^192\.168\./.test(host) ||
    /^172\.(1[6-9]|2\d|3[0-1])\./.test(host)
  )
}

export function resolveLocalMediaUrl(url?: string | null) {
  const value = typeof url === 'string' ? url.trim() : ''
  if (!value) return ''

  if (
    value.startsWith('data:image/') ||
    value.startsWith('wxfile://') ||
    value.startsWith('file://') ||
    value.startsWith('blob:') ||
    value.startsWith('http://tmp/') ||
    value.startsWith('https://tmp/')
  ) {
    return value
  }

  if (value.startsWith('cloud://')) return ''

  if (value.startsWith('//')) {
    return ALLOW_REMOTE_MEDIA ? `https:${value}` : ''
  }

  if (/^https?:\/\//i.test(value)) {
    const host = getHttpHost(value)
    const origin = getHttpOrigin(value)
    const apiOrigin = API_ORIGIN.toLowerCase()
    if (isPrivateHost(host) || (!!apiOrigin && origin === apiOrigin)) {
      return value
    }
    return ALLOW_REMOTE_MEDIA ? value : ''
  }

  if (value.startsWith('/assets/') || value.startsWith('/tmp/')) {
    return value
  }

  if (value.startsWith('/')) {
    return `${API_ORIGIN}${value}`
  }

  return `${API_ORIGIN}/${value}`
}
