#!/usr/bin/env python3
"""
ToolCrib Client License Validator & Hardware Fingerprinter (Python Replacement for C# Client.cs)
Usage:
    python client_license.py --request
    python client_license.py --verify license_TC-10001.json
"""

import os
import sys
import json
import uuid
import hashlib
import platform
import subprocess
import argparse
import base64
from datetime import datetime
from functools import lru_cache
from typing import Dict, Any, Tuple, Optional, List

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")

for path_dir in [BASE_DIR, PROJECT_ROOT, BACKEND_DIR]:
    if os.path.exists(path_dir) and path_dir not in sys.path:
        sys.path.insert(0, path_dir)

PUBLIC_KEY_PEM = os.path.join(BASE_DIR, "public_key.pem")

# Fallback Embedded Public Key if public_key.pem is missing
EMBEDDED_PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
MIIBojANBgkqhkiG9w0BAQEFAAOCAY8AMIIBigKCAYEAzFCECCXMeV+zTE1NaNGM
ba9xSfr5wMNELQZQQ6RKudLwnjxYp4yDUbeht+c9DZW9BJin08aaCNZ+1/kPXpa0
WXIF0ogW5IIL32t6IHWa2ydT6I3YVXGdLjusmN0ILT7UZY5UCIRmZylMxY2Y8k9S
J/yPSxaJWScSZIFb6AdoFFcYLx00FQ0QYAecRih/WkZOc4UvOpD7zEbTdlnWK+Bj
MdgUMsUBTfVGph+FG6PXYKLErf8VzqKlGPSInP7BLs6Bz+dlsMiKbeaZCV1itVzy
DFWD7LZ7ZrT6cAhB7BrtScrIDXz1sUtaBXxLIkn8MJQPconGMhNzbWJqBcHvkQZQ
XM9YA2M9tUEJ1A3ZvOcQDZHJnQTxr8K+CLa65Km8NhH6Ti6ijda7Qea00XcSUGXY
lXY6bFbPZq2sVjd+YN6pB3OKylH4IGYngQiItHV9Nf1v6QH4QvhUdVhFfKQF+xvj
Cm1lQfTep/riCzmXb0S8vI5qZoX7RrmosT7AJpB+ADMLAgMBAAE=
-----END PUBLIC KEY-----"""


def _run_cmd(cmd: str) -> str:
    """Run command quietly and return trimmed output"""
    try:
        out = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL)
        return out.decode('utf-8', errors='ignore').strip()
    except Exception:
        return ""


def get_mac_address() -> str:
    """Get primary MAC address"""
    try:
        import psutil
        for interface, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if hasattr(psutil, 'AF_LINK') and addr.family == psutil.AF_LINK:
                    mac = addr.address.replace("-", "").replace(":", "").upper()
                    if mac and mac != "000000000000":
                        return mac
    except Exception:
        pass

    mac_num = uuid.getnode()
    return f"{mac_num:012X}"


def get_system_uuid() -> str:
    """Get System UUID from WMI / WMIC / PowerShell"""
    if platform.system() == "Windows":
        val = _run_cmd("powershell (Get-CimInstance -ClassName Win32_ComputerSystemProduct).UUID")
        if val:
            return val
        val = _run_cmd("wmic csproduct get uuid")
        lines = [l.strip() for l in val.splitlines() if l.strip() and "UUID" not in l]
        if lines:
            return lines[0]
    return "UNKNOWN_UUID"


def get_motherboard_serial() -> str:
    """Get Motherboard Serial Number"""
    if platform.system() == "Windows":
        val = _run_cmd("powershell (Get-CimInstance -ClassName Win32_BaseBoard).SerialNumber")
        if val:
            return val
        val = _run_cmd("wmic baseboard get serialnumber")
        lines = [l.strip() for l in val.splitlines() if l.strip() and "SerialNumber" not in l]
        if lines:
            return lines[0]
    return "UNKNOWN_MB"


def get_bios_serial() -> str:
    """Get BIOS Serial Number"""
    if platform.system() == "Windows":
        val = _run_cmd("powershell (Get-CimInstance -ClassName Win32_BIOS).SerialNumber")
        if val:
            return val
        val = _run_cmd("wmic bios get serialnumber")
        lines = [l.strip() for l in val.splitlines() if l.strip() and "SerialNumber" not in l]
        if lines:
            return lines[0]
    return "UNKNOWN_BIOS"


def get_disk_serials() -> str:
    """Get Physical Disk Serials"""
    if platform.system() == "Windows":
        val = _run_cmd("powershell (Get-CimInstance -ClassName Win32_DiskDrive).SerialNumber")
        if val:
            serials = sorted([s.strip() for s in val.splitlines() if s.strip()])
            return ",".join(serials)
    return "UNKNOWN_DISK"


def generate_fingerprint(mac: str, uuid_str: str, mb_serial: str, bios_serial: str, disk_serials: str) -> str:
    """Compute 64-char SHA-256 machine fingerprint matching C# Client.cs logic"""
    raw_str = (
        f"{mac.upper()}|"
        f"{uuid_str.upper()}|"
        f"{mb_serial.upper()}|"
        f"{bios_serial.upper()}|"
        f"{disk_serials.upper()}"
    )
    return hashlib.sha256(raw_str.encode('utf-8')).hexdigest().upper()


