# ADR-003: LAN TLS via Traefik and Ed25519 Signed Audit Checkpoints

- **Status:** Accepted (Phase 0/1)
- **Date:** 2026-11-24
- **Decisions covered:** `O-05`, `O-06`, `FR-SEC-01`, `FR-SEC-10`, `FR-SEC-11`

## Context
Shared campus Wi-Fi/LAN environments cannot be assumed private (Maksakha & Vanijja, 2026), so plaintext HTTP exposes credentials and exam responses to LAN eavesdropping/MITM. Separately, a plain hash chain in the database can be rewritten by a compromised privileged host user unless anchored by a protected signing key (Crosby & Wallach, 2009).

## Decision
1. **LAN TLS (`O-05`):**
   - Local development runs Traefik on `:80` (HTTP) for frictionless iteration.
   - Campus LAN deployments enable Traefik `:443` (HTTPS) using a file-provider TLS configuration pointing to a local private-CA certificate (`mkcert` or campus IT CA) with zero public Internet / ACME requirement.
2. **Audit Signing Key Protection (`O-06`):**
   - Audit events are stored append-only with hash chaining (`prev_hash` -> `event_hash`).
   - Periodic checkpoints (`signed_audit_checkpoints`) are signed using an **Ed25519** private key mounted as a read-only secret file outside the database and inaccessible to ordinary application users; the public verification key is published for independent verification.

## Consequences
- **Positive:** Protects candidate credentials and answers on shared campus Wi-Fi without needing Internet; prevents silent database-only rewriting of audit history.
- **Trade-offs:** Campus deployments require distributing the private CA root certificate (or documenting the risk if an operator explicitly disables TLS); root host compromise remains a documented residual risk in [04_THREAT_MODEL.md](../../specifications/04_THREAT_MODEL.md).
