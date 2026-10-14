#!/usr/bin/env python3
"""
ToolCrib RSA & Ed25519 License Generator (Python Replacement for C# LicenseGenerator.cs)
Usage:
    python generate_license.py --generate-keys
    python generate_license.py --request machine_request.txt --id QM-10001 --product "Quotation Modal" --days 365
"""

import os
import sys
import json
import argparse
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PRIVATE_KEY_PEM = os.path.join(BASE_DIR, "private_key.pem")
PUBLIC_KEY_PEM = os.path.join(BASE_DIR, "public_key.pem")


def generate_rsa_keys(key_size: int = 3072) -> Tuple[str, str]:
    """Generate RSA 3072-bit private and public key pair in PEM format."""
    print("\n==========================================")
    print("       GENERATING RSA 3072-BIT KEYS       ")
    print("==========================================")
    
    if os.path.exists(PRIVATE_KEY_PEM) or os.path.exists(PUBLIC_KEY_PEM):
        print("[WARNING] RSA keys already exist in License directory.")
        print(f"Private Key: {PRIVATE_KEY_PEM}")
        print(f"Public Key:  {PUBLIC_KEY_PEM}")
        print("Do NOT regenerate keys unless you intend to replace existing keys.")
        with open(PUBLIC_KEY_PEM, "r", encoding="utf-8") as f:
            pub_pem = f.read()
        with open(PRIVATE_KEY_PEM, "r", encoding="utf-8") as f:
            priv_pem = f.read()
        return priv_pem, pub_pem

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size
    )
    public_key = private_key.public_key()

    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')

    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')

    with open(PRIVATE_KEY_PEM, "w", encoding="utf-8") as f:
        f.write(priv_pem)

    with open(PUBLIC_KEY_PEM, "w", encoding="utf-8") as f:
        f.write(pub_pem)

    # Sync public_key.pem to backend/ if backend directory exists
    backend_pub = os.path.join(os.path.dirname(BASE_DIR), "backend", "public_key.pem")
    try:
        with open(backend_pub, "w", encoding="utf-8") as f:
            f.write(pub_pem)
        print(f"Synced public_key.pem to backend: {backend_pub}")
    except Exception:
        pass

    print(f"[OK] Private key saved: {PRIVATE_KEY_PEM}")
    print(f"[OK] Public key saved:  {PUBLIC_KEY_PEM}")
    print("\n---------------- PUBLIC KEY ----------------")
    print(pub_pem.strip())
    print("--------------------------------------------\n")
    return priv_pem, pub_pem


def load_private_key() -> rsa.RSAPrivateKey:
    """Load RSA private key from private_key.pem"""
    if not os.path.exists(PRIVATE_KEY_PEM):
        print("Private key not found. Generating new RSA keypair...")
        generate_rsa_keys()

    with open(PRIVATE_KEY_PEM, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def generate_license_from_request(
    machine_request_file: str,
    license_id: str = "QM-10001",
    product: str = "Quotation Modal",
    days: int = 365,
    out_file: str = None
) -> Dict[str, Any]:
    """Generate RSA digital signed license file from a machine request file."""
    if not os.path.exists(machine_request_file):
        raise FileNotFoundError(f"Machine request file not found: {machine_request_file}")

    with open(machine_request_file, "r", encoding="utf-8") as f:
        request_data = json.load(f)

    fingerprint = request_data.get("Fingerprint", "").strip().upper()
    if not fingerprint or len(fingerprint) != 64:
        raise ValueError("Invalid machine fingerprint in request. Must be a 64-char SHA-256 hex string.")

    issued_at = datetime.utcnow()
    expires_at = (issued_at + timedelta(days=days)) if days > 0 else (issued_at + timedelta(days=3650))
    expiry_str = expires_at.isoformat() + "Z"

    # Canonical data string to sign: LicenseId|Fingerprint|Product|Expiry
    data_to_sign = f"{license_id.strip()}|{fingerprint}|{product.strip()}|{expiry_str}"
    data_bytes = data_to_sign.encode("utf-8")

    # RSA PKCS1v15 SHA-256 signature
    priv_key = load_private_key()
    signature_bytes = priv_key.sign(
        data_bytes,
        padding.PKCS1v15(),
        hashes.SHA256()
    )

    import base64
    signature_b64 = base64.b64encode(signature_bytes).decode("utf-8")

    license_dict = {
        "LicenseId": license_id.strip(),
        "Fingerprint": fingerprint,
        "Product": product.strip(),
        "Expiry": expiry_str,
        "Signature": signature_b64
    }

    license_json = json.dumps(license_dict, indent=2)

    if not out_file:
        out_file = os.path.join(BASE_DIR, f"license_{license_id}.json")

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(license_json)

    print("\n==========================================")
    print("    Quotation Modal License Generator     ")
    print("==========================================")
    print(f"License ID:   {license_id}")
    print(f"Product:      {product}")
    print(f"Fingerprint:  {fingerprint}")
    print(f"Validity:     {days if days > 0 else 'Perpetual'} days (Expires: {expiry_str})")
    print("------------------------------------------")
    print(f"Saved License File: {out_file}\n")
    print("LICENSE DATA JSON:")
    print(license_json)
    print("------------------------------------------\n")

    return license_dict


def main():
    parser = argparse.ArgumentParser(description="ToolCrib Python RSA License Generator")
    parser.add_argument("--generate-keys", action="store_true", help="Generate RSA 3072-bit key pair")
    parser.add_argument("--request", type=str, help="Path to machine_request.txt file")
    parser.add_argument("--id", type=str, default="QM-10001", help="License ID (e.g. QM-10001)")
    parser.add_argument("--product", type=str, default="Quotation Modal", help="Product name")
    parser.add_argument("--days", type=int, default=365, help="Validity duration in days (default: 365, 0 for perpetual)")
    parser.add_argument("--out", type=str, help="Output path for license.json file")

    args = parser.parse_args()

    if args.generate_keys or (not args.request and not os.path.exists(PRIVATE_KEY_PEM)):
        generate_rsa_keys()
        if not args.request:
            return

    if args.request:
        generate_license_from_request(
            machine_request_file=args.request,
            license_id=args.id,
            product=args.product,
            days=args.days,
            out_file=args.out
        )
    else:
        print('Usage: python generate_license.py --request machine_request.txt --id QM-10001 --product "Quotation Modal" --days 365')
        print("Use --generate-keys to generate RSA keypair.")


if __name__ == "__main__":
    main()
