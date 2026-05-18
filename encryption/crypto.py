import nacl.utils
import nacl.public
import nacl.encoding
import nacl.secret
import nacl.hash
import base64


def generate_keypair():
    """Generate a new public/private key pair."""
    private_key = nacl.public.PrivateKey.generate()
    public_key = private_key.public_key
    return (
        base64.b64encode(bytes(private_key)).decode("utf-8"),
        base64.b64encode(bytes(public_key)).decode("utf-8"),
    )


def encrypt_message(plaintext: str, recipient_public_key_b64: str, sender_private_key_b64: str) -> str:
    """
    Encrypt a message compatible with TweetNaCl JS format:
    nonce (24 bytes) + ciphertext, base64-encoded.
    """
    recipient_pub = nacl.public.PublicKey(
        base64.b64decode(recipient_public_key_b64)
    )
    # PyNaCl private key is 32 bytes raw scalar
    sender_priv_bytes = base64.b64decode(sender_private_key_b64)
    if len(sender_priv_bytes) == 64:
        sender_priv_bytes = sender_priv_bytes[:32]
    sender_priv = nacl.public.PrivateKey(sender_priv_bytes)

    box = nacl.public.Box(sender_priv, recipient_pub)
    # PyNaCl box.encrypt returns nonce+ciphertext already concatenated
    encrypted = box.encrypt(plaintext.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")


def decrypt_message(
    ciphertext_b64: str,
    sender_public_key_b64: str,
    recipient_private_key_b64: str,
) -> str:
    """Decrypt a nonce-prepended ciphertext from TweetNaCl or PyNaCl."""
    sender_pub = nacl.public.PublicKey(
        base64.b64decode(sender_public_key_b64)
    )
    recipient_priv_bytes = base64.b64decode(recipient_private_key_b64)
    if len(recipient_priv_bytes) == 64:
        recipient_priv_bytes = recipient_priv_bytes[:32]
    recipient_priv = nacl.public.PrivateKey(recipient_priv_bytes)

    box = nacl.public.Box(recipient_priv, sender_pub)
    # decrypt() accepts nonce+ciphertext as produced by encrypt()
    ciphertext = base64.b64decode(ciphertext_b64)
    decrypted = box.decrypt(ciphertext)
    return decrypted.decode("utf-8")
