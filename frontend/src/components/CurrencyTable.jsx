import { useState } from 'react'
import BiasLabel from './BiasLabel'
import PercentileGauge from './PercentileGauge'
import { fmt2, fmtPct, scoreColor, scoreBg } from '../utils/formatters'

const COLS = [
  { key: 'currency', label: 'Valuutta', sortable: true },
  { key: 'net_percent_lf', label: 'Net % LF', sortable: true, fmt: fmtPct },
  { key: 'delta_1w', label: '1vk muutos', sortable: true, fmt: fmtPct },
  { key: 'delta_4w', label: '4vk muutos', sortable: true, fmt: fmtPct },
  { key: 'oi_lf_ratio_delta_4w', label: 'OI muutos', sortable: true, fmt: (v) => v == null ? '–' : `${(v * 100).toFixed(2)} %` },
  { key: 'currency_score', label: 'Score', sortable: true, fmt: fmt2 },
  { key: 'percentile_52w', label: 'Percentile', sortable: true },
  { key: 'bias_label', label: 'Bias', sortable: false },
  { key: 'commentary', label: 'Kommentaari', sortable: false },
]

export default function CurrencyTable({ data }) {
  const [sortKey, setSortKey] = useState('currency_score')
  const [sortDir, setSortDir] = useState('desc')

  const handleSort = (key) => {
    if (key === sortKey) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortKey(key); setSortDir('desc') }
  }

  const sorted = [...(data || [])].sort((a, b) => {
    const av = a[sortKey], bv = b[sortKey]
    if (av == null && bv == null) return 0
    if (av == null) return 1
    if (bv == null) return -1
    const cmp = typeof av === 'string' ? av.localeCompare(bv) : av - bv
    return sortDir === 'asc' ? cmp : -cmp
  })

  if (!data || data.length === 0) {
    return <EmptyState msg="Ei valuuttadataa saatavilla. Tuo ensin COT-historia." />
  }

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={tableStyle}>
        <thead>
          <tr>
            {COLS.map(c => (
              <th
                key={c.key}
                onClick={c.sortable ? () => handleSort(c.key) : undefined}
                style={{ ...thStyle, cursor: c.sortable ? 'pointer' : 'default' }}
              >
                {c.label}
                {c.sortable && sortKey === c.key && (
                  <span style={{ marginLeft: 4, opacity: 0.7 }}>{sortDir === 'asc' ? '↑' : '↓'}</span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map(row => (
            <tr key={row.currency} style={{ background: scoreBg(row.currency_score) }}>
              <td style={{ ...tdStyle, fontWeight: 700, color: scoreColor(row.currency_score) }}>
                {row.currency}
              </td>
              <td style={tdStyle}>{fmtPct(row.net_percent_lf)}</td>
              <td style={{ ...tdStyle, color: row.delta_1w > 0 ? '#4ade80' : row.delta_1w < 0 ? '#f87171' : '#94a3b8' }}>
                {fmtPct(row.delta_1w)}
              </td>
              <td style={{ ...tdStyle, color: row.delta_4w > 0 ? '#4ade80' : row.delta_4w < 0 ? '#f87171' : '#94a3b8' }}>
                {fmtPct(row.delta_4w)}
              </td>
              <td style={tdStyle}>{row.oi_lf_ratio_delta_4w != null ? `${(row.oi_lf_ratio_delta_4w * 100).toFixed(2)} %` : '–'}</td>
              <td style={{ ...tdStyle, color: scoreColor(row.currency_score), fontWeight: 600 }}>
                {fmt2(row.currency_score)}
              </td>
              <td style={tdStyle}>
                <PercentileGauge value={row.percentile_52w} />
              </td>
              <td style={tdStyle}>
                <BiasLabel label={row.bias_label} />
              </td>
              <td style={{ ...tdStyle, maxWidth: '320px', fontSize: '0.78rem', color: '#94a3b8' }}>
                {row.commentary || '–'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function EmptyState({ msg }) {
  return (
    <div style={{ textAlign: 'center', padding: '48px', color: '#475569' }}>
      <div style={{ fontSize: '2rem', marginBottom: '12px' }}>📊</div>
      <div>{msg}</div>
    </div>
  )
}

const tableStyle = {
  width: '100%',
  borderCollapse: 'collapse',
  fontSize: '0.85rem',
}
const thStyle = {
  padding: '10px 12px',
  textAlign: 'left',
  color: '#64748b',
  fontWeight: 600,
  borderBottom: '1px solid #1e293b',
  whiteSpace: 'nowrap',
  fontSize: '0.78rem',
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
}
const tdStyle = {
  padding: '10px 12px',
  borderBottom: '1px solid #0f172a',
  color: '#cbd5e1',
  verticalAlign: 'middle',
}
