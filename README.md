# COT Currency Strength Bias Analyzer

Analysoi CFTC:n COT Financial Futures -dataa ja laskee valuuttakohtaiset vahvuuspisteet sekä valuuttaparikohtaisen biasin.

## Käynnistys kehitykseen

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Frontend käynnistyy osoitteessa http://localhost:5173
API-dokumentaatio: http://localhost:8000/docs

## Julkaisu Renderiin

1. Luo tili osoitteessa [render.com](https://render.com)
2. Yhdistä GitHub-repositorio
3. Render tunnistaa `render.yaml`-tiedoston automaattisesti
4. Deploy käynnistyy

## Datan tuonti

1. Avaa sovellus → **Tuo dataa**
2. Klikkaa **"Hae historia"** – sovellus lataa CFTC:ltä automaattisesti vuodesta 2010 alkaen
3. Tai lataa oma CSV/Excel-tiedostosi

## Teknologia

- **Backend**: Python + FastAPI + SQLAlchemy + SQLite
- **Frontend**: React 18 + Vite + Recharts
- **Laskenta**: pandas + numpy + scipy
- **Hosting**: Render (ilmainen tier)
