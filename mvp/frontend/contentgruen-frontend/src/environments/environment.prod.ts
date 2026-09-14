export const environment = {
  production: true,
  baseUrl: '${API_BASE_URL}',
  useKeycloak: '${USE_KEYCLOAK}',
  // Commit des Builds, setzt replace-env.sh aus dem Build-Arg GIT_SHA ein
  gitSha: '${GIT_SHA}'
};