@lru_cache(maxsize=1)
def get_machine_info() -> Dict[str, str]:
    """Gather complete hardware information and SHA-256 fingerprint"""
    mac = get_mac_address()
    sys_uuid = get_system_uuid()
    mb = get_motherboard_serial()
    bios = get_bios_serial()
    disk = get_disk_serials()
    fingerprint = generate_fingerprint(mac, sys_uuid, mb, bios, disk)

    return {
        "MacAddress": mac,
        "SystemUuid": sys_uuid,
        "MotherboardSerial": mb,
        "BiosSerial": bios,
        "DiskSerial": disk,
        "Fingerprint": fingerprint
    }


def generate_machine_request_file(out_path: str = None) -> str:
    """Save machine_request.txt containing hardware info and fingerprint"""
    info = get_machine_info()
    if not out_path:
        out_path = os.path.join(BASE_DIR, "machine_request.txt")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2)

    print("\n==========================================")
    print("      HARDWARE MACHINE REQUEST GENERATED   ")
    print("==========================================")
    print(f"MAC Address:         {info['MacAddress']}")
    print(f"System UUID:         {info['SystemUuid']}")
    print(f"Motherboard Serial:  {info['MotherboardSerial']}")
    print(f"BIOS Serial:         {info['BiosSerial']}")
    print(f"Disk Serials:        {info['DiskSerial']}")
    print(f"SHA-256 Fingerprint: {info['Fingerprint']}")
    print("------------------------------------------")
    print(f"Saved Machine Request File: {out_path}\n")
    return out_path


def load_public_key() -> rsa.RSAPublicKey:
    """Load RSA public key from public_key.pem or embedded constant"""
    key_pem = None
    if os.path.exists(PUBLIC_KEY_PEM):
        with open(PUBLIC_KEY_PEM, "r", encoding="utf-8") as f:
            key_pem = f.read()

    if not key_pem or "BEGIN PUBLIC KEY" not in key_pem:
        key_pem = EMBEDDED_PUBLIC_KEY_PEM

    return serialization.load_pem_public_key(key_pem.encode('utf-8'))


def safe_b64decode(s: str) -> bytes:
    """Safe Base64 decoder supporting standard base64, URL-safe base64 (- and _), missing padding '=', and length misalignment"""
    if not s:
        return b""
    clean = str(s).strip().replace("-", "+").replace("_", "/")
    rem = len(clean) % 4
    if rem == 1:
        clean = clean[:-1]
        rem = len(clean) % 4
    if rem > 0:
        clean += "=" * (4 - rem)
    try:
        return base64.b64decode(clean)
    except Exception:
        return b""


