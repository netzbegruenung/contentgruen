#!/bin/sh
# Chromium fuer die Frontend-Tests in der CI (.woodpecker/ci.yaml, Schritt frontend).
# Der Schritt laeuft als root, dort startet Chrome nur ohne Sandbox; /dev/shm ist im
# Container klein. Der Wrapper unter CHROME_BIN setzt beides.
set -eu
apt-get update -qq
apt-get install -y -qq --no-install-recommends chromium >/dev/null
cat > /usr/local/bin/chromium-ci <<'SKRIPT'
#!/bin/sh
exec /usr/bin/chromium --no-sandbox --disable-dev-shm-usage "$@"
SKRIPT
chmod +x /usr/local/bin/chromium-ci
/usr/local/bin/chromium-ci --version
