import { useEffect, useState } from 'react'
import { getBiasDashboard, getAvailableDates } from '../api/client'
import StrengthBar from '../components/StrengthBar'

const COLORS = {
  long: '#007A5C',
  short: '#A81B30',
  neutral: '#4A5568',
  deltaUp: '#00C87A',
  deltaDown: '#FF4D6A',
  deltaZero: '#3A4258',
}

function DeltaCell({ value }) {
  if (value == null) return <span style={{ color: COLORS.neutral }}>—</span>
  const color = value > 0 ? COLORS.deltaUp : value < 0 ? COLORS.deltaDown : COLORS.deltaZero
  const arrow = value > 0 ? '▲' : value < 0 ? '▼' : '·'
  return (
    <span style={{ color, fontSize: '0.8rem', fontWeight: 600 }}>
      {arrow} {value > 0 ? '+' : ''}{value.toFixed(2)}
    </span>
  )
}

function NetPctCell({ value }) {
  if (value == null) return <span style={{ color: COLORS.neutral }}>–</span>
  const color = value > 0 ? COLORS.deltaUp : value < 0 ? COLORS.deltaDown : COLORS.neutral
  return <span style={{ color, fontWeight: 600 }}>{value > 0 ? '+' : ''}{value.toFixed(2)}%</span>
}

