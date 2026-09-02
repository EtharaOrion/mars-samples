#!/usr/bin/env python3
"""keyring_bootstrap.py - deterministic Ed25519 keypair derivation.

Derives the approval-gate signing keypair from the Stage-0 pre_canary_hash
via HKDF-SHA256, writes verify.pem (0644, world-readable) and sign.pem
(0600, appgate-only). Copies verify.pem to /etc/nginx/keys/verify.pem too.
"""
from __future__ import annotations

import os
import sys

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

STAGE_0_PRE_CANARY_HASH = '40957312577600f101c323ac43cac55597a805609c1a9b3687ba1176c4a4e302'


def derive_keypair() -> Ed25519PrivateKey:
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=STAGE_0_PRE_CANARY_HASH.encode('utf-8'),
        info=b'ed25519-approval-gate-signing-key-v1',
    )
    seed = hkdf.derive(b'')
    return Ed25519PrivateKey.from_private_bytes(seed)


def main() -> int:
    priv = derive_keypair()
    pub = priv.public_key()

    verify_pem = pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    sign_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    os.makedirs('/etc/approval_gate/keys', exist_ok=True)
    os.makedirs('/etc/nginx/keys', exist_ok=True)

    with open('/etc/approval_gate/keys/verify.pem', 'wb') as fh:
        fh.write(verify_pem)
    os.chmod('/etc/approval_gate/keys/verify.pem', 0o644)

    with open('/etc/approval_gate/keys/sign.pem', 'wb') as fh:
        fh.write(sign_pem)
    os.chmod('/etc/approval_gate/keys/sign.pem', 0o600)

    with open('/etc/nginx/keys/verify.pem', 'wb') as fh:
        fh.write(verify_pem)
    os.chmod('/etc/nginx/keys/verify.pem', 0o644)

    import pwd
    try:
        appgate = pwd.getpwnam('appgate')
        os.chown('/etc/approval_gate/keys/verify.pem', appgate.pw_uid, appgate.pw_gid)
        os.chown('/etc/approval_gate/keys/sign.pem', appgate.pw_uid, appgate.pw_gid)
        os.chown('/etc/nginx/keys/verify.pem', appgate.pw_uid, appgate.pw_gid)
    except KeyError:
        pass

    print('keyring bootstrap complete')
    return 0


if __name__ == '__main__':
    sys.exit(main())
