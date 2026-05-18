"""
generate_certs.py — Auto-detects LAN IP, embeds it in SAN.
Run once:  python generate_certs.py
"""
import os, socket, ipaddress
from datetime import datetime, timedelta, timezone
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

CERT_DIR  = os.path.join(os.path.dirname(__file__), "certs")
CERT_FILE = os.path.join(CERT_DIR, "cert.pem")
KEY_FILE  = os.path.join(CERT_DIR, "key.pem")
os.makedirs(CERT_DIR, exist_ok=True)

def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close(); return ip
    except: return "127.0.0.1"

def generate():
    lan_ip = get_lan_ip()
    print(f"\n  Detected LAN IP: {lan_ip}")
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME,           "IN"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Tamil Nadu"),
        x509.NameAttribute(NameOID.LOCALITY_NAME,          "Coimbatore"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME,      "SecureMsg Prototype"),
        x509.NameAttribute(NameOID.COMMON_NAME,            lan_ip),
    ])
    san = [x509.DNSName("localhost"), x509.DNSName("securemsg.local"),
           x509.IPAddress(ipaddress.IPv4Address("127.0.0.1"))]
    if lan_ip not in ("127.0.0.1", "0.0.0.0"):
        san.append(x509.IPAddress(ipaddress.IPv4Address(lan_ip)))
    cert = (x509.CertificateBuilder()
        .subject_name(subject).issuer_name(issuer)
        .public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=825))
        .add_extension(x509.SubjectAlternativeName(san), critical=False)
        .sign(key, hashes.SHA256()))
    with open(KEY_FILE, "wb") as f:
        f.write(key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption()))
    with open(CERT_FILE, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    print(f"  certs: {CERT_FILE}")
    print(f"  covers: localhost, 127.0.0.1, {lan_ip}")
    # Save LAN IP for start scripts to use
    with open(os.path.join(CERT_DIR, "lan_ip.txt"), "w") as f:
        f.write(lan_ip)
    print(f"\n  ✓ Done. Run: python -m uvicorn server:app --ssl-keyfile certs/key.pem --ssl-certfile certs/cert.pem --host 0.0.0.0 --port 8443")
    print(f"\n  TRUST CERT:")
    print(f"  Linux:   sudo cp certs/cert.pem /usr/local/share/ca-certificates/securemsg.crt && sudo update-ca-certificates")
    print(f"  Windows (PowerShell as Admin): Import-Certificate -FilePath .\\certs\\cert.pem -CertStoreLocation Cert:\\LocalMachine\\Root")
    print(f"  OR just click 'Advanced > Proceed' in browser (fine for prototype)")
    print(f"\n  Share with other machines: https://{lan_ip}:8443")

if __name__ == "__main__":
    generate()
