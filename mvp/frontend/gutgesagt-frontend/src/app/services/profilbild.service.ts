import { Injectable, computed, signal } from '@angular/core';
import { UserInfo } from '../auth/auth.service';

/** Ein waehlbares Profilbild. Die Kennung ist neutral, die Dateinamen sind es nicht. */
export interface Profilbild {
  id: string;
  url: string;
  alt: string;
}

/**
 * Lokal ausgeliefert statt von der DiceBear-API: sonst ginge bei jedem
 * Seitenaufruf die IP-Adresse an einen Drittanbieter. Erzeugt von
 * scripts/generate-avatars.mjs.
 */
export const ANONYMES_PROFILBILD = '/avatars/anon-question.svg';

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
 * Alle Bilder aus public/avatars. Die Reihenfolge mischt bewusst: keine Einteilung
 * nach Geschlecht, und die Beschreibungen sagen, was zu sehen ist.
 */
const BILDER: readonly Profilbild[] = [
  { id: 'formen', url: '/avatars/anon-shapes.svg', alt: 'Geometrische Formen in Blau' },
  { id: 'gesicht-01', url: '/avatars/female1.svg', alt: 'Lächelndes Gesicht mit kurzen dunklen Haaren' },
  { id: 'gesicht-02', url: '/avatars/male1.svg', alt: 'Lächelndes Gesicht mit grauem Haarkranz' },
  { id: 'gesicht-03', url: '/avatars/female3.svg', alt: 'Lächelndes Gesicht mit Brille und Haarknoten' },
  { id: 'gesicht-04', url: '/avatars/male2.svg', alt: 'Lachendes Gesicht mit roten Locken' },
  { id: 'gesicht-05', url: '/avatars/female4.svg', alt: 'Lachendes Gesicht mit Bart und Blumen im Haar' },
  { id: 'gesicht-06', url: '/avatars/male3.svg', alt: 'Lachendes Gesicht mit langen hellen Haaren' },
  { id: 'gesicht-07', url: '/avatars/anon-female.svg', alt: 'Lachendes Gesicht mit hellblonden Haaren und Augenklappe' },
  { id: 'gesicht-08', url: '/avatars/male4.svg', alt: 'Lachendes Gesicht mit langen dunklen Haaren' },
  { id: 'gesicht-09', url: '/avatars/female5.svg', alt: 'Lächelndes Gesicht mit kurzen rotbraunen Haaren' },
  { id: 'gesicht-10', url: '/avatars/male5.svg', alt: 'Lächelndes Gesicht mit kurzen rosa Haaren' },
  { id: 'gesicht-11', url: '/avatars/female2.svg', alt: 'Lachendes Gesicht mit Haarknoten und Augenklappe' },
  { id: 'gesicht-12', url: '/avatars/anon-male.svg', alt: 'Lachendes Gesicht mit Blumenkranz im Haar' },
  { id: 'gesicht-13', url: '/avatars/male6.svg', alt: 'Lachendes Gesicht mit langen weißen Locken' },
  { id: 'gesicht-14', url: '/avatars/female6.svg', alt: 'Lachendes Gesicht mit kinnlangen Haaren und Jackett' },
];

const FRAGEZEICHEN: Profilbild = { id: 'fragezeichen', url: ANONYMES_PROFILBILD, alt: 'Fragezeichen auf grauem Grund' };

/** Hoechstens zwei Anfangsbuchstaben, je einer aus den ersten Namensteilen mit Buchstaben. */
export function initialen(name: string | null): string {
  const buchstaben = (name ?? '')
    .split(/\s+/)
    .map((teil) => teil.match(/\p{L}/u)?.[0])
    .filter((b): b is string => !!b)
    .slice(0, 2);
  return buchstaben.length ? buchstaben.join('').toUpperCase() : '?';
}

/** Gruener Grund, weisse Schrift; Satz wie beim Fragezeichen in generate-avatars.mjs. */
function initialenBild(name: string | null): string {
  const svg =
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">' +
    '<rect width="100" height="100" fill="#008939" />' +
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
    FRAGEZEICHEN,
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
    return id === INITIALEN || id === FRAGEZEICHEN.id || BILDER.some((bild) => bild.id === id);
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
