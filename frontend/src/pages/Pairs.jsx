import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getPairs } from '../api/client'
import { fmtDate, fmtNum, biasColor, biasBackground, convictionColor, divergenceColor, reversalColor } from '../utils/formatters'
import InfoTip from '../components/InfoTip'

const S = {
  page:   { maxWidth: 1400 },
  header: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20, flexWrap: 'wrap', gap: 12 },
  title:  { fontSize: '1.4rem', fontWeight: 700, color: '#e2e8f0', margin: 0 },
  filters:{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' },
  select: { background: '#1e293b', border: '1px solid #334155', borderRadius: 6, color: '#e2e8f0', padding: '6px 10px', fontSize: '0.82rem' },
  table:  { width: '100%', borderCollapse: 'collapse' },
  th:     { textAlign: 'left', padding: '10px 12px', fontSize: '0.72rem', fontWeight: 700, letterSpacing: '0.08em',
            textTransform: 'uppercase', color: '#64748b', borderBottom: '1px solid #1e293b' },
  td:     { padding: '9px 12px', fontSize: '0.85rem', borderBottom: '1px solid #0f172a', verticalAlign: 'middle' },
  row:    { cursor: 'pointer', transition: 'background 0.1s' },
}

function BiasChip({ label }) {
  return (
    <span style={{ fontSize: '0.72rem', fontWeight: 600, padding: '3px 9px', borderRadius: 12,
      color: biasColor(label), background: biasBackground(label), border: `1px solid ${biasColor(label)}33` }}>
      {label || 'Neutral'}
    </span>
  )
}

const CONVICTION_ORDER = { High: 3, Medium: 2, Low: 1 }
const RR_ORDER = { High: 3, Medium: 2, Low: 1 }

