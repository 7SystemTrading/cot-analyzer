export default function PercentileGauge({ value }) {
  if (value == null) return <span style={{ color: '#94a3b8' }}>–</span>

  const pct = Math.round(value)
  const color =
    pct >= 90 ? '#22c55e' :
    pct >= 75 ? '#4ade80' :
    pct >= 25 ? '#94a3b8' :
    pct >= 10 ? '#fca5a5' :
    '#ef4444'

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: '120px' }}>
      <div style={{
        flex: 1,
        height: '6px',
        borderRadius: '3px',
        background: '#1e293b',
        overflow: 'hidden',
      }}>
        <div style={{
          width: `${pct}%`,
          height: '100%',
          background: color,
          borderRadius: '3px',
          transition: 'width 0.3s ease',
        }} />
      </div>
      <span style={{ color, fontSize: '0.8rem', fontWeight: 600, minWidth: '32px' }}>
        {pct}
      </span>
    </div>
  )
}
