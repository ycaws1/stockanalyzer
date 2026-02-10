"""
Script to generate VAPID keys for web push notifications.
Run this once and add the output to your .env file.
"""
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
import base64

def generate_vapid_keys():
    # Generate EC key pair for VAPID (required: P-256 / secp256r1)
    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    public_key = private_key.public_key()
    
    # Private key in raw format (32 bytes)
    private_bytes = private_key.private_numbers().private_value.to_bytes(32, 'big')
    private_b64 = base64.urlsafe_b64encode(private_bytes).decode().rstrip('=')
    
    # Public key in uncompressed point format (65 bytes)
    public_bytes = public_key.public_bytes(
        serialization.Encoding.X962,
        serialization.PublicFormat.UncompressedPoint
    )
    public_b64 = base64.urlsafe_b64encode(public_bytes).decode().rstrip('=')
    
    return public_b64, private_b64

if __name__ == "__main__":
    public_key, private_key = generate_vapid_keys()
    
    print("\n" + "="*60)
    print("VAPID Keys Generated Successfully!")
    print("="*60)
    print("\nAdd these to your backend/.env file:\n")
    print(f"VAPID_PUBLIC_KEY={public_key}")
    print(f"VAPID_PRIVATE_KEY={private_key}")
    print(f"VAPID_SUBJECT=mailto:admin@stockanalyzer-bay.vercel.app")
    print("\n" + "="*60)
    print("\nAlso add this to your frontend/.env.local file:\n")
    print(f"NEXT_PUBLIC_VAPID_KEY={public_key}")
    print("="*60 + "\n")
