// API Configuration — uses Next.js proxy rewrites to avoid CORS/IPv6 issues
const envBaseUrl = process.env.NEXT_PUBLIC_API_URL?.trim()

// In local dev, default to direct backend calls to avoid proxy timeouts on long requests.
export const API_BASE_URL = envBaseUrl
  ? envBaseUrl.replace(/\/$/, '')
  : process.env.NODE_ENV === 'development'
  ? 'http://127.0.0.1:5000'
  : ''

export const API_ENDPOINTS = {
  EVALUATE_UPLOAD: `${API_BASE_URL}/api/evaluate/upload`,
  EVALUATE_STREAM: `${API_BASE_URL}/api/evaluate/stream`,
  EVALUATE_TEXT: `${API_BASE_URL}/api/evaluate/text`,
  REPORTS: `${API_BASE_URL}/api/reports`,
  HEALTH: `${API_BASE_URL}/api/health`,
  ANALYTICS_OVERVIEW: `${API_BASE_URL}/api/analytics/overview`,
} as const
