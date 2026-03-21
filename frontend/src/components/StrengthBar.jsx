/**
 * Visuaalinen palkki strength_index-arvolle (-50…+50).
 * Positiivinen → vihreä oikealle, negatiivinen → punainen vasemmalle.
 */
export default function StrengthBar({ value, threshold = 25 }) {
  if (value == null) return <span style={{ color: '#4A5568' }}>–</span>

  const maxAbs = 50
  const pct = Math.min(Math.abs(value) / maxAbs, 1) * 50 // 0–50% leveydestä
  const isPositive = value >= 0

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: '160px' }}>
      {/* Numeerinen arvo */}
      <span style={{
        minWidth: '42px',
        textAlign: 'right',
        fontWeight: 700,
        fontSize: '0.85rem',
        color: isPositive ? '#00C87A' : '#FF4D6A',
      }}>
        {value > 0 ? '+' : ''}{value.toFixed(1)}
      </span>

      {/* Palkki */}
      <div style={{
        flex: 1,
        height: '14px',
        background: '#1a1f2e',
        borderRadius: '3px',
        position: 'relative',
        overflow: 'hidden',
      }}>
        {/* Keskiviiva */}
        <div style={{
          position: 'absolute',
          left: '50%',
          top: 0,
          bottom: 0,
          width: '1px',
          background: '#334155',
          zIndex: 2,
        }} />

        {/* Kynnysviivat */}
        <div style={{
          position: 'absolute',
          left: `${50 + (threshold / maxAbs) * 50}%`,
          top: 0, bottom: 0, width: '1px',
          background: '#475569',
          zIndex: 1,
        }} />
        <div style={{
          position: 'absolute',
          left: `${50 - (threshold / maxAbs) * 50}%`,
          top: 0, bottom: 0, width: '1px',
          background: '#475569',
          zIndex: 1,
        }} />

        {/* Täyttöpalkki */}
        <div style={{
          position: 'absolute',
          top: '2px',
          bottom: '2px',
          borderRadius: '2px',
          background: isPositive ? '#007A5C' : '#A81B30',
          ...(isPositive
            ? { left: '50%', width: `${pct}%` }
            : { right: '50%', width: `${pct}%` }
          ),
          transition: 'width 0.3s ease',
        }} />
      </div>
    </div>
  )
}
