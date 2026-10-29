import { Injectable } from '@angular/core';

/**
 * Lokal ausgeliefert statt von der DiceBear-API: sonst ginge bei jedem
 * Seitenaufruf die IP-Adresse an einen Drittanbieter. Erzeugt von
 * scripts/generate-avatars.mjs.
 */
export const ANONYMER_AVATAR = '/avatars/anon-question.svg';

export const PROFILBILDER: readonly string[] = [
  '/avatars/female1.svg',
  '/avatars/female2.svg',
  '/avatars/female3.svg',
  '/avatars/female4.svg',
  '/avatars/female5.svg',
  '/avatars/female6.svg',
  '/avatars/male1.svg',
  '/avatars/male2.svg',
  '/avatars/male3.svg',
  '/avatars/male4.svg',
  '/avatars/male5.svg',
  '/avatars/male6.svg',
];

/** Schluessel, unter denen fruehere Versionen das Bild im sessionStorage ablegten. */
export const ALTE_PROFILBILD_SCHLUESSEL: readonly string[] = [
  'profilePicture',
  'anonymousAvatar',
  'userAvatar',
];

/**
 * Profilbild im Kopf der Seite. Es liegt nur im Speicher der laufenden Seite, nicht
 * im Browser: Ein ausgelostes Bild ist keine ausdrücklich gewünschte Funktion und
 * daher nicht von § 25 Abs. 2 TDDDG gedeckt (#437). Nach dem Neuladen wird neu gelost.
 */
@Injectable({ providedIn: 'root' })
export class ProfilbildService {
  private ausgelost: string | null = null;

  constructor() {
    this.alteEintraegeLoeschen();
  }

  /** Besucher sehen den anonymen Avatar, Mitwirkende ein einmal je Seite ausgelostes Bild. */
  profilbild(angemeldet: boolean): string {
    if (!angemeldet) {
      return ANONYMER_AVATAR;
    }
    this.ausgelost ??= PROFILBILDER[Math.floor(Math.random() * PROFILBILDER.length)];
    return this.ausgelost;
  }

  private alteEintraegeLoeschen(): void {
    try {
      ALTE_PROFILBILD_SCHLUESSEL.forEach((schluessel) => sessionStorage.removeItem(schluessel));
    } catch {
      // Ohne Zugriff auf den Storage liegt dort auch nichts zum Loeschen.
    }
  }
}
