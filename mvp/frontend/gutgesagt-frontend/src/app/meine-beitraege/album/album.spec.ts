import { ContentResult } from '../../services/dtos/contributionDtos';
import { Thema } from '../../services/dtos/themenDtos';
import { Meilenstein } from '../../services/usage-tracking.service';
import {
  KEIN_FILTER,
  OHNE_THEMA,
  abschnittStand,
  beitraegeInThemen,
  abschnitte,
  albumEintrag,
  filterAktiv,
  filtern,
  kennzahlen,
  naechsterMeilenstein,
  stilAuswahl,
  suchform,
  themenAuswahl,
} from './album';

const KLIMA: Thema = { schluessel: 'klima', name: 'Klima', motiv: 'themen/klima.svg' };
const WOHNEN: Thema = { schluessel: 'wohnen', name: 'Wohnen', motiv: 'themen/wohnen.svg' };
const SOZIALES: Thema = { schluessel: 'soziales', name: 'Soziales', motiv: 'themen/soziales.svg' };

let laufend = 0;

function beitrag(felder: Partial<ContentResult> & { themen?: Thema[]; aussageText?: string } = {}): ContentResult {
  const { themen, aussageText, ...rest } = felder;
  laufend++;
  return {
    id: `b${laufend}`,
    created: `2026-11-${String(10 + (laufend % 10)).padStart(2, '0')}T10:00:00`,
    text: 'Gut gedämmte Häuser brauchen viel weniger Heizenergie.',
    content_type: 'commentary',
    title: 'Sanieren senkt die Nebenkosten',
    usage_count: 0,
    score: 0,
    aussage:
      themen === undefined && aussageText === undefined
        ? null
        : { id: `a${laufend}`, text: aussageText ?? 'Sanierung macht Mieten teuer.', themen: themen ?? [] },
    ...rest,
  };
}

