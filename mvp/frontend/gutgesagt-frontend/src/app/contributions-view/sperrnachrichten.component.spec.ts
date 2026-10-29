import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { of, throwError } from 'rxjs';

import { SperrnachrichtenComponent } from './sperrnachrichten.component';
import { Sperrnachricht, SperrnachrichtService } from '../services/sperrnachricht.service';
import { LEGAL_ENTITY } from '../shared/legal-entity';

function nachricht(felder: Partial<Sperrnachricht> = {}): Sperrnachricht {
  return {
    id: 'sperre-1',
    content_id: 'b1',
    content_type: 'commentary',
    titel: 'Tempolimit rettet Leben',
    sperrgrund: 'unterstellung',
    begruendung: 'Unterstellt der Gegenseite Bosheit.',
    gesperrt_am: '2026-10-29T10:00:00+00:00',
    aufgehoben_am: null,
    widerspruch: null,
    widerspruch_am: null,
    pruefergebnis: null,
    pruefung_begruendung: null,
    geprueft_am: null,
    ...felder,
  };
}

describe('SperrnachrichtenComponent', () => {
  let fixture: ComponentFixture<SperrnachrichtenComponent>;
  let service: jasmine.SpyObj<SperrnachrichtService>;

  function anzeigen(...nachrichten: Sperrnachricht[]) {
    service.meine.and.returnValue(of(nachrichten));
    fixture = TestBed.createComponent(SperrnachrichtenComponent);
    fixture.detectChanges();
  }

  function text(): string {
    return fixture.nativeElement.textContent;
  }

  function knopf(beschriftung: string): HTMLButtonElement | undefined {
    const knoepfe = Array.from(fixture.nativeElement.querySelectorAll('button')) as HTMLButtonElement[];
    return knoepfe.find((b) => b.textContent?.includes(beschriftung));
  }

  beforeEach(() => {
    service = jasmine.createSpyObj('SperrnachrichtService', ['meine', 'widersprechen']);
    service.widersprechen.and.returnValue(of({ success: true }));
    TestBed.configureTestingModule({
      imports: [SperrnachrichtenComponent],
      providers: [provideNoopAnimations(), { provide: SperrnachrichtService, useValue: service }],
    });
  });

  it('zeigt ohne Sperre nichts', () => {
    anzeigen();

    expect(fixture.nativeElement.querySelector('section')).toBeNull();
  });

  it('nennt Entscheidung, Sperrgrund, Begründung und Widerspruchsweg', () => {
    anzeigen(nachricht());

    expect(text()).toContain('„Tempolimit rettet Leben“');
    expect(text()).toContain('gesperrt');
    expect(text()).toContain('Unterstellung über Motive');
    expect(text()).toContain('Unterstellt der Gegenseite Bosheit.');
    expect(text()).toContain('widersprechen');
    expect(text()).toContain(LEGAL_ENTITY.KONTAKT_MAIL);
    expect(knopf('Widersprechen')).toBeTruthy();
  });

  it('nennt einen Beitrag ohne Titel allgemein', () => {
    anzeigen(nachricht({ titel: null }));

    expect(text()).toContain('einen deiner Beiträge');
  });

  it('schickt den Widerspruch und lädt den neuen Stand', () => {
    anzeigen(nachricht());
    knopf('Widersprechen')!.click();
    fixture.detectChanges();
    fixture.componentInstance.widerspruchText = 'Das ist belegt.';
    service.meine.and.returnValue(of([nachricht({ widerspruch_am: '2026-10-29T12:00:00+00:00' })]));

    knopf('Widerspruch senden')!.click();
    fixture.detectChanges();

    expect(service.widersprechen).toHaveBeenCalledWith('sperre-1', 'Das ist belegt.');
    expect(text()).toContain('liegt bei uns');
    expect(knopf('Widersprechen')).toBeUndefined();
  });

  it('meldet einen Fehler beim Senden und lässt das Feld offen', () => {
    service.widersprechen.and.returnValue(throwError(() => ({ status: 500 })));
    anzeigen(nachricht());
    knopf('Widersprechen')!.click();
    fixture.detectChanges();

    knopf('Widerspruch senden')!.click();
    fixture.detectChanges();

    expect(text()).toContain('ging nicht raus');
    expect(knopf('Widerspruch senden')).toBeTruthy();
  });

  it('zeigt den eigenen Widerspruch', () => {
    anzeigen(nachricht({ widerspruch: 'Das ist belegt.', widerspruch_am: '2026-10-29T12:00:00+00:00' }));

    expect(text()).toContain('Dein Widerspruch');
    expect(text()).toContain('Das ist belegt.');
  });

  it('sagt beim Weg per E-Mail, dass die Antwort per E-Mail kommt', () => {
    anzeigen(nachricht());

    expect(text()).toContain('dann antworten wir dir per E-Mail');
  });

  it('zeigt das Ergebnis der erneuten Prüfung', () => {
    anzeigen(
      nachricht({
        widerspruch_am: '2026-10-29T12:00:00+00:00',
        pruefergebnis: 'sperre_bleibt',
        pruefung_begruendung: 'Bleibt eine Unterstellung.',
        geprueft_am: '2026-10-30T09:00:00+00:00',
      }),
    );

    expect(text()).toContain('Sie bleibt.');
    expect(text()).toContain('Bleibt eine Unterstellung.');
    expect(text()).not.toContain('liegt bei uns');
  });

  it('sagt nach erfolgreichem Widerspruch, dass die Sperre aufgehoben ist', () => {
    anzeigen(
      nachricht({
        aufgehoben_am: '2026-10-30T09:00:00+00:00',
        widerspruch_am: '2026-10-29T12:00:00+00:00',
        pruefergebnis: 'entsperrt',
        geprueft_am: '2026-10-30T09:00:00+00:00',
      }),
    );

    expect(text()).toContain('aufgehoben');
    expect(text()).toContain('wieder sichtbar');
    expect(text()).not.toContain('aus Suche und Ansicht genommen');
    expect(text()).not.toContain('liegt bei uns');
  });
});
