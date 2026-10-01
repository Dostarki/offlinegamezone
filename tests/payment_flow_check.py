"""End-to-end backend payment flow test: wallet SIWE auth, $1 access quote/submit,
open market order quote/submit. Read-only on-chain (fake tx hashes, no real funds)."""
import json
import secrets
import sys
import requests
from eth_account import Account
from eth_account.messages import encode_defunct

BASE = "https://zone-trade.preview.emergentagent.com"
DOMAIN = "zone-trade.preview.emergentagent.com"
URI = "https://zone-trade.preview.emergentagent.com"
FAKE_TX = "0x" + secrets.token_hex(32)

results = []

def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}")

acct = Account.create()
s = requests.Session()

# 1. SIWE challenge
r = s.post(f"{BASE}/api/auth/challenge", json={
    "address": acct.address, "chain_id": 4663, "domain": DOMAIN, "uri": URI})
check("auth challenge", r.status_code == 200, f"HTTP {r.status_code} {r.text[:200]}")
if r.status_code != 200:
    sys.exit(1)
msg = r.json()["message"]

# 2. Sign + verify
sig = acct.sign_message(encode_defunct(text=msg)).signature.hex()
r = s.post(f"{BASE}/api/auth/verify", json={"message": msg, "signature": sig})
check("auth verify (SIWE)", r.status_code == 200 and r.json().get("authenticated"),
      f"HTTP {r.status_code} {r.text[:200]}")
if r.status_code != 200:
    sys.exit(1)
token = r.json()["token"]
auth = {"Authorization": f"Bearer {token}"}

# 3. Access status ($1 entry)
r = s.get(f"{BASE}/api/access", headers=auth)
check("access status", r.status_code == 200 and r.json().get("paid") is False
      and r.json().get("price_usd") == "1.00" and r.json().get("chain_id") == 4663,
      f"HTTP {r.status_code} {r.text[:300]}")

# 4. Access quote
r = s.post(f"{BASE}/api/access/quote", headers=auth)
ok = r.status_code == 200
detail = f"HTTP {r.status_code} "
order_id = None
if ok:
    body = r.json()
    order = body.get("order") or {}
    order_id = order.get("order_id")
    quote = order.get("quote") or {}
    detail += f"status={order.get('status')} recipient={quote.get('recipient')} wei={quote.get('amount_wei')} expires={quote.get('expires_at')}"
    ok = (order.get("status") == "awaiting_payment"
          and quote.get("recipient", "").lower() == "0x45d9aa6ef98407dda4911c6f4a9af59f3de4e334"
          and int(quote.get("amount_wei", "0")) > 0
          and quote.get("chain_id") == 4663
          and quote.get("payment_mode") == "native_transfer")
else:
    detail += r.text[:200]
check("access $1 quote", ok, detail)

# 5. Access submit with unknown tx hash -> must stay unpaid, graceful 'submitted'
r = s.post(f"{BASE}/api/access/submit", headers=auth,
           json={"order_id": order_id, "tx_hash": FAKE_TX})
ok = r.status_code == 200 and r.json().get("paid") is False
check("access submit unknown tx stays unpaid", ok, f"HTTP {r.status_code} {r.text[:300]}")

# 6. Access status again -> not paid, no entitlement leak
r = s.get(f"{BASE}/api/access", headers=auth)
check("access still unpaid after fake tx", r.status_code == 200 and r.json().get("paid") is False,
      f"HTTP {r.status_code}")

# 7. Market catalog
r = s.get(f"{BASE}/api/offgame-market/catalog")
ok = r.status_code == 200 and r.json()["capabilities"]["purchase_enabled"] is True
check("market catalog", ok, f"HTTP {r.status_code}")

# 7b. Baseline gold (new profiles start with 150 default gold)
r = s.get(f"{BASE}/api/account/economy", headers=auth)
gold_before = int(r.json().get("gold", 0)) if r.status_code == 200 else -1

# 8. Market order + quote (pack_field $2)
r = s.post(f"{BASE}/api/offgame-market/orders", headers=auth, json={"sku": "pack_field"})
ok = r.status_code == 200
detail = f"HTTP {r.status_code} "
m_order_id = None
if ok:
    order = r.json().get("order") or {}
    m_order_id = order.get("order_id")
    quote = order.get("quote") or {}
    detail += f"status={order.get('status')} sku={order.get('sku')} wei={quote.get('amount_wei')} recipient={quote.get('recipient')}"
    ok = (order.get("status") == "awaiting_payment" and int(quote.get("amount_wei", "0")) > 0
          and quote.get("recipient", "").lower() == "0x45d9aa6ef98407dda4911c6f4a9af59f3de4e334")
else:
    detail += r.text[:200]
check("market order + quote", ok, detail)

# 9. Market submit with unknown tx -> graceful, not fulfilled
FAKE_TX2 = "0x" + secrets.token_hex(32)
r = s.post(f"{BASE}/api/offgame-market/orders/{m_order_id}/submit", headers=auth,
           json={"tx_hash": FAKE_TX2})
ok = r.status_code == 200 and r.json().get("status") in ("submitted", "confirming")
check("market submit unknown tx queued", ok, f"HTTP {r.status_code} {r.text[:300]}")

# 10. Market order state unchanged / not fulfilled
r = s.get(f"{BASE}/api/offgame-market/orders/{m_order_id}", headers=auth)
ok = r.status_code == 200 and r.json()["order"].get("status") in ("submitted", "confirming", "awaiting_payment")
check("market order not fulfilled by fake tx", ok, f"HTTP {r.status_code} status={r.json()['order'].get('status') if r.status_code==200 else '?'}")

# 11. Economy unchanged (no gold granted from fake tx)
r = s.get(f"{BASE}/api/account/economy", headers=auth)
ok = r.status_code == 200 and int(r.json().get("gold", -1)) == gold_before
check("no gold granted without payment", ok, f"HTTP {r.status_code} gold_before={gold_before} gold_after={r.json().get('gold') if r.status_code==200 else '?'}")

# 12. Chain RPC reachable from pod and reports 4663
r = requests.post("https://rpc.mainnet.chain.robinhood.com",
                  json={"jsonrpc": "2.0", "id": 1, "method": "eth_chainId", "params": []}, timeout=10)
ok = r.status_code == 200 and int(r.json()["result"], 16) == 4663
check("Robinhood RPC eth_chainId == 4663", ok, f"HTTP {r.status_code} {r.text[:120]}")

# 13. Coinbase spot price reachable
r = requests.get("https://api.coinbase.com/v2/prices/ETH-USD/spot", timeout=10)
ok = r.status_code == 200 and r.json()["data"]["base"] == "ETH"
check("Coinbase ETH-USD spot reachable", ok, f"HTTP {r.status_code} {r.text[:120]}")

failed = [n for n, ok, _ in results if not ok]
print(f"\n{len(results) - len(failed)}/{len(results)} passed")
sys.exit(1 if failed else 0)
