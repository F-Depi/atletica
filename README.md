# AtleticaDB

A web application for browsing Italian national athletics (track and field) rankings, athlete profiles, and society/team data. It covers results from 2005 to the present, sourced from the [FIDAL](https://www.fidal.it/graduatorie.php) (Federazione Italiana di Atletica Leggera) official rankings.

The database powering this application is maintained in a companion project: [database-atletica-italiana](https://github.com/F-Depi/database-atletica-italiana).

---

## Features

- **National Rankings** — Browse and filter Italian athletics rankings by discipline, category, year, gender, region, province, and society. Supports both indoor and outdoor results.
- **Athlete Profiles** — View individual athlete performance histories, personal records, and seasonal bests, with links to official FIDAL profiles.
- **Society/Team Profiles** — Explore team rosters, seasonal performance summaries, and member statistics.
- **Unified Search** — Full-text search for athletes and societies.
- **Wind Data** — Context-aware wind condition display for sprints, hurdles, and horizontal jumps.
- **Error Reporting** — Users can submit data correction reports directly from the interface.
- **Responsive UI** — Mobile-friendly layout with dark/light theme support.

---

## Tech Stack

| Layer      | Technology                                      |
|------------|-------------------------------------------------|
| Backend    | Python · [Flask](https://flask.palletsprojects.com/) |
| Database   | PostgreSQL · SQLAlchemy · psycopg2              |
| Data       | pandas                                          |
| Frontend   | Jinja2 templates · Vanilla JS · Custom CSS      |
| Security   | flask-wtf (CSRF) · flask-limiter (rate limiting)|
| Production | Gunicorn                                        |

---

## Project Structure

```
atletica/
├── app/
│   ├── app.py               # Flask app initialization and main routes
│   ├── models.py            # Database connection and SQLAlchemy models
│   ├── rankings.py          # Rankings page and API
│   ├── atleti.py            # Athlete profile pages
│   ├── societa.py           # Society/team profile pages
│   ├── ricerca.py           # Search functionality
│   ├── error_reporting.py   # Error report submission
│   ├── utils.py             # Shared helper functions
│   ├── data/                # JSON configuration files (disciplines, categories, regions)
│   ├── static/              # CSS, JavaScript, and images
│   └── templates/           # Jinja2 HTML templates
├── run.py                   # Development server entry point
├── requirements.txt         # Python dependencies
├── combine_css.sh           # Script to combine CSS files
└── LICENSE                  # GNU GPLv3
```

---

## Getting Started

### Prerequisites

- Python 3.9+
- PostgreSQL (with a database populated by [database-atletica-italiana](https://github.com/F-Depi/database-atletica-italiana))

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/F-Depi/atletica.git
cd atletica

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

### Configuration

Create a `config.py` file in the project root (it is excluded from version control):

```python
DB_CONFIG = {
    'user': 'your_postgres_user',
    'password': 'your_postgres_password',
    'host': 'localhost',
    'database': 'atletica_db',
}

SECRET_KEY = 'your-secret-key-here'
```

### Running the Application

```bash
# Development (auto-reload enabled)
python run.py

# Production
gunicorn -b 0.0.0.0:8000 app.app:app
```

The application is available at `http://localhost:5000` in development mode.

### Building CSS

The project ships individual CSS modules. To concatenate them into a single file:

```bash
chmod +x combine_css.sh
./combine_css.sh
```

---

## API Reference

### Rankings

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/rankings` | Rankings page (query params: `disciplina`, `categoria`, `sesso`, `anno`, `regione`, `provincia`, `societa`, `ambiente`) |
| `GET` | `/api/disciplines/all` | All available disciplines |
| `GET` | `/api/disciplines/<category>/<gender>` | Disciplines filtered by category and gender |
| `GET` | `/api/discipline_info/<discipline>` | Discipline metadata (wind info, type, classification) |

### Athlete & Society

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/atleta/<path:atleta_path>` | Athlete profile |
| `GET` | `/societa/<cod_societa>` | Society profile |
| `GET` | `/societa/<cod_societa>/seasonal` | Society seasonal performance summary |

### Search & Utilities

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/ricerca/api?q=<query>` | Search athletes and societies (rate-limited: 30 req/min) |
| `GET` | `/get-csrf-token` | Obtain a CSRF token |
| `POST` | `/api/segnala-errore` | Submit a data error report (rate-limited: 5 req/min) |

---

## Database Schema

The application connects to a PostgreSQL database with the following tables.

### `results` — Performance records

| Column | Type | Description |
|--------|------|-------------|
| `id` | integer (PK) | Auto-incremented identifier |
| `atleta` | varchar | Athlete name |
| `prestazione` | double precision | Numeric performance value |
| `vento` | numeric | Wind reading (m/s) |
| `tempo` | varchar | Formatted performance string |
| `cronometraggio` | varchar | Timing method (manual / electronic) |
| `anno` | integer | Season year |
| `categoria` | varchar | Age category |
| `società` | varchar | Society/team name |
| `disciplina` | varchar | Event name |
| `ambiente` | char | `I` = indoor, `P` = outdoor |
| `sesso` | char | `M` = male, `F` = female |
| `data` | date | Date of performance |
| `luogo` | varchar | Location |
| `posizione` | varchar | Finishing position |
| `link_atleta` | varchar | FIDAL athlete profile link |
| `link_società` | varchar | FIDAL society profile link |
| `cod_società` | char | Society code |
| `guess_codice` | ARRAY | Inferred discipline codes |
| `note` | varchar | Additional notes |

### `atleti` — Athlete master data

| Column | Type | Description |
|--------|------|-------------|
| `link_atleta` | text (PK) | Unique FIDAL athlete link |
| `atleta` | text | Athlete name |
| `categoria` | text | Current age category |
| `società` | text | Current society |
| `anno` | integer | Birth year |

### `discipline` — Event definitions

| Column | Type | Description |
|--------|------|-------------|
| `codice` | varchar (PK) | Discipline code (e.g. `03` for 100 m) |
| `disciplina` | varchar | Discipline name |
| `tipo` | varchar | Category type (Corse Piane, Salti, Lanci, Ostacoli, Siepi, Marcia, Prove Multiple) |
| `classifica` | varchar | `tempo` (time) or `distanza` (distance) |
| `vento` | boolean | Whether wind readings apply |
| `categoria` | ARRAY | Applicable age categories |
| `ordine` | integer | Display order |
| `note` | varchar | Additional notes |
| `ultimo_aggiornamento` | timestamp | Last updated |

---

## Roadmap

- [ ] Wind calculation for outdoor combined events (prove multiple)
- [ ] Import all-time record lists provided by FIDAL ([link](https://www.fidal.it/content/Statistiche/25404))
- [ ] Statistics dashboard based on [existing data](https://github.com/F-Depi/database-atletica-italiana/tree/main/statistiche)
- [ ] Direct database query interface
- [ ] Live race results integration ([AtleticaDB-live](https://github.com/F-Depi/AtleticaDB-live))

---

## Related Projects

- [database-atletica-italiana](https://github.com/F-Depi/database-atletica-italiana) — Scripts that collect, clean, and maintain the athletics database.
- [AtleticaDB-live](https://github.com/F-Depi/AtleticaDB-live) — Live race results integration (work in progress).

---

## License

This project is licensed under the [GNU General Public License v3.0](LICENSE).
