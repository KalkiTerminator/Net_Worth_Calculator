# models.py — Defines the structure of our database tables.
#
# KEY CONCEPTS:
# - A "model" is a Python class that represents a table in the database.
#   Each instance of the class = one row in the table.
# - SQLAlchemy ORM maps Python classes to SQL tables automatically.
#   For example: the User class below creates a "users" table with columns
#   for id, name, email, password_hash, and created_at.
# - "Mapped[type]" tells Python and SQLAlchemy what type each column holds.
# - "mapped_column()" defines the column's database properties (type, constraints).
# - "relationship()" creates a link between two tables so you can easily
#   access related data (e.g., user.calculations gives all calculations by that user).

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """
    Base class that all models inherit from.
    SQLAlchemy uses this to keep track of all the tables we define.
    When we call Base.metadata.create_all(), it creates all the tables at once.
    """
    pass


class User(Base):
    """
    Represents a user account in our app.

    Database table: "users"
    Columns:
      - id:            Auto-incrementing unique ID (primary key)
      - name:          The user's display name (up to 100 characters)
      - email:         The user's email (must be unique — no two users share an email)
      - password_hash: The bcrypt-hashed password (we NEVER store plain passwords!)
      - created_at:    Timestamp of when the account was created (set automatically)
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    # unique=True means no duplicate emails; index=True makes email lookups faster
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    # server_default=func.now() tells PostgreSQL to set this to the current time automatically
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # This creates a one-to-many relationship: one user can have many calculations.
    # back_populates="user" links this to the Calculation.user field below.
    calculations: Mapped[list["Calculation"]] = relationship(back_populates="user")


class Calculation(Base):
    """
    Represents a single net worth calculation saved by a user.

    Database table: "calculations"
    Columns:
      - id:                Auto-incrementing unique ID
      - user_id:           Which user made this calculation (foreign key to users.id)
      - assets:            JSON dict of asset names and values, e.g. {"Cash / Savings": 5000}
      - liabilities:       JSON dict of liability names and values
      - total_assets:      Sum of all asset values
      - total_liabilities: Sum of all liability values
      - net_worth:         total_assets - total_liabilities
      - created_at:        When this calculation was made
    """
    __tablename__ = "calculations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # ForeignKey("users.id") means this column references the "id" column in the "users" table.
    # This is how we link each calculation to the user who made it.
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    # JSON columns store Python dicts directly in the database — very handy!
    assets: Mapped[dict] = mapped_column(JSON)
    liabilities: Mapped[dict] = mapped_column(JSON)
    total_assets: Mapped[float] = mapped_column(Float)
    total_liabilities: Mapped[float] = mapped_column(Float)
    net_worth: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Links back to the User model — calc.user gives the User who made this calculation
    user: Mapped["User"] = relationship(back_populates="calculations")
