# Copyright (c) 2019, Bosch Engineering Center Cluj and BFMC organizers
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.

# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.

# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE
# Import necessary modules
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import (
    load_pem_private_key,
    load_pem_public_key,
)
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding


def gen_key():
    """
    Generate a new RSA private key with a public exponent of 65537 and a key size of 2048 bits.
    Returns:
        private_key (cryptography.hazmat.backends.openssl.rsa._RSAPrivateKey): The generated private key.
    """
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )
    return private_key


def save_private_key(pk, filename):
    """
    Save the private key to a file in PEM format.
    Args:
        pk (cryptography.hazmat.backends.openssl.rsa._RSAPrivateKey): The private key to save.
        filename (str): The name of the file to save the private key to.
    """
    pem = pk.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    with open(filename, "wb") as pem_out:
        pem_out.write(pem)


def save_public_key(pk, filename):
    """
    Save the public key to a file in PEM format.
    Args:
        pk (cryptography.hazmat.backends.openssl.rsa._RSAPublicKey): The public key to save.
        filename (str): The name of the file to save the public key to.
    """
    pem = pk.public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.PKCS1
    )
    with open(filename, "wb") as pem_out:
        pem_out.write(pem)


def load_private_key(filename):
    """
    Load a private key from a file in PEM format.
    Args:
        filename (str): The name of the file containing the private key.
    Returns:
        private_key (cryptography.hazmat.backends.openssl.rsa._RSAPrivateKey): The loaded private key.
    """
    with open(filename, "rb") as pem_in:
        pemlines = pem_in.read()
    private_key = load_pem_private_key(pemlines, None, default_backend())
    return private_key


def load_public_key(filename):
    """
    Load a public key from a file in PEM format.
    Args:
        filename (str): The name of the file containing the public key.
    Returns:
        public_key (cryptography.hazmat.backends.openssl.rsa._RSAPublicKey): The loaded public key.
    """
    with open(filename, "rb") as pem_in:
        pemlines = pem_in.read()
    public_key = load_pem_public_key(pemlines, default_backend())
    return public_key


def sign_data(private_key, plain_text):
    """
    Sign the given plain text using the private key.
    Args:
        private_key (cryptography.hazmat.backends.openssl.rsa._RSAPrivateKey): The private key to use for signing.
        plain_text (bytes): The plain text to sign.
    Returns:
        signature (bytes): The signature of the plain text.
    """
    signature = private_key.sign(
        data=plain_text,
        padding=padding.PSS(
            mgf=padding.MGF1(hashes.MD5()), salt_length=padding.PSS.MAX_LENGTH
        ),
        algorithm=hashes.MD5(),
    )
    return signature


def verify_data(public_key, plain_text, signature):
    """
    Verify the given plain text and signature using the public key.
    Args:
        public_key (cryptography.hazmat.backends.openssl.rsa._RSAPublicKey): The public key to use for verification.
        plain_text (bytes): The plain text to verify.
        signature (bytes): The signature to verify.
    Returns:
        is_signature_correct (bool): True if the signature is correct, False otherwise.
    """
    try:
        public_key.verify(
            signature=signature,
            data=plain_text,
            padding=padding.PSS(
                mgf=padding.MGF1(hashes.MD5()), salt_length=padding.PSS.MAX_LENGTH
            ),
            algorithm=hashes.MD5(),
        )
        is_signature_correct = True
    except InvalidSignature:
        is_signature_correct = False
    return is_signature_correct