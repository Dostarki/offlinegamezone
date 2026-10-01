# Password-only admin authentication testing playbook

## Scope
Existing bcrypt + JWT access/refresh authentication. No email registration, wallet requirement, new provider, IP whitelist, or browser binding. Read `/app/memory/test_credentials.md`. Use the public URL from frontend/.env, never a previous fork's URL. Do not test payments or send funds.

## 1. Database verification
Use MONGO_URL and DB_NAME from backend/.env. Verify operator account hash is bcrypt (do not print hash), admin_accounts.id unique, admin_sessions.sid unique and expires_at TTL, login_attempts.identifier unique and expires_at TTL. Existing seed is idempotent. Do not modify password or delete unrelated sessions.

## 2. API verification
POST /api/admin/login with JSON password and a configured site Origin. Expect role admin and admin_access/admin_refresh cookies, Secure + HttpOnly, path /api/admin. GET /me, /settings and /status must succeed with cookies, and return 401 without a session. POST /refresh renews access; POST /logout invalidates that session on the server. Saving settings requires both valid session and trusted Origin.

## 3. Origin and client independence
The allowed origins combine comma-separated ADMIN_ORIGIN, ADMIN_PROXY_ORIGIN and CORS_ORIGINS. Confirm configured www, apex, public preview and rewritten proxy origins work. Reject missing, null, foreign, suffix-spoofed and wildcard origins; do not trust arbitrary forwarded-host headers. Multiple independent clients may log in at once with the same password. Changing client IP/User-Agent must not bind or invalidate a session. Log out one session and ensure another stays valid. Use isolated fixtures for simulated IP changes and brute-force tests; do not lock the real operator out.

## 4. Browser verification
Use independent fresh browser contexts and Chromium/Firefox/WebKit where installed; report engines actually exercised. No wallet connection is needed. Test wrong password, correct password, settings load/save/restore, page reload keeping session, and logout. Cookies are application SameSite=Strict; preview edge may rewrite to None; Partitioned. Do not weaken Secure/HttpOnly or CSRF checks to make tests pass.

## Limits
### Current local-simulation import
- User-reported injected wallet crash reproduced in browser: `walletDetails.rkDetails.id` was undefined because `injectedWallet().createConnector({})` skipped RainbowKit metadata. Fix: ALWAYS use `connectorsForWallets` for both full and injected-only lists. WalletConnect's projectId requirement does not apply when only `injectedWallet` is instantiated.
- Mandatory regression: no wallet, legacy window.ethereum/MetaMask, EIP-6963, full connect + actual SIWE signature, disconnect/reload. Do not stub auth API responses.
- Auth playbook reconfirmed: bcrypt + JWT (15min access/7day refresh), HttpOnly/Secure cookies, explicit Origin allowlist and idempotent seed. This remains PASSWORD-ONLY; no email/register/reset flows were added.
- Inspect only rejected Origin in backend logs, then add the observed trusted ingress origin to ADMIN_PROXY_ORIGIN. Never trust arbitrary forwarded headers or widen to wildcard.
- Use public frontend/.env URL; confirm /api/admin/login, /me, settings update+restore, logout, and reject missing/null/foreign Origin.

Public gateway tests cannot demonstrate independent real ISP egress IPs; explicitly distinguish simulated client IP coverage from real network testing. Production deployment in progress is not proof that these new changes are live. Preserve original world settings in finally blocks and remove only test-created sessions. No UI layout change is planned.
