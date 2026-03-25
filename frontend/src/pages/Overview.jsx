import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { getOverview } from '../api/client'
import { fmtDate, fmtNum, biasColor, biasBackground, reversalColor, convictionColor, divergenceColor } from '../utils/formatters'

const COT_GUIDE_ITEMS = [
  { icon: '📋', title: 'Mikä on COT-raportti?', text: 'CFTC (Commodity Futures Trading Commission) julkaisee viikoittain Commitment of Traders -raportin, joka kertoo kuinka institutionaaliset toimijat ovat positioituneet valuuttafutuurimarkkinoilla. Raportti on julkinen ja perustuu todellisiin kaupankäyntipositioihin.' },
  { icon: '👥', title: 'Kolme trader-ryhmää', text: 'Non-Commercials (spekulantit) – suuret hedgerahastot ja institutionaaliset sijoittajat, jotka pyrkivät tuottoon. Commercials (hedgaajat) – yritykset, jotka suojaavat valuuttariskiään. Non-Reportables – pienet toimijat, alle raportointikynnyksen.' },
  { icon: '📈', title: 'Trendi vs. kääntymisriski', text: 'Kun spekulanttien positioning on historiallisessa puoliväliä (50. persentiili) ja nousee, se vahvistaa trendiä. Kun positioning ylittää 90. persentiilitason, asema on "ruuhkautunut" ja kääntymisriski kasvaa merkittävästi. Äärimmäinen long-positio voi tarkoittaa exhaustionia eikä vahvistusta.' },
  { icon: '💱', title: 'Parivaluuttojen analyysi', text: 'Pair Score = base-valuutan COT Score miinus quote-valuutan COT Score. Esim. EURUSD: EUR-score − USD-score. Vahvin valuutta paritetaan heikoimman kanssa parhaan edge:n löytämiseksi.' },
]