def verify_license_data(license_json_or_dict: Any) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Verify RSA & Ed25519 license data against current host machine fingerprint and RSA/Ed25519 public keys.
    Returns: (is_valid, status_message, verification_details)
    """
    details = {
        "license_id": None,
        "product": None,
        "expiry": None,
        "fingerprint": None,
        "signature_valid": False,
        "fingerprint_match": False,
        "expiration_valid": False
    }

    try:
        if isinstance(license_json_or_dict, str):
            license_data = json.loads(license_json_or_dict.strip())
        else:
            license_data = license_json_or_dict

        license_id = str(license_data.get("LicenseId", "")).strip()
        fingerprint = str(license_data.get("Fingerprint", "")).strip().upper()
        product = str(license_data.get("Product") or license_data.get("Project") or license_data.get("Product Name") or "").strip()
        expiry_str = str(license_data.get("Expiry", "")).strip()
        signature_b64 = str(license_data.get("Signature", "")).strip()

        details["license_id"] = license_id
        details["fingerprint"] = fingerprint
        details["product"] = product
        details["expiry"] = expiry_str

        if not license_id or not fingerprint or not signature_b64:
            return False, "Invalid license format: Missing LicenseId, Fingerprint, or Signature", details

        # 1. Check Host Hardware Fingerprint Match
        current_info = get_machine_info()
        current_fp = current_info["Fingerprint"]
        current_mac = current_info["MacAddress"]

        if fingerprint == current_fp or current_mac in fingerprint or (len(current_mac) >= 8 and current_mac in fingerprint):
            details["fingerprint_match"] = True
        else:
            return False, f"Hardware Fingerprint mismatch (License: {fingerprint[:12]}..., Machine: {current_fp[:12]}...)", details

        # 2. Expiration Date Check
        if expiry_str:
            clean_expiry = expiry_str.rstrip("Z")
            try:
                if "T" in clean_expiry:
                    expiry_dt = datetime.fromisoformat(clean_expiry)
                else:
                    expiry_dt = datetime.strptime(clean_expiry, "%Y-%m-%d")

                if datetime.utcnow() > expiry_dt:
                    return False, f"License expired on {expiry_dt.strftime('%Y-%m-%d')}", details
                details["expiration_valid"] = True
            except Exception:
                details["expiration_valid"] = True
        else:
            details["expiration_valid"] = True

        # 3. Verify Signature (RSA or Ed25519)
        signature_bytes = safe_b64decode(signature_b64)
        data_to_verify = f"{license_id}|{fingerprint}|{product}|{expiry_str}"
        data_bytes = data_to_verify.encode('utf-8')

        sig_valid = False
        if signature_bytes:
            # Try RSA verification first
            try:
                pub_key = load_public_key()
                pub_key.verify(
                    signature_bytes,
                    data_bytes,
                    padding.PKCS1v15(),
                    hashes.SHA256()
                )
                sig_valid = True
            except Exception:
                sig_valid = False

            # Try Ed25519 verification as fallback
            if not sig_valid:
                try:
                    import importlib
                    lic_utils = importlib.import_module("license_utils")
                    ed_pub = lic_utils.get_public_key()
                    try:
                        ed_pub.verify(signature_bytes, data_bytes)
                        sig_valid = True
                    except Exception:
                        pass
                except Exception:
                    pass

        details["signature_valid"] = sig_valid

        if not sig_valid:
            return False, "Signature verification failed (license tampered or wrong key)", details

        return True, "License is valid and verified", details

    except Exception as e:
        return False, f"License verification error: {str(e)}", details


def main():
    parser = argparse.ArgumentParser(description="ToolCrib Python Client License Validator")
    parser.add_argument("--request", action="store_true", help="Generate machine_request.txt file")
    parser.add_argument("--verify", type=str, help="Path to license.json file to verify")

    args = parser.parse_args()

    if args.request:
        generate_machine_request_file()
    elif args.verify:
        if not os.path.exists(args.verify):
            print(f"Error: License file not found: {args.verify}")
            sys.exit(1)
        with open(args.verify, "r", encoding="utf-8") as f:
            lic_json = f.read()

        is_valid, msg, details = verify_license_data(lic_json)
        print("\n==========================================")
        print("      ToolCrib License Verification       ")
        print("==========================================")
        print(f"Status:       {'[VALID LICENSE]' if is_valid else '[INVALID LICENSE]'}")
        print(f"Message:      {msg}")
        print(f"License ID:   {details.get('license_id')}")
        print(f"Product:      {details.get('product')}")
        print(f"Expiry:       {details.get('expiry')}")
        print(f"RSA Signature: {'[Verified]' if details.get('signature_valid') else '[Invalid]'}")
        print(f"Fingerprint:  {'[Host Match]' if details.get('fingerprint_match') else '[Host Mismatch]'}")
        print("------------------------------------------\n")
    else:
        info = get_machine_info()
        print("\nMachine Information:")
        print(json.dumps(info, indent=2))
        print("\nUse --request to output machine_request.txt, or --verify license.json to check a license.")


if __name__ == "__main__":
    main()
