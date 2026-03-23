import { useEffect, useState } from 'react'
import { getExhaustionSignals, getAvailableDates } from '../api/client'
import { fmtDateWithDay, fmt2 } from '../utils/formatters'
import WeekSelector from '../components/WeekSelector'

export default function Exhaustion() {
  const [data, setData] = useState(null)
  const [dates, setDates] = useState([])
  const [selectedDate, setSelectedDate] = useState(null)
  const [threshold, setThreshold] = useState(1.5)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    getAvailableDates().then(r => setDates(r.data)).catch(() => {})
  }, [])

  useEffect(() => {
    setLoading(true); setError(null)
    getExhaustionSignals(selectedDate, threshold)
      .then(r => setData(r.data))
      .catch(e => setError(e.response?.data?.detail || e.message))
      .finally(() => setLoading(false))
  }, [selectedDate, threshold])

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
        <h1 style={h1}>Exhaustion Contrarian</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <label style={labelSm}>Kynnys (|z|):</label>
            <select value={threshold} onChange={e => setThreshold(Number(e.target.value))} style={selectStyle}>
              <option value={1.0}>1.0 (herkempi)</option>
              <option value={1.5}>1.5 (oletus)</option>
              <option value={2.0}>2.0 (tiukempi)</option>
            </select>
          </div>
          <WeekSelector dates={dates} selected={selectedDate} onChange={setSelectedDate} />
        </div>
      </div>

      {/* Metodologia */}
      <div style={{ ...card, marginBottom: '20px', borderLeft: '3px solid #3b82f6' }}>
        <p style={{ color: '#94a3b8', fontSize: '0.82rem', lineHeight: 1.7, margin: 0 }}>
          <strong style={{ color: '#e2e8f0' }}>Malli:</strong> Kun valuuttaparin positioning-ero (A-komponentti) on äärimmäinen ({'>'}|z|×2 = {'>'}3.0)
          ja edelleen kasvamassa, seuraavan viikon hinta kääntyy kontraariseen suuntaan <strong style={{ color: '#4ade80' }}>57%</strong> ajasta
          (200vk backtesti, Sharpe ~0.86, avg tuotto +0.115%/vk).
          <br />
          <strong style={{ color: '#fbbf24' }}>Strong</strong> = positioning äärimmäinen JA kasvaa (vahvin signaali).{' '}
          <strong style={{ color: '#94a3b8' }}>Moderate</strong> = positioning äärimmäinen mutta ei enää kasva (heikompi).
        </p>
      </div>

      {loading ? <div style={loadingStyle}>Ladataan...</div>
       : error ? <div style={errorStyle}>Virhe: {error}</div>
       : data && (
        <>
          {/* Päivämäärät */}
          <div style={{ ...card, marginBottom: '20px' }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '20px', alignItems: 'center' }}>
              {data.report_date && (
                <div>
                  <span style={labelSm}>Positiot mitattu:</span>{' '}
                  <strong style={{ color: '#e2e8f0' }}>{fmtDateWithDay(data.report_date)}</strong>
                </div>
              )}
              {data.publish_date && (
                <div>
                  <span style={labelSm}>Julkaistu:</span>{' '}
                  <span style={{ color: '#94a3b8' }}>{fmtDateWithDay(data.publish_date)}</span>
                </div>
              )}
              <div style={{ marginLeft: 'auto', display: 'flex', gap: '12px' }}>
                <Badge color="#ef4444" label={`Short-signaalit: ${data.contrarian_short.length}`} />
                <Badge color="#22c55e" label={`Long-signaalit: ${data.contrarian_long.length}`} />
                <Badge color="#475569" label={`Neutraalit: ${data.neutral_count}`} />
              </div>
            </div>
          </div>

          {/* Taulukot */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: '20px' }}>
            <SignalTable
              title="Contrarian SHORT (ennusta laskua)"
              subtitle="Positioning äärimmäisen pitkä → exhaustion → kontraarinen short-bias"
              signals={data.contrarian_short}
              color="#ef4444"
              icon="🔻"
            />
            <SignalTable
              title="Contrarian LONG (ennusta nousua)"
              subtitle="Positioning äärimmäisen lyhyt → exhaustion → kontraarinen long-bias"
              signals={data.contrarian_long}
              color="#22c55e"
              icon="🔺"
            />
          </div>

          {data.contrarian_short.length === 0 && data.contrarian_long.length === 0 && (
            <div style={{ ...card, marginTop: '20px', textAlign: 'center', padding: '48px' }}>
              <div style={{ fontSize: '2.5rem', marginBottom: '12px' }}>⚖️</div>
              <div style={{ color: '#94a3b8', fontSize: '0.95rem' }}>
                Ei exhaustion-signaaleja tällä viikolla. Positioning ei ole äärimmäinen yhdelläkään parilla.
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

function SignalTable({ title, subtitle, signals, color, icon }) {
  return (
    <div style={{ ...card, borderTop: `3px solid ${color}` }}>
      <h2 style={{ color: '#e2e8f0', fontSize: '1rem', fontWeight: 700, marginBottom: '4px' }}>
        {icon} {title}
      </h2>
      <p style={{ color: '#64748b', fontSize: '0.78rem', marginBottom: '16px' }}>{subtitle}</p>

      {signals.length === 0 ? (
        <div style={{ color: '#475569', textAlign: 'center', padding: '24px', fontSize: '0.85rem' }}>
          Ei signaaleja
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {signals.map(s => (
            <SignalCard key={s.pair} signal={s} color={color} />
          ))}
        </div>
      )}
    </div>
  )
}

function SignalCard({ signal: s, color }) {
  const isStrong = s.signal_strength === 'strong'
  const borderColor = isStrong ? color : '#334155'
  const bgColor = isStrong ? `${color}10` : '#0f172a'

  return (
    <div style={{
      padding: '12px 16px',
      borderRadius: '8px',
      border: `1px solid ${borderColor}`,
      background: bgColor,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontWeight: 800, fontSize: '1.1rem', color }}>{s.pair}</span>
          <span style={{
            padding: '2px 8px', borderRadius: '4px', fontSize: '0.72rem', fontWeight: 700,
            background: isStrong ? color : '#334155',
            color: isStrong ? '#fff' : '#94a3b8',
          }}>
            {isStrong ? 'STRONG' : 'MODERATE'}
          </span>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '0.78rem', color: '#64748b' }}>Pair A (z-score ero)</div>
          <div style={{ fontWeight: 700, color, fontSize: '1rem' }}>{fmt2(s.pair_A)}</div>
        </div>
      </div>

      {/* A:n muutos */}
      <div style={{ display: 'flex', gap: '16px', marginBottom: '8px', fontSize: '0.78rem' }}>
        {s.pair_A_prev != null && (
          <div style={{ color: '#64748b' }}>
            Edellinen: <span style={{ color: '#94a3b8' }}>{fmt2(s.pair_A_prev)}</span>
            {' → '}
            <span style={{ color: s.a_growing ? color : '#94a3b8', fontWeight: 600 }}>
              {s.a_growing ? '↑ kasvaa (exhaustion rakentuu)' : '↓ ei kasva'}
            </span>
          </div>
        )}
      </div>

      {/* Sanallinen kuvaus */}
      <div style={{ fontSize: '0.78rem', color: '#94a3b8', lineHeight: 1.6 }}>
        {s.note}
      </div>
    </div>
  )
}

function Badge({ color, label }) {
  return (
    <span style={{
      padding: '4px 10px', borderRadius: '6px',
      background: `${color}18`, color, fontSize: '0.8rem', fontWeight: 600,
    }}>
      {label}
    </span>
  )
}

const h1 = { fontSize: '1.5rem', fontWeight: 700, color: '#f1f5f9' }
const card = { background: '#0f172a', borderRadius: '12px', border: '1px solid #1e293b', padding: '20px' }
const labelSm = { color: '#64748b', fontSize: '0.82rem' }
const selectStyle = { background: '#1e293b', color: '#e2e8f0', border: '1px solid #334155', padding: '6px 12px', borderRadius: '6px', fontSize: '0.85rem', cursor: 'pointer' }
const loadingStyle = { textAlign: 'center', padding: '64px', color: '#64748b' }
const errorStyle = { textAlign: 'center', padding: '64px', color: '#ef4444' }
