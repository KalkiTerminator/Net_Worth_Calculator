# main.py — The heart of our app. Contains all the routes (URL endpoints) and logic.
#
# KEY CONCEPTS:
# - FastAPI is a web framework — it listens for HTTP requests (GET, POST) and
#   returns responses (HTML pages, redirects, etc.).
# - A "route" is a function that handles a specific URL. For example,
#   @app.get("/") handles requests to the homepage.
# - GET = reading/viewing a page. POST = submitting data (forms).
# - "async" functions can pause while waiting for slow operations (like database
#   queries) without blocking other users. This is called asynchronous programming.

import os
from contextlib import asynccontextmanager
from pathlib import Path

# FastAPI imports:
# - Cookie: reads cookies from the browser (used for login sessions)
# - Depends: "dependency injection" — automatically provides things routes need (like a DB session)
# - Form: reads form data submitted by HTML forms
# - Request: the incoming HTTP request object
from fastapi import Cookie, Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles  # Serves CSS, images, etc.
from fastapi.templating import Jinja2Templates  # Renders HTML templates
import bcrypt as _bcrypt  # Password hashing library (aliased to avoid name conflicts)
from itsdangerous import BadSignature, URLSafeSerializer  # Signs/verifies session cookies
from sqlalchemy import select  # SQL SELECT query builder
from sqlalchemy.ext.asyncio import AsyncSession

# Import our database connection and models (defined in database.py and models.py)
from database import engine, get_db
from models import Base, Calculation, User

# SECRET_KEY is used to sign session cookies so they can't be tampered with.
# On Render, this is set as an environment variable. The fallback is for local dev only.
SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")
# URLSafeSerializer creates tokens that are safe to store in cookies.
# It uses SECRET_KEY to sign data, so only our server can create valid tokens.
serializer = URLSafeSerializer(SECRET_KEY)


