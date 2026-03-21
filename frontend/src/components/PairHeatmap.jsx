import { heatmapColor, fmt2 } from '../utils/formatters'

// Forex-standardin mukainen hierarkia
const CURRENCIES = ['EUR', 'GBP', 'AUD', 'NZD', 'USD', 'CAD', 'CHF', 'JPY']

export default function PairHeatmap({ data, minScore = 0 }) {
  if (!data || data.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '48px', color: '#475569' }}>
        <div style={{ fontSize: '2rem', marginBottom: '12px' }}>📊</div>
        <div>Ei heatmap-dataa saatavilla.</div>
      </div>
    )
  }

  // Indeksoidaan data pair → score
  const scoreMap = {}
  data.forEach(d => { scoreMap[d.pair] = d.pair_score })

  const cell = 56

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ borderCollapse: 'separate', borderSpacing: '3px', fontSize: '0.72rem' }}>
        <thead>
          <tr>
            <th style={headerCellStyle}>Base →</th>
            {CURRENCIES.map(c => (
              <th key={c} style={headerCellStyle}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {CURRENCIES.map(base => (
            <tr key={base}>
              <td style={headerCellStyle}>{base}</td>
              {CURRENCIES.map(quote => {
                if (base === quote) {
                  return <td key={quote} style={{ ...dataCellStyle(cell), background: '#0f172a', color: '#334155' }}>—</td>
                }
                const pair = `${base}${quote}`
                const score = scoreMap[pair]
                const dimmed = minScore > 0 && (score == null || Math.abs(score) < minScore)
                const bg = heatmapColor(score)
                const textColor = score == null ? '#475569' : Math.abs(score) > 0.5 ? '#f1f5f9' : '#94a3b8'
                return (
                  <td
                    key={quote}
                    style={{
                      ...dataCellStyle(cell),
                      background: bg,
                      color: textColor,
                      opacity: dimmed ? 0.15 : 1,
                      transition: 'opacity 0.2s ease',
                    }}
                    title={`${pair}: ${score != null ? fmt2(score) : 'N/A'}`}
                  >
                    {score != null ? fmt2(score) : '–'}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ marginTop: '12px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.75rem', color: '#64748b' }}>
        <span>Vahva laskeva</span>
        {[-2.5, -1.5, -0.5, 0, 0.5, 1.5, 2.5].map(v => (
          <div key={v} style={{ width: '24px', height: '14px', background: heatmapColor(v), borderRadius: '2px' }} />
        ))}
        <span>Vahva nouseva</span>
        <span style={{ marginLeft: '16px' }}>Solu: base/quote pair score</span>
      </div>
    </div>
  )
}

const headerCellStyle = {
  padding: '6px 8px',
  background: '#0f172a',
  color: '#64748b',
  fontWeight: 700,
  textAlign: 'center',
  fontSize: '0.75rem',
}

const dataCellStyle = (size) => ({
  width: `${size}px`,
  height: `${size}px`,
  textAlign: 'center',
  fontWeight: 600,
  borderRadius: '4px',
  cursor: 'default',
})
