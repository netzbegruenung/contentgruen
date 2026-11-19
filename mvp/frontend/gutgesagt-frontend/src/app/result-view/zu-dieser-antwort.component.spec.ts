import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { ZuDieserAntwortComponent, laengenZeilen } from './zu-dieser-antwort.component';
import { KartenDaten } from '../beitragskarte/karten-daten';
import { GLANZ_TEXT } from '../shared/components/siegel/siegel-auszeichnung';

function karte(teil: Partial<KartenDaten> = {}): KartenDaten {
  return {
    id: 'k-1',
    typ: 'commentary',
    titel: 'Windräder schützen Vögel besser als Kohle',
    text: 'x'.repeat(320),
    erstellt: '2026-11-10T10:00:00Z',
    autor: null,
    autorName: 'Anna B.',
    autorAbzeichen: 3,
    nutzung: 2,
    quellen: [{ id: 'q-1', url: 'https://example.org/studie' }],
    ...teil,
  };
}

describe('laengenZeilen', () => {
  it('nennt am Kommentar mit Kurzfassung jede vorhandene Fassung samt Plattform', () => {
    const zeilen = laengenZeilen(karte({ extra: { kurz: 'k'.repeat(180) } }));
    expect(zeilen).toEqual([
      { fassung: 'Kurz', zeichen: 180, passt: true },
      { fassung: 'Mittel', zeichen: 320, passt: false },
    ]);
  });

  it('nennt ohne Fassungen nur den einen Text, ohne Text nichts', () => {
    expect(laengenZeilen(karte({ typ: 'generictext', text: 'y'.repeat(280) }))).toEqual([
      { fassung: null, zeichen: 280, passt: true },
    ]);
    expect(laengenZeilen(karte({ text: null }))).toEqual([]);
  });
});

