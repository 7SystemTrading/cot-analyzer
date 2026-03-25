export const fmtDate = (d) => {
  if (!d) return '—'
  const dt = new Date(d)
  return dt.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
}

export const fmtPct = (v) => {
  if (v == null) return '—'
  return `${(Number(v) * 100).toFixed(1)}%`
}

export const fmtNum = (v, decimals = 2) => {
  if (v == null) return '—'
  return Number(v).toFixed(decimals)
}

export const fmtK = (v) => {
  if (v == null) return '—'
  const n = Number(v)
  if (Math.abs(n) >= 1000) return `${(n / 1000).toFixed(1)}K`
  return n.toFixed(0)
}

export const biasColor = (label) => {
  if (!label) return '#64748b'
  const l = label.toLowerCase()
  if (l.includes('strong bullish')) return '#22c55e'
  if (l.includes('bullish'))        return '#86efac'
  if (l.includes('strong bearish')) return '#ef4444'
  if (l.includes('bearish'))        return '#fca5a5'
  return '#64748b'
}

export const biasBackground = (label) => {
  if (!label) return 'transparent'
  const l = label.toLowerCase()
  if (l.includes('strong bullish')) return 'rgba(34,197,94,0.12)'
  if (l.includes('bullish'))        return 'rgba(134,239,172,0.10)'
  if (l.includes('strong bearish')) return 'rgba(239,68,68,0.12)'
  if (l.includes('bearish'))        return 'rgba(252,165,165,0.10)'
  return 'transparent'
}

export const reversalColor = (risk) => {
  if (risk === 'High')   return '#ef4444'
  if (risk === 'Medium') return '#f97316'
  return '#22c55e'
}

export const convictionColor = (c) => {
  if (c === 'High')   return '#22c55e'
  if (c === 'Medium') return '#f59e0b'
  return '#64748b'
}

export const divergenceColor = (type) => {
  if (type === 'Bullish') return '#22c55e'
  if (type === 'Bearish') return '#ef4444'
  return '#64748b'
}
