import { useEffect, useState } from 'react'
import { getDashboard, getAvailableDates } from '../api/client'
import DataStatusBanner from '../components/DataStatusBanner'
import BiasLabel from '../components/BiasLabel'
import { scoreColor, fmt2, fmtPct, fmtDate } from '../utils/formatters'
import { Link } from 'react-router-dom'

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [dates, setDates] = useState([])
  const [selectedDate, setSelectedDate] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Hae saatavilla olevat viikot
  useEffect(() => {
    getAvailableDates()
      .then(r => setDates(r.data))
      .catch(() => {})
  }, [])

  // Hae dashboard-data kun viikko vaihtuu
  useEffect(() => {
    setLoading(true)
    setError(null)
    getDashboard(selectedDate)
      .then(r => setData(r.data))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [selectedDate])

  if (loading) return <Loading />
  if (error) return <ErrorMsg msg={error} />

  const { data_status, top_currencies, bottom_currencies, top_pairs, bottom_pairs } = data

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
        <h1 style={h1}>Dashboard</h1>
        {dates.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <label style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Positiot mitattu:</label>
            <select
              value={selectedDate || ''}
              onChange={e => setSelectedDate(e.target.value || null)}
              style={selectStyle}
            >
              <option value="">Uusin</option>
              {dates.map(d => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>
        )}
      </div>

      <div style={{ marginBottom: '20px' }}>
        <DataStatusBanner status={data_status} />
      </div>

      {data_status.status === 'no_data' ? (
        <NoDataGuide />
      ) : (
        <>
          <div style={grid2}>
            <Section title="Vahvimmat valuutat" linkTo="/valuutat">
              {top_currencies.map(c => <CurrencyCard key={c.currency} data={c} />)}
            </Section>
            <Section title="Heikoimmat valuutat" linkTo="/valuutat">
              {bottom_currencies.map(c => <CurrencyCard key={c.currency} data={c} />)}
            </Section>
          </div>

          <div style={{ ...grid2, marginTop: '24px' }}>
            <Section title="Top 5 Bullish parit" linkTo="/parit">
              {top_pairs.map(p => <PairCard key={p.pair} data={p} />)}
            </Section>
            <Section title="Top 5 Bearish parit" linkTo="/parit">
              {bottom_pairs.map(p => <PairCard key={p.pair} data={p} />)}
            </Section>
          </div>
        </>
      )}
    </div>
  )
}

function NoDataGuide() {
  return (
    <div style={{
      textAlign: 'center', padding: '64px 24px',
      background: '#0f172a', borderRadius: '12px', border: '1px solid #1e293b',
    }}>
      <div style={{ fontSize: '3rem', marginBottom: '16px' }}>📥</div>
      <h2 style={{ color: '#e2e8f0', marginBottom: '8px' }}>Ei dataa ladattu</h2>
      <p style={{ color: '#94a3b8', marginBottom: '24px' }}>
        Aloita tuomalla COT-historia CFTC:ltä tai lataamalla oma CSV-tiedostosi.
      </p>
      <Link to="/tuo-dataa" style={{
        display: 'inline-block', padding: '10px 24px',
        background: '#3b82f6', color: '#fff', borderRadius: '8px',
        textDecoration: 'none', fontWeight: 600,
      }}>
        Siirry tuomaan dataa →
      </Link>
    </div>
  )
}

function Section({ title, linkTo, children }) {
  return (
    <div style={{ background: '#0f172a', borderRadius: '12px', border: '1px solid #1e293b', padding: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h2 style={{ color: '#e2e8f0', fontSize: '1rem', fontWeight: 700 }}>{title}</h2>
        <Link to={linkTo} style={{ color: '#60a5fa', fontSize: '0.8rem', textDecoration: 'none' }}>Näytä kaikki →</Link>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {children.length === 0
          ? <div style={{ color: '#475569', fontSize: '0.85rem' }}>Ei dataa</div>
          : children}
      </div>
    </div>
  )
}

function CurrencyCard({ data: d }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '10px 14px', background: '#1e293b', borderRadius: '8px',
    }}>
      <span style={{ fontWeight: 700, fontSize: '1.1rem', color: scoreColor(d.currency_score), minWidth: '48px' }}>
        {d.currency}
      </span>
      <span style={{ color: '#94a3b8', fontSize: '0.8rem' }}>
        Net%: {fmtPct(d.net_percent_lf)}
      </span>
      <span style={{ color: scoreColor(d.currency_score), fontWeight: 600 }}>
        {fmt2(d.currency_score)}
      </span>
      <BiasLabel label={d.bias_label} />
    </div>
  )
}

function PairCard({ data: d }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '10px 14px', background: '#1e293b', borderRadius: '8px',
    }}>
      <span style={{ fontWeight: 700, fontSize: '1rem', color: scoreColor(d.pair_score), minWidth: '72px' }}>
        {d.pair}
      </span>
      <span style={{ color: scoreColor(d.pair_score), fontWeight: 600 }}>
        {fmt2(d.pair_score)}
      </span>
      <BiasLabel label={d.bias_label} />
    </div>
  )
}

function Loading() {
  return <div style={{ textAlign: 'center', padding: '64px', color: '#64748b' }}>Ladataan...</div>
}
function ErrorMsg({ msg }) {
  return <div style={{ textAlign: 'center', padding: '64px', color: '#ef4444' }}>Virhe: {msg}</div>
}

const h1 = { fontSize: '1.5rem', fontWeight: 700, color: '#f1f5f9' }
const grid2 = { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }
const selectStyle = {
  background: '#1e293b', color: '#e2e8f0', border: '1px solid #334155',
  padding: '6px 12px', borderRadius: '6px', fontSize: '0.85rem', cursor: 'pointer',
}
