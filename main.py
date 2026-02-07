import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Cookie, Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from itsdangerous import BadSignature, URLSafeSerializer
from passlib.hash import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import engine, get_db
from models import Base, Calculation, User

SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")
serializer = URLSafeSerializer(SECRET_KEY)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if engine is not None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(lifespan=lifespan)

BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


# --- Auth helpers ---


def create_session_cookie(user_id: int) -> str:
    return serializer.dumps(user_id)


def get_user_id_from_cookie(session: str | None) -> int | None:
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
    user_id = get_user_id_from_cookie(session)
    if user_id is None:
        return None
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


# --- Routes ---


@app.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    session: str | None = Cookie(None, alias="session"),
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(session, db)
    return templates.TemplateResponse("index.html", {"request": request, "user": user})


@app.post("/calculate", response_class=HTMLResponse)
async def calculate(
    request: Request,
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

    total_assets = sum(assets.values())
    total_liabilities = sum(liabilities.values())
    net_worth = total_assets - total_liabilities

    user = await get_current_user(session, db)

    # Save to DB if user is logged in
    if user:
        calc = Calculation(
            user_id=user.id,
            assets=assets,
            liabilities=liabilities,
            total_assets=total_assets,
            total_liabilities=total_liabilities,
            net_worth=net_worth,
        )
        db.add(calc)
        await db.commit()

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
            "show_result": True,
            "saved": user is not None,
        },
    )


@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})


@app.post("/signup", response_class=HTMLResponse)
async def signup(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    if password != confirm_password:
        return templates.TemplateResponse(
            "signup.html",
            {"request": request, "error": "Passwords do not match.", "name": name, "email": email},
        )

    if len(password) < 6:
        return templates.TemplateResponse(
            "signup.html",
            {"request": request, "error": "Password must be at least 6 characters.", "name": name, "email": email},
        )

    # Check if email already exists
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        return templates.TemplateResponse(
            "signup.html",
            {"request": request, "error": "An account with this email already exists.", "name": name, "email": email},
        )

    user = User(
        name=name,
        email=email,
        password_hash=bcrypt.hash(password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie("session", create_session_cookie(user.id), httponly=True, samesite="lax")
    return response


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not bcrypt.verify(password, user.password_hash):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid email or password.", "email": email},
        )

    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie("session", create_session_cookie(user.id), httponly=True, samesite="lax")
    return response


@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("session")
    return response


@app.get("/history", response_class=HTMLResponse)
async def history(
    request: Request,
    session: str | None = Cookie(None, alias="session"),
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(session, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    result = await db.execute(
        select(Calculation)
        .where(Calculation.user_id == user.id)
        .order_by(Calculation.created_at.desc())
    )
    calculations = result.scalars().all()

    return templates.TemplateResponse(
        "history.html",
        {"request": request, "user": user, "calculations": calculations},
    )
