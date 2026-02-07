from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


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

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "assets": assets,
            "liabilities": liabilities,
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "net_worth": net_worth,
            "show_result": True,
        },
    )
