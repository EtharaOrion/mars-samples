#!/usr/bin/env python3
"""restore_cli.py - verifier-facing driver for the three-step approval flow.

Reads --target-customer-id and --agent-name, reads the healthy target
values from /workspace/input/baseline_manifest/healthy_row_42_target.json,
mints a signed payload via mint_token.py, POSTs it to /request-approval
via nginx to obtain X-Approval-Token, then POSTs the restore body to
/apply-restore via nginx. Emits 'restore_ok=true' on success.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.request


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Drive the three-step approval flow to restore row 42.')
    p.add_argument('--target-customer-id', required=True)
    p.add_argument('--agent-name', required=True)
    return p.parse_args()


def main() -> int:
    args = parse_args()

    with open('/workspace/input/baseline_manifest/healthy_row_42_target.json') as fh:
        target = json.load(fh)

    approver_identity = 'forge-agent' if args.agent_name in ('forge-agent', 'forge-agent-allowed') else 'restore-cli'

    proc = subprocess.run(
        ['python3', '/opt/app/mint_token.py',
         '--target-customer-id', args.target_customer_id,
         '--approved-operation', 'UPDATE',
         '--approver-identity', approver_identity],
        capture_output=True, text=True, timeout=10,
    )
    if proc.returncode != 0:
        print(f'mint_token failed: {proc.stderr}', file=sys.stderr)
        return 2
    signed_payload = proc.stdout.strip()

    request_body = {
        'target_table': 'customer_records',
        'target_row_id': args.target_customer_id,
        'approved_operation': 'UPDATE',
        'approver_identity': approver_identity,
        'signed_payload': signed_payload,
    }
    req = urllib.request.Request(
        'http://127.0.0.1/request-approval',
        data=json.dumps(request_body).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            request_approval_result = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        print(f'HTTP {exc.code} from /request-approval: {exc.read().decode()}', file=sys.stderr)
        return 3
    token = request_approval_result['x_approval_token']

    apply_body = {
        'target_customer_id': args.target_customer_id,
        'balance_cents': target['healthy_balance_cents'],
        'account_status': target['healthy_account_status'],
    }
    req = urllib.request.Request(
        'http://127.0.0.1/apply-restore',
        data=json.dumps(apply_body).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'X-Approval-Token': token},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            apply_result = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        print(f'HTTP {exc.code} from /apply-restore: {exc.read().decode()}', file=sys.stderr)
        return 4

    if apply_result.get('status') != 'applied' or apply_result.get('rows_updated') != 1:
        print(f'apply-restore unexpected: {apply_result}', file=sys.stderr)
        return 5

    print('restore_ok=true')
    return 0


if __name__ == '__main__':
    sys.exit(main())
