# Net Worth Calculator

A web app that calculates your net worth (Assets - Liabilities) with user accounts and calculation history.

**Live:** [net-worth-calculator.onrender.com](https://net-worth-calculator.onrender.com)

## Features

- Calculate net worth from assets and liabilities
- User signup/login with secure password hashing (bcrypt)
- Calculation history saved to PostgreSQL
- Clean, responsive UI that works on mobile
- Color-coded results (green = positive, red = negative)

## Tech Stack

- **Backend:** Python, FastAPI
- **Frontend:** HTML, CSS, Jinja2 templates
- **Database:** PostgreSQL (async via SQLAlchemy + asyncpg)
- **Auth:** Session cookies (itsdangerous) + bcrypt
- **Deployment:** Render

## Project Structure

```
├── main.py              # FastAPI app — routes and auth logic
├── database.py          # Database connection setup
├── models.py            # User and Calculation database models
├── templates/
│   ├── base.html        # Shared layout with nav bar
│   ├── index.html       # Calculator page
│   ├── signup.html      # Signup form
│   ├── login.html       # Login form
│   └── history.html     # Calculation history
├── static/
│   └── style.css        # Styling
├── requirements.txt     # Python dependencies
├── render.yaml          # Render deployment config
└── pyproject.toml       # Project metadata (uv)
```

## Run Locally

1. **Clone the repo:**
   ```bash
   git clone git@github.com:KalkiTerminator/Net_Worth_Calculator.git
   cd Net_Worth_Calculator
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   ```

3. **Set environment variables:**
   ```bash
   export DATABASE_URL="postgresql://user:pass@localhost:5432/networth"
   export SECRET_KEY="any-random-string"
   ```

4. **Run the app:**
   ```bash
   uv run uvicorn main:app --reload
   ```

5. **Open** [http://localhost:8000](http://localhost:8000)

## Deploy on Render

1. Push code to GitHub
2. On Render, create a **PostgreSQL** database (free tier)
3. Create a **Web Service** connected to your repo
4. Add environment variables:
   - `DATABASE_URL` — Internal Database URL from your Render PostgreSQL
   - `SECRET_KEY` — any random string
5. Set start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Deploy!
