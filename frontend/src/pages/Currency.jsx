import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  ReferenceLine, BarChart, Bar, Cell, ComposedChart, Area,
} from 'recharts'
import { getCurrencyDetail } from '../api/client'
import { fmtDate, fmtNum, fmtK, fmtPct, biasColor, biasBackground, reversalColor } from '../utils/formatters'
import InfoTip from '../components/InfoTip'

const CURRENCIES = ['EUR', 'GBP', 'AUD', 'NZD', 'USD', 'CAD', 'CHF', 'JPY']

const S = {
  page:    { maxWidth: 1200 },
  header:  { display: 'flex', alignItems: 'center', gap: 16, marginBottom: 24, flexWrap: 'wrap' },
  back:    { color: '#64748b', cursor: 'pointer', fontSize: '0.85rem', textDecoration: 'underline' },
  title:   { fontSize: '1.4rem', fontWeight: 800, color: '#e2e8f0', margin: 0 },
  grid:    { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 14, marginBottom: 24 },
  statBox: { background: '#0f172a', border: '1px solid #1e293b', borderRadius: 8, padding: '12px 16px' },
  label:   { fontSize: '0.72rem', color: '#64748b', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 },
  value:   { fontSize: '1.2rem', fontWeight: 700, color: '#e2e8f0' },
  card:    { background: '#0f172a', border: '1px solid #1e293b', borderRadius: 10, padding: '20px' },
  select:  { background: '#1e293b', border: '1px solid #334155', borderRadius: 6, color: '#e2e8f0', padding: '6px 10px', fontSize: '0.85rem' },
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

function ExplanationBox({ text }) {
  if (!text) return null
  return (
    <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 10,
      padding: '16px 20px', marginBottom: 20, color: '#94a3b8', lineHeight: 1.7, fontSize: '0.88rem' }}>
      {text}
    </div>
  )
}

