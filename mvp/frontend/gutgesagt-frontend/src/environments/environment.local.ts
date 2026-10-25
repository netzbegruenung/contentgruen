export const environment = {
  production: false,
  baseUrl: '', // Relative Aufrufe; ng serve leitet sie per proxy.conf.json an das BFF (5054)
  useKeycloak: 'false',
  gitSha: 'dev'
};
