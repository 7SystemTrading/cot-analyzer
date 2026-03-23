/**
 * Minikynttilä-kuvaaja – näyttää 5 päivän OHLC-kynttilät pienessä tilassa.
 */
export default function MiniCandleChart({ candles, width = 180, height = 50 }) {
  if (!candles || candles.length === 0) {
    return <div style={{ width, height, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#475569', fontSize: '0.7rem' }}>–</div>
  }

  // Laske skaala
  const allHighs = candles.map(c => c.high)
  const allLows = candles.map(c => c.low)
  const yMin = Math.min(...allLows)
  const yMax = Math.max(...allHighs)
  const yRange = yMax - yMin || 1

  const pad = 6
  const candleWidth = Math.min(14, (width - pad * 2) / candles.length - 4)
  const totalW = candles.length * (candleWidth + 4) + pad * 2

  const scaleY = (v) => pad + (1 - (v - yMin) / yRange) * (height - pad * 2)

  return (
    <svg width={Math.min(width, totalW)} height={height} style={{ display: 'block' }}>
      {candles.map((c, i) => {
        const x = pad + i * (candleWidth + 4) + candleWidth / 2
        const isUp = c.close >= c.open
        const bodyTop = scaleY(Math.max(c.open, c.close))
        const bodyBot = scaleY(Math.min(c.open, c.close))
        const bodyH = Math.max(1, bodyBot - bodyTop)
        const color = isUp ? '#22c55e' : '#ef4444'

        return (
          <g key={i}>
            {/* Wick */}
            <line
              x1={x} y1={scaleY(c.high)}
              x2={x} y2={scaleY(c.low)}
              stroke={color} strokeWidth={1}
            />
            {/* Body */}
            <rect
              x={x - candleWidth / 2} y={bodyTop}
              width={candleWidth} height={bodyH}
              fill={color} rx={1}
            />
          </g>
        )
      })}
    </svg>
  )
}
