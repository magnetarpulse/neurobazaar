import ssl
import os
from pathlib import Path

def get_neurobazaar_dir():
    """Get the root directory of the Neurobazaar project."""
    cwd = os.getcwd()
    index = cwd.index('neurobazaar')
    return cwd[:index + len('neurobazaar')]

def get_key_storage_dir():
    """Create and return path to the hidden key storage directory."""
    neurobazaar_dir = get_neurobazaar_dir()
    key_dir = Path(neurobazaar_dir) / '.ssl'
    key_dir.mkdir(mode=0o700, exist_ok=True)  
    return key_dir

def load_ssl_context(cert_file, pkey_file):
    """Load SSL context from certificate and private key files."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_file, pkey_file)
    return context

def save_ssl_files(cert, pkey):
    """Save certificate and private key to files."""
    from cryptography.hazmat.primitives import serialization
    
    key_dir = get_key_storage_dir()
    cert_file = key_dir / 'cert.pem'
    pkey_file = key_dir / 'pkey.pem'
    
    cert_file.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    
    pkey_file.write_bytes(
        pkey.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    
    pkey_file.chmod(0o600)
    
    return str(cert_file), str(pkey_file)

def generate_ssl_pair(host):
    """Generate a self-signed SSL certificate and private key."""
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        import datetime
    except ImportError:
        raise TypeError(
            "Using ad-hoc certificates requires the cryptography library."
        ) from None

    key_dir = get_key_storage_dir()
    cert_file = key_dir / 'cert.pem'
    pkey_file = key_dir / 'pkey.pem'
    
    if cert_file.exists() and pkey_file.exists():
        return str(cert_file), str(pkey_file)

    cn = f"*.{host}/CN={host}"
    pkey = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name(
        [
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Dummy Certificate"),
            x509.NameAttribute(NameOID.COMMON_NAME, cn),
        ]
    )
    
    one_day = datetime.timedelta(1, 0, 0)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(pkey.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.today() - one_day)
        .not_valid_after(datetime.datetime.today() + (one_day * 365))
        .add_extension(x509.ExtendedKeyUsage([x509.OID_SERVER_AUTH]), critical=False)
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(cn)]), critical=False)
        .sign(private_key=pkey, algorithm=hashes.SHA256())
    )
    
    return save_ssl_files(cert, pkey)

def main():
    host = "localhost"
    cert_file, pkey_file = generate_ssl_pair(host)
    return cert_file, pkey_file

if __name__ == "__main__":
    main()