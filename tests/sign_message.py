"""Sign arbitrary SIWE/plaintext message with a provided private key."""

import argparse
import base64

from eth_account import Account
from eth_account.messages import encode_defunct


def decode_message(raw: str) -> str:
    if raw.startswith('0x'):
        try:
            return bytes.fromhex(raw[2:]).decode('utf-8')
        except Exception:
            return raw
    return base64.b64decode(raw.encode('utf-8')).decode('utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--private-key', required=True)
    parser.add_argument('--message', required=True)
    args = parser.parse_args()

    text = decode_message(args.message)
    signed = Account.sign_message(encode_defunct(text=text), private_key=args.private_key)
    print(signed.signature.hex())
