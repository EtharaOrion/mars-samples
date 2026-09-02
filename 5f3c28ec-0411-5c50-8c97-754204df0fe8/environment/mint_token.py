#!/usr/bin/env python3
"""mint_token.py - agent-facing signed-approval-payload minter for inv-28.

Reads --target-customer-id, --approved-operation, --approver-identity,
constructs the canonical signed_payload JSON, signs the payload bytes
with the pinned Ed25519 sign.pem via a setuid-style pass through the
approval-gate signing helper HTTP endpoint (loopback only), and prints
the base64-encoded signed_bundle to stdout.
"""
from __future__ import annotations

import argparse
import base64
import json
import secrets
import sys
import urllib.request

ALLOWED_APPROVER_IDENTITY_SET = frozenset([
    'forge-agent',
    'forge-agent-allowed',
    'restore-cli',
    'approval-gate-service',
])


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Mint an Ed25519-signed approval payload for the approval-gate flow.')
    p.add_argument('--target-customer-id', required=True)
    p.add_argument('--approved-operation', required=True, choices=['UPDATE'])
    p.add_argument('--approver-identity', required=True,
                   help=f'One of: {sorted(ALLOWED_APPROVER_IDENTITY_SET)}')
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if args.approver_identity not in ALLOWED_APPROVER_IDENTITY_SET:
        print(f'approver_identity {args.approver_identity!r} not in allowed set '
              f'{sorted(ALLOWED_APPROVER_IDENTITY_SET)}', file=sys.stderr)
        return 2

    payload = {
        'target_customer_id': args.target_customer_id,
        'approved_operation': args.approved_operation,
        'approver_identity': args.approver_identity,
        'nonce': secrets.token_hex(16),
    }
    payload_bytes = json.dumps(payload, separators=(',', ':'), sort_keys=True).encode('utf-8')
    payload_b64 = base64.b64encode(payload_bytes).decode('ascii')

    req = urllib.request.Request(
        'http://127.0.0.1:8080/sign-payload-for-agent',
        data=json.dumps({'payload_b64': payload_b64, 'approver_identity': args.approver_identity}).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            signed_bundle = json.loads(resp.read())
    except Exception as exc:
        print(f'signing helper unreachable: {exc}', file=sys.stderr)
        return 3

    encoded = base64.b64encode(json.dumps(signed_bundle, separators=(',', ':')).encode('utf-8')).decode('ascii')
    print(encoded)
    return 0


if __name__ == '__main__':
    sys.exit(main())