export default function BiasDashboard() {
  const [data, setData] = useState(null)
  const [dates, setDates] = useState([])
  const [selectedDate, setSelectedDate] = useState(null)
  const [threshold, setThreshold] = useState(25)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    getAvailableDates().then(r => setDates(r.data)).catch(() => {})
  }, [])

  useEffect(() => {
    setLoading(true)
    setError(null)
    getBiasDashboard(selectedDate, threshold)
      .then(r => setData(r.data))
      .catch(e => setError(e.response?.data?.detail || e.message))
      .finally(() => setLoading(false))
  }, [selectedDate, threshold])

  if (loading) return <div style={loadingStyle}>Ladataan...</div>
  if (error) return <div style={errorStyle}>Virhe: {error}</div>
  if (!data) return null

  return (
    <div>
      {/* Otsikko + kontrollit */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
        <h1 style={h1}>COT Bias Dashboard</h1>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
          {dates.length > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <label style={labelStyle}>Viikko:</label>
              <select value={selectedDate || ''} onChange={e => setSelectedDate(e.target.value || null)} style={selectStyle}>
                <option value="">Uusin</option>
                {dates.map(d => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>
          )}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <label style={labelStyle}>Kynnys:</label>
            <select value={threshold} onChange={e => setThreshold(Number(e.target.value))} style={selectStyle}>
              {[15, 20, 25, 30, 35].map(v => <option key={v} value={v}>±{v}</option>)}
            </select>
          </div>
        </div>
      </div>

      {/* Raporttipäivä + yhteenveto */}
      <div style={{ display: 'flex', gap: '12px', marginBottom: '24px', flexWrap: 'wrap' }}>
        <InfoBadge label="Raporttipäivä" value={data.report_date || '–'} />
        <InfoBadge label="Long" value={`${data.strong_long.length} (${data.strong_long.filter(p => p.confirmed).length} strong)`} color={COLORS.long} />
        <InfoBadge label="Short" value={`${data.strong_short.length} (${data.strong_short.filter(p => p.confirmed).length} strong)`} color={COLORS.short} />
        <InfoBadge label="Neutral" value={data.neutral_count} color={COLORS.neutral} />
      </div>

      {/* Valuuttayhteenveto */}
      <div style={{ ...card, marginBottom: '24px' }}>
        <h2 style={cardH}>Valuutat – Net % LF & Deltat</h2>
        <div style={{ overflowX: 'auto' }}>
          <table style={tableStyle}>
            <thead>
              <tr>
                {['Valuutta', 'Net % LF', 'Δ1 (1vk)', 'Δ2 (2vk)', 'Δ3 (3vk)', 'Δ4 (4vk)'].map(h => (
                  <th key={h} style={thStyle}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.currencies.map(c => (
                <tr key={c.currency}>
                  <td style={{ ...tdStyle, fontWeight: 700, fontSize: '0.95rem' }}>{c.currency}</td>
                  <td style={tdStyle}><NetPctCell value={c.net_pct_lf} /></td>
                  <td style={tdStyle}><DeltaCell value={c.delta_1} /></td>
                  <td style={tdStyle}><DeltaCell value={c.delta_2} /></td>
                  <td style={tdStyle}><DeltaCell value={c.delta_3} /></td>
                  <td style={tdStyle}><DeltaCell value={c.delta_4} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Strong Long -taulukko */}
      <div style={{ ...card, marginBottom: '24px', borderColor: data.strong_long.length > 0 ? '#007A5C40' : '#1e293b' }}>
        <h2 style={{ ...cardH, color: COLORS.long }}>
          ▲ Long ({data.strong_long.length})
          {data.strong_long.filter(p => p.confirmed).length > 0 && (
            <span style={{ fontSize: '0.8rem', color: '#00C87A', marginLeft: '8px' }}>
              ({data.strong_long.filter(p => p.confirmed).length} confirmed)
            </span>
          )}
        </h2>
        {data.strong_long.length === 0 ? (
          <div style={emptyStyle}>Ei Long-pareja tällä viikolla (index &gt; kynnys)</div>
        ) : (
          <PairTable pairs={data.strong_long} type="long" threshold={threshold} />
        )}
      </div>

      {/* Strong Short -taulukko */}
      <div style={{ ...card, borderColor: data.strong_short.length > 0 ? '#A81B3040' : '#1e293b' }}>
        <h2 style={{ ...cardH, color: COLORS.short }}>
          ▼ Short ({data.strong_short.length})
          {data.strong_short.filter(p => p.confirmed).length > 0 && (
            <span style={{ fontSize: '0.8rem', color: '#FF4D6A', marginLeft: '8px' }}>
              ({data.strong_short.filter(p => p.confirmed).length} confirmed)
            </span>
          )}
        </h2>
        {data.strong_short.length === 0 ? (
          <div style={emptyStyle}>Ei Short-pareja tällä viikolla (index &lt; −kynnys)</div>
        ) : (
          <PairTable pairs={data.strong_short} type="short" threshold={threshold} />
        )}
      </div>

      {/* Metodologia ja tulkintaohje */}
      <MethodologySection threshold={threshold} />
    </div>
  )
}

function MethodologySection({ threshold }) {
  const [open, setOpen] = useState(true)

  return (
    <div style={{ ...card, marginTop: '24px' }}>
      <h2
        onClick={() => setOpen(o => !o)}
        style={{ ...cardH, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px', userSelect: 'none' }}
      >
        <span style={{ transition: 'transform 0.2s', transform: open ? 'rotate(90deg)' : 'rotate(0deg)', display: 'inline-block' }}>▶</span>
        Laskennan kuvaus ja tulkintaohje
      </h2>

      {open && (
        <div style={{ color: '#94a3b8', fontSize: '0.88rem', lineHeight: 1.8 }}>

          {/* Yleiskuvaus */}
          <MSection title="Yleiskuvaus">
            <p>
              COT Bias Dashboard tuottaa viikoittaisen suosituksen 28 valuuttaparille CFTC:n julkaiseman
              Commitments of Traders -raportin perusteella. Analyysi kohdistuu <strong>Leveraged Funds</strong> -luokkaan
              (institutionaaliset spekulatiiviset toimijat), joiden positioinnin muutokset heijastavat markkinasentimentin
              suuntaa.
            </p>
            <p style={{ marginTop: '8px' }}>
              Raportti julkaistaan perjantaisin ja kuvaa <strong>tiistain</strong> positionointitilannetta. Data on siis
              aina 3–5 päivää vanhaa — tämä on COT-analyysin perusrajoite.
            </p>
          </MSection>

          {/* Sarakkeiden selitykset */}
          <MSection title="Sarakkeiden selitykset">
            <DefTable rows={[
              ['Net % LF', 'Leveraged Funds -nettopositio suhteessa heidän avoimeen intressiinsä. Kaava: (Long − Short) / (Long + Short) × 100. Arvo vaihtelee välillä −100 %...+100 %. Positiivinen = instituutiot ovat netto-ostajia, negatiivinen = netto-myyjiä.'],
              ['Δ1 (1vk)', 'Net % LF:n muutos 1 viikossa. Kertoo tuoreimman positioning-muutoksen suunnan ja voimakkuuden. Tämä on bias-suosituksen avainmuuttuja.'],
              ['Δ2–Δ4', 'Net % LF:n muutos 2, 3 ja 4 viikossa. Näistä näet, onko muutos tuore (vain Δ1 liikkuu) vai osa pidempää trendiä (kaikki deltat samansuuntaisia). "—" tarkoittaa, ettei riittävästi historiaa ole saatavilla.'],
              ['Strength Index', `Kahden valuutan suhteellinen voimakkuus: (Net%LF_A − Net%LF_B) / 2. Asteikko −50…+50. Positiivinen arvo = A vahvempi kuin B. Nykyinen kynnysarvo on ±${threshold}.`],
              ['STRONG LONG', `Korostettu signaali: Strength Index > +${threshold}, JA base-valuutan Δ1 > 0 (vahvistuu), JA quote-valuutan Δ1 < 0 (heikkenee). Kaikki kolme ehtoa täyttyvät samanaikaisesti.`],
              ['STRONG SHORT', `Korostettu signaali: Strength Index < −${threshold}, JA base-valuutan Δ1 < 0 (heikkenee), JA quote-valuutan Δ1 > 0 (vahvistuu). Kaikki kolme ehtoa täyttyvät samanaikaisesti.`],
              ['LONG / SHORT', `Parin Strength Index ylittää kynnyksen (±${threshold}), mutta vähintään yksi delta-ehto ei täyty. Pari näytetään himmenettynä taulukossa. Positioning-ero on olemassa, mutta viikkoliike ei vahvista suuntaa.`],
            ]} />
          </MSection>

          {/* Värikoodit */}
          <MSection title="Värikoodit">
            <DefTable rows={[
              ['🟢 Vihreä arvo', 'Positiivinen Net % LF tai positiivinen delta (▲). Valuutan positioning vahvistuu.'],
              ['🔴 Punainen arvo', 'Negatiivinen Net % LF tai negatiivinen delta (▼). Valuutan positioning heikkenee.'],
              ['Korostettu rivi', 'STRONG-signaali: sekä positioning-ero että viikkomuutossuunnat tukevat biasia. Rivi on täydellä opaciteetilla ja taustavärillä.'],
              ['Himmennetty rivi', 'Pelkkä positioning-ero ylittää kynnyksen, mutta deltat eivät vahvista suuntaa. Matala opacity ja harmaa badge.'],
            ]} />
          </MSection>

          {/* Tulkintaohje */}
          <MSection title="Miten tulkitsen tuloksia?">
            <GuideItem
              title="1. Aloita STRONG-signaaleista"
              text="Korostetut rivit ovat vahvimmat tilanteet: suuri positioning-ero JA tuore viikkomuutos tukee suuntaa. Nämä ovat ensisijaisia bias-kandidaatteja."
            />
            <GuideItem
              title="2. Tarkista valuuttayhteenveto"
              text="Katso yläosan valuuttataulukosta, mitkä valuutat ovat selkeästi nettopositiivisia (+) ja mitkä negatiivisia (−). Vahvin bias syntyy, kun yhdistät vahvan valuutan (iso positiivinen Net%LF) heikkoa vastaan (iso negatiivinen Net%LF)."
            />
            <GuideItem
              title="3. Arvioi deltat kokonaisuutena"
              text="Jos kaikki deltat (Δ1–Δ4) osoittavat samaan suuntaan, kyseessä on vahva, pitkäkestoinen trendi. Jos vain Δ1 on muuttunut, muutos on tuore — se voi olla uuden trendin alku tai yksittäinen viikkohäiriö."
            />
            <GuideItem
              title="4. Himmennetyt rivit ovat odotustilassa"
              text="LONG/SHORT ilman STRONG-korostusta tarkoittaa, että positioning-ero on merkittävä, mutta viimeisin viikkodata ei tue suuntaa. Seuraa näitä — ne voivat muuttua STRONG-signaaleiksi seuraavalla viikolla."
            />
            <GuideItem
              title="5. Muuta kynnysarvoa tarpeen mukaan"
              text={`Oletuskynnys ±${threshold} on konservatiivinen. Alenna kynnystä (esim. ±15) saadaksesi enemmän signaaleja, tai nosta (esim. ±30) nähdäksesi vain kaikkein vahvimmat asetelmat.`}
            />
          </MSection>

          {/* Varoitukset */}
          <MSection title="⚠ Tärkeät rajoitukset">
            <ul style={{ paddingLeft: '20px', lineHeight: 2 }}>
              <li>COT-data on <strong>viiveellinen</strong> — se kuvaa tiistain tilannetta, julkaistaan perjantaina.</li>
              <li>Strength Index mittaa <strong>suhteellista positioning-eroa</strong>, ei absoluuttista hintaennustetta.</li>
              <li>STRONG-signaali ei ole automaattinen kaupankäyntisignaali — se on <strong>bias-suositus</strong>, joka vaatii aina vahvistuksen hintaliikkeestä tai muusta analyysistä.</li>
              <li>Äärimmäinen positioning voi jatkua pitkään ilman trendikäännettä.</li>
              <li>Leveraged Funds -positiointi ei yksinään määritä valuuttakursseja — makrotekijät, keskuspankkipolitiikka ja riskisentimentti vaikuttavat myös.</li>
            </ul>
          </MSection>
        </div>
      )}
    </div>
  )
}

function MSection({ title, children }) {
  return (
    <div style={{ marginBottom: '20px' }}>
      <h3 style={{ color: '#e2e8f0', fontSize: '0.95rem', fontWeight: 700, marginBottom: '8px', paddingBottom: '6px', borderBottom: '1px solid #1e293b' }}>
        {title}
      </h3>
      {children}
    </div>
  )
}

function DefTable({ rows }) {
  return (
    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', marginTop: '6px' }}>
      <tbody>
        {rows.map(([term, desc], i) => (
          <tr key={i}>
            <td style={{ padding: '8px 12px', borderBottom: '1px solid #0f172a', color: '#e2e8f0', fontWeight: 600, whiteSpace: 'nowrap', verticalAlign: 'top', width: '160px' }}>
              {term}
            </td>
            <td style={{ padding: '8px 12px', borderBottom: '1px solid #0f172a', color: '#94a3b8', lineHeight: 1.6 }}>
              {desc}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function GuideItem({ title, text }) {
  return (
    <div style={{ marginBottom: '12px' }}>
      <div style={{ color: '#60a5fa', fontWeight: 600, fontSize: '0.88rem', marginBottom: '2px' }}>{title}</div>
      <div style={{ color: '#94a3b8', fontSize: '0.85rem', lineHeight: 1.6, paddingLeft: '4px' }}>{text}</div>
    </div>
  )
}

function PairTable({ pairs, type, threshold }) {
  const signalColor = type === 'long' ? COLORS.long : COLORS.short
  const signalLabel = type === 'long' ? 'LONG' : 'SHORT'

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={tableStyle}>
        <thead>
          <tr>
            <th style={thStyle}>Valuuttapari</th>
            <th style={{ ...thStyle, minWidth: '200px' }}>Strength Index</th>
            <th style={thStyle}>Net%LF (A)</th>
            <th style={thStyle}>Net%LF (B)</th>
            <th style={thStyle}>Δ1 A / B</th>
            <th style={thStyle}>Δ2 A / B</th>
            <th style={thStyle}>Δ3 A / B</th>
            <th style={thStyle}>Δ4 A / B</th>
          </tr>
        </thead>
        <tbody>
          {pairs.map(p => {
            const confirmed = p.confirmed
            const rowBg = confirmed
              ? (type === 'long' ? 'rgba(0,122,92,0.12)' : 'rgba(168,27,48,0.12)')
              : 'transparent'
            const rowBorder = confirmed
              ? (type === 'long' ? '1px solid rgba(0,122,92,0.25)' : '1px solid rgba(168,27,48,0.25)')
              : undefined
            const dimOpacity = confirmed ? 1 : 0.55

            return (
            <tr key={p.pair} style={{ background: rowBg, borderLeft: rowBorder, opacity: dimOpacity }}>
              <td style={tdStyle}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontWeight: 700, fontSize: '0.95rem', color: '#e2e8f0' }}>
                    {p.pair}
                  </span>
                  {confirmed ? (
                    <span style={{
                      fontSize: '0.65rem', fontWeight: 700, padding: '2px 6px',
                      borderRadius: '3px', background: `${signalColor}30`, color: signalColor,
                      letterSpacing: '0.05em', border: `1px solid ${signalColor}`,
                    }}>
                      STRONG {signalLabel}
                    </span>
                  ) : (
                    <span style={{
                      fontSize: '0.65rem', fontWeight: 600, padding: '2px 6px',
                      borderRadius: '3px', background: '#1e293b', color: '#64748b',
                      letterSpacing: '0.05em',
                    }}>
                      {signalLabel}
                    </span>
                  )}
                </div>
              </td>
              <td style={tdStyle}>
                <StrengthBar value={p.strength_index} threshold={threshold} />
              </td>
              <td style={tdStyle}><NetPctCell value={p.net_pct_lf_base} /></td>
              <td style={tdStyle}><NetPctCell value={p.net_pct_lf_quote} /></td>
              <td style={tdStyle}>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <DeltaCell value={p.delta_1_base} />
                  <span style={{ color: '#334155' }}>/</span>
                  <DeltaCell value={p.delta_1_quote} />
                </div>
              </td>
              <td style={tdStyle}>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <DeltaCell value={p.delta_2_base} />
                  <span style={{ color: '#334155' }}>/</span>
                  <DeltaCell value={p.delta_2_quote} />
                </div>
              </td>
              <td style={tdStyle}>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <DeltaCell value={p.delta_3_base} />
                  <span style={{ color: '#334155' }}>/</span>
                  <DeltaCell value={p.delta_3_quote} />
                </div>
              </td>
              <td style={tdStyle}>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <DeltaCell value={p.delta_4_base} />
                  <span style={{ color: '#334155' }}>/</span>
                  <DeltaCell value={p.delta_4_quote} />
                </div>
              </td>
            </tr>
          )})}
        </tbody>
      </table>
    </div>
  )
}

function InfoBadge({ label, value, color = '#60a5fa' }) {
  return (
    <div style={{
      padding: '8px 14px', borderRadius: '8px',
      background: '#0f172a', border: '1px solid #1e293b',
      display: 'flex', alignItems: 'center', gap: '8px',
    }}>
      <span style={{ color: '#64748b', fontSize: '0.78rem' }}>{label}:</span>
      <span style={{ color, fontWeight: 700, fontSize: '0.9rem' }}>{value}</span>
    </div>
  )
}

// Tyylit
const h1 = { fontSize: '1.5rem', fontWeight: 700, color: '#f1f5f9' }
const card = { background: '#0f172a', borderRadius: '12px', border: '1px solid #1e293b', padding: '20px' }
const cardH = { color: '#e2e8f0', fontSize: '1rem', fontWeight: 700, marginBottom: '16px' }
const labelStyle = { color: '#94a3b8', fontSize: '0.85rem' }
const selectStyle = { background: '#1e293b', color: '#e2e8f0', border: '1px solid #334155', padding: '6px 12px', borderRadius: '6px', fontSize: '0.85rem', cursor: 'pointer' }
const tableStyle = { width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }
const thStyle = { padding: '10px 12px', textAlign: 'left', color: '#64748b', fontWeight: 600, borderBottom: '1px solid #1e293b', whiteSpace: 'nowrap', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }
const tdStyle = { padding: '10px 12px', borderBottom: '1px solid #0f172a', color: '#cbd5e1', verticalAlign: 'middle' }
const loadingStyle = { textAlign: 'center', padding: '64px', color: '#64748b' }
const errorStyle = { textAlign: 'center', padding: '64px', color: '#ef4444' }
const emptyStyle = { textAlign: 'center', padding: '32px', color: '#475569', fontSize: '0.9rem' }
