"""FastAPI approval-gate service for inv-28.

Exposes /health, /request-approval, /apply, /verify-token-edge.
Ed25519 signature verification via python3-cryptography.
change_approvals row insertion via psycopg2.
"""
from __future__ import annotations

import base64
import hashlib
import json
import secrets
import sys
from typing import Any

import psycopg2
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

sys.path.insert(0, '/etc/approval_gate')
import config as cfg  # type: ignore

app = FastAPI()

with open(cfg.VERIFY_KEY_PATH, 'rb') as _fh:
    VERIFY_KEY = load_pem_public_key(_fh.read())
with open(cfg.SIGN_KEY_PATH, 'rb') as _fh:
    SIGN_KEY = load_pem_private_key(_fh.read(), password=None)

_ACTIVE_TOKENS: dict[str, dict[str, Any]] = {}


def _connect() -> psycopg2.extensions.connection:
    return psycopg2.connect(cfg.PRODUCTION_DSN)


def _mint_token() -> str:
    return secrets.token_urlsafe(32)


def _token_digest(token: str) -> str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


@app.get('/health')
def health() -> JSONResponse:
    return JSONResponse({'status': 'ok'})


@app.post('/sign-payload-for-agent')
async def sign_payload_for_agent(req: Request) -> JSONResponse:
    body = await req.json()
    approver_identity = body.get('approver_identity')
    payload_b64 = body.get('payload_b64')
    if approver_identity not in cfg.ALLOWED_APPROVER_IDENTITY_SET:
        raise HTTPException(status_code=403, detail='approver_identity not in allowed set')
    payload_bytes = base64.b64decode(payload_b64)
    signature = SIGN_KEY.sign(payload_bytes)
    return JSONResponse({
        'payload': payload_b64,
        'signature': base64.b64encode(signature).decode('ascii'),
    })


@app.get('/verify-token-edge')
def verify_token_edge(
    x_approval_token: str | None = Header(default=None),
    x_original_uri: str | None = Header(default=None),
) -> JSONResponse:
    if x_original_uri and x_original_uri.rstrip('/').endswith('/request-approval'):
        return JSONResponse({'ok': True})
    if not x_approval_token:
        raise HTTPException(status_code=403, detail='missing X-Approval-Token')
    entry = _ACTIVE_TOKENS.get(x_approval_token)
    if not entry:
        raise HTTPException(status_code=403, detail='unknown or expired token')
    return JSONResponse({'ok': True})


@app.post('/request-approval')
async def request_approval(req: Request) -> JSONResponse:
    body = await req.json()
    signed_payload_b64 = body.get('signed_payload')
    approver_identity = body.get('approver_identity')
    target_table = body.get('target_table')
    target_row_id = body.get('target_row_id')
    approved_operation = body.get('approved_operation')

    if approver_identity not in cfg.ALLOWED_APPROVER_IDENTITY_SET:
        raise HTTPException(status_code=403, detail='approver_identity not in allowed set')
    if target_table != cfg.CUSTOMER_RECORDS_TABLE:
        raise HTTPException(status_code=400, detail='unsupported target_table')

    signed_bundle = json.loads(base64.b64decode(signed_payload_b64))
    payload_b64 = signed_bundle['payload']
    signature_b64 = signed_bundle['signature']
    payload_bytes = base64.b64decode(payload_b64)
    signature_bytes = base64.b64decode(signature_b64)
    try:
        VERIFY_KEY.verify(signature_bytes, payload_bytes)
    except InvalidSignature:
        raise HTTPException(status_code=403, detail='signature_verification_failed')

    payload = json.loads(payload_bytes.decode('utf-8'))
    if payload.get('target_customer_id') != target_row_id:
        raise HTTPException(status_code=400, detail='target_row_id mismatch')
    if payload.get('approver_identity') != approver_identity:
        raise HTTPException(status_code=400, detail='approver_identity mismatch')
    if payload.get('approved_operation') != approved_operation:
        raise HTTPException(status_code=400, detail='approved_operation mismatch')

    token = _mint_token()
    conn = _connect()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                'INSERT INTO change_approvals '
                '(approval_id, approval_token_digest, target_table, target_row_id, '
                ' approved_operation, approver_identity, signed_payload_bytes, approval_signature) '
                'VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s)',
                (_token_digest(token), target_table, target_row_id,
                 approved_operation, approver_identity, payload_bytes, signature_bytes),
            )
    finally:
        conn.close()

    _ACTIVE_TOKENS[token] = {
        'target_row_id': target_row_id,
        'approved_operation': approved_operation,
        'approver_identity': approver_identity,
    }
    return JSONResponse({'x_approval_token': token, 'approval_token_digest': _token_digest(token)})


@app.post('/apply')
async def apply_change(req: Request, x_approval_token: str | None = Header(default=None)) -> JSONResponse:
    if not x_approval_token or x_approval_token not in _ACTIVE_TOKENS:
        raise HTTPException(status_code=403, detail='invalid or missing X-Approval-Token')
    entry = _ACTIVE_TOKENS[x_approval_token]

    body = await req.json()
    target_customer_id = body.get('target_customer_id')
    balance_cents = body.get('balance_cents')
    account_status = body.get('account_status')

    if entry['target_row_id'] != target_customer_id:
        raise HTTPException(status_code=400, detail='apply target_row_id mismatch')

    conn = _connect()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                'UPDATE customer_records SET balance_cents = %s, account_status = %s, '
                'updated_at = now(), updated_by = %s WHERE customer_id = %s',
                (balance_cents, account_status, entry['approver_identity'], target_customer_id),
            )
            rowcount = cur.rowcount
    finally:
        conn.close()

    if rowcount != 1:
        raise HTTPException(status_code=500, detail=f'apply UPDATE affected {rowcount} rows, expected 1')

    return JSONResponse({'status': 'applied', 'rows_updated': rowcount})
