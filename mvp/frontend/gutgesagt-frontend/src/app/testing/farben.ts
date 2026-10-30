/** Eine CSS-Farbe so, wie der Browser sie auflöst: `rgb(r, g, b)`. */
export function aufgeloest(farbe: string): string {
  const probe = document.createElement('span');
  probe.style.color = farbe;
  document.body.appendChild(probe);
  const rgb = getComputedStyle(probe).color;
  probe.remove();
  return rgb;
}

/** Wert einer Farbvariable aus dem geladenen Theme (`src/theme/custom-theme.scss`), z. B. `--primary-dark`. */
export function themaFarbe(variable: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(variable).trim();
}
