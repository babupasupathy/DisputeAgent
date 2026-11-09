"""FastAPI mock of the store backend and the processor dispute API.

    uvicorn src.backend.api:app --reload
"""
from __future__ import annotations

from contextlib import contextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.backend import repository as repo
from src.backend.db import connect

app = FastAPI(title="Dispute Agent mock backend (synthetic data)")


@contextmanager
def db():
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def _call(fn, *args, **kw):
    with db() as conn:
        try:
            return fn(conn, *args, **kw)
        except repo.NotFound as e:
            raise HTTPException(404, str(e))
        except PermissionError as e:
            raise HTTPException(403, str(e))


@app.get("/orders/{order_id}")
def order(order_id: str):
    return _call(repo.get_order_details, order_id)


@app.get("/orders/{order_id}/tracking")
def tracking(order_id: str):
    return _call(repo.get_shipping_tracking, order_id)


@app.get("/orders/{order_id}/communications")
def comms(order_id: str):
    return _call(repo.get_support_communications, order_id)


@app.get("/orders/{order_id}/refunds")
def refunds(order_id: str):
    return _call(repo.get_refund_status, order_id)


@app.get("/customers/{customer_id}/history")
def customer(customer_id: str):
    return _call(repo.get_customer_history, customer_id)


@app.get("/processor/disputes/{dispute_id}")
def dispute(dispute_id: str):
    return _call(repo.get_dispute_details, dispute_id)


@app.get("/processor/disputes/{dispute_id}/deadline")
def deadline(dispute_id: str):
    return _call(repo.check_deadline, dispute_id)


class Escalation(BaseModel):
    summary: str
    reason: str


@app.post("/processor/disputes/{dispute_id}/escalate")
def escalate(dispute_id: str, body: Escalation):
    return _call(repo.escalate_to_human, dispute_id, body.summary, body.reason)


class Submission(BaseModel):
    payload: dict
    approved_by: str | None = None


@app.post("/processor/disputes/{dispute_id}/submit")
def submit(dispute_id: str, body: Submission):
    return _call(repo.submit_response, dispute_id, body.payload, approved_by=body.approved_by)
