// Vorschau wie Test/Produktion: /api/auth/modes antwortet lokal mit dem Modus dort
// (nur Keycloak-Anmeldung, keine Direktanmeldung); alles andere wie proxy.conf.json an das BFF.
// Aufruf: npx ng serve --proxy-config proxy.prod-modi.cjs (siehe docs/DEV-SETUP.md)
const ziel = { target: 'http://localhost:5054', secure: false };
module.exports = {
  '/api/auth/modes': {
    ...ziel,
    bypass(req, res) {
      res.setHeader('Content-Type', 'application/json');
      res.end(JSON.stringify({ keycloakEnabled: true, managedAuthEnabled: false }));
      return false;
    },
  },
  '/api': ziel,
  '/content': ziel,
  '/recent': ziel,
  '/getMetrics': ziel,
  '/report': ziel,
  '/reports': ziel,
};
