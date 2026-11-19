import { ROUTES } from './constants/app.constants';

/**
 * Die Adresse, unter der andere den Beitrag oeffnen (#603), ohne Query und Anker.
 * Gebraucht beim Teilen auf der Beitragsseite und an der Karte (#640, B7).
 */
export function beitragsLink(id: string, origin: string = window.location.origin): string {
  return `${origin}${ROUTES.BEITRAG}/${encodeURIComponent(id)}`;
}
