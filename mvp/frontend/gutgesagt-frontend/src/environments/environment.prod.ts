export const environment = {
  production: true,
  baseUrl: '${API_BASE_URL}',
  useKeycloak: '${USE_KEYCLOAK}',
  // Commit des Builds, setzt replace-env.sh aus dem Build-Arg GIT_SHA ein
  gitSha: '${GIT_SHA}',
  // Version aus dem Git-Tag beim Release-Build (Build-Arg APP_VERSION), sonst leer: package.json gilt
  appVersion: '${APP_VERSION}'
};