# --- App Startup ---


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs once when the app starts up (before handling any requests).
    We use this to create our database tables if they don't exist yet.

    Base.metadata.create_all looks at all our models (User, Calculation) and
    creates the corresponding tables in PostgreSQL. If the tables already exist,
    it does nothing — safe to run every time.
    """
    if engine is not None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield  # App runs here; after yield would be shutdown cleanup


# Create the FastAPI application with our startup logic
app = FastAPI(lifespan=lifespan)

# Tell FastAPI where to find our static files (CSS) and HTML templates
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


# ============================================================================
# AUTH HELPERS — Functions that handle login sessions
# ============================================================================
# HOW SESSION AUTH WORKS:
# 1. User logs in with email + password
# 2. We create a signed cookie containing their user ID
# 3. Browser sends this cookie with every request automatically
# 4. We read the cookie to know who's logged in
# 5. On logout, we delete the cookie


def create_session_cookie(user_id: int) -> str:
    """
    Creates a signed cookie value containing the user's ID.
    "Signed" means it's cryptographically protected — users can't forge it.
    Example: user_id=5 might become "NQ.sGh7k2..." — looks like gibberish,
    but our server can decode it back to 5.
    """
    return serializer.dumps(user_id)


def get_user_id_from_cookie(session: str | None) -> int | None:
    """
    Reads and verifies the session cookie.
    Returns the user_id if the cookie is valid, or None if it's missing/invalid.
    BadSignature means someone tried to tamper with the cookie — we reject it.
    """
    if not session:
        return None
    try:
        return serializer.loads(session)
    except BadSignature:
        return None


async def get_current_user(
    session: str | None = Cookie(None, alias="session"),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """
    Gets the currently logged-in User object from the database.
    Returns None if not logged in or if the user doesn't exist anymore.

    - Cookie(None, alias="session") reads the cookie named "session" from the browser
    - Depends(get_db) automatically provides a database session
    """
    user_id = get_user_id_from_cookie(session)
    if user_id is None:
        return None
    # SELECT * FROM users WHERE id = user_id
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()  # Returns the User or None


# ============================================================================
# ROUTES — Each function handles a specific URL
# ============================================================================


# ----- Homepage -----

@app.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    session: str | None = Cookie(None, alias="session"),
    db: AsyncSession = Depends(get_db),
):
    """
    GET / — Shows the calculator form.
    We check if the user is logged in so the nav bar can show their name.
    """
    user = await get_current_user(session, db)
    return templates.TemplateResponse("index.html", {"request": request, "user": user})


# ----- Calculator -----

@app.post("/calculate", response_class=HTMLResponse)
async def calculate(
    request: Request,
    # Form(...) reads these values from the HTML form submission.
    # Each parameter name matches the "name" attribute in the <input> tags.
    cash: float = Form(0),
    investments: float = Form(0),
    property_value: float = Form(0),
    vehicles: float = Form(0),
    other_assets: float = Form(0),
    mortgage: float = Form(0),
    student_loans: float = Form(0),
    credit_card: float = Form(0),
    car_loans: float = Form(0),
    other_liabilities: float = Form(0),
    session: str | None = Cookie(None, alias="session"),
    db: AsyncSession = Depends(get_db),
):
    """
    POST /calculate — Receives the form data, calculates net worth,
    saves to database if user is logged in, and shows results.
    """
    # Organize the form values into dictionaries
    assets = {
        "Cash / Savings": cash,
        "Investments": investments,
        "Property": property_value,
        "Vehicles": vehicles,
        "Other Assets": other_assets,
    }
    liabilities = {
        "Mortgage": mortgage,
        "Student Loans": student_loans,
        "Credit Card Debt": credit_card,
        "Car Loans": car_loans,
        "Other Liabilities": other_liabilities,
    }

    # The core calculation: Net Worth = Assets - Liabilities
    total_assets = sum(assets.values())
    total_liabilities = sum(liabilities.values())
    net_worth = total_assets - total_liabilities

    # Check if user is logged in
    user = await get_current_user(session, db)

    # If logged in, save the calculation to the database for history
    if user:
        calc = Calculation(
            user_id=user.id,
            assets=assets,
            liabilities=liabilities,
            total_assets=total_assets,
            total_liabilities=total_liabilities,
            net_worth=net_worth,
        )
        db.add(calc)        # Stage the new row (like git add)
        await db.commit()   # Save to database (like git commit)

    # Render the same page but now with results shown
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "user": user,
            "assets": assets,
            "liabilities": liabilities,
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "net_worth": net_worth,
            "show_result": True,          # Tells the template to show the results section
            "saved": user is not None,    # Shows "Saved to history" if logged in
        },
    )


# ----- Signup -----

@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    """GET /signup — Shows the signup form."""
    return templates.TemplateResponse("signup.html", {"request": request})


@app.post("/signup", response_class=HTMLResponse)
async def signup(
    request: Request,
    # Form(...) means these fields are REQUIRED (... = no default value)
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """
    POST /signup — Creates a new user account.
    Steps: validate input → check for existing email → hash password → save user → log them in
    """
    # Validation: make sure passwords match
    if password != confirm_password:
        return templates.TemplateResponse(
            "signup.html",
            {"request": request, "error": "Passwords do not match.", "name": name, "email": email},
        )

    # Validation: minimum password length
    if len(password) < 6:
        return templates.TemplateResponse(
            "signup.html",
            {"request": request, "error": "Password must be at least 6 characters.", "name": name, "email": email},
        )

    # Check if someone already registered with this email
    # SELECT * FROM users WHERE email = email
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        return templates.TemplateResponse(
            "signup.html",
            {"request": request, "error": "An account with this email already exists.", "name": name, "email": email},
        )

    # Create the user with a HASHED password.
    # bcrypt.hashpw() turns "mypassword" into something like "$2b$12$LJ3m5..."
    # gensalt() generates a random "salt" — this ensures even identical passwords
    # produce different hashes, making them much harder to crack.
    # .encode() converts string to bytes (bcrypt works with bytes)
    # .decode() converts the result back to a string for storage
    user = User(
        name=name,
        email=email,
        password_hash=_bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode(),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)  # Reload from DB to get the auto-generated id

    # Log the user in by setting a session cookie, then redirect to homepage
    # status_code=303 tells the browser to redirect with a GET request (not POST)
    response = RedirectResponse(url="/", status_code=303)
    # httponly=True means JavaScript can't read this cookie (security best practice)
    # samesite="lax" prevents the cookie from being sent in cross-site requests (CSRF protection)
    response.set_cookie("session", create_session_cookie(user.id), httponly=True, samesite="lax")
    return response


# ----- Login -----

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """GET /login — Shows the login form."""
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """
    POST /login — Authenticates the user.
    Steps: find user by email → verify password → set session cookie
    """
    # Look up the user by email
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    # checkpw() compares the plain password against the stored hash.
    # It re-hashes the input with the same salt and checks if the result matches.
    # This way we NEVER need to know or store the actual password.
    if not user or not _bcrypt.checkpw(password.encode(), user.password_hash.encode()):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid email or password.", "email": email},
        )

    # Password correct — log them in with a session cookie
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie("session", create_session_cookie(user.id), httponly=True, samesite="lax")
    return response


# ----- Logout -----

@app.get("/logout")
async def logout():
    """
    GET /logout — Logs the user out by deleting the session cookie.
    The browser removes the cookie, so subsequent requests won't have it.
    """
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("session")
    return response


# ----- Calculation History -----

@app.get("/history", response_class=HTMLResponse)
async def history(
    request: Request,
    session: str | None = Cookie(None, alias="session"),
    db: AsyncSession = Depends(get_db),
):
    """
    GET /history — Shows all past calculations for the logged-in user.
    If not logged in, redirects to the login page.
    """
    user = await get_current_user(session, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    # SELECT * FROM calculations WHERE user_id = user.id ORDER BY created_at DESC
    # .desc() means newest first
    result = await db.execute(
        select(Calculation)
        .where(Calculation.user_id == user.id)
        .order_by(Calculation.created_at.desc())
    )
    calculations = result.scalars().all()  # Convert result to a list of Calculation objects

    return templates.TemplateResponse(
        "history.html",
        {"request": request, "user": user, "calculations": calculations},
    )
