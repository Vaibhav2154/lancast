#!/usr/bin/env bash
# Generate a local private LAN CA and SAN server certificate for Traefik (ADR-003, O-05).
# Requires zero Internet connectivity; uses standard OpenSSL only.
#
# Usage:
#   ./infrastructure/scripts/generate-lan-certs.sh [LAN_IP_OR_HOST ...]
# Example:
#   ./infrastructure/scripts/generate-lan-certs.sh 192.168.1.50 lancast.local

set -euo pipefail

CERT_DIR="$(cd "$(dirname "$0")/../.." && pwd)/infrastructure/gateway/certs"
mkdir -p "$CERT_DIR"
chmod 700 "$CERT_DIR"

CA_KEY="$CERT_DIR/lancast-ca.key"
CA_CRT="$CERT_DIR/lancast-ca.crt"
SRV_KEY="$CERT_DIR/lancast.key"
SRV_CSR="$CERT_DIR/lancast.csr"
SRV_CRT="$CERT_DIR/lancast.crt"
EXT_CFG="$CERT_DIR/san.cnf"

# Always include localhost and 127.0.0.1 for local verification, plus all provided hosts/IPs.
SANS=("DNS:localhost" "IP:127.0.0.1")
for arg in "$@"; do
  if [[ "$arg" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] || [[ "$arg" == *:* ]]; then
    SANS+=("IP:$arg")
  else
    SANS+=("DNS:$arg")
  fi
done

SAN_JOINED="$(IFS=,; echo "${SANS[*]}")"

if [[ ! -f "$CA_KEY" || ! -f "$CA_CRT" ]]; then
  echo "Generating LANCAST local private CA..."
  openssl req -x509 -new -nodes -newkey rsa:4096 -sha256 -days 1825 \
    -subj "/CN=LANCAST Local Campus CA/O=LANCAST" \
    -keyout "$CA_KEY" -out "$CA_CRT" >/dev/null 2>&1
  chmod 600 "$CA_KEY"
  chmod 644 "$CA_CRT"
fi

cat > "$EXT_CFG" <<EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = $SAN_JOINED
EOF

echo "Generating LANCAST server certificate for: $SAN_JOINED"
openssl req -new -nodes -newkey rsa:2048 \
  -subj "/CN=lancast.local/O=LANCAST" \
  -keyout "$SRV_KEY" -out "$SRV_CSR" >/dev/null 2>&1

openssl x509 -req -in "$SRV_CSR" -CA "$CA_CRT" -CAkey "$CA_KEY" -CAcreateserial \
  -out "$SRV_CRT" -days 825 -sha256 -extfile "$EXT_CFG" >/dev/null 2>&1

rm -f "$SRV_CSR" "$EXT_CFG" "$CERT_DIR/lancast-ca.srl"
chmod 600 "$SRV_KEY"
chmod 644 "$SRV_CRT"

echo "Generated certificates in $CERT_DIR:"
echo "  CA cert (distribute/trust on campus clients): $CA_CRT"
echo "  Server cert & key (mounted by Traefik):       $SRV_CRT / $SRV_KEY"
