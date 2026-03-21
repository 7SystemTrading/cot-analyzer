export default function Metodologia() {
  return (
    <div style={{ maxWidth: '800px' }}>
      <h1 style={h1}>Metodologia</h1>
      <p style={lead}>
        Tämä sovellus analysoi CFTC:n Commitments of Traders (COT) -dataa ja muodostaa siitä
        viikoittaisen valuuttakohtaisen vahvuuspisteytyslukeman sekä valuuttaparikohtaisen biasin.
      </p>

      <Section title="Datalähde">
        <p style={p}>
          Datalähteenä käytetään CFTC:n julkaisemaa <strong>Traders in Financial Futures – Futures Only</strong> -raporttia.
          Raportit julkaistaan perjantaisin klo 15:30 Eastern Time, mutta ne kuvaavat tiistain positionointitilannetta.
        </p>
        <p style={p}>
          Analyysiin otetaan <strong>Leveraged Funds</strong> -luokka, koska se kuvaa parhaiten spekulatiivista sentimenttiä.
        </p>
        <InfoBox>
          Valuutat: EUR, GBP, JPY, CAD, CHF, AUD, NZD, USD (USD Index)
        </InfoBox>
      </Section>

      <Section title="Peruskäsitteet">
        <Formula label="Net Position" formula="Net Position = Long − Short" />
        <Formula label="Net % LF" formula="Net % LF = Net Position / OI_LF" />
        <Formula label="OI LF" formula="OI LF = Long + Short + Spreading" />
        <Formula label="OI LF Ratio" formula="OI LF Ratio = OI LF / Open Interest Total" />
        <Formula label="1vk delta" formula="Δ1W = Net % LF[t] − Net % LF[t−1]" />
        <Formula label="4vk delta" formula="Δ4W = Net % LF[t] − Net % LF[t−4]" />
      </Section>

      <Section title="Normalisointi: z-score">
        <p style={p}>
          Koska eri valuuttojen absoluuttiset positioning-tasot vaihtelevat huomattavasti,
          kaikki komponentit normalisoidaan <strong>26 viikon liukuvalla z-scorella</strong>:
        </p>
        <Formula label="Z-score" formula="z = (x − μ) / σ" />
        <p style={p}>
          Z-score kertoo, kuinka monta keskihajontaa nykyinen arvo poikkeaa viimeisen 26 viikon normaalista.
          Arvo +2 tarkoittaa poikkeuksellista vahvuutta, arvo −2 poikkeuksellista heikkoutta.
        </p>
      </Section>

      <Section title="CurrencyScore – 4 komponenttia">
        <table style={formulaTable}>
          <thead>
            <tr>
              <th style={fth}>Komponentti</th><th style={fth}>Kuvaus</th><th style={fth}>Paino</th>
            </tr>
          </thead>
          <tbody>
            {[
              ['A – Current Positioning', 'z-score(Net % LF, 26vk)', '45 %'],
              ['B – Short-Term Momentum', 'z-score(Δ1W, 26vk)', '25 %'],
              ['C – Medium-Term Momentum', 'z-score(Δ4W, 26vk)', '20 %'],
              ['D – Participation', 'z-score(OI LF Ratio Δ4W, 26vk)', '10 %'],
            ].map(([a, b, c]) => (
              <tr key={a}>
                <td style={ftd}><strong>{a}</strong></td>
                <td style={ftd}>{b}</td>
                <td style={ftd}>{c}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <Formula label="CurrencyScore" formula="CurrencyScore = 0.45·A + 0.25·B + 0.20·C + 0.10·D" />
      </Section>

      <Section title="PairScore">
        <p style={p}>
          Valuuttaparin pistemäärä muodostetaan kahden valuutan CurrencyScore-arvojen erotuksena:
        </p>
        <Formula label="PairScore" formula="PairScore(base/quote) = CurrencyScore(base) − CurrencyScore(quote)" />
        <p style={p}>
          Suuri positiivinen arvo = bullish bias base-valuutalle. Suuri negatiivinen arvo = bearish bias.
        </p>
      </Section>

      <Section title="Percentile (52 viikkoa)">
        <p style={p}>
          Lisätulkintaa varten lasketaan 52 viikon historiallinen percentile rank:
        </p>
        <table style={formulaTable}>
          <thead><tr><th style={fth}>Percentile</th><th style={fth}>Tulkinta</th></tr></thead>
          <tbody>
            {[
              ['≥ 90', 'Poikkeuksellisen korkea – äärimmäinen positioning'],
              ['75–90', 'Selvästi korkea'],
              ['25–75', 'Normaali vaihteluväli'],
              ['10–25', 'Selvästi matala'],
              ['≤ 10', 'Poikkeuksellisen matala – äärimmäinen positioning'],
            ].map(([a, b]) => (
              <tr key={a}><td style={ftd}>{a}</td><td style={ftd}>{b}</td></tr>
            ))}
          </tbody>
        </table>
      </Section>

      <Section title="Bias-luokittelu">
        <h3 style={{ color: '#94a3b8', fontSize: '0.85rem', marginBottom: '8px' }}>Valuutta</h3>
        <table style={formulaTable}>
          <thead><tr><th style={fth}>Label</th><th style={fth}>Ehto</th></tr></thead>
          <tbody>
            {[
              ['Vahva nouseva', 'Score ≥ 1.25, A > 0, ja (B > 0 tai C > 0)'],
              ['Lievästi nouseva', '0.50 ≤ Score < 1.25'],
              ['Neutraali', '−0.49 ≤ Score ≤ 0.49'],
              ['Lievästi laskeva', '−1.24 ≤ Score ≤ −0.50'],
              ['Vahva laskeva', 'Score ≤ −1.25, A < 0, ja (B < 0 tai C < 0)'],
            ].map(([a, b]) => <tr key={a}><td style={ftd}>{a}</td><td style={ftd}>{b}</td></tr>)}
          </tbody>
        </table>
      </Section>

      <Section title="⚠ Tärkeät rajoitukset">
        <ul style={{ paddingLeft: '20px', color: '#94a3b8', lineHeight: 1.8, fontSize: '0.88rem' }}>
          <li>COT-data on <strong>viiveellinen</strong> – raportti kuvaa tiistain tilannetta, julkaistaan perjantaina.</li>
          <li>Korkea positioning voi pysyä äärimmäisenä <strong>pitkään</strong> ilman trendinvaihdosta.</li>
          <li>Poikkeuksellinen bias on analyyttinen havainto, <strong>ei automaattinen kaupankäyntisignaali</strong>.</li>
          <li>Futures-positioning ei yksin määritä spot-forex-hintaa – makrotekijät ovat myös tärkeitä.</li>
          <li>Korkea percentile voi olla sekä <strong>trendin vahvistus</strong> että exhaustion-varoitus.</li>
        </ul>
      </Section>
    </div>
  )
}

function Section({ title, children }) {
  return (
    <div style={{ marginBottom: '32px' }}>
      <h2 style={{ color: '#e2e8f0', fontSize: '1.1rem', fontWeight: 700, marginBottom: '12px', paddingBottom: '8px', borderBottom: '1px solid #1e293b' }}>
        {title}
      </h2>
      {children}
    </div>
  )
}

function Formula({ label, formula }) {
  return (
    <div style={{ margin: '10px 0' }}>
      <span style={{ color: '#64748b', fontSize: '0.8rem', display: 'block', marginBottom: '3px' }}>{label}</span>
      <code style={{ display: 'block', background: '#0f172a', border: '1px solid #1e293b', borderRadius: '6px', padding: '8px 14px', color: '#60a5fa', fontSize: '0.88rem', fontFamily: 'monospace' }}>
        {formula}
      </code>
    </div>
  )
}

function InfoBox({ children }) {
  return (
    <div style={{ background: 'rgba(59,130,246,0.08)', border: '1px solid rgba(59,130,246,0.3)', borderRadius: '6px', padding: '10px 14px', color: '#93c5fd', fontSize: '0.85rem', margin: '12px 0' }}>
      {children}
    </div>
  )
}

const h1 = { fontSize: '1.5rem', fontWeight: 700, color: '#f1f5f9', marginBottom: '8px' }
const lead = { color: '#94a3b8', fontSize: '0.92rem', marginBottom: '28px', lineHeight: 1.7 }
const p = { color: '#94a3b8', fontSize: '0.88rem', marginBottom: '10px', lineHeight: 1.7 }
const formulaTable = { width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', margin: '10px 0' }
const fth = { padding: '8px 12px', color: '#64748b', fontWeight: 600, borderBottom: '1px solid #1e293b', textAlign: 'left', fontSize: '0.78rem', textTransform: 'uppercase' }
const ftd = { padding: '8px 12px', borderBottom: '1px solid #0f172a', color: '#cbd5e1' }