describe('ZuDieserAntwortComponent', () => {
  let fixture: ComponentFixture<ZuDieserAntwortComponent>;

  function zeigen(daten: KartenDaten): HTMLElement {
    TestBed.configureTestingModule({ imports: [ZuDieserAntwortComponent], providers: [provideRouter([])] });
    fixture = TestBed.createComponent(ZuDieserAntwortComponent);
    fixture.componentRef.setInput('karte', daten);
    fixture.detectChanges();
    return fixture.nativeElement;
  }

  const text = (el: Element | null) => (el?.textContent ?? '').replace(/\s+/g, ' ').trim();

  it('heisst "Zu dieser Antwort" und ist als Bereich danach benannt', () => {
    const el = zeigen(karte());
    const titel = el.querySelector('h3')!;
    expect(text(titel)).toBe('Zu dieser Antwort');
    expect(el.querySelector('aside')!.getAttribute('aria-labelledby')).toBe(titel.id);
  });

  it('zeigt Laenge, Stil, Guete und Alter, wie die volle Karte sie kennt', () => {
    const el = zeigen(
      karte({
        extra: { kurz: 'k'.repeat(180), stil: 'sachlich' },
        guete: { wert: 8, erfuellt: ['passiv'], stimmenZaehlen: true, hilfreich: 6, nichtHilfreich: 1 },
      }),
    );
    const fassungen = Array.from(el.querySelectorAll('.zda-fassung'));
    expect(fassungen.map((f) => text(f.querySelector('.zda-zeichen')))).toEqual([
      'Kurz · 180 Zeichen',
      'Mittel · 320 Zeichen',
    ]);
    const chips = (f: Element) => Array.from(f.querySelectorAll('.zda-chip'));
    expect(chips(fassungen[0]).map((c) => text(c).replace(/ ?(check|block)$/, ''))).toEqual([
      'Mastodon',
      'Bluesky',
      'X',
    ]);
    expect(fassungen.map((f) => chips(f).every((c) => c.classList.contains('zda-chip--aus'))))
      .withContext('nur bis 280 Zeichen passt es')
      .toEqual([false, true]);
    expect(fassungen.map((f) => f.querySelector('.zda-chips')!.getAttribute('aria-label'))).toEqual([
      'passt auf',
      'zu lang für',
    ]);
    expect(text(el.querySelector('.zda-stil dt'))).toMatch(/Stil$/);
    expect(text(el.querySelector('.zda-stil-chip'))).toBe('sachlich');
    expect(text(el.querySelector('.zda-stil dd .zda-klein'))).not.toBe('');
    const guete = el.querySelector('.zda-guete')!;
    expect(text(guete.querySelector('.zda-gross'))).toBe('8/10');
    expect(text(guete.querySelector('.zda-guete-kopf .cdk-visually-hidden'))).toBe('Güte 8 von 10');
    expect(guete.querySelector('app-siegel')!.getAttribute('aria-hidden')).toBe('true');
    expect(text(guete.querySelector('.zda-kriterien'))).toMatch(/^check ?Aktiv formuliert$/);
    expect(text(guete)).toContain('Die Stimmen anderer sind eingerechnet. Je mehr Menschen bewerten, desto mehr zählt ihr Urteil.');
    expect(guete.querySelector('a.zda-mehr')!.getAttribute('href')).toBe('/about#siegel');
    expect(text(el.querySelector('.zda-alter dd'))).toContain('10.11.2026');
    el.querySelectorAll('mat-icon').forEach((icon) => expect(icon.getAttribute('aria-hidden')).toBe('true'));
  });

  it('zeigt das Alter gross und das Datum klein, nach fuenf Tagen nur das Datum', () => {
    const erstellt = new Date(Date.now() - 2 * 24 * 3600 * 1000 - 3600 * 1000).toISOString();
    const el = zeigen(karte({ erstellt }));
    expect(text(el.querySelector('.zda-alter .zda-gross-text'))).toBe('vor 2 Tagen');
    expect(text(el.querySelector('.zda-alter .zda-klein'))).toMatch(/^\d\d\.\d\d\.\d{4}$/);
    fixture.componentRef.setInput('karte', karte());
    fixture.detectChanges();
    expect(text(el.querySelector('.zda-alter .zda-gross-text'))).toBe('10.11.2026');
    expect(el.querySelector('.zda-alter .zda-klein')).toBeNull();
  });

  it('nennt eine neue Antwort ohne Note in Worten statt einer grossen Zahl', () => {
    const guete = { wert: null, erfuellt: [], stimmenZaehlen: false, hilfreich: null, nichtHilfreich: null };
    const el = zeigen(karte({ guete }));
    expect(el.querySelector('.zda-gross')).toBeNull();
    expect(text(el.querySelector('.zda-guete-kopf'))).toBe('Neu: noch keine Güte');
  });

  it('nennt keine Person, keine Nutzung und keine Herkunft: die stehen auf der Karte', () => {
    const el = zeigen(karte());
    expect(text(el)).not.toContain('Anna B.');
    expect(text(el)).not.toContain('Meilenstein');
    expect(text(el)).not.toContain('genutzt');
    expect(text(el)).not.toContain('example.org');
  });

  it('zieht Guete und Glanz nach, wenn die Karte daneben sie meldet, nur fuer dieselbe Karte', () => {
    const guete = { wert: 6, erfuellt: [], stimmenZaehlen: false, hilfreich: null, nichtHilfreich: null };
    const el = zeigen(karte({ guete, nutzung: 2 }));
    const kopf = () => text(el.querySelector('.zda-guete-kopf .cdk-visually-hidden'));
    expect(kopf()).toBe('Güte 6 von 10');
    expect(text(el.querySelector('.zda-guete'))).not.toContain(GLANZ_TEXT);

    fixture.componentRef.setInput('kennzahlen', { id: 'andere', guete: { ...guete, wert: 9 }, nutzung: 2 });
    fixture.detectChanges();
    expect(kopf()).withContext('andere Karte zaehlt nicht').toBe('Güte 6 von 10');

    fixture.componentRef.setInput('kennzahlen', { id: 'k-1', guete: { ...guete, wert: 7 }, nutzung: 500 });
    fixture.detectChanges();
    expect(kopf()).toBe('Güte 7 von 10');
    expect(text(el.querySelector('.zda-gross'))).toBe('7/10');
    expect(text(el.querySelector('.zda-guete'))).toContain(GLANZ_TEXT);
  });

  it('laesst Stil und Guete weg, wo die Karte keine hat', () => {
    const el = zeigen(karte({ typ: 'generictext' }));
    expect(el.querySelector('.zda-stil')).toBeNull();
    expect(el.querySelector('.zda-guete')).toBeNull();
    expect(el.querySelector('.zda-laenge')).toBeTruthy();
  });
});
