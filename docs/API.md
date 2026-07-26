# AuraFit — API Reference

All APIs use the standard response envelope:
```json
{
  "success": true,
  "data": {},
  "meta": {"request_id": "uuid", "timestamp": "ISO-8601"},
  "errors": null
}
```

Error format:
```json
{
  "success": false,
  "data": null,
  "errors": [{"code": "VALIDATION_ERROR", "message": "...", "field": "email"}]
}
```

---

## User Service (port 8001) — `/api/v1`

### Authentication

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | Public | Register new user |
| POST | `/auth/login` | Public | Login → access + refresh tokens |
| POST | `/auth/refresh` | Public | Refresh access token |
| POST | `/auth/logout` | Bearer | Logout (blocklist token) |
| POST | `/auth/verify-email` | Public | Verify email with OTP |
| POST | `/auth/resend-verification` | Public | Resend verification email |
| POST | `/auth/forgot-password` | Public | Initiate password reset |
| POST | `/auth/reset-password` | Public | Set new password |
| GET  | `/auth/google` | Public | Google OAuth redirect |
| GET  | `/auth/google/callback` | Public | OAuth callback handler |

### Users & Profiles

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/users/me` | Bearer | Current user info |
| PATCH | `/users/me` | Bearer | Update user info |
| DELETE | `/users/me` | Bearer | Delete account |
| GET | `/profiles/me` | Bearer | User beauty profile |
| PUT | `/profiles/me` | Bearer | Update profile |
| GET | `/preferences` | Bearer | Notification preferences |
| PUT | `/preferences` | Bearer | Update preferences |

### Sessions & MFA

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/sessions` | Bearer | List active sessions |
| DELETE | `/sessions/{id}` | Bearer | Revoke session |
| DELETE | `/sessions/all` | Bearer | Revoke all sessions |
| POST | `/mfa/enable` | Bearer | Start TOTP MFA setup |
| POST | `/mfa/verify` | Bearer | Verify and activate MFA |
| POST | `/mfa/disable` | Bearer | Disable MFA |

### Facial Analysis

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/analysis/scan` | Bearer | Submit selfie for analysis |
| GET | `/analysis/scans` | Bearer | List scan history |
| GET | `/analysis/scans/{id}` | Bearer | Get specific scan result |
| DELETE | `/analysis/scans/{id}` | Bearer | Delete scan |
| GET | `/analysis/scans/active` | Bearer | Current active scan |

### Color Intelligence

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/color/compute` | Bearer | Compute color profile from scan |
| GET | `/color/profile` | Bearer | Active color profile |
| GET | `/color/history` | Bearer | Color profile history |
| DELETE | `/color/profiles/{id}` | Bearer | Delete color profile |
| GET | `/color/season-guide` | Public | Educational guide for 16 seasons |

### Wardrobe

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/wardrobes` | Bearer | List user wardrobes |
| POST | `/wardrobes` | Bearer | Create wardrobe |
| DELETE | `/wardrobes/{id}` | Bearer | Delete wardrobe |
| GET | `/wardrobes/{id}/items` | Bearer | List wardrobe items |
| POST | `/wardrobes/{id}/items` | Bearer | Add item to wardrobe |
| PATCH | `/wardrobes/{id}/items/{item_id}` | Bearer | Update item |
| DELETE | `/wardrobes/{id}/items/{item_id}` | Bearer | Remove item |
| POST | `/wardrobes/{id}/outfits` | Bearer | Create outfit |
| GET | `/wardrobes/{id}/outfits` | Bearer | List outfits |

### Style DNA

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/style-dna/quiz` | Public | Quiz definition (35 questions) |
| POST | `/style-dna/quiz/start` | Bearer | Start quiz session |
| POST | `/style-dna/quiz/{session_id}/respond` | Bearer | Answer one question |
| POST | `/style-dna/quiz/{session_id}/complete` | Bearer | Complete + compute archetypes |
| POST | `/style-dna/generate` | Bearer | Generate full Style DNA report |
| GET | `/style-dna/report` | Bearer | Current active report |
| GET | `/style-dna/report/{id}` | Bearer | Specific report |
| GET | `/style-dna/report/history` | Bearer | All reports |
| GET | `/style-dna/report/{id}/section/{section}` | Bearer | One section |

