import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { SimpleChange } from '@angular/core';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of, throwError } from 'rxjs';

import {
  AntwortAuf,
  AntwortAufComponent,
  VORSCHLAG_AB_ZEICHEN,
  VORSCHLAG_VERZOEGERUNG_MS,
} from './antwort-auf.component';
import { AuthService } from '../../auth/auth.service';
import { StatementService } from '../../services/statement.service';
import { LoggingService } from '../../services/logging.service';
import { StatementSearchResult } from '../../services/dtos/statementDtos';

describe('AntwortAufComponent', () => {
  let fixture: ComponentFixture<AntwortAufComponent>;
  let component: AntwortAufComponent;
  let statementService: jasmine.SpyObj<StatementService>;
  let gemeldet: AntwortAuf[];

  const VORSCHLAG: StatementSearchResult = {
    id: 'a-1',
    text: 'Wärmepumpen sind im Altbau zu teuer',
    replysuggestions_count: 2,
    score: 0.8,
  };

  beforeEach(async () => {
    statementService = jasmine.createSpyObj('StatementService', ['aussageVorschlaege']);
    statementService.aussageVorschlaege.and.returnValue(of([VORSCHLAG]));

    await TestBed.configureTestingModule({
      imports: [AntwortAufComponent, NoopAnimationsModule],
      providers: [
        { provide: StatementService, useValue: statementService },
        { provide: LoggingService, useValue: jasmine.createSpyObj('LoggingService', ['warn', 'error', 'debug']) },
        // Die Kopf-Karte fragt den Dienst nach der eigenen Kennung ("Von: Du").
        { provide: AuthService, useValue: { getUserInfo: () => null } },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(AntwortAufComponent);
    component = fixture.componentInstance;
    gemeldet = [];
    component.aussageChange.subscribe((wert) => gemeldet.push(wert));
    fixture.detectChanges();
  });

  function seite(): HTMLElement {
    return fixture.nativeElement;
  }

  function tippen(text: string): void {
    const feld: HTMLTextAreaElement = seite().querySelector('.antwort-eingabe')!;
    feld.value = text;
    feld.dispatchEvent(new Event('input'));
    fixture.detectChanges();
  }

  function adresse(aussage: AntwortAuf): void {
    component.aussage = aussage;
    component.ngOnChanges({ aussage: new SimpleChange(undefined, aussage, false) });
    fixture.detectChanges();
  }

  it('ist ein optionales Feld mit Beispiel und einer Hilfezeile', () => {
    expect(seite().querySelector('mat-label')!.textContent).toContain('Antwort auf (optional)');
    const feld: HTMLTextAreaElement = seite().querySelector('.antwort-eingabe')!;
    expect(feld.placeholder).toContain('z. B.');
    expect(seite().querySelectorAll('mat-hint').length).toBe(1);
    expect(seite().textContent).not.toContain('Diese Aussage wird gespeichert');
    expect(seite().querySelector('.input-instruction')).toBeNull();
  });

  it('meldet Getipptes sofort als Text ohne ID', () => {
    tippen('Windräder');

    expect(gemeldet[gemeldet.length - 1]).toEqual({ id: '', text: 'Windräder' });
    expect(component.wert).toEqual({ id: '', text: 'Windräder' });
  });

  it('schlaegt erst ab einer Mindestlaenge und nach kurzer Pause vor', fakeAsync(() => {
    tippen('a'.repeat(VORSCHLAG_AB_ZEICHEN - 1));
    tick(VORSCHLAG_VERZOEGERUNG_MS);
    expect(statementService.aussageVorschlaege).not.toHaveBeenCalled();

    tippen('Wärmepumpen teuer');
    tick(VORSCHLAG_VERZOEGERUNG_MS - 1);
    expect(statementService.aussageVorschlaege).not.toHaveBeenCalled();
    tick(1);
    fixture.detectChanges();

    expect(statementService.aussageVorschlaege).toHaveBeenCalledOnceWith('Wärmepumpen teuer');
    expect(seite().querySelectorAll('.vorschlag').length).toBe(1);
  }));

  it('uebernimmt einen Vorschlag mit ID und zeigt ihn als Kopf-Karte', fakeAsync(() => {
    tippen('Wärmepumpen teuer');
    tick(VORSCHLAG_VERZOEGERUNG_MS);
    fixture.detectChanges();

    (seite().querySelector('.vorschlag') as HTMLButtonElement).click();
    fixture.detectChanges();

    expect(gemeldet[gemeldet.length - 1]).toEqual({ id: 'a-1', text: VORSCHLAG.text });
    expect(seite().querySelector('.karte--kopf .karte-titel')!.textContent).toContain(VORSCHLAG.text);
    expect(seite().querySelector('.antwort-eingabe')).toBeNull();
    expect(seite().querySelector('.vorschlaege')).toBeNull();
  }));

  it('bietet nach der Suche an, den getippten Text als neue Aussage zu nehmen', fakeAsync(() => {
    statementService.aussageVorschlaege.and.returnValue(of([]));
    tippen('Windräder machen Lärm');
    expect(seite().querySelector('.neue-aussage')).withContext('erst nach der Suche').toBeNull();

    tick(VORSCHLAG_VERZOEGERUNG_MS);
    fixture.detectChanges();
    const knopf: HTMLButtonElement = seite().querySelector('.neue-aussage')!;
    expect(knopf.textContent).toContain('Als neue Aussage anlegen: „Windräder machen Lärm“');

    knopf.click();
    fixture.detectChanges();

    expect(gemeldet[gemeldet.length - 1]).toEqual({ id: '', text: 'Windräder machen Lärm' });
    expect(seite().querySelector('.karte--kopf .karte-titel')!.textContent).toContain('Windräder machen Lärm');
    expect(seite().querySelector('.neu-marke')!.textContent).toContain('neu');
    expect(component.wert).toEqual({ id: '', text: 'Windräder machen Lärm' });
  }));

  it('steht unter den Vorschlaegen und kennzeichnet eine vorhandene Aussage nicht als neu', fakeAsync(() => {
    tippen('Wärmepumpen teuer');
    tick(VORSCHLAG_VERZOEGERUNG_MS);
    fixture.detectChanges();

    const block = seite().querySelector('.vorschlaege')!;
    expect(block.lastElementChild!.classList).toContain('neue-aussage');

    (seite().querySelector('.vorschlag') as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(seite().querySelector('.neu-marke')).toBeNull();
  }));

  it('sagt unter dem Feld, was beim Speichern passiert: zu kurz oder neue Aussage', () => {
    tippen('Windrad');
    const hinweis = () => seite().querySelector('mat-hint')!;
    expect(hinweis().textContent).toContain('Mindestens 10 Zeichen – oder leer lassen.');
    expect(hinweis().classList).toContain('zu-kurz');
    expect(component.feldZustand).toBe('zu-kurz');

    tippen('Windräder töten Vögel');
    expect(hinweis().textContent).toContain('Wird als neue Aussage angelegt.');
    expect(component.feldZustand).toBe('neu');

    tippen('');
    expect(hinweis().textContent).toContain('Die Aussage, auf die du reagierst');
    expect(component.feldZustand).toBe('leer');
  });

  it('bietet einen zu kurzen Text nicht als neue Aussage an', fakeAsync(() => {
    statementService.aussageVorschlaege.and.returnValue(of([]));

    tippen('Windrad 1'); // 9 Zeichen: gesucht wird schon, anlegen geht noch nicht
    tick(VORSCHLAG_VERZOEGERUNG_MS);
    fixture.detectChanges();
    expect(seite().querySelector('.neue-aussage')).toBeNull();

    tippen('Windrad 10'); // 10 Zeichen
    tick(VORSCHLAG_VERZOEGERUNG_MS);
    fixture.detectChanges();
    expect(seite().querySelector('.neue-aussage')).toBeTruthy();
  }));

  it('entfernt die gewaehlte Aussage wieder', () => {
    adresse({ id: 'a-1', text: VORSCHLAG.text });

    (seite().querySelector('.entfernen') as HTMLButtonElement).click();
    fixture.detectChanges();

    expect(gemeldet[gemeldet.length - 1]).toEqual({ id: '', text: '' });
    expect(seite().querySelector('.antwort-eingabe')).toBeTruthy();
    expect(component.wert).toEqual({ id: '', text: '' });
  });

  it('zeigt eine Aussage aus der Adresse mit ID als gewaehlt, ohne ID als Text im Feld', () => {
    adresse({ id: 'a-1', text: 'Mit ID' });
    expect(seite().querySelector('.karte--kopf')).toBeTruthy();

    adresse({ id: '', text: 'Nur Text' });
    expect(seite().querySelector('.karte--kopf')).toBeNull();
    expect((seite().querySelector('.antwort-eingabe') as HTMLTextAreaElement).value).toBe('Nur Text');
    expect(component.wert).toEqual({ id: '', text: 'Nur Text' });
  });

  it('bleibt ohne Vorschlaege nutzbar, wenn die Suche scheitert', fakeAsync(() => {
    statementService.aussageVorschlaege.and.returnValue(throwError(() => new Error('500')));

    tippen('Wärmepumpen teuer');
    tick(VORSCHLAG_VERZOEGERUNG_MS);
    fixture.detectChanges();

    expect(seite().querySelector('.vorschlag')).toBeNull();
    expect(seite().querySelector('.neue-aussage')).toBeTruthy();
    expect(component.wert.text).toBe('Wärmepumpen teuer');
  }));

  it('zeigt den Hinweis, wenn die Aussage aus der Adresse nicht ladbar war', () => {
    fixture.componentRef.setInput('hinweis', 'Die Aussage ist nicht mehr verfügbar');
    fixture.detectChanges();

    expect(seite().querySelector('.aussage-hinweis')!.textContent).toContain('nicht mehr verfügbar');
  });
});