export default function Currency() {
  const { symbol } = useParams()
  const navigate   = useNavigate()
  const [data, setData]   = useState(null)
  const [loading, setLoading] = useState(true)
  const [availDates, setAvailDates] = useState([])
  const [selectedDate, setSelectedDate] = useState(null)

  useEffect(() => {
    if (!symbol) return
    setLoading(true)
    getCurrencyDetail(symbol.toUpperCase(), selectedDate, 104)
      .then(r => {
        setData(r.data)
        setAvailDates(r.data.available_dates || [])
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [symbol, selectedDate])

  if (loading) return <div style={{ color: '#64748b', padding: 40 }}>Loading...</div>
  if (!data)   return <div style={{ color: '#ef4444', padding: 40 }}>No data</div>

  const cur  = data.current
  const hist = data.history || []

  const chartData = hist.map(h => ({
    date:      h.report_date,
    ncNet:     h.nc_net,
    commNet:   h.comm_net,
    netChange: h.net_change,
    pctOI:     h.net_pct_oi != null ? h.net_pct_oi * 100 : null,
    score:     h.currency_score,
    pct:       h.percentile != null ? h.percentile * 100 : null,
  }))

  return (
    <div style={S.page}>
      <div style={S.header}>
        <span style={S.back} onClick={() => navigate('/')}>← Overview</span>
        <div style={{ display: 'flex', gap: 8 }}>
          {CURRENCIES.map(c => (
            <button key={c} onClick={() => navigate(`/currency/${c}`)}
              style={{ padding: '4px 10px', borderRadius: 6, border: '1px solid #334155',
                background: c === symbol?.toUpperCase() ? '#1e3a5f' : 'transparent',
                color: c === symbol?.toUpperCase() ? '#fff' : '#64748b',
                cursor: 'pointer', fontSize: '0.8rem', fontWeight: 600 }}>
              {c}
            </button>
          ))}
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <div>
          <h1 style={{ ...S.title, color: biasColor(cur?.bias_label) }}>
            {symbol?.toUpperCase()}
            <span style={{ fontSize: '1rem', fontWeight: 400, color: '#64748b', marginLeft: 12 }}>
              {cur?.bias_label}
            </span>
          </h1>
          <div style={{ color: '#64748b', fontSize: '0.82rem', marginTop: 2 }}>
            Report: {fmtDate(data.report_date)}
          </div>
        </div>
        <select style={S.select} value={selectedDate || data.report_date || ''} onChange={e => setSelectedDate(e.target.value)}>
          {availDates.map(d => (
            <option key={d} value={d}>{fmtDate(d)}</option>
          ))}
        </select>
      </div>

      <ExplanationBox text={cur?.explanation} />

      {cur && (
        <div style={S.grid}>
          <StatBox label="COT Score" value={fmtNum(cur.currency_score)}
            color={biasColor(cur.bias_label)}
            tip="Yhdistetty pistearvo välillä −2…+2. Laskee suunnan (pitkä/lyhyt), viikkomuutoksen (momentum) ja persentiilipohjaisen vahvuuden. Positiivinen = bullish, negatiivinen = bearish." />
          <StatBox label="Percentile" value={cur.percentile != null ? `${(cur.percentile * 100).toFixed(0)}th` : '—'}
            color={cur.extreme_score >= 2 ? '#f97316' : '#e2e8f0'}
            tip="Kuinka korkea spekulanttien netto-positio on verrattuna viimeiseen 3 vuoteen. 100. pers. = kaikista aikojen korkein. Yli 85 % lisää kääntymisriskiä — 'ruuhkainen' positio." />
          <StatBox label="Net Position" value={fmtK(cur.nc_net)}
            tip="Non-commercial (spekulantit) pitkät miinus lyhyet kontraktit futuuripörssissä. Positiivinen = spekulantit nettopitkinä = bullish sentiment. Yksikkö: tuhansia kontrakteja." />
          <StatBox label="Week Change" value={fmtK(cur.net_change)}
            color={cur.net_change > 0 ? '#22c55e' : cur.net_change < 0 ? '#ef4444' : '#e2e8f0'}
            tip="Net-position muutos viikossa. Vihreä = spekulantit lisäsivät nousupositioita. Punainen = lisäsivät laskupositioita tai purkivat nousuja." />
          <StatBox label="Net % of Open Interest" value={fmtPct(cur.net_pct_oi)}
            tip="Net-positio jaettuna avoimilla sopimuksilla (Open Interest). Normalisoi eri kokoisten markkinoiden vertailun. Yli ±20 % = vahva institutionaalinen positioning." />
          <StatBox label="Reversal Risk" value={cur.reversal_risk || 'Low'}
            color={reversalColor(cur.reversal_risk)}
            tip="Käänteisliikkeen todennäköisyys. High = äärimmäinen positioning (≥85. pers.) + kaupalliset hedgaajat ovat vastapuolella. Ei tarkoita käänteen varmuutta — varoitus positioiden kasvattamista vastaan." />
          <StatBox label="Extreme" value={
            cur.extreme_score === 3 ? 'Historical' :
            cur.extreme_score === 2 ? 'Major' :
            cur.extreme_score === 1 ? 'Mild' : 'None'
          } color={cur.extreme_score >= 2 ? '#f97316' : '#64748b'}
            tip="Positioning-ääripää historiallisesti. Mild = 70. persentiilin yli, Major = 85., Historical = 95. Korkeampi extreme = suurempi kääntymisriski trendin vastasuuntaan." />
          <StatBox label="Commercial Opp." value={cur.commercial_opposition === 1 ? 'Yes' : 'No'}
            color={cur.commercial_opposition === 1 ? '#f97316' : '#64748b'}
            tip="Ovatko kaupalliset hedgaajat (yritykset) spekulanttien vastapuolella? Kun hedgaajat myyvät mitä spekulantit ostavat, se on historiallisesti liittynyt trendikäänteisiin." />
        </div>
      )}

      {/* Net Position Chart with percentile overlay */}
      {chartData.length > 0 && (
        <div style={{ ...S.card, marginBottom: 20 }}>
          <div style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase',
            letterSpacing: '0.08em', color: '#64748b', marginBottom: 6 }}>
            Net Position (Non-Commercial) — {hist.length} weeks
          </div>
          <div style={{ fontSize: '0.7rem', color: '#475569', marginBottom: 10 }}>
            <span style={{ color: '#3b82f6' }}>■</span> NC Net (spekulantit) &nbsp;
            <span style={{ color: '#f97316' }}>■</span> Comm Net (hedgaajat) &nbsp;
            <span style={{ color: '#a78bfa' }}>■</span> Persentiili % (oikea akseli)
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <ComposedChart data={chartData} margin={{ top: 4, right: 48, bottom: 0, left: 0 }}>
              <XAxis dataKey="date" tick={{ fill: '#475569', fontSize: 10 }}
                tickFormatter={d => d ? d.slice(2, 7) : ''} interval={Math.floor(chartData.length / 8)} />
              <YAxis yAxisId="pos" tick={{ fill: '#475569', fontSize: 10 }} tickFormatter={v => fmtK(v)} width={48} />
              <YAxis yAxisId="pct" orientation="right" domain={[0, 100]}
                tick={{ fill: '#6d5fad', fontSize: 10 }} tickFormatter={v => `${v}%`} width={40}
                ticks={[0, 25, 50, 70, 85, 95, 100]} />
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 6, fontSize: '0.8rem' }}
                labelFormatter={d => fmtDate(d)}
                formatter={(v, name) => name === 'Percentile' ? [`${v?.toFixed(0)}%`, name] : [fmtK(v), name]}
              />
              <ReferenceLine yAxisId="pos" y={0} stroke="#334155" strokeDasharray="3 3" />
              {/* Percentile zone bands */}
              <ReferenceLine yAxisId="pct" y={95} stroke="#f97316" strokeDasharray="2 4" strokeOpacity={0.5}
                label={{ value: 'Historic 95%', position: 'insideTopRight', fill: '#f97316', fontSize: 9 }} />
              <ReferenceLine yAxisId="pct" y={85} stroke="#f59e0b" strokeDasharray="2 4" strokeOpacity={0.4}
                label={{ value: 'Major 85%', position: 'insideTopRight', fill: '#f59e0b', fontSize: 9 }} />
              <ReferenceLine yAxisId="pct" y={70} stroke="#eab308" strokeDasharray="2 4" strokeOpacity={0.3}
                label={{ value: 'Mild 70%', position: 'insideTopRight', fill: '#eab308', fontSize: 9 }} />
              <Line yAxisId="pos" dataKey="ncNet" name="NC Net" stroke="#3b82f6" strokeWidth={1.5} dot={false} />
              <Line yAxisId="pos" dataKey="commNet" name="Comm Net" stroke="#f97316" strokeWidth={1} dot={false} strokeDasharray="4 2" />
              <Line yAxisId="pct" dataKey="pct" name="Percentile" stroke="#a78bfa" strokeWidth={1} dot={false} strokeDasharray="2 2" strokeOpacity={0.8} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Weekly Change Bars */}
      {chartData.length > 0 && (
        <div style={{ ...S.card, marginBottom: 20 }}>
          <div style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase',
            letterSpacing: '0.08em', color: '#64748b', marginBottom: 14 }}>
            Weekly Position Change
          </div>
          <ResponsiveContainer width="100%" height={140}>
            <BarChart data={chartData.slice(-52)} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <XAxis dataKey="date" tick={false} />
              <YAxis tick={{ fill: '#475569', fontSize: 10 }} tickFormatter={v => fmtK(v)} width={48} />
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 6, fontSize: '0.8rem' }}
                labelFormatter={d => fmtDate(d)}
                formatter={(v) => [fmtK(v ?? 0), 'Change']}
              />
              <ReferenceLine y={0} stroke="#334155" />
              <Bar dataKey="netChange">
                {chartData.slice(-52).map((entry, i) => (
                  <Cell key={i} fill={entry.netChange > 0 ? '#22c55e' : '#ef4444'} fillOpacity={0.7} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Bias Timeline */}
      {chartData.length > 0 && (
        <div style={S.card}>
          <div style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase',
            letterSpacing: '0.08em', color: '#64748b', marginBottom: 14 }}>
            COT Score Timeline
          </div>
          <ResponsiveContainer width="100%" height={140}>
            <LineChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <XAxis dataKey="date" tick={{ fill: '#475569', fontSize: 10 }}
                tickFormatter={d => d ? d.slice(2, 7) : ''} interval={Math.floor(chartData.length / 8)} />
              <YAxis domain={[-2, 2]} tick={{ fill: '#475569', fontSize: 10 }} width={28}
                ticks={[-2, -1, 0, 1, 2]} />
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 6, fontSize: '0.8rem' }}
                labelFormatter={d => fmtDate(d)}
                formatter={(v) => [fmtNum(v), 'Score']}
              />
              <ReferenceLine y={0} stroke="#334155" strokeDasharray="3 3" />
              <ReferenceLine y={1.5} stroke="#22c55e" strokeDasharray="2 4" strokeOpacity={0.4} />
              <ReferenceLine y={-1.5} stroke="#ef4444" strokeDasharray="2 4" strokeOpacity={0.4} />
              <Line dataKey="score" name="Score" stroke="#a78bfa" strokeWidth={1.5} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
