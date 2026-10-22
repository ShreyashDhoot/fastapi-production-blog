# Backend Learning Notes

This document tracks your progress through Python backend development concepts, architectures, and practices.

---

## 1. Client vs. Server Architecture & Validation
- **Client Side:** Code running directly on the user's device (browser/mobile). Can perform quick cosmetic or UI validation, but **cannot be trusted** because users can inspect, modify, or bypass it.
- **Server Side:** Code running on the backend host (Python/FastAPI). Must enforce all core business rules, permissions, and data integrity checks.
- **Network Failures:** If connectivity drops, the client notices immediately when attempting to send a request; the server remains unaware of requests that never reach its door.

---

## 2. Web Communication & The Role of JavaScript
- **HTTP Methods:** HTML `<form>` elements natively only support `GET` and `POST`.
- **Why Frontend JS is Used in APIs:** Modern REST APIs use verbs like `PATCH` (partial updates) and `DELETE`. JavaScript (`fetch`) allows web pages to send these methods and update the UI in-place without a full-page browser refresh.
- **HTTP Status Codes Encountered:**
  - `200 OK`: Request succeeded with a response body.
  - `201 Created`: Resource successfully created.
  - `204 No Content`: Action succeeded (e.g., delete), with nothing needed in the response body.
  - `404 Not Found`: Target resource does not exist.
  - `422 Unprocessable Entity`: Request format was understood, but fields failed validation (e.g. required field missing or wrong type).

---

## 3. Stateless Authentication (JWT & Bearer Tokens)

### The Metaphor
- **The Passport:** Username + Password (used once at login to prove identity).
- **The Wristband:** The Access Token (Bearer Token / JWT) stamped by the server and worn by the client for subsequent requests.
- **Bearer:** Means "whoever carries this token is granted the access stamped on it."

### Token Anatomy: `Header.Payload.Signature`
1. **Header:** Algorithm info (e.g. `HS256`), plain text encoded in Base64.
2. **Payload:** User claims (e.g. `{"sub": "user_id", "exp": <timestamp>}`), plain text encoded in Base64. Not encrypted; readable by anyone.
3. **Signature:** Cryptographic seal generated on the server using `Header + Payload + SECRET_KEY`.

### The Verification Loop (Stateless Verification)
- The client sends the entire token in the `Authorization: Bearer <token>` header.
- The server reads the plain payload directly from Base64.
- The server recalculates what the signature should be using its own local `SECRET_KEY` (from `.env`).
- If the calculated signature matches the client's signature, the payload has not been tampered with.
- **No database query is required** to verify that a token is genuine.

### Expiration (`exp`)
- Tokens store an exact expiration timestamp in the payload.
- The server compares `exp` against its own system clock.
- If a client attempts to edit the `exp` timestamp, the signature verification fails immediately.

### Refresh Tokens vs. Access Tokens
- **Access Token:** Short-lived (15–60 mins) for frequent API calls; limits the damage if intercepted.
- **Refresh Token:** Long-lived (days/months), stored securely (e.g. `HttpOnly` cookies); used only at `/refresh` to issue new access tokens without requiring the user to re-enter passwords.

---

## 4. Current Progress & Next Topics
- [x] Topic 1: How the web works (HTTP, requests/responses, status codes)
- [x] Topic 3: FastAPI basics (routes, schemas, debugging 422 errors)
- [x] Topic 6: Authentication theory (JWT, secret keys, bearer tokens, expiration)
- [ ] Topic 6 (Practical): Integrating token-based authorization into FastAPI endpoints (`Depends(oauth2_scheme)`)
- [ ] Topic 6 (Practical): Storing and sending tokens from the frontend
- [ ] Topic 5: Database migrations & relationships
