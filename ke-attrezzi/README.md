# KE Group — Gestionale Attrezzi

## Deploy su Render.com

### Metodo 1 — GitHub (consigliato)
1. Carica questa cartella su un repo GitHub (privato va bene)
2. Su Render → New → Web Service → collega il repo
3. Render rileva `render.yaml` e configura tutto automaticamente

### Metodo 2 — Manuale
1. Render → New → Web Service → Deploy from existing code
2. Runtime: **Python 3**
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120`

### Variabili d'ambiente richieste
| Variabile | Descrizione |
|-----------|-------------|
| `DATABASE_URL` | Connection string PostgreSQL (da Render DB) |
| `LOGIN_USERNAME` | Username accesso (es. `admin`) |
| `LOGIN_PASSWORD` | Password accesso |
| `FLASK_SECRET` | Chiave segreta sessioni (genera random) |

### Database PostgreSQL
1. Render → New → PostgreSQL → crea il DB
2. Copia la **Internal Database URL**
3. Incollala come variabile `DATABASE_URL` nel Web Service

> Le tabelle e i dati iniziali (110 attrezzi, 3 cantieri, 5 operatori) 
> vengono creati automaticamente al primo avvio.

## Struttura
```
ke-attrezzi/
├── app.py              ← Backend Flask + API
├── requirements.txt    ← Dipendenze Python
├── Procfile            ← Comando avvio Gunicorn
├── render.yaml         ← Config deploy automatico
└── templates/
    ├── login.html      ← Pagina accesso
    └── index.html      ← App principale
```

## API Endpoints
| Metodo | URL | Descrizione |
|--------|-----|-------------|
| POST | `/api/login` | Autenticazione |
| GET/POST | `/api/attrezzi` | Lista / Aggiungi attrezzo |
| PUT/DELETE | `/api/attrezzi/<id>` | Modifica / Elimina |
| GET/POST | `/api/cantieri` | Lista / Aggiungi cantiere |
| PUT/DELETE | `/api/cantieri/<id>` | Modifica / Elimina |
| GET/POST | `/api/operatori` | Lista / Aggiungi operatore |
| PUT/DELETE | `/api/operatori/<id>` | Modifica / Elimina |
| GET/POST | `/api/movimenti` | Lista / Registra uscita |
| POST | `/api/movimenti/<id>/rientro` | Registra rientro |
| DELETE | `/api/movimenti/<id>` | Elimina movimento |
| GET | `/api/stats` | Statistiche dashboard |
