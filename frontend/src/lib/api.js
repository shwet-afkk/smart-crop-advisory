// api.js — Thin fetch wrapper for the FastAPI backend.
// In dev, Vite proxies /api/* to http://localhost:8000 (see vite.config.js).
// In production, VITE_API_BASE_URL can point to your deployed backend URL.

const API_ROOT = import.meta.env.VITE_API_BASE_URL 
  ? `${import.meta.env.VITE_API_BASE_URL.replace(/\/+$/, '')}/api`
  : '/api'

export async function analyzeCrop({ file, lat, lon, locationName, language }) {
  const form = new FormData()
  form.append('image', file)
  if (lat != null) form.append('lat', lat)
  if (lon != null) form.append('lon', lon)
  if (locationName) form.append('location_name', locationName)
  form.append('language', language || 'kn')

  const res = await fetch(`${API_ROOT}/analyze-crop`, { method: 'POST', body: form })
  if (!res.ok) {
    const detail = await safeDetail(res)
    throw new Error(detail || `Analyze request failed (${res.status})`)
  }
  return res.json()
}

export async function fetchWeatherContext({ lat, lon, locationName } = {}) {
  const params = new URLSearchParams()
  if (lat != null) params.set('lat', lat)
  if (lon != null) params.set('lon', lon)
  if (locationName) params.set('location_name', locationName)

  const res = await fetch(`${API_ROOT}/weather-context?${params.toString()}`)
  if (!res.ok) throw new Error(`Weather request failed (${res.status})`)
  return res.json()
}

export async function voiceQuery({ transcript, sourceLanguage, targetLanguage, contextDisease }) {
  const res = await fetch(`${API_ROOT}/voice-query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      transcript,
      source_language: sourceLanguage,
      target_language: targetLanguage,
      context_disease: contextDisease || null,
    }),
  })
  if (!res.ok) throw new Error(`Voice query failed (${res.status})`)
  return res.json()
}

export async function checkHealth() {
  const res = await fetch(`${API_ROOT}/health`)
  if (!res.ok) throw new Error('Backend unreachable')
  return res.json()
}

async function safeDetail(res) {
  try {
    const data = await res.json()
    return data.detail
  } catch {
    return null
  }
}
