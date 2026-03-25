import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, ComposedChart } from 'recharts'
import { getPairDetail } from '../api/client'
import { fmtDate, fmtNum, fmtK, biasColor, biasBackground, convictionColor, divergenceColor, reversalColor } from '../utils/formatters'
import InfoTip from '../components/InfoTip'

const DISPLAY_PAIRS = [
  'EURGBP','EURAUD','EURNZD','EURUSD','EURCAD','EURCHF','EURJPY',
  'GBPAUD','GBPNZD','GBPUSD','GBPCAD','GBPCHF','GBPJPY',
  'AUDNZD','AUDUSD','AUDCAD','AUDCHF','AUDJPY',
  'NZDUSD','NZDCAD','NZDCHF','NZDJPY',
  'USDCAD','USDCHF','USDJPY',
  'CADCHF','CADJPY','CHFJPY',
]

const S = {
  page:    { maxWidth: 1200 },
  header:  { display: 'flex', alignItems: 'center', gap: 14, marginBottom: 20, flexWrap: 'wrap' },
  back:    { color: '#64748b', cursor: 'pointer', fontSize: '0.85rem', textDecoration: 'underline' },
  title:   { fontSize: '1.4rem', fontWeight: 800, color: '#e2e8f0', margin: 0 },
  grid:    { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12, marginBottom: 20 },
  statBox: { background: '#0f172a', border: '1px solid #1e293b', borderRadius: 8, padding: '12px 16px' },
  label:   { fontSize: '0.72rem', color: '#64748b', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 },
  value:   { fontSize: '1.1rem', fontWeight: 700, color: '#e2e8f0' },
  card:    { background: '#0f172a', border: '1px solid #1e293b', borderRadius: 10, padding: '20px', marginBottom: 20 },
  twoCol:  { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 20 },
}

function StatBox({ label, value, color, tip }) {
  return (
    <div style={S.statBox}>
      <div style={S.label}>
        {label}
        {tip && <InfoTip text={tip} />}
      </div>
      <div style={{ ...S.value, color: color || '#e2e8f0' }}>{value}</div>
    </div>
  )
}

function CurrencyCard({ data, title }) {
  if (!data) return null
  return (
    <div style={S.card}>
      <div style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase',
        letterSpacing: '0.08em', color: '#64748b', marginBottom: 12 }}>{title}</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10 }}>
        <span style={{ fontSize: '1.3rem', fontWeight: 800, color: biasColor(data.bias_label) }}>
          {data.currency}
        </span>
        <span style={{ fontSize: '0.8rem', color: biasColor(data.bias_label) }}>{data.bias_label}</span>
        <span style={{ fontSize: '0.8rem', color: reversalColor(data.reversal_risk), marginLeft: 'auto' }}>
          {data.reversal_risk} risk
        </span>
      </div>
      {data.explanation && (
        <div style={{ color: '#94a3b8', lineHeight: 1.65, fontSize: '0.83rem' }}>{data.explanation}</div>
      )}
    </div>
  )
}