describe('Album (album.ts)', () => {
  describe('albumEintrag', () => {
    it('zeigt die beantwortete Aussage als „Antwort auf“ und nimmt ihre Themen', () => {
      const eintrag = albumEintrag(beitrag({ themen: [KLIMA, WOHNEN], aussageText: 'Klimaschutz kostet nur.' }));

      expect(eintrag.karte.statement?.text).toBe('Klimaschutz kostet nur.');
      expect(eintrag.themen.map((t) => t.schluessel)).toEqual(['klima', 'wohnen']);
    });

    it('fuehrt Beitraege ohne Aussage ohne Thema und ohne „Antwort auf“', () => {
      const eintrag = albumEintrag(beitrag());

      expect(eintrag.karte.statement).toBeUndefined();
      expect(eintrag.themen).toEqual([]);
    });

    it('nimmt den Stil des Kommentars', () => {
      expect(albumEintrag(beitrag({ style: 'humorvoll' })).stil).toBe('humorvoll');
      expect(albumEintrag(beitrag({ content_type: 'generic_text' })).stil).toBeNull();
    });
  });

  describe('filtern', () => {
    const eintraege = () => [
      albumEintrag(beitrag({ id: 'waerme', title: 'Wärmepumpe lohnt sich', themen: [KLIMA], usage_count: 3, style: 'sachlich' })),
      albumEintrag(beitrag({ id: 'miete', title: 'Mietpreisbremse schützt', themen: [WOHNEN, SOZIALES], style: 'humorvoll' })),
      albumEintrag(beitrag({ id: 'ohne', title: 'Straßenbahn statt Stau', text: 'Kurz.' })),
    ];
    const ids = (liste: { karte: { id: string } }[]) => liste.map((e) => e.karte.id);

    it('findet ohne Umlaute und ß, Wort fuer Wort in beliebiger Reihenfolge', () => {
      expect(suchform('Straße Wärme')).toBe('strasse warme');
      expect(ids(filtern(eintraege(), { ...KEIN_FILTER, suche: 'warmepumpe' }))).toEqual(['waerme']);
      expect(ids(filtern(eintraege(), { ...KEIN_FILTER, suche: 'stau strassenbahn' }))).toEqual(['ohne']);
    });

    it('sucht auch in der Aussage, im Stil und in den Themen', () => {
      expect(ids(filtern(eintraege(), { ...KEIN_FILTER, suche: 'mieten teuer humorvoll' }))).toEqual(['miete']);
      expect(ids(filtern(eintraege(), { ...KEIN_FILTER, suche: 'soziales' }))).toEqual(['miete']);
    });

    it('filtert nach Thema, auch nach „Ohne Thema“, nach Stil und nach genutzt', () => {
      expect(ids(filtern(eintraege(), { ...KEIN_FILTER, thema: 'soziales' }))).toEqual(['miete']);
      expect(ids(filtern(eintraege(), { ...KEIN_FILTER, thema: OHNE_THEMA.schluessel }))).toEqual(['ohne']);
      expect(ids(filtern(eintraege(), { ...KEIN_FILTER, stil: 'sachlich' }))).toEqual(['waerme']);
      expect(ids(filtern(eintraege(), { ...KEIN_FILTER, nurGenutzt: true }))).toEqual(['waerme']);
    });

    it('erkennt, ob ein Filter gesetzt ist; Leerzeichen allein zaehlen nicht', () => {
      expect(filterAktiv(KEIN_FILTER)).toBeFalse();
      expect(filterAktiv({ ...KEIN_FILTER, suche: '   ' })).toBeFalse();
      expect(filterAktiv({ ...KEIN_FILTER, nurGenutzt: true })).toBeTrue();
    });
  });

  describe('abschnitte', () => {
    it('stellt einen Beitrag mit drei Themen in alle drei Abschnitte, „Ohne Thema“ zuletzt', () => {
      const liste = abschnitte([
        albumEintrag(beitrag({ id: 'drei', themen: [KLIMA, WOHNEN, SOZIALES] })),
        albumEintrag(beitrag({ id: 'ohne' })),
      ]);

      expect(liste.map((a) => a.thema.schluessel)).toEqual(['klima', 'wohnen', 'soziales', 'ohne-thema']);
      expect(liste.every((a) => a.eintraege.length === 1)).toBeTrue();
      expect(liste[3].thema).toEqual(OHNE_THEMA);
    });

    it('ordnet Abschnitte nach genutzten Beitraegen, darin die meistgenutzten zuerst', () => {
      const liste = abschnitte([
        albumEintrag(beitrag({ id: 'k1', themen: [KLIMA] })),
        albumEintrag(beitrag({ id: 'k2', themen: [KLIMA] })),
        albumEintrag(beitrag({ id: 'w1', themen: [WOHNEN], usage_count: 2 })),
        albumEintrag(beitrag({ id: 'w2', themen: [WOHNEN], usage_count: 9 })),
      ]);

      expect(liste.map((a) => a.thema.schluessel)).toEqual(['wohnen', 'klima']);
      expect(liste[0].eintraege.map((e) => e.karte.id)).toEqual(['w2', 'w1']);
      expect(abschnittStand(liste[0])).toBe('2 von 2 genutzt');
      expect(abschnittStand(liste[1])).toBe('2 Beiträge · noch keiner genutzt');
    });
  });

  describe('kennzahlen und Auswahl', () => {
    it('zaehlt jeden Beitrag einmal, auch wenn er in mehreren Abschnitten steht', () => {
      const eintraege = [
        albumEintrag(beitrag({ themen: [KLIMA, WOHNEN], usage_count: 4, nutzung_letzte_7_tage: 1 })),
        albumEintrag(beitrag({ usage_count: 3, nutzung_letzte_7_tage: 2 })),
      ];

      expect(kennzahlen(eintraege)).toEqual({ beitraege: 2, nutzung: 7, dieseWoche: 3, themen: 2 });
    });

    it('bietet nur vorkommende Themen und Stile an, mit Zahl', () => {
      const eintraege = [
        albumEintrag(beitrag({ themen: [KLIMA], style: 'sachlich' })),
        albumEintrag(beitrag({ themen: [KLIMA], style: 'sachlich' })),
        albumEintrag(beitrag({ style: 'bissig' })),
      ];

      expect(themenAuswahl(eintraege)).toEqual([
        { wert: 'klima', name: 'Klima', anzahl: 2 },
        { wert: 'ohne-thema', name: 'Ohne Thema', anzahl: 1 },
      ]);
      expect(stilAuswahl(eintraege)).toEqual([
        { wert: 'sachlich', name: 'sachlich', anzahl: 2 },
        { wert: 'bissig', name: 'deutlich', anzahl: 1 },
      ]);
    });
  });

  describe('naechsterMeilenstein', () => {
    const m = (kennung: string, art: Meilenstein['art'], stand: number, schwelle: number, erreicht = false): Meilenstein => ({
      kennung, name: kennung, untertitel: '', beschreibung: '', bild: '', bildnachweis: '', art, stand, schwelle, erreicht,
    });

    it('nimmt den offenen mit dem groessten Anteil', () => {
      expect(naechsterMeilenstein([m('einwurf', 'weg', 0, 1), m('zehn', 'wirkung', 6, 10), m('hundert', 'wirkung', 83, 100)])?.kennung).toBe('hundert');
    });

    it('nimmt bei Gleichstand einen der Wirkung, sonst den ersten der Liste', () => {
      expect(naechsterMeilenstein([m('einwurf', 'weg', 0, 1), m('genutzt', 'wirkung', 0, 1)])?.kennung).toBe('genutzt');
      expect(naechsterMeilenstein([m('einwurf', 'weg', 0, 1), m('haelt', 'weg', 0, 1)])?.kennung).toBe('einwurf');
    });

    it('liefert null, wenn alle erreicht sind oder es keine gibt', () => {
      expect(naechsterMeilenstein([m('a', 'wirkung', 1, 1, true)])).toBeNull();
      expect(naechsterMeilenstein([])).toBeNull();
    });
  });

  describe('beitraegeInThemen', () => {
    it('nennt Beitraege und Themen in Ein- und Mehrzahl', () => {
      expect(beitraegeInThemen({ beitraege: 244, nutzung: 0, dieseWoche: 0, themen: 12 })).toBe('244 Beiträge in 12 Themen');
      expect(beitraegeInThemen({ beitraege: 1, nutzung: 0, dieseWoche: 0, themen: 1 })).toBe('1 Beitrag in 1 Thema');
      expect(beitraegeInThemen({ beitraege: 3, nutzung: 0, dieseWoche: 0, themen: 0 })).toBe('3 Beiträge');
    });
  });
});
