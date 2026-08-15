# Deploying OmniBrain to omnibrain.in

This gets `https://omnibrain.in` serving the real app: nginx terminating
TLS, proxying `/` to the Streamlit frontend and `/api/` to the FastAPI
backend, with auto-renewing Let's Encrypt certificates.

I can't do the steps below myself — I have no access to your domain's
DNS, no server to run this on, and no network access from this sandbox.
Everything under `deploy/` and the root `docker-compose.yml` is built
and ready; this is what running it looks like.

## 0. What you need before starting

- **A server** with a public IP — any VPS works (DigitalOcean, Hetzner,
  AWS Lightsail, etc.). 2GB RAM minimum; `sentence-transformers` and
  `chromadb` are not tiny. Ubuntu 22.04/24.04 assumed below.
- **Ownership of omnibrain.in** with access to its DNS settings, at
  whatever registrar you bought it from.
- **A Gemini API key** (for `/chat` to actually generate answers).

## 1. Point the domain at the server

In your DNS provider's dashboard, add:

| Type | Host | Value                  |
|------|------|------------------------|
| A    | @    | `<your server's IP>`   |
| A    | www  | `<your server's IP>`   |

DNS propagation can take anywhere from a few minutes to a few hours.
Confirm it's live before continuing:

```bash
dig +short omnibrain.in
# should print your server's IP
```

Let's Encrypt verifies domain ownership by connecting to
`http://omnibrain.in` directly — the cert step in §4 will fail until
this resolves correctly.

## 2. Prepare the server

SSH into the server, then install Docker:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker   # or log out/in
```

Open ports 80 and 443 in whatever firewall/security-group the server
uses (most cloud providers block everything but SSH by default).

## 3. Get the project onto the server

Copy the `omnibrain/` folder there however you prefer — `scp`, `rsync`,
or pushing it to a private git repo and cloning. Example with `rsync`:

```bash
rsync -avz --exclude '__pycache__' ./omnibrain/ user@your-server-ip:/opt/omnibrain/
ssh user@your-server-ip
cd /opt/omnibrain
```

Set the backend's real config:

```bash
cp backend/.env.example backend/.env
nano backend/.env   # set GEMINI_API_KEY at minimum
```

## 4. Get the first SSL certificate

```bash
chmod +x deploy/init-letsencrypt.sh
./deploy/init-letsencrypt.sh you@your-email.com
```

This script (see `deploy/init-letsencrypt.sh`) starts nginx in a
bootstrap HTTP-only mode, requests the certificate from Let's Encrypt
via the webroot challenge, then swaps in the real HTTPS config
(`deploy/nginx/omnibrain.conf`) and reloads nginx. It only needs to
run once — renewal is automatic afterward (see §6).

## 5. Start everything

```bash
docker compose up -d --build
```

This builds and starts four containers: `backend`, `frontend`,
`nginx`, and `certbot` (which just sits in the background renewing
the cert every ~60 days). Check they're healthy:

```bash
docker compose ps
docker compose logs -f backend    # watch for startup errors
```

Visit `https://omnibrain.in` — you should see the OmniBrain dashboard,
and the sidebar should show **Backend Connected** / **AI Engine Active**.

## 6. Renewal (automatic, nothing to do)

The `certbot` service in `docker-compose.yml` runs `certbot renew`
every 12 hours in a loop; Let's Encrypt certs are valid for 90 days,
so this renews well before expiry. Nginx needs a reload after a
renewal to pick up the new cert — if you notice the cert not
refreshing, `docker compose exec nginx nginx -s reload` picks it up
manually.

## 7. Updating the app later

```bash
cd /opt/omnibrain
# pull/copy your changes in
docker compose up -d --build
```

Docker rebuilds only what changed; the named volumes
(`omnibrain-uploads`, `omnibrain-reports`, `omnibrain-vectorstore`)
persist across rebuilds, so indexed documents and websites survive
an update.

## Troubleshooting

- **Cert request fails with a timeout/connection error** — DNS hasn't
  propagated yet, or port 80 is blocked by a firewall. Re-check §1 and
  the firewall/security-group rules.
- **Frontend loads but shows "Backend Offline"** — check
  `docker compose logs backend`. Most common cause: `GEMINI_API_KEY`
  missing doesn't block startup, but a missing/invalid Gemini key
  will surface as errors only once you actually ask a question.
- **502 from nginx** — a container crashed or is still starting.
  `docker compose ps` shows status; `docker compose logs <service>`
  shows why.
- **Streamlit loads but nothing updates when you click things** —
  usually a proxy dropping WebSocket upgrade headers. Confirm
  `deploy/nginx/omnibrain.conf` is the file actually mounted (not the
  bootstrap one) — `docker compose exec nginx cat /etc/nginx/conf.d/omnibrain.conf`
  should show the `location /api/` block.