export default function PairDetail() {
  const { pair }   = useParams()
  const navigate   = useNavigate()
  const [data, setData]     = useState(null)
  const [loading, setLoading] = useState(true)
  const [selectedDate, setSelectedDate] = useState(null)

  useEffect(() => {
    if (!pair) return
    setLoading(true)
    getPairDetail(pair.toUpperCase(), selectedDate, 104)
      .then(r => { setData(r.data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [pair, selectedDate])

  if (loading) return <div style={{ color: '#64748b', padding: 40 }}>Loading...</div>
  if (!data)   return <div style={{ color: '#ef4444', padding: 40 }}>No data</div>

  const cur  = data.current
  const hist = data.history || []

  const chartData = hist.map(h => ({
    date:       h.report_date,
    score:      h.pair_score,
    baseNet:    h.base_nc_net,
    quoteNet:   h.quote_nc_net,
    spread:     h.base_nc_net != null && h.quote_nc_net != null
                  ? h.base_nc_net - h.quote_nc_net : null,
  }))

  return (
    <div style={S.page}>
      <div style={S.header}>
        <span style={S.back} onClick={() => navigate('/pairs')}>← Pairs</span>
      </div>

      {/* Pair selector */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 20 }}>
        {DISPLAY_PAIRS.map(p => (
          <button key={p} onClick={() => navigate(`/pair/${p}`)}
            style={{ padding: '3px 9px', borderRadius: 5, border: '1px solid #334155',
              background: p === pair?.toUpperCase() ? '#1e3a5f' : 'transparent',
              color: p === pair?.toUpperCase() ? '#fff' : '#64748b',
              cursor: 'pointer', fontSize: '0.75rem', fontWeight: 600 }}>
            {p}
          </button>
        ))}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20, flexWrap: 'wrap', gap: 10 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 14 }}>
          <h1 style={{ ...S.title, color: biasColor(cur?.pair_label) }}>
            {pair?.toUpperCase()}
          </h1>
          <span style={{ color: biasColor(cur?.pair_label), fontSize: '1rem' }}>{cur?.pair_label}</span>
        </div>
        <select
          style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 6, color: '#e2e8f0', padding: '6px 10px', fontSize: '0.85rem', cursor: 'pointer' }}
          value={selectedDate || data.report_date || ''}
          onChange={e => setSelectedDate(e.target.value)}>
          {(data.available_dates || []).map(d => (
            <option key={d} value={d}>{fmtDate(d)}</option>
          ))}
        </select>
      </div>

      {/* Explanation */}
      {cur?.explanation && (
        <div style={{ ...S.card, color: '#94a3b8', lineHeight: 1.7, fontSize: '0.88rem' }}>
          {cur.explanation}
        </div>
      )}

      {/* Stats */}
      {cur && (
        <div style={S.grid}>
          <StatBox label="Pair Score" value={fmtNum(cur.pair_score)} color={biasColor(cur.pair_label)}
            tip="Base-valuutan COT Score miinus quote-valuutan score. Skaala −4…+4. Yli +2 = vahvasti bullish parille, alle −2 = vahvasti bearish." />
          <StatBox label="Conviction" value={cur.conviction || '—'} color={convictionColor(cur.conviction)}
            tip="Signaalin luotettavuus. High = vahva pair score ilman kääntymisriskiä. Vähennetään 1 piste jos jommalla kummalla valuutalla on High Reversal Risk." />
          <StatBox label="Base Score" value={`${cur.base_currency}: ${fmtNum(cur.base_score)}`}
            tip="Base-valuutan (ensimmäinen valuutta parissa) COT Score välillä −2…+2." />
          <StatBox label="Quote Score" value={`${cur.quote_currency}: ${fmtNum(cur.quote_score)}`}
            tip="Quote-valuutan (toinen valuutta parissa) COT Score välillä −2…+2." />
          <StatBox label="Divergence" value={cur.divergence_type || 'None'}
            color={cur.divergence_type ? divergenceColor(cur.divergence_type) : '#64748b'}
            tip="Bullish: hinta on laskenut mutta COT-positiointi on noussut → mahdollinen pohja. Bearish: hinta noussut mutta positiointi laskenut → mahdollinen huippu." />
          <StatBox label="Divergence Strength"
            value={cur.divergence_strength != null ? fmtNum(cur.divergence_strength) : '—'}
            tip="Divergenssin voimakkuus välillä 0–1. Lähellä 1 = selkeä ristiriita hinnan ja positioning-liikkeen välillä." />
          <StatBox label="Base Rev. Risk" value={cur.base_reversal_risk || 'Low'}
            color={reversalColor(cur.base_reversal_risk)}
            tip="Base-valuutan kääntymisriski. High = äärimmäinen positioning (≥85. pers.) + hedgaajat vastapuolella. Ei tarkoita varmuutta — varoittaa lisäämästä positioita." />
          <StatBox label="Quote Rev. Risk" value={cur.quote_reversal_risk || 'Low'}
            color={reversalColor(cur.quote_reversal_risk)}
            tip="Quote-valuutan kääntymisriski. High = äärimmäinen positioning (≥85. pers.) + hedgaajat vastapuolella." />
        </div>
      )}

      {/* Pair Score Timeline */}
      {chartData.length > 0 && (
        <div style={S.card}>
          <div style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase',
            letterSpacing: '0.08em', color: '#64748b', marginBottom: 14 }}>
            Pair Score Timeline
          </div>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <XAxis dataKey="date" tick={{ fill: '#475569', fontSize: 10 }}
                tickFormatter={d => d ? d.slice(2, 7) : ''} interval={Math.floor(chartData.length / 8)} />
              <YAxis domain={[-4, 4]} tick={{ fill: '#475569', fontSize: 10 }} width={28}
                ticks={[-4, -2, 0, 2, 4]} />
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 6, fontSize: '0.8rem' }}
                labelFormatter={d => fmtDate(d)}
                formatter={(v) => [fmtNum(v), 'Score']}
              />
              <ReferenceLine y={0} stroke="#334155" strokeDasharray="3 3" />
              <ReferenceLine y={2} stroke="#22c55e" strokeDasharray="2 4" strokeOpacity={0.35} />
              <ReferenceLine y={-2} stroke="#ef4444" strokeDasharray="2 4" strokeOpacity={0.35} />
              <Line dataKey="score" stroke="#a78bfa" strokeWidth={1.5} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Pair Spread Chart — baseNet - quoteNet (spec §21.4) */}
      {chartData.length > 0 && chartData.some(d => d.spread != null) && (
        <div style={S.card}>
          <div style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase',
            letterSpacing: '0.08em', color: '#64748b', marginBottom: 6 }}>
            NC Net Spread — {cur?.base_currency} minus {cur?.quote_currency}
          </div>
          <div style={{ fontSize: '0.72rem', color: '#475569', marginBottom: 6 }}>
            Positiivinen spread = base-valuutan spekulantit ovat nettopidemmällä kuin quote-valuutan.
          </div>
          <div style={{ fontSize: '0.7rem', color: '#475569', marginBottom: 10 }}>
            <span style={{ color: '#3b82f6' }}>■</span> {cur?.base_currency} Net &nbsp;
            <span style={{ color: '#f97316' }}>■</span> {cur?.quote_currency} Net &nbsp;
            <span style={{ color: '#22c55e' }}>■</span> Spread
          </div>
          <ResponsiveContainer width="100%" height={180}>
            <ComposedChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <XAxis dataKey="date" tick={{ fill: '#475569', fontSize: 10 }}
                tickFormatter={d => d ? d.slice(2, 7) : ''} interval={Math.floor(chartData.length / 8)} />
              <YAxis tick={{ fill: '#475569', fontSize: 10 }} tickFormatter={v => fmtK(v)} width={52} />
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 6, fontSize: '0.8rem' }}
                labelFormatter={d => fmtDate(d)}
                formatter={(v, name) => [fmtK(v), name]}
              />
              <ReferenceLine y={0} stroke="#334155" strokeDasharray="3 3" />
              <Line dataKey="baseNet" name={cur?.base_currency} stroke="#3b82f6" strokeWidth={1} dot={false} strokeOpacity={0.7} />
              <Line dataKey="quoteNet" name={cur?.quote_currency} stroke="#f97316" strokeWidth={1} dot={false} strokeOpacity={0.7} />
              <Line dataKey="spread" name="Spread" stroke="#22c55e" strokeWidth={1.5} dot={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Currency detail cards */}
      <div style={S.twoCol}>
        <CurrencyCard data={data.base_detail}  title={`Base: ${cur?.base_currency}`} />
        <CurrencyCard data={data.quote_detail} title={`Quote: ${cur?.quote_currency}`} />
      </div>
    </div>
  )
}
