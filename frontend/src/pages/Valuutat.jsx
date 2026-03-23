import { useEffect, useState } from 'react'
import { getCurrencyRanking, getAvailableDates } from '../api/client'
import CurrencyTable from '../components/CurrencyTable'

export default function Valuutat() {
  const [data, setData] = useState([])
  const [dates, setDates] = useState([])
  const [selectedDate, setSelectedDate] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    getAvailableDates()
      .then(r => {
        setDates(r.data)
        if (r.data.length > 0) setSelectedDate(r.data[0])
      })
      .catch(() => setDates([]))
  }, [])

  useEffect(() => {
    setLoading(true)
    getCurrencyRanking(selectedDate)
      .then(r => setData(r.data))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [selectedDate])

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
        <h1 style={h1}>Valuuttaranking</h1>
        {dates.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <label style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Positiot mitattu:</label>
            <select
              value={selectedDate || ''}
              onChange={e => setSelectedDate(e.target.value || null)}
              style={selectStyle}
            >
              {dates.map(d => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>
        )}
      </div>

      {loading ? (
        <div style={loadingStyle}>Ladataan...</div>
      ) : error ? (
        <div style={errorStyle}>Virhe: {error}</div>
      ) : (
        <div style={{ background: '#0f172a', borderRadius: '12px', border: '1px solid #1e293b', padding: '20px' }}>
          <CurrencyTable data={data} />
        </div>
      )}
    </div>
  )
}

const h1 = { fontSize: '1.5rem', fontWeight: 700, color: '#f1f5f9' }
const loadingStyle = { textAlign: 'center', padding: '64px', color: '#64748b' }
const errorStyle = { textAlign: 'center', padding: '64px', color: '#ef4444' }
const selectStyle = {
  background: '#1e293b', color: '#e2e8f0', border: '1px solid #334155',
  padding: '6px 12px', borderRadius: '6px', fontSize: '0.85rem', cursor: 'pointer',
}
