// Numeerinen muotoilu
export const fmt2 = (v) => (v == null ? '–' : Number(v).toFixed(2))
export const fmt1 = (v) => (v == null ? '–' : Number(v).toFixed(1))
export const fmtPct = (v) => (v == null ? '–' : `${(Number(v) * 100).toFixed(1)} %`)
export const fmtPctile = (v) => (v == null ? '–' : `${Math.round(v)}.`)

// Värit scoren perusteella (CSS-string)
export const scoreColor = (score) => {
  if (score == null) return '#94a3b8'
  if (score >= 1.5) return '#22c55e'
  if (score >= 0.75) return '#4ade80'
  if (score >= 0.25) return '#86efac'
  if (score >= -0.25) return '#94a3b8'
  if (score >= -0.75) return '#fca5a5'
  if (score >= -1.5) return '#f87171'
  return '#ef4444'
}

// Taustaväri (pehmeämpi) taulukkosoluille
export const scoreBg = (score) => {
  if (score == null) return 'transparent'
  if (score >= 1.5) return 'rgba(34,197,94,0.15)'
  if (score >= 0.5) return 'rgba(34,197,94,0.08)'
  if (score >= -0.5) return 'transparent'
  if (score >= -1.5) return 'rgba(239,68,68,0.08)'
  return 'rgba(239,68,68,0.15)'
}

// Heatmap-interpolointi: punainen (-3) → harmaa (0) → vihreä (+3)
export const heatmapColor = (score, maxAbs = 2.5) => {
  if (score == null) return '#1e293b'
  const clamped = Math.max(-maxAbs, Math.min(maxAbs, score))
  const ratio = clamped / maxAbs // -1..+1
  if (ratio > 0) {
    const g = Math.round(34 + (197 - 34) * ratio)
    const r = Math.round(34 + (34 - 34) * ratio)
    return `rgba(34,${g},94,${0.2 + ratio * 0.65})`
  } else {
    const abs = Math.abs(ratio)
    return `rgba(239,68,68,${0.15 + abs * 0.65})`
  }
}

// Bias-labelin väri
export const biasColor = (label) => {
  if (!label) return '#94a3b8'
  const l = label.toLowerCase()
  if (l.includes('poikkeuksellinen nou')) return '#22c55e'
  if (l.includes('vahva nou')) return '#4ade80'
  if (l.includes('lievästi nou')) return '#86efac'
  if (l.includes('neutraali')) return '#94a3b8'
  if (l.includes('lievästi las')) return '#fca5a5'
  if (l.includes('vahva las')) return '#f87171'
  if (l.includes('poikkeuksellinen las')) return '#ef4444'
  return '#94a3b8'
}

// Päivämäärän muotoilu
export const fmtDate = (d) => {
  if (!d) return '–'
  return new Date(d).toLocaleDateString('fi-FI', { day: '2-digit', month: '2-digit', year: 'numeric' })
}
