import { useEffect, useRef, useState } from 'react'
import { uploadFile, fetchHistory, fetchLatest, getImportLogs } from '../api/client'
import { fmtDate } from '../utils/formatters'

export default function TuoData() {
  const [logs, setLogs] = useState([])
  const [dragging, setDragging] = useState(false)
  const [uploadResult, setUploadResult] = useState(null)
  const [fetchResult, setFetchResult] = useState(null)
  const [historyYear, setHistoryYear] = useState('')
  const [loading, setLoading] = useState(false)
  const [activeOp, setActiveOp] = useState(null)
  const fileRef = useRef()

  const loadLogs = () => {
    getImportLogs(20).then(r => setLogs(r.data)).catch(() => {})
  }

  useEffect(() => { loadLogs() }, [])

  const handleFile = async (file) => {
    if (!file) return
    const fd = new FormData()
    fd.append('file', file)
    setLoading(true); setActiveOp('upload'); setUploadResult(null)
    try {
      const r = await uploadFile(fd)
      setUploadResult({ ok: true, ...r.data })
      loadLogs()
    } catch (e) {
      setUploadResult({ ok: false, message: e.response?.data?.detail || e.message })
    } finally { setLoading(false); setActiveOp(null) }
  }

  const handleDrop = (e) => {
    e.preventDefault(); setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  const handleFetchHistory = async () => {
    setLoading(true); setActiveOp('history'); setFetchResult(null)
    try {
      const r = await fetchHistory(historyYear ? parseInt(historyYear) : null)
      setFetchResult({ ok: true, ...r.data })
      loadLogs()
    } catch (e) {
      setFetchResult({ ok: false, message: e.response?.data?.detail || e.message })
    } finally { setLoading(false); setActiveOp(null) }
  }

  const handleFetchLatest = async () => {
    setLoading(true); setActiveOp('latest'); setFetchResult(null)
    try {
      const r = await fetchLatest()
      setFetchResult({ ok: true, ...r.data })
      loadLogs()
    } catch (e) {
      setFetchResult({ ok: false, message: e.response?.data?.detail || e.message })
    } finally { setLoading(false); setActiveOp(null) }
  }

  const currentYear = new Date().getFullYear()
  const years = Array.from({ length: currentYear - 2009 }, (_, i) => 2010 + i).reverse()

  return (
    <div>
      <h1 style={h1}>Tuo dataa</h1>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px', marginBottom: '24px' }}>

        {/* Automaattinen haku */}
        <div style={card}>
          <h2 style={cardH}>Hae CFTC:ltä automaattisesti</h2>
          <p style={desc}>Hakee datan suoraan CFTC:n julkisesta tietokannasta. Historia ladataan vuosi kerrallaan.</p>

          <div style={{ display: 'flex', gap: '8px', marginBottom: '12px', flexWrap: 'wrap' }}>
            <select value={historyYear} onChange={e => setHistoryYear(e.target.value)} style={selectStyle}>
              <option value="">Kaikki vuodet (2010–nyt)</option>
              {years.map(y => <option key={y} value={y}>{y}</option>)}
            </select>
            <button onClick={handleFetchHistory} disabled={loading} style={btnPrimary}>
              {activeOp === 'history' ? 'Haetaan...' : 'Hae historia'}
            </button>
          </div>

          <button onClick={handleFetchLatest} disabled={loading} style={{ ...btnSecondary, width: '100%' }}>
            {activeOp === 'latest' ? 'Haetaan...' : '🔄 Hae uusin viikko'}
          </button>

          {fetchResult && (
            <ResultBox result={fetchResult} />
          )}
        </div>

        {/* Manuaalinen lataus */}
        <div style={card}>
          <h2 style={cardH}>Lataa CSV / Excel</h2>
          <p style={desc}>Lataa CFTC:n COT Futures Only -raportti (CSV tai .xlsx). Duplikaatit ohitetaan automaattisesti.</p>

          <div
            onDragOver={e => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            onClick={() => fileRef.current?.click()}
            style={{
              border: `2px dashed ${dragging ? '#3b82f6' : '#334155'}`,
              borderRadius: '8px',
              padding: '32px',
              textAlign: 'center',
              cursor: 'pointer',
              background: dragging ? 'rgba(59,130,246,0.05)' : '#0f172a',
              transition: 'all 0.2s',
              marginBottom: '12px',
            }}
          >
            <div style={{ fontSize: '2rem', marginBottom: '8px' }}>📂</div>
            <div style={{ color: '#64748b', fontSize: '0.85rem' }}>
              Raahaa tiedosto tähän tai <span style={{ color: '#60a5fa' }}>klikkaa</span>
            </div>
            <div style={{ color: '#475569', fontSize: '0.75rem', marginTop: '4px' }}>CSV, .xlsx, .xls</div>
          </div>
          <input ref={fileRef} type="file" accept=".csv,.xlsx,.xls" style={{ display: 'none' }}
            onChange={e => handleFile(e.target.files[0])} />

          {uploadResult && <ResultBox result={uploadResult} />}
        </div>
      </div>

      {/* Import-loki */}
      <div style={card}>
        <h2 style={{ ...cardH, marginBottom: '16px' }}>Import-historia</h2>
        {logs.length === 0 ? (
          <div style={{ color: '#475569', fontSize: '0.85rem' }}>Ei import-lokirivejä.</div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
              <thead>
                <tr>
                  {['Aika', 'Lähde', 'Tiedosto', 'Yhteensä', 'Tallennettu', 'Ohitettu', 'Status', 'Virheet'].map(h => (
                    <th key={h} style={{ padding: '8px 12px', color: '#64748b', fontWeight: 600, borderBottom: '1px solid #1e293b', textAlign: 'left', fontSize: '0.75rem', textTransform: 'uppercase' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {logs.map(l => (
                  <tr key={l.id}>
                    <td style={logTd}>{l.imported_at ? new Date(l.imported_at).toLocaleString('fi-FI') : '–'}</td>
                    <td style={logTd}>{l.source_type}</td>
                    <td style={{ ...logTd, maxWidth: '180px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{l.source_file || '–'}</td>
                    <td style={logTd}>{l.rows_total}</td>
                    <td style={{ ...logTd, color: '#4ade80' }}>{l.rows_inserted}</td>
                    <td style={{ ...logTd, color: '#94a3b8' }}>{l.rows_skipped}</td>
                    <td style={{ ...logTd, color: l.status === 'ok' ? '#4ade80' : l.status === 'partial' ? '#fde047' : '#ef4444' }}>
                      {l.status}
                    </td>
                    <td style={{ ...logTd, color: '#ef4444', maxWidth: '200px', fontSize: '0.75rem' }}>
                      {l.errors ? l.errors.split('\n')[0] : '–'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

function ResultBox({ result }) {
  return (
    <div style={{
      marginTop: '12px', padding: '12px', borderRadius: '6px',
      background: result.ok ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)',
      border: `1px solid ${result.ok ? '#22c55e' : '#ef4444'}`,
      color: result.ok ? '#4ade80' : '#fca5a5',
      fontSize: '0.82rem',
    }}>
      <div style={{ fontWeight: 700, marginBottom: '4px' }}>{result.ok ? '✓ Onnistui' : '✗ Virhe'}</div>
      <div>{result.message}</div>
      {result.ok && (
        <div style={{ color: '#94a3b8', marginTop: '4px' }}>
          Tallennettu: {result.rows_inserted} | Ohitettu: {result.rows_skipped}
        </div>
      )}
    </div>
  )
}

const h1 = { fontSize: '1.5rem', fontWeight: 700, color: '#f1f5f9', marginBottom: '20px' }
const card = { background: '#0f172a', borderRadius: '12px', border: '1px solid #1e293b', padding: '20px' }
const cardH = { color: '#e2e8f0', fontSize: '1rem', fontWeight: 700, marginBottom: '8px' }
const desc = { color: '#64748b', fontSize: '0.82rem', marginBottom: '16px', lineHeight: 1.5 }
const selectStyle = { background: '#1e293b', color: '#e2e8f0', border: '1px solid #334155', padding: '7px 10px', borderRadius: '6px', fontSize: '0.85rem' }
const btnPrimary = { padding: '8px 16px', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 600, fontSize: '0.85rem' }
const btnSecondary = { padding: '8px 16px', background: '#1e293b', color: '#94a3b8', border: '1px solid #334155', borderRadius: '6px', cursor: 'pointer', fontSize: '0.85rem' }
const logTd = { padding: '8px 12px', borderBottom: '1px solid #0f172a', color: '#cbd5e1', verticalAlign: 'middle' }
