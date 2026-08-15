#!/usr/bin/env bash
#
# One-time setup: obtains the first Let's Encrypt certificate for
# omnibrain.in, then swaps nginx over to the full HTTPS config.
# Run this once, from the project root, on the actual server —
# omnibrain.in's DNS A records must already point at this server's
# IP before you run it (Let's Encrypt verifies domain ownership by
# hitting http://omnibrain.in/.well-known/acme-challenge/... directly).
#
# Usage:
#   chmod +x deploy/init-letsencrypt.sh
#   ./deploy/init-letsencrypt.sh you@example.com

set -euo pipefail

DOMAINS=(omnibrain.in www.omnibrain.in)
EMAIL="${1:-}"
RSA_KEY_SIZE=4096
DATA_PATH="./deploy/certbot"
NGINX_CONF="./deploy/nginx/omnibrain.conf"
NGINX_INITIAL_CONF="./deploy/nginx/omnibrain-initial.conf"

if [ -z "$EMAIL" ]; then
  echo "Usage: $0 you@example.com"
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required. Install it first (see DEPLOY.md)."
  exit 1
fi

echo "### Switching nginx to its bootstrap (HTTP-only) config until a certificate exists..."
cp "$NGINX_CONF" "$NGINX_CONF.final-backup"
cp "$NGINX_INITIAL_CONF" "$NGINX_CONF"

mkdir -p "$DATA_PATH/conf" "$DATA_PATH/www"

echo "### Starting nginx..."
docker compose up -d nginx

echo "### Requesting Let's Encrypt certificate for: ${DOMAINS[*]}"
domain_args=""
for domain in "${DOMAINS[@]}"; do
  domain_args="$domain_args -d $domain"
done

docker compose run --rm --entrypoint "\
  certbot certonly --webroot -w /var/www/certbot \
    $domain_args \
    --email $EMAIL \
    --rsa-key-size $RSA_KEY_SIZE \
    --agree-tos \
    --non-interactive" certbot

echo "### Restoring the full HTTPS nginx config..."
cp "$NGINX_CONF.final-backup" "$NGINX_CONF"
rm -f "$NGINX_CONF.final-backup"

echo "### Reloading nginx with HTTPS enabled..."
docker compose exec nginx nginx -s reload || docker compose restart nginx

echo "### Done. https://omnibrain.in should now be live with a valid certificate."
echo "### The 'certbot' service in docker-compose.yml auto-renews it (checks every 12h)."
