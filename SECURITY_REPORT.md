# Laporan Penetration Test - WBS BPKH AI

**Tanggal:** 5 Januari 2026
**Standar:** ISO 27001:2022, OWASP Top 10 2021
**Target:** https://wbs-bpkh.up.railway.app
**Severity Rating:** CVSS 3.1

---

## Executive Summary

Penetration test dilakukan terhadap sistem Whistleblowing BPKH untuk mengidentifikasi kerentanan keamanan. Ditemukan **7 kerentanan** dengan rincian:

| Severity | Jumlah |
|----------|--------|
| CRITICAL | 1 |
| HIGH | 3 |
| MEDIUM | 2 |
| LOW | 1 |

---

## Temuan Kerentanan

### 1. [CRITICAL] CORS Misconfiguration dengan Credentials
**CVSS Score:** 9.1 (Critical)
**OWASP Category:** A05:2021 - Security Misconfiguration
**Lokasi:** `backend/main.py:85-91`

**Deskripsi:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # VULNERABLE
    allow_credentials=True,  # DANGEROUS COMBINATION
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Dampak:**
- Attacker dapat membuat website jahat yang melakukan request ke API dengan kredensial pengguna
- Session hijacking dan CSRF attacks menjadi mungkin
- Data sensitif whistleblower dapat dicuri

**Bukti:**
```
$ curl -I "https://wbs-bpkh.up.railway.app/api/v1/reports" -H "Origin: https://evil-site.com"
Access-Control-Allow-Credentials: true
Access-Control-Allow-Origin: *
```

**Rekomendasi:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://wbs.bpkh.go.id",
        "https://wbs-bpkh.up.railway.app"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

---

### 2. [HIGH] Stored XSS Vulnerability
**CVSS Score:** 7.5 (High)
**OWASP Category:** A03:2021 - Injection
**Lokasi:** Input fields (subject, description)

**Deskripsi:**
Input dari pengguna disimpan dan ditampilkan tanpa sanitasi, memungkinkan injeksi script.

**Bukti:**
```bash
$ curl -X POST "/api/v1/reports" -d '{"subject":"<script>alert(1)</script>","description":"..."}'
# Response: {"title":"<script>alert(1)</script>", ...}
```

**Dampak:**
- Script injection pada dashboard admin
- Session hijacking
- Defacement

**Rekomendasi:**
1. Sanitasi input menggunakan library seperti `bleach`:
```python
import bleach
sanitized_input = bleach.clean(user_input, strip=True)
```

2. Encode output di frontend:
```javascript
element.textContent = data.title;  // NOT innerHTML
```

---

### 3. [HIGH] Hardcoded Default Secrets
**CVSS Score:** 7.2 (High)
**OWASP Category:** A02:2021 - Cryptographic Failures
**Lokasi:** `backend/config.py:24, 46`

**Deskripsi:**
```python
secret_key: str = Field(default="change-me-in-production", ...)
jwt_secret: str = Field(default="change-this-jwt-secret-in-production", ...)
```

**Dampak:**
- Jika environment variable tidak di-set, default secret akan digunakan
- Attacker dapat forge JWT tokens
- Complete authentication bypass

**Rekomendasi:**
```python
secret_key: str = Field(..., env="SECRET_KEY")  # Required, no default
jwt_secret: str = Field(..., env="JWT_SECRET")  # Required, no default
```

---

### 4. [HIGH] API Documentation Exposed in Production
**CVSS Score:** 5.3 (Medium)
**OWASP Category:** A01:2021 - Broken Access Control
**Lokasi:** `/docs`, `/openapi.json`

**Deskripsi:**
Swagger UI dan OpenAPI specification tersedia publik di production.

**Bukti:**
```
GET /openapi.json → 200 OK (Full API schema)
GET /docs → 200 OK (Swagger UI)
```

**Dampak:**
- Attacker mendapat blueprint lengkap API
- Mempermudah reconnaissance
- Endpoint tersembunyi terekspos

**Rekomendasi:**
```python
# Disable in production
if not settings.debug:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
```

---

### 5. [MEDIUM] Sensitive Data in Logs
**CVSS Score:** 4.3 (Medium)
**OWASP Category:** A09:2021 - Security Logging and Monitoring Failures
**Lokasi:** `backend/routers/auth.py:35, 61`

**Deskripsi:**
```python
logger.info(f"Login attempt for: {credentials.email}, user found: {user is not None}, password_len: {len(credentials.password)}")
logger.info(f"Hash from DB: {user.get('password_hash', 'MISSING')[:30]}...")
```

**Dampak:**
- Password length dan hash partial terekspos di logs
- Membantu attacker dalam brute force

**Rekomendasi:**
```python
logger.info(f"Login attempt for user: {credentials.email}")
# Remove password_len and hash logging
```

---

### 6. [MEDIUM] Missing Rate Limiting Implementation
**CVSS Score:** 4.3 (Medium)
**OWASP Category:** A04:2021 - Insecure Design
**Lokasi:** Config defined but not implemented

**Deskripsi:**
```python
rate_limit_per_minute: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
```
Rate limit didefinisikan di config tapi tidak diimplementasikan.

**Dampak:**
- Brute force attacks pada login
- DoS attacks
- API abuse

**Rekomendasi:**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/v1/auth/login")
@limiter.limit("5/minute")
async def login(...):
    ...
```

---

### 7. [LOW] Missing Security Headers
**CVSS Score:** 3.1 (Low)
**OWASP Category:** A05:2021 - Security Misconfiguration

**Deskripsi:**
Response tidak mengandung security headers yang direkomendasikan.

**Missing Headers:**
- X-Content-Type-Options
- X-Frame-Options
- Content-Security-Policy
- Strict-Transport-Security

**Rekomendasi:**
```python
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
```

---

## Temuan Positif (Best Practices yang Sudah Diimplementasi)

| Aspek | Status | Catatan |
|-------|--------|---------|
| Password Hashing | ✅ PASS | bcrypt dengan salt rounds=12 |
| JWT Token Expiry | ✅ PASS | 1 jam access, 7 hari refresh |
| Account Lockout | ✅ PASS | 5 percobaan, 30 menit lockout |
| Password Strength | ✅ PASS | Min 8 char, upper, lower, digit, special |
| Role-Based Access Control | ✅ PASS | Hierarchy-based RBAC |
| Parameterized Queries | ✅ PASS | Supabase client prevents SQL injection |
| Ticket ID Entropy | ✅ PASS | 8-char UUID hex, hard to guess |
| Audit Logging | ✅ PASS | Actions logged to audit_logs |

---

## Prioritas Remediasi

| Priority | Vulnerability | Effort |
|----------|--------------|--------|
| 1 | CORS Misconfiguration | Low |
| 2 | XSS Sanitization | Medium |
| 3 | Remove Default Secrets | Low |
| 4 | Disable API Docs in Prod | Low |
| 5 | Remove Sensitive Logs | Low |
| 6 | Implement Rate Limiting | Medium |
| 7 | Add Security Headers | Low |

---

## Kesimpulan

Sistem WBS BPKH AI memiliki fondasi keamanan yang baik (authentication, authorization, password handling), namun memerlukan perbaikan segera pada konfigurasi CORS dan sanitasi input.

**Rekomendasi:** Perbaiki kerentanan CRITICAL dan HIGH sebelum sistem digunakan untuk data whistleblowing yang sebenarnya.

---

*Laporan ini dibuat berdasarkan penetration test terbatas. Untuk assessment lengkap, disarankan melakukan penetration test profesional yang mencakup infrastructure, network, dan social engineering testing.*
