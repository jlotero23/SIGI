const API_BASE = import.meta.env.VITE_API_URL || '/api'

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, options)
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || err.message || `Error ${res.status}`)
  }
  return res.json()
}

export const api = {
  getStatus: () => request('/status'),
  getKpis: () => request('/kpis'),
  getChart: () => request('/charts/demand'),
  getForecasts: () => request('/forecasts/latest'),
  getRecommendations: () => request('/recommendations/latest'),
  getHistory: () => request('/executions/history'),
  runForecast: () => request('/agents/forecast/run', { method: 'POST' }),
  runReplenishment: () => request('/agents/replenishment/run', { method: 'POST' }),
  uploadDataset: (file) => {
    const form = new FormData()
    form.append('file', file)
    return request('/dataset/upload', { method: 'POST', body: form })
  },
}
