from __future__ import annotations

import os
import time
from decimal import Decimal
from typing import Annotated

import psycopg
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from psycopg.rows import dict_row

POSTGRES_DSN = os.getenv("POSTGRES_DSN", "postgresql://app:app@localhost:5432/app")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "local-secret-token")

app = FastAPI(title="Mock E-commerce Order API", version="1.0.0")


class OrderCreate(BaseModel):
    order_id: str = Field(min_length=3)
    customer_email: EmailStr
    amount: Decimal = Field(gt=0)
    status: str = "created"


class StatusUpdate(BaseModel):
    status: str


def get_connection():
    return psycopg.connect(POSTGRES_DSN, row_factory=dict_row)


def require_auth(authorization: Annotated[str | None, Header()] = None) -> None:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    expected = f"Bearer {AUTH_TOKEN}"
    if authorization != expected:
        raise HTTPException(status_code=403, detail="Invalid bearer token")


@app.on_event("startup")
def startup() -> None:
    for _ in range(30):
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        create table if not exists orders (
                            order_id text primary key,
                            customer_email text not null,
                            amount numeric(12,2) not null,
                            status text not null,
                            created_at timestamptz not null default now(),
                            updated_at timestamptz not null default now()
                        )
                        """
                    )
                    cur.execute(
                        """
                        create table if not exists order_audit (
                            id bigserial primary key,
                            order_id text not null references orders(order_id) on delete cascade,
                            event_type text not null,
                            payload jsonb not null default '{}'::jsonb,
                            created_at timestamptz not null default now()
                        )
                        """
                    )
                conn.commit()
            return
        except Exception:
            time.sleep(1)
    raise RuntimeError("Could not initialize database")


@app.get("/health")
def health():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("select 1 as ok")
                cur.fetchone()
        database = "ok"
    except Exception:
        database = "down"
    return {"status": "ok", "database": database}


@app.get("/auth/check")
def auth_check(_: None = Depends(require_auth)):
    return {"authenticated": True}


@app.post("/orders", status_code=201)
def create_order(payload: OrderCreate, _: None = Depends(require_auth)):
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    insert into orders(order_id, customer_email, amount, status)
                    values (%(order_id)s, %(customer_email)s, %(amount)s, %(status)s)
                    """,
                    payload.model_dump(mode="json"),
                )
                cur.execute(
                    """
                    insert into order_audit(order_id, event_type, payload)
                    values (%(order_id)s, 'created', jsonb_build_object('status', %(status)s))
                    """,
                    {"order_id": payload.order_id, "status": payload.status},
                )
            except psycopg.errors.UniqueViolation as exc:
                raise HTTPException(status_code=409, detail="Order already exists") from exc
        conn.commit()
    output = payload.model_dump(mode="json")
    output["amount"] = float(payload.amount)
    return output


@app.get("/orders/{order_id}")
def get_order(order_id: str, _: None = Depends(require_auth)):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "select order_id, customer_email, amount, status from orders where order_id = %(order_id)s",
                {"order_id": order_id},
            )
            row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Order not found")
    row["amount"] = float(row["amount"])
    return row


@app.patch("/orders/{order_id}/status")
def update_status(order_id: str, payload: StatusUpdate, _: None = Depends(require_auth)):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update orders
                set status = %(status)s, updated_at = now()
                where order_id = %(order_id)s
                returning order_id, customer_email, amount, status
                """,
                {"order_id": order_id, "status": payload.status},
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Order not found")
            cur.execute(
                """
                insert into order_audit(order_id, event_type, payload)
                values (%(order_id)s, 'status_changed', jsonb_build_object('status', %(status)s))
                """,
                {"order_id": order_id, "status": payload.status},
            )
        conn.commit()
    row["amount"] = float(row["amount"])
    return row


@app.get("/orders/{order_id}/audit")
def get_audit(order_id: str, _: None = Depends(require_auth)):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select event_type, payload, created_at::text as created_at
                from order_audit
                where order_id = %(order_id)s
                order by id
                """,
                {"order_id": order_id},
            )
            return {"events": cur.fetchall()}


@app.get("/slow")
def slow(seconds: int = Query(default=1, ge=0, le=10)):
    time.sleep(seconds)
    return {"slept_seconds": seconds}
