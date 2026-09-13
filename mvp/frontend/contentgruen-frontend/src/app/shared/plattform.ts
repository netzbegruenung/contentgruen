/**
 * Die Plattform eines Links, rein aus dem Hostnamen abgeleitet.
 *
 * Zweck ist der Filter im Fangkorb: Wer kein Instagram-Konto hat, kann einen
 * Instagram-Einwurf nicht ansehen und blendet ihn aus. Deshalb gibt es nur die
 * Plattformen, die dafuer ein Konto verlangen, und fuer alles andere "Web".
 */
export type Plattform = 'instagram' | 'youtube' | 'tiktok' | 'web';

/** Alle Plattformen in Anzeigereihenfolge. */
export const PLATTFORMEN: ReadonlyArray<{ wert: Plattform; name: string }> = [
  { wert: 'instagram', name: 'Instagram' },
  { wert: 'youtube', name: 'YouTube' },
  { wert: 'tiktok', name: 'TikTok' },
  { wert: 'web', name: 'Web' },
];

const DOMAINS: ReadonlyArray<[Plattform, string[]]> = [
  ['instagram', ['instagram.com']],
  ['youtube', ['youtube.com', 'youtu.be']],
  ['tiktok', ['tiktok.com']],
];

/**
 * Die Plattform zu einem Link, oder null ohne Link.
 *
 * Subdomains zaehlen mit (m.youtube.com, vm.tiktok.com), aehnlich klingende
 * Domains nicht (notinstagram.com). Eine unlesbare Adresse ist trotzdem ein
 * Link und zaehlt als Web.
 */
export function plattformAusUrl(url: string | null | undefined): Plattform | null {
  const adresse = url?.trim();
  if (!adresse) {
    return null;
  }

  let host: string;
  try {
    host = new URL(adresse).hostname.toLowerCase();
  } catch {
    return 'web';
  }

  for (const [plattform, domains] of DOMAINS) {
    if (domains.some((domain) => host === domain || host.endsWith(`.${domain}`))) {
      return plattform;
    }
  }
  return 'web';
}

export function plattformName(plattform: Plattform): string {
  return PLATTFORMEN.find((eintrag) => eintrag.wert === plattform)?.name ?? 'Web';
}