export default function Pairs() {
  const [data, setData]   = useState(null)
  const [loading, setLoading] = useState(true)
  const [labelFilter, setLabelFilter]       = useState('')
  const [convictionFilter, setConviction]   = useState('')
  const [divergenceOnly, setDivergenceOnly] = useState(false)
  const [selectedDate, setSelectedDate] = useState(null)
  const [sortBy, setSortBy]   = useState('score')   // score | conviction | baseRR | quoteRR
  const [sortDir, setSortDir] = useState('desc')
  const navigate = useNavigate()

  const handleSort = (col) => {
    if (sortBy === col) setSortDir(d => d === 'desc' ? 'asc' : 'desc')
    else { setSortBy(col); setSortDir('desc') }
  }

  const sortIcon = (col) => sortBy === col ? (sortDir === 'desc' ? ' ▼' : ' ▲') : ' ⇅'

  const load = async (rd) => {
    setLoading(true)
    try {
      const filters = {}
      if (convictionFilter) filters.conviction_filter = convictionFilter
      if (divergenceOnly) filters.divergence_only = true
      const res = await getPairs(rd, filters)
      setData(res.data)
    } catch {
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load(selectedDate) }, [selectedDate, convictionFilter, divergenceOnly])

  const pairs = data?.pairs || []
  const filtered = (() => {
    let arr = labelFilter
      ? pairs.filter(p => (p.pair_label || '').toLowerCase().includes(labelFilter.toLowerCase()))
      : [...pairs]
    const dir = sortDir === 'desc' ? -1 : 1
    arr.sort((a, b) => {
      if (sortBy === 'score')      return dir * ((Math.abs(a.pair_score || 0)) - (Math.abs(b.pair_score || 0))) * -1 || 0
      if (sortBy === 'conviction') return dir * ((CONVICTION_ORDER[b.conviction] || 0) - (CONVICTION_ORDER[a.conviction] || 0))
      if (sortBy === 'baseRR')     return dir * ((RR_ORDER[b.base_reversal_risk] || 0) - (RR_ORDER[a.base_reversal_risk] || 0))
      if (sortBy === 'quoteRR')    return dir * ((RR_ORDER[b.quote_reversal_risk] || 0) - (RR_ORDER[a.quote_reversal_risk] || 0))
      return 0
    })
    return arr
  })()

  return (
    <div style={S.page}>
      <div style={S.header}>
        <div>
          <h1 style={S.title}>Currency Pairs</h1>
          <div style={{ color: '#64748b', fontSize: '0.82rem', marginTop: 4 }}>
            {data?.report_date ? `Report: ${fmtDate(data.report_date)}` : ''}
            &nbsp;·&nbsp; {filtered.length} pairs
          </div>
        </div>
        <div style={S.filters}>
          <select style={S.select}
            value={selectedDate || data?.report_date || ''}
            onChange={e => setSelectedDate(e.target.value)}>
            {(data?.available_dates || []).map(d => (
              <option key={d} value={d}>{fmtDate(d)}</option>
            ))}
          </select>
          <select style={S.select} value={labelFilter} onChange={e => setLabelFilter(e.target.value)}>
            <option value="">All biases</option>
            <option value="Strong Bullish">Strong Bullish</option>
            <option value="Bullish">Bullish</option>
            <option value="Neutral">Neutral</option>
            <option value="Bearish">Bearish</option>
            <option value="Strong Bearish">Strong Bearish</option>
          </select>
          <select style={S.select} value={convictionFilter} onChange={e => setConviction(e.target.value)}>
            <option value="">All conviction</option>
            <option value="High">High</option>
            <option value="Medium">Medium</option>
            <option value="Low">Low</option>
          </select>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.82rem', color: '#94a3b8', cursor: 'pointer' }}>
            <input type="checkbox" checked={divergenceOnly} onChange={e => setDivergenceOnly(e.target.checked)} />
            Divergence only
          </label>
        </div>
      </div>

      {loading ? (
        <div style={{ color: '#64748b', padding: 40 }}>Loading...</div>
      ) : (
        <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 10, overflow: 'hidden' }}>
          <div style={{ padding: '12px 16px', borderBottom: '1px solid #1e293b', fontSize: '0.78rem', color: '#475569' }}>
            Parit on rankattu COT-signaalin vahvuuden mukaan. Klikkaa paria nähdäksesi historiallisen analyysin.
          </div>
          <table style={S.table}>
            <thead>
              <tr>
                <th style={S.th}>Pair</th>
                <th style={S.th}>Bias</th>
                <th style={{ ...S.th, cursor: 'pointer', userSelect: 'none' }} onClick={() => handleSort('score')}>
                  Score{sortIcon('score')}
                  <InfoTip text="Pair Score −4…+4: base-valuutan COT Score miinus quote-valuutan score. Korkea positiivinen arvo = base vahva suhteessa quoteen." />
                </th>
                <th style={{ ...S.th, cursor: 'pointer', userSelect: 'none' }} onClick={() => handleSort('conviction')}>
                  Conviction{sortIcon('conviction')}
                  <InfoTip text="Signaalin luotettavuus. High = vahva score eikä kääntymisriskiä. Matala = heikko signaali tai jommalla kummalla valuutalla on High Reversal Risk." />
                </th>
                <th style={{ ...S.th, cursor: 'pointer', userSelect: 'none' }} onClick={() => handleSort('baseRR')}>
                  Base Rev. Risk{sortIcon('baseRR')}
                  <InfoTip text="Base-valuutan (esim. EUR EURUSD:ssa) kääntymisriski. High = äärimmäinen positioning + kaupalliset hedgaajat vastapuolella." />
                </th>
                <th style={{ ...S.th, cursor: 'pointer', userSelect: 'none' }} onClick={() => handleSort('quoteRR')}>
                  Quote Rev. Risk{sortIcon('quoteRR')}
                  <InfoTip text="Quote-valuutan (esim. USD EURUSD:ssa) kääntymisriski. High = äärimmäinen positioning + kaupalliset hedgaajat vastapuolella." />
                </th>
                <th style={S.th}>
                  Divergence
                  <InfoTip text="Bullish-divergenssi: hinta laskee mutta COT-positiointi nousee → mahdollinen pohja. Bearish: hinta nousee, positiointi laskee → mahdollinen huippu." />
                </th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(p => (
                <tr key={p.pair} style={S.row}
                  onClick={() => navigate(`/pair/${p.pair}`)}
                  onMouseEnter={e => e.currentTarget.style.background = '#1e293b'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                  <td style={{ ...S.td, fontWeight: 700, color: '#e2e8f0' }}>{p.pair}</td>
                  <td style={S.td}><BiasChip label={p.pair_label} /></td>
                  <td style={{ ...S.td, color: biasColor(p.pair_label), fontWeight: 600 }}>
                    {fmtNum(p.pair_score)}
                  </td>
                  <td style={{ ...S.td, color: convictionColor(p.conviction), fontWeight: 600 }}>
                    {p.conviction || '—'}
                  </td>
                  <td style={{ ...S.td, color: reversalColor(p.base_reversal_risk), fontSize: '0.78rem' }}>
                    {p.base_reversal_risk || 'Low'}
                  </td>
                  <td style={{ ...S.td, color: reversalColor(p.quote_reversal_risk), fontSize: '0.78rem' }}>
                    {p.quote_reversal_risk || 'Low'}
                  </td>
                  <td style={{ ...S.td }}>
                    {p.divergence_type ? (
                      <span style={{ color: divergenceColor(p.divergence_type), fontSize: '0.78rem', fontWeight: 600 }}>
                        ⚡ {p.divergence_type}
                      </span>
                    ) : (
                      <span style={{ color: '#334155', fontSize: '0.78rem' }}>—</span>
                    )}
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={7} style={{ ...S.td, color: '#64748b', textAlign: 'center', padding: 32 }}>
                    No pairs match the current filters
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