function CotGuide() {
  const [open, setOpen] = useState(() => {
    try { return localStorage.getItem('cot_guide_open') !== 'false' } catch { return true }
  })
  const toggle = () => {
    const next = !open
    setOpen(next)
    try { localStorage.setItem('cot_guide_open', String(next)) } catch {}
  }
  return (
    <div style={{ background: '#0a1628', border: '1px solid #1e3a5f', borderRadius: 10, marginBottom: 24 }}>
      <button onClick={toggle} style={{
        width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '12px 20px', background: 'none', border: 'none', cursor: 'pointer',
        color: '#60a5fa', fontSize: '0.82rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em',
      }}>
        <span>📖 Miten tulkita COT-dataa?</span>
        <span style={{ fontSize: '0.9rem', color: '#475569' }}>{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div style={{ padding: '0 20px 18px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 14 }}>
          {COT_GUIDE_ITEMS.map(item => (
            <div key={item.title} style={{ background: '#0f172a', borderRadius: 8, padding: '12px 14px' }}>
              <div style={{ fontSize: '0.78rem', fontWeight: 700, color: '#60a5fa', marginBottom: 6 }}>
                {item.icon} {item.title}
              </div>
              <div style={{ fontSize: '0.75rem', color: '#64748b', lineHeight: 1.6 }}>{item.text}</div>
            </div>
          ))}
          <div style={{ gridColumn: '1 / -1', fontSize: '0.7rem', color: '#334155', marginTop: 4 }}>
            ⚠️ Ei sijoitusneuvoja. COT-data on yksi analyysiväline muiden joukossa — ei itsenäinen kaupankäyntisignaali.
            Lähde: CFTC Legacy COT Report.
          </div>
        </div>
      )}
    </div>
  )
}

const S = {
  page:     { maxWidth: 1400 },
  header:   { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24, flexWrap: 'wrap', gap: 12 },
  title:    { fontSize: '1.4rem', fontWeight: 700, color: '#e2e8f0', margin: 0 },
  subtitle: { color: '#64748b', fontSize: '0.85rem', marginTop: 4 },
  grid:     { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 20, marginBottom: 24 },
  card:     { background: '#0f172a', border: '1px solid #1e293b', borderRadius: 10, padding: '16px 20px' },
  cardTitle:{ fontSize: '0.75rem', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: '#64748b', marginBottom: 14 },
  row:      { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 10px', borderRadius: 6, marginBottom: 4, cursor: 'pointer', transition: 'background 0.1s' },
  badge:    { fontSize: '0.72rem', fontWeight: 600, padding: '2px 8px', borderRadius: 12, background: 'rgba(255,255,255,0.06)' },
  select:   { background: '#1e293b', border: '1px solid #334155', borderRadius: 6, color: '#e2e8f0', padding: '6px 10px', fontSize: '0.85rem', cursor: 'pointer' },
}

function BiasChip({ label }) {
  return (
    <span style={{ fontSize: '0.72rem', fontWeight: 600, padding: '3px 9px', borderRadius: 12,
      color: biasColor(label), background: biasBackground(label), border: `1px solid ${biasColor(label)}33` }}>
      {label || 'Neutral'}
    </span>
  )
}

function ReversalBadge({ risk }) {
  if (!risk || risk === 'Low') return null
  return (
    <span style={{ fontSize: '0.68rem', fontWeight: 700, padding: '2px 7px', borderRadius: 10,
      color: reversalColor(risk), background: `${reversalColor(risk)}18`, border: `1px solid ${reversalColor(risk)}44`,
      marginLeft: 6 }}>
      {risk} RR
    </span>
  )
}

export default function Overview() {
  const [data, setData]   = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedDate, setSelectedDate] = useState(null)
  const navigate = useNavigate()

  const load = useCallback(async (rd) => {
    setLoading(true)
    setError(null)
    try {
      const res = await getOverview(rd)
      setData(res.data)
    } catch (e) {
      setError('Failed to load data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load(selectedDate) }, [selectedDate, load])

  const availableDates = data?.available_dates || []

  if (loading && !data) return <div style={{ color: '#64748b', padding: 40 }}>Loading...</div>
  if (error)            return <div style={{ color: '#ef4444', padding: 40 }}>{error}</div>
  if (!data)            return null

  // Stale data check (§15): warn if report is older than 10 days
  const reportAge = data.report_date
    ? Math.floor((Date.now() - new Date(data.report_date).getTime()) / 86400000)
    : null

  // Event type helpers
  const eventIcon = (type) =>
    type === 'bias_shift' ? '🔄' : type === 'new_extreme' ? '⚠️' : '⚡'
  const eventColor = (type) =>
    type === 'bias_shift' ? '#60a5fa' : type === 'new_extreme' ? '#f97316' : '#a78bfa'

  return (
    <div style={S.page}>
      <CotGuide />

      {/* Stale data banner (§15) */}
      {reportAge !== null && reportAge > 10 && (
        <div style={{ background: '#422006', border: '1px solid #92400e', borderRadius: 8,
          padding: '10px 16px', marginBottom: 16, color: '#fbbf24', fontSize: '0.85rem', display: 'flex', gap: 8 }}>
          <span>⚠️</span>
          <span>Data may be stale — latest report is <strong>{reportAge} days old</strong> ({fmtDate(data.report_date)}). Check the Data page to fetch new data.</span>
        </div>
      )}

      <div style={S.header}>
        <div>
          <h1 style={S.title}>COT Dashboard</h1>
          <div style={S.subtitle}>
            Report: {fmtDate(data.report_date)} &nbsp;·&nbsp; Published: {fmtDate(data.publish_date)}
          </div>
        </div>
        <select
          style={S.select}
          value={selectedDate || data.report_date || ''}
          onChange={e => setSelectedDate(e.target.value)}
        >
          {availableDates.map(d => (
            <option key={d} value={d}>{fmtDate(d)}</option>
          ))}
        </select>
      </div>

      <div style={S.grid}>
        {/* Currency Ranking */}
        <div style={S.card}>
          <div style={S.cardTitle}>Currency Ranking</div>
          {data.currencies_ranked.map(c => (
            <div key={c.currency} style={{ ...S.row, background: 'transparent' }}
              onClick={() => navigate(`/currency/${c.currency}`)}
              onMouseEnter={e => e.currentTarget.style.background = '#1e293b'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ fontWeight: 700, fontSize: '0.95rem', color: '#e2e8f0', width: 36 }}>{c.currency}</span>
                <BiasChip label={c.bias_label} />
                <ReversalBadge risk={c.reversal_risk} />
              </div>
              <span style={{ color: biasColor(c.bias_label), fontWeight: 600, fontSize: '0.9rem' }}>
                {fmtNum(c.currency_score)}
              </span>
            </div>
          ))}
        </div>

        {/* Top Pairs */}
        <div style={S.card}>
          <div style={S.cardTitle}>Top Pairs by Conviction</div>
          {data.top_pairs.slice(0, 8).map(p => (
            <div key={p.pair} style={{ ...S.row, background: 'transparent' }}
              onClick={() => navigate(`/pair/${p.pair}`)}
              onMouseEnter={e => e.currentTarget.style.background = '#1e293b'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ fontWeight: 700, fontSize: '0.9rem', color: '#e2e8f0', width: 72 }}>{p.pair}</span>
                <BiasChip label={p.pair_label} />
                {p.divergence_type && (
                  <span style={{ fontSize: '0.68rem', color: divergenceColor(p.divergence_type) }}>
                    ⚡ {p.divergence_type} div
                  </span>
                )}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ color: convictionColor(p.conviction), fontSize: '0.78rem', fontWeight: 600 }}>
                  {p.conviction}
                </span>
                <span style={{ color: biasColor(p.pair_label), fontWeight: 600, fontSize: '0.9rem' }}>
                  {fmtNum(p.pair_score)}
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* Events (§14) */}
        {data.events?.length > 0 && (
          <div style={S.card}>
            <div style={S.cardTitle}>This Week's Events</div>
            {data.events.map((e, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 10,
                padding: '7px 10px', borderRadius: 6, marginBottom: 3,
                background: `${eventColor(e.event_type)}10`,
                borderLeft: `3px solid ${eventColor(e.event_type)}` }}>
                <span style={{ fontSize: '0.85rem' }}>{eventIcon(e.event_type)}</span>
                <span style={{ fontSize: '0.82rem', color: '#cbd5e1', lineHeight: 1.4 }}>{e.detail}</span>
              </div>
            ))}
          </div>
        )}

        {/* Extremes */}
        {data.extremes.length > 0 && (
          <div style={S.card}>
            <div style={S.cardTitle}>Extreme Positioning</div>
            {data.extremes.map(e => (
              <div key={e.currency} style={{ ...S.row, background: biasBackground(e.bias_label) }}
                onClick={() => navigate(`/currency/${e.currency}`)}
                onMouseEnter={el => el.currentTarget.style.opacity = '0.8'}
                onMouseLeave={el => el.currentTarget.style.opacity = '1'}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{ fontWeight: 700, color: '#e2e8f0', width: 36 }}>{e.currency}</span>
                  <BiasChip label={e.bias_label} />
                  <ReversalBadge risk={e.reversal_risk} />
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ color: '#94a3b8', fontSize: '0.78rem' }}>
                    {e.percentile != null ? `${(e.percentile * 100).toFixed(0)}th pct` : ''}
                  </span>
                  <span style={{ fontSize: '0.78rem', color: '#f97316', fontWeight: 700 }}>
                    {'★'.repeat(e.extreme_score || 0)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
