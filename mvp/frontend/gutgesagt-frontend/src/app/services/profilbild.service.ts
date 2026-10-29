import { Injectable, computed, signal } from '@angular/core';
import { UserInfo } from '../auth/auth.service';

/** Ein waehlbares Profilbild. Die Kennung ist neutral, die Dateinamen sind es nicht. */
export interface Profilbild {
  id: string;
  url: string;
  alt: string;
}

/** Was Besucher im Kopf sehen; ein Profilbild haben nur Mitwirkende. */
export const ANONYMES_PROFILBILD = '/icons/Profile_avatar_placeholder_large.png';

/** Kennung der Option, die statt eines Bildes die Initialen der Person zeigt. */
export const INITIALEN = 'initialen';

/** Schluessel im localStorage. Er entsteht erst, wenn die Person ein Bild waehlt (#437). */
export const PROFILBILD_SCHLUESSEL = 'gutgesagt-profilbild';

/**
 * Schluessel, unter denen fruehere Versionen das Bild ungefragt im sessionStorage
 * ablegten. Das Aufraeumen kann entfallen, wenn keine Sitzung von vor #437 mehr offen ist.
 */
export const ALTE_PROFILBILD_SCHLUESSEL: readonly string[] = [
  'profilePicture',
  'anonymousAvatar',
  'userAvatar',
];

/**
 * Fluent Emoji 3D (Microsoft, MIT), erzeugt von scripts/profilbilder_holen.py; dort
 * stehen Quelle, Commit und dieselbe Reihenfolge. Lizenz in
 * public/avatars/FLUENT-EMOJI-LIZENZ.txt. Die Beschreibungen sagen, was zu sehen ist,
 * nicht welches Geschlecht.
 */
const MENSCHEN: readonly Profilbild[] = [
  { id: 'mensch-01', url: '/avatars/mensch-01.png', alt: 'Person mit langen braunen Haaren, mittlerer Hautton' },
  { id: 'mensch-02', url: '/avatars/mensch-02.png', alt: 'Person mit kurzen schwarzen Haaren, dunkler Hautton' },
  { id: 'mensch-03', url: '/avatars/mensch-03.png', alt: 'Person mit kurzen dunklen Haaren, heller Hautton' },
  { id: 'mensch-04', url: '/avatars/mensch-04.png', alt: 'Ältere Person mit grauem Haar, mitteldunkler Hautton' },
  { id: 'mensch-05', url: '/avatars/mensch-05.png', alt: 'Ältere Person mit grauem Haarkranz, mittelheller Hautton' },
  { id: 'mensch-06', url: '/avatars/mensch-06.png', alt: 'Ältere Person mit grauem Haar, dunkler Hautton' },
  { id: 'mensch-07', url: '/avatars/mensch-07.png', alt: 'Person mit Kopftuch, mittelheller Hautton' },
  { id: 'mensch-08', url: '/avatars/mensch-08.png', alt: 'Person mit Bart, mitteldunkler Hautton' },
  { id: 'mensch-09', url: '/avatars/mensch-09.png', alt: 'Person mit langen Locken, dunkler Hautton' },
  { id: 'mensch-10', url: '/avatars/mensch-10.png', alt: 'Person mit weißem Haar, heller Hautton' },
  { id: 'mensch-11', url: '/avatars/mensch-11.png', alt: 'Person im Rollstuhl, mittlerer Hautton' },
  { id: 'mensch-12', url: '/avatars/mensch-12.png', alt: 'Person mit langen roten Haaren, heller Hautton' },
  { id: 'mensch-13', url: '/avatars/mensch-13.png', alt: 'Person mit Glatze, mitteldunkler Hautton' },
  { id: 'mensch-14', url: '/avatars/mensch-14.png', alt: 'Person mit blonden Haaren, mittelheller Hautton' },
  { id: 'mensch-15', url: '/avatars/mensch-15.png', alt: 'Person mit kurzen Locken, mittlerer Hautton' },
  { id: 'mensch-16', url: '/avatars/mensch-16.png', alt: 'Gehörlose Person, die auf ihr Ohr zeigt, dunkler Hautton' },
  { id: 'mensch-17', url: '/avatars/mensch-17.png', alt: 'Person mit Blindenstock, mittelheller Hautton' },
  { id: 'mensch-18', url: '/avatars/mensch-18.png', alt: 'Person mit weißem Haar, mitteldunkler Hautton' },
  { id: 'mensch-19', url: '/avatars/mensch-19.png', alt: 'Person mit kurzen roten Haaren, mittlerer Hautton' },
  { id: 'mensch-20', url: '/avatars/mensch-20.png', alt: 'Person mit schwarzen Locken, heller Hautton' },
];

