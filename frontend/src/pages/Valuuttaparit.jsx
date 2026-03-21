import { useEffect, useState } from 'react'
import { getPairRanking, getHeatmapData, getAvailableDates } from '../api/client'
import PairHeatmap from '../components/PairHeatmap'
import BiasLabel from '../components/BiasLabel'
import PercentileGauge from '../components/PercentileGauge'
import { fmt2, scoreColor, scoreBg } from '../utils/formatters'

export default function Valuuttaparit() {
  const [pairs, setPairs] = useState([])
  const [heatmap, setHeatmap] = useState([])
  const [dates, setDates] = useState([])
  const [selectedDate, setSelectedDate] = useState(null)
  const [minScore, setMinScore] = useState(0)
  const [tab, setTab] = useState('heatmap')
  const [loading, setLoading] = useState(true)
  const [sortKey, setSortKey] = useState('pair_score')
  const [sortDir, setSortDir] = useState('desc')

  useEffect(() => {
    getAvailableDates()
      .then(r => { setDates(r.data); if (r.data.length > 0) setSelectedDate(r.data[0]) })
      .catch(() => {})
  }, [])

  useEffect(() => {
    setLoading(true)
    Promise.all([
      getPairRanking(selectedDate, minScore),
      getHeatmapData(selectedDate),
    ])
      .then(([pr, hm]) => { setPairs(pr.data); setHeatmap(hm.data) })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [selectedDate, minScore])

  const handleSort = (k) => {
    if (k === sortKey) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortKey(k); setSortDir('desc') }
  }

  const sorted = [...pairs].sort((a, b) => {
    const av = a[sortKey], bv = b[sortKey]
    if (av == null && bv == null) return 0
    if (av == null) return 1
    if (bv == null) return -1
    const cmp = typeof av === 'string' ? av.localeCompare(bv) : av - bv
    return sortDir === 'asc' ? cmp : -cmp
  })

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
        <h1 style={h1}>Valuuttaparit</h1>
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
          {dates.length > 0 && (
            <select value={selectedDate || ''} onChange={e => setSelectedDate(e.target.value || null)} style={selectStyle}>
              {dates.map(d => <option key={d} value={d}>{d}</option>)}
            </select>
          )}
          <select value={minScore} onChange={e => setMinScore(Number(e.target.value))} style={selectStyle}>
            <option value={0}>Kaikki parit</option>
            <option value={0.5}>|Score| ≥ 0.5</option>
            <option value={1.0}>|Score| ≥ 1.0</option>
            <option value={1.5}>|Score| ≥ 1.5</option>
          </select>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '4px', marginBottom: '20px' }}>
        {[{ id: 'heatmap', label: 'Heatmap' }, { id: 'table', label: 'Taulukko' }].map(t => (
          <button key={t.id} onClick={() => setTab(t.id)} style={tabStyle(tab === t.id)}>
            {t.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '64px', color: '#64748b' }}>Ladataan...</div>
      ) : (
        <div style={{ background: '#0f172a', borderRadius: '12px', border: '1px solid #1e293b', padding: '20px' }}>
          {tab === 'heatmap' ? (
            <PairHeatmap data={heatmap} minScore={minScore} />
          ) : (
            <PairTable data={sorted} onSort={handleSort} sortKey={sortKey} sortDir={sortDir} />
          )}
        </div>
      )}
    </div>
  )
}

function PairTable({ data, onSort, sortKey, sortDir }) {
  const cols = [
    { key: 'pair', label: 'Pari' },
    { key: 'base_score', label: 'Base Score' },
    { key: 'quote_score', label: 'Quote Score' },
    { key: 'pair_score', label: 'Pair Score' },
    { key: 'pair_percentile_52w', label: 'Percentile' },
    { key: 'bias_label', label: 'Bias' },
    { key: 'commentary', label: 'Kommentaari' },
  ]

  if (!data.length) return <div style={{ textAlign: 'center', padding: '48px', color: '#475569' }}>Ei dataa</div>

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
        <thead>
          <tr>
            {cols.map(c => (
              <th key={c.key} onClick={() => onSort(c.key)}
                style={{ padding: '10px 12px', color: '#64748b', fontWeight: 600, borderBottom: '1px solid #1e293b', cursor: 'pointer', whiteSpace: 'nowrap', fontSize: '0.78rem', textTransform: 'uppercase', letterSpacing: '0.05em', textAlign: 'left' }}>
                {c.label}{sortKey === c.key && <span style={{ marginLeft: 4, opacity: 0.7 }}>{sortDir === 'asc' ? '↑' : '↓'}</span>}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map(row => (
            <tr key={row.pair} style={{ background: scoreBg(row.pair_score) }}>
              <td style={{ ...td, fontWeight: 700, color: scoreColor(row.pair_score) }}>{row.pair}</td>
              <td style={{ ...td, color: scoreColor(row.base_score) }}>{fmt2(row.base_score)}</td>
              <td style={{ ...td, color: scoreColor(row.quote_score) }}>{fmt2(row.quote_score)}</td>
              <td style={{ ...td, color: scoreColor(row.pair_score), fontWeight: 700 }}>{fmt2(row.pair_score)}</td>
              <td style={td}><PercentileGauge value={row.pair_percentile_52w} /></td>
              <td style={td}><BiasLabel label={row.bias_label} /></td>
              <td style={{ ...td, maxWidth: '300px', fontSize: '0.78rem', color: '#94a3b8' }}>{row.commentary || '–'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

const h1 = { fontSize: '1.5rem', fontWeight: 700, color: '#f1f5f9' }
const selectStyle = { background: '#1e293b', color: '#e2e8f0', border: '1px solid #334155', padding: '6px 12px', borderRadius: '6px', fontSize: '0.85rem', cursor: 'pointer' }
const tabStyle = (active) => ({
  padding: '8px 18px', borderRadius: '6px', border: 'none', cursor: 'pointer',
  background: active ? '#3b82f6' : '#1e293b',
  color: active ? '#fff' : '#94a3b8',
  fontWeight: active ? 700 : 400, fontSize: '0.85rem',
})
const td = { padding: '10px 12px', borderBottom: '1px solid #0f172a', color: '#cbd5e1', verticalAlign: 'middle' }