### Subscriptions

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/subscriptions/plans` | Public | All plans with pricing |
| GET | `/subscriptions/me` | Bearer | User subscription + usage |
| GET | `/subscriptions/usage` | Bearer | Current period counters |
| POST | `/subscriptions/check` | Bearer | Feature gate check |
| POST | `/subscriptions/upgrade` | Bearer | Initiate plan upgrade |
| POST | `/subscriptions/cancel` | Bearer | Cancel at period end |
| POST | `/subscriptions/webhook/razorpay` | HMAC | Razorpay webhook |
| POST | `/subscriptions/webhook/stripe` | Stripe | Stripe webhook |

### Chat (AI Beauty Assistant)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/chat/message` | Bearer | Send message, get AI response |
| GET | `/chat/history` | Bearer | Conversation history |
| DELETE | `/chat/history` | Bearer | Clear history |

### Admin

| Method | Path | Auth | Role |
|---|---|---|---|
| GET | `/admin/dashboard` | Bearer | ADMIN |
| GET | `/admin/users` | Bearer | ADMIN |
| GET | `/admin/users/{id}` | Bearer | ADMIN |
| PATCH | `/admin/users/{id}/role` | Bearer | ADMIN |
| DELETE | `/admin/users/{id}` | Bearer | ADMIN |
| GET | `/admin/analytics/ai` | Bearer | ADMIN |
| GET | `/admin/queue/status` | Bearer | ADMIN |

---

## Recommendation Service (port 8003) — `/api/v1`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/recommendations` | Internal | Hybrid recommendations |
| POST | `/recommendations/feedback` | Internal | Click/save/purchase feedback |
| POST | `/interactions` | Internal | Record interaction event |
| GET | `/products` | Public | Search + filter catalog |
| GET | `/products/{id}` | Public | Product detail |
| GET | `/products/{id}/similar` | Public | Similar products (CB + CF) |
| GET | `/products/{id}/reviews` | Public | Product reviews |
| GET | `/categories` | Public | Category tree |
| GET | `/brands` | Public | Brand list |
| GET | `/alternatives/{product_id}` | Public | Smart affordable alternatives |
| POST | `/alternatives/compare/shade` | Public | Shade ΔE comparison |
| POST | `/alternatives/compare/ingredients` | Public | Ingredient Jaccard |
| POST | `/alternatives/compare/fragrance` | Public | Note pyramid comparison |

---

## Facial Analysis Service (port 8010) — `/api/v1`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/analyze` | Internal | Run full analysis pipeline |
| GET | `/health` | Public | Service health |

Pipeline output includes:
- `face_shape`: oval / round / square / heart / oblong / diamond
- `skin_tone.tone`: fair / light / medium / olive / tan / deep
- `skin_tone.undertone`: cool / warm / neutral
- `skin_tone.ita_angle`: float (ITA° measurement)
- `skin_tone.fitzpatrick`: int (1–6)
- `acne_analysis.severity`: none / mild / moderate / severe
- `hair_analysis.dominant_color`: hex string
- `symmetry.overall_score`: float (0–1)

---

## Virtual Try-On Service (port 8020) — `/api/v1`

| Method | Path | Content-Type | Description |
|---|---|---|---|
| POST | `/tryon/makeup` | multipart/form-data | Lipstick/foundation/eyeshadow AR |
| POST | `/tryon/hair` | multipart/form-data | Hair colour simulation |
| POST | `/wardrobe/classify` | multipart/form-data | Classify clothing item |
| POST | `/wardrobe/outfits` | application/json | Generate outfit combinations |
| POST | `/wardrobe/capsule` | application/json | Capsule wardrobe analysis |
| POST | `/celebrity/match` | multipart/form-data | Celebrity style matching |
| GET | `/health` | — | Service health |

### Try-On request example
```bash
curl -X POST http://localhost:8020/api/v1/tryon/makeup \
  -F "file=@selfie.jpg" \
  -F "hex_color=#C41E3A" \
  -F "try_on_type=lipstick" \
  -F "intensity=0.8"
```

### Response
```json
{
  "success": true,
  "try_on_type": "lipstick",
  "applied_hex": "#C41E3A",
  "result_b64": "/9j/4AAQSkZJRgABA...",
  "processing_ms": 243,
  "face_detected": true
}
```

---

## Rate Limiting

| Zone | Limit | Applied to |
|---|---|---|
| `auth_limit` | 5 req/min | `/auth/login`, `/auth/register` |
| `ai_limit` | 10 req/min | `/analysis/scan`, `/tryon/*`, `/celebrity/*` |
| `api_limit` | 60 req/min | All other `/api/v1/*` |
| `global_limit` | 120 req/min | All requests |

Exceeded limit response: `HTTP 429 Too Many Requests` with `Retry-After` header.

---

## Authentication

All protected endpoints require:
```
Authorization: Bearer <access_token>
```

Access tokens expire in 15 minutes. Use `/auth/refresh` with the refresh token to get a new access token. Refresh tokens are rotated on each use (single-use).