/** Natur und Tiere, keine politischen Symbole. */
const MOTIVE: readonly Profilbild[] = [
  { id: 'igel', url: '/avatars/igel.png', alt: 'Igel' },
  { id: 'sonnenblume', url: '/avatars/sonnenblume.png', alt: 'Sonnenblume' },
  { id: 'laubbaum', url: '/avatars/laubbaum.png', alt: 'Laubbaum' },
  { id: 'daumen-hoch', url: '/avatars/daumen-hoch.png', alt: 'Daumen hoch' },
  { id: 'setzling', url: '/avatars/setzling.png', alt: 'Setzling' },
  { id: 'schmetterling', url: '/avatars/schmetterling.png', alt: 'Schmetterling' },
  { id: 'biene', url: '/avatars/biene.png', alt: 'Biene' },
  { id: 'marienkaefer', url: '/avatars/marienkaefer.png', alt: 'Marienkäfer' },
  { id: 'eule', url: '/avatars/eule.png', alt: 'Eule' },
  { id: 'fuchs', url: '/avatars/fuchs.png', alt: 'Fuchs' },
  { id: 'katze', url: '/avatars/katze.png', alt: 'Katze' },
  { id: 'hund', url: '/avatars/hund.png', alt: 'Hund' },
  { id: 'schildkroete', url: '/avatars/schildkroete.png', alt: 'Schildkröte' },
  { id: 'pilz', url: '/avatars/pilz.png', alt: 'Pilz' },
  { id: 'kleeblatt', url: '/avatars/kleeblatt.png', alt: 'Vierblättriges Kleeblatt' },
  { id: 'sonne', url: '/avatars/sonne.png', alt: 'Sonne' },
  { id: 'erde', url: '/avatars/erde.png', alt: 'Erdkugel' },
  { id: 'fahrrad', url: '/avatars/fahrrad.png', alt: 'Fahrrad' },
  { id: 'tulpe', url: '/avatars/tulpe.png', alt: 'Tulpe' },
  { id: 'tannenbaum', url: '/avatars/tannenbaum.png', alt: 'Tannenbaum' },
];

/** Aus diesen 40 wird ohne eigene Wahl das feste Bild abgeleitet. */
const BILDER: readonly Profilbild[] = [...MENSCHEN, ...MOTIVE];

/** Hoechstens zwei Anfangsbuchstaben, je einer aus den ersten Namensteilen mit Buchstaben. */
export function initialen(name: string | null): string {
  const buchstaben = (name ?? '')
    .split(/\s+/)
    .map((teil) => teil.match(/\p{L}/u)?.[0])
    .filter((b): b is string => !!b)
    .slice(0, 2);
  return buchstaben.length ? buchstaben.join('').toUpperCase() : '?';
}

/** Weiss auf Tanne (--primary-dark), rund wie die uebrigen Bilder. */
function initialenBild(name: string | null): string {
  const svg =
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">' +
    '<circle cx="50" cy="50" r="50" fill="#005437" />' +
    '<text x="50%" y="50%" font-family="Arial, Helvetica, sans-serif" font-size="42" ' +
    `fill="#ffffff" text-anchor="middle" dy="15">${initialen(name)}</text>` +
    '</svg>';
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

/** FNV-1a: klein, ohne Abhaengigkeit, und dieselbe Kennung ergibt immer dasselbe Bild. */
function streuwert(text: string): number {
  let wert = 0x811c9dc5;
  for (let i = 0; i < text.length; i++) {
    wert ^= text.charCodeAt(i);
    wert = Math.imul(wert, 0x01000193);
  }
  return wert >>> 0;
}

/**
 * Profilbild im Kopf der Seite. Ohne Wahl ist es aus der Kennung abgeleitet und
 * nirgends gespeichert. Erst wenn die Person selbst ein Bild waehlt, merkt sich der
 * Browser diese Wahl im localStorage, bis sie sie zuruecksetzt (#437).
 */
@Injectable({ providedIn: 'root' })
export class ProfilbildService {
  private readonly person = signal<UserInfo | null>(null);
  private readonly wahl = signal<string | null>(null);

  /** Alle waehlbaren Bilder, die Initialen zuerst; sie haengen am Namen der Person. */
  readonly auswahl = computed<Profilbild[]>(() => [
    { id: INITIALEN, url: initialenBild(this.person()?.userName ?? null), alt: 'Deine Initialen auf grünem Grund' },
    ...BILDER,
  ]);

  /** Die Kennung der eigenen Wahl, oder null, solange die Person nicht gewaehlt hat. */
  readonly gewaehlt = this.wahl.asReadonly();

  readonly bild = computed<string>(() => {
    const person = this.person();
    if (!person?.isAuthenticated) {
      return ANONYMES_PROFILBILD;
    }
    const gewaehlt = this.auswahl().find((option) => option.id === this.wahl());
    if (gewaehlt) {
      return gewaehlt.url;
    }
    return BILDER[streuwert(person.userId ?? '') % BILDER.length].url;
  });

  constructor() {
    this.alteEintraegeLoeschen();
    this.wahl.set(this.gespeicherteWahl());
  }

  setzePerson(person: UserInfo | null): void {
    this.person.set(person);
  }

  /** Nur nach der ausdruecklichen Wahl im Dialog: erst dann wird etwas gespeichert. */
  waehlen(id: string): void {
    if (!this.istBekannt(id)) {
      return;
    }
    this.wahl.set(id);
    try {
      localStorage.setItem(PROFILBILD_SCHLUESSEL, id);
    } catch {
      // Ohne Storage gilt die Wahl eben nur, solange die Seite offen ist.
    }
  }

  zuruecksetzen(): void {
    this.wahl.set(null);
    this.entfernen(localStorage, PROFILBILD_SCHLUESSEL);
  }

  private istBekannt(id: string | null): id is string {
    return id === INITIALEN || BILDER.some((bild) => bild.id === id);
  }

  private gespeicherteWahl(): string | null {
    let gespeichert: string | null;
    try {
      gespeichert = localStorage.getItem(PROFILBILD_SCHLUESSEL);
    } catch {
      return null;
    }
    if (gespeichert !== null && !this.istBekannt(gespeichert)) {
      this.entfernen(localStorage, PROFILBILD_SCHLUESSEL);
      return null;
    }
    return gespeichert;
  }

  private alteEintraegeLoeschen(): void {
    ALTE_PROFILBILD_SCHLUESSEL.forEach((schluessel) => this.entfernen(sessionStorage, schluessel));
  }

  private entfernen(speicher: Storage, schluessel: string): void {
    try {
      speicher.removeItem(schluessel);
    } catch {
      // Ohne Zugriff auf den Storage liegt dort auch nichts zum Loeschen.
    }
  }
}
