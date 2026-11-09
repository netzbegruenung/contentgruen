import { ROUTES } from './constants/app.constants';

export const LINK_KOPIERT = 'Link kopiert.';
export const LINK_NICHT_KOPIERT = 'Kopieren hat nicht geklappt.';

/**
 * Die Adresse, unter der andere den Beitrag oeffnen (#603), ohne Query und Anker.
 * Gebraucht auf der Beitragsseite und im ⋮-Menue der Karte (#640).
 */
export function beitragsLink(id: string, origin: string = window.location.origin): string {
  return `${origin}${ROUTES.BEITRAG}/${encodeURIComponent(id)}`;
}
