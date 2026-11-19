#!/bin/sh
# Chromium fuer die Frontend-Tests in der CI (.woodpecker/ci.yaml, Schritt frontend).
# Der Schritt laeuft als root, dort startet Chrome nur ohne Sandbox; /dev/shm ist im
# Container klein. Der Wrapper unter CHROME_BIN setzt beides.
# Das CI-Image fuer Node (Dockerfile.ci, Ziel ci-node) fuehrt dieses Skript beim Bauen aus:
# Dort ist der Wrapper schon da und der Schritt spart apt-get.
set -eu
if [ -x /usr/local/bin/chromium-ci ]; then
  echo "Chromium aus dem CI-Image"
  exec /usr/local/bin/chromium-ci --version
fi
apt-get update -qq
apt-get install -y -qq --no-install-recommends chromium >/dev/null
cat > /usr/local/bin/chromium-ci <<'SKRIPT'
#!/bin/sh
exec /usr/bin/chromium --no-sandbox --disable-dev-shm-usage "$@"
SKRIPT
chmod +x /usr/local/bin/chromium-ci
/usr/local/bin/chromium-ci --version
