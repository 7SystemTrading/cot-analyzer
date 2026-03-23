import { useCallback, useEffect } from 'react'

/**
 * Viikkonavigaatio nuolinäppäimillä + dropdown.
 * Props:
 *   dates       – kaikki saatavilla olevat päivämäärät (uusin ensin)
 *   selected    – valittu päivämäärä (null = uusin)
 *   onChange    – (dateString | null) => void
 *   label      – valinnan otsikko (oletus: "Positiot mitattu")
 */
export default function WeekSelector({ dates, selected, onChange, label = 'Positiot mitattu' }) {
  // Nykyisen valinnan indeksi dates-taulukossa
  const currentIdx = selected ? dates.indexOf(selected) : 0

  const goPrev = useCallback(() => {
    if (dates.length === 0) return
    const nextIdx = Math.min(currentIdx + 1, dates.length - 1)
    onChange(dates[nextIdx])
  }, [dates, currentIdx, onChange])

  const goNext = useCallback(() => {
    if (dates.length === 0) return
    const nextIdx = Math.max(currentIdx - 1, 0)
    onChange(nextIdx === 0 ? null : dates[nextIdx])
  }, [dates, currentIdx, onChange])

  // Näppäimistökuuntelu: ← ja →
  useEffect(() => {
    const handler = (e) => {
      // Älä reagoi jos käyttäjä on input/select/textarea -elementissä
      const tag = e.target.tagName.toLowerCase()
      if (tag === 'input' || tag === 'select' || tag === 'textarea') return

      if (e.key === 'ArrowLeft') {
        e.preventDefault()
        goPrev()
      } else if (e.key === 'ArrowRight') {
        e.preventDefault()
        goNext()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [goPrev, goNext])

  if (dates.length === 0) return null

  const isNewest = currentIdx <= 0
  const isOldest = currentIdx >= dates.length - 1

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
      <label style={labelStyle}>{label}:</label>

      <button
        onClick={goPrev}
        disabled={isOldest}
        title="Edellinen viikko (←)"
        style={arrowBtn(isOldest)}
      >
        ◀
      </button>

      <select
        value={selected || ''}
        onChange={e => onChange(e.target.value || null)}
        style={selectStyle}
      >
        <option value="">Uusin</option>
        {dates.map(d => (
          <option key={d} value={d}>{d}</option>
        ))}
      </select>

      <button
        onClick={goNext}
        disabled={isNewest}
        title="Seuraava viikko (→)"
        style={arrowBtn(isNewest)}
      >
        ▶
      </button>

      <span style={hintStyle}>← →</span>
    </div>
  )
}

const labelStyle = { color: '#94a3b8', fontSize: '0.85rem' }

const selectStyle = {
  background: '#1e293b', color: '#e2e8f0', border: '1px solid #334155',
  padding: '6px 12px', borderRadius: '6px', fontSize: '0.85rem', cursor: 'pointer',
  minWidth: '130px',
}

const arrowBtn = (disabled) => ({
  background: disabled ? '#0f172a' : '#1e293b',
  color: disabled ? '#334155' : '#e2e8f0',
  border: '1px solid #334155',
  borderRadius: '6px',
  padding: '5px 10px',
  cursor: disabled ? 'default' : 'pointer',
  fontSize: '0.8rem',
  lineHeight: 1,
  opacity: disabled ? 0.4 : 1,
  transition: 'all 0.15s',
})

const hintStyle = {
  color: '#334155',
  fontSize: '0.7rem',
  marginLeft: '4px',
}
