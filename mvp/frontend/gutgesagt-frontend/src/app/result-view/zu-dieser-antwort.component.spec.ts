import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { ZuDieserAntwortComponent, laengenZeilen } from './zu-dieser-antwort.component';
import { KartenDaten } from '../beitragskarte/karten-daten';

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
    const zeilen = Array.from(el.querySelectorAll('.zda-laenge li'));
    expect(zeilen.map((z) => text(z.firstElementChild))).toEqual(['Kurz: 180 Zeichen', 'Mittel: 320 Zeichen']);
    expect(zeilen.map((z) => !!z.querySelector('.zda-passt'))).withContext('nur bis 280 Zeichen').toEqual([true, false]);
    expect(text(zeilen[0].querySelector('.zda-passt'))).toContain('passt auf Mastodon/Bluesky/X');
    expect(text(el.querySelector('.zda-stil dt'))).toBe('Stil');
    expect(text(el.querySelector('.zda-stil dd'))).toMatch(/^sachlich: /);
    const guete = el.querySelector('.zda-guete')!;
    expect(text(guete.querySelector('.zda-guete-kopf'))).toBe('Güte 8 von 10');
    expect(text(guete.querySelector('.zda-kriterien'))).toMatch(/^check ?Aktiv formuliert$/);
    expect(text(guete)).toContain('Die Stimmen anderer sind eingerechnet.');
    expect(guete.querySelector('a.zda-mehr')!.getAttribute('href')).toBe('/about#siegel');
    expect(text(el.querySelector('.zda-alter'))).toContain('(10.11.2026)');
  });

  it('nennt keine Person, keine Nutzung und keine Herkunft: die stehen auf der Karte', () => {
    const el = zeigen(karte());
    expect(text(el)).not.toContain('Anna B.');
    expect(text(el)).not.toContain('Meilenstein');
    expect(text(el)).not.toContain('genutzt');
    expect(text(el)).not.toContain('example.org');
  });

  it('laesst Stil und Guete weg, wo die Karte keine hat', () => {
    const el = zeigen(karte({ typ: 'generictext' }));
    expect(el.querySelector('.zda-stil')).toBeNull();
    expect(el.querySelector('.zda-guete')).toBeNull();
    expect(el.querySelector('.zda-laenge')).toBeTruthy();
  });
});
