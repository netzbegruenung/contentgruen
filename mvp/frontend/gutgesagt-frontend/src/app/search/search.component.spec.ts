import { ComponentFixture, TestBed, discardPeriodicTasks, fakeAsync, flush, tick } from '@angular/core/testing';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideAnimations } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';
import { NavigationService } from '../services/navigation.service';
import { BreakpointObserver, BreakpointState } from '@angular/cdk/layout';
import { CdkTextareaAutosize } from '@angular/cdk/text-field';
import { By } from '@angular/platform-browser';
import { BehaviorSubject, of } from 'rxjs';
import { HOT_TAKES } from '../shared/startbeispiel';

import { SCHMAL, SUCHANFRAGEN_ABSCHNITT, SUCHHINWEIS, SUCHHINWEIS_KURZ, SearchComponent } from './search.component';

describe('SearchComponent', () => {
  let component: SearchComponent;
  let fixture: ComponentFixture<SearchComponent>;
  let navigationServiceMock: any;
  /** Bildschirmbreite fuer die Komponente: matches = unter 600 px. */
  let breite$: BehaviorSubject<BreakpointState>;

  beforeEach(async () => {
    navigationServiceMock = jasmine.createSpyObj('NavigationService', ['navigateToResult']);
    breite$ = new BehaviorSubject<BreakpointState>({ matches: false, breakpoints: {} });

    await TestBed.configureTestingModule({
      imports: [
        SearchComponent,
        MatFormFieldModule,
        MatInputModule,
      ],
      providers: [
        { provide: NavigationService, useValue: navigationServiceMock },
        {
          provide: BreakpointObserver,
          // Material fragt selbst weitere Medienabfragen ab (etwa forced-colors)
          useValue: {
            observe: (q: string) => (q === SCHMAL ? breite$ : of({ matches: false, breakpoints: {} })),
            isMatched: () => false,
          },
        },
        provideHttpClient(),
        provideHttpClientTesting(),
        provideAnimations(),
        provideRouter([])
      ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(SearchComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  // R56 (#644): Auf einer Seite mit nur einem Feld war der Pflichtstern Formularsprache
  it('beschriftet das Feld ohne Pflichtstern', () => {
    const feld: HTMLElement = fixture.nativeElement.querySelector('mat-form-field');
    expect(feld.querySelector('mat-label')!.textContent!.trim()).toBe('Worauf willst du antworten? Text einfügen');
    expect(feld.querySelector('.mat-mdc-form-field-required-marker')).toBeNull();
    expect(feld.querySelector('input')!.hasAttribute('required')).toBeFalse();
  });

  it('nimmt ueber den Treffern (compactMode) die kurze Beschriftung', () => {
    fixture.componentRef.setInput('compactMode', true);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('mat-label').textContent.trim()).toBe('Worauf antworten? Text einfügen');
  });

  // Persona-Test Gerd: dass der Suchtext gespeichert wird, stand nur in der Datenschutzerklärung
  describe('Hinweis unter dem Feld', () => {
    function hinweis(): HTMLElement {
      return fixture.nativeElement.querySelector('.such-hinweis');
    }

    // Wortlaut rechtlich abgestimmt (16.11.2026): Aenderungen hier fallen auf
    it('sagt, dass Suchtexte ohne Namen gespeichert und erst nach Prüfung öffentlich werden', () => {
      expect(hinweis().textContent!.replace(/\s+/g, ' ').trim()).toBe(
        'Suchtexte speichern wir ohne deinen Namen. Nach Prüfung können sie öffentlich werden. Mehr dazu im Datenschutz',
      );
      expect(SUCHHINWEIS).toBe('Suchtexte speichern wir ohne deinen Namen. Nach Prüfung können sie öffentlich werden.');
    });

    it('verlinkt den Abschnitt „Deine Suchanfragen“ der Datenschutzerklärung', () => {
      const link = hinweis().querySelector('a') as HTMLAnchorElement;
      expect(link.textContent!.trim()).toBe('Mehr dazu im Datenschutz');
      expect(link.getAttribute('href')).toBe(`/datenschutz#${SUCHANFRAGEN_ABSCHNITT}`);
    });

    it('ist per aria-describedby mit dem Suchfeld verbunden', () => {
      const feld = fixture.nativeElement.querySelector('input') as HTMLInputElement;
      const id = hinweis().id;
      expect(id).toBeTruthy();
      expect(feld.getAttribute('aria-describedby')).toBe(id);
    });

    it('steht über den Treffern (compactMode) einzeilig mit „Mehr“ auf denselben Abschnitt (E5)', () => {
      fixture.componentRef.setInput('compactMode', true);
      fixture.detectChanges();

      expect(hinweis().textContent!.replace(/\s+/g, ' ').trim()).toBe('Suchtexte speichern wir ohne deinen Namen. Mehr');
      expect(SUCHHINWEIS_KURZ).toBe('Suchtexte speichern wir ohne deinen Namen.');
      const link = hinweis().querySelector('a') as HTMLAnchorElement;
      expect(link.getAttribute('href')).toBe(`/datenschutz#${SUCHANFRAGEN_ABSCHNITT}`);
    });
  });

  // R55 (#644): Fokus nur, wenn der Start es verlangt
  it('fokussiert das Feld nur mit autofokus', () => {
    expect(document.activeElement).not.toBe(fixture.nativeElement.querySelector('input'));

    const mitFokus = TestBed.createComponent(SearchComponent);
    mitFokus.componentRef.setInput('autofokus', true);
    mitFokus.componentRef.setInput('feldId', 'suche');
    document.body.appendChild(mitFokus.nativeElement);
    try {
      mitFokus.detectChanges();
      const input = mitFokus.nativeElement.querySelector('input') as HTMLInputElement;
      expect(input.id).toBe('suche');
      expect(document.activeElement).toBe(input);
    } finally {
      mitFokus.nativeElement.remove();
    }
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('onSearch', () => {
    it('should call navigationService.navigateToResult with the search query after debounce', fakeAsync(() => {
      const testQuery = 'test';
      component.searchQuery = testQuery;

      component.onSearch();
      tick(300); // Wait for debounce

      expect(navigationServiceMock.navigateToResult).toHaveBeenCalledWith(testQuery);
    }));

    it('should navigate to result-view when search query is provided', fakeAsync(() => {
      const testQuery = 'test query';
      component.searchQuery = testQuery;

      component.onSearch();
      tick(300); // Wait for debounce

      expect(navigationServiceMock.navigateToResult).toHaveBeenCalledWith(testQuery);
    }));

    it('should not navigate when search query is empty', fakeAsync(() => {
      component.searchQuery = '';

      component.onSearch();
      tick(300); // Wait for debounce

      expect(navigationServiceMock.navigateToResult).not.toHaveBeenCalled();
    }));

    it('should handle search navigation correctly', fakeAsync(() => {
      const testQuery = 'environment policy';
      component.searchQuery = testQuery;

      component.onSearch();
      tick(300); // Wait for debounce

      expect(navigationServiceMock.navigateToResult).toHaveBeenCalledWith(testQuery);
    }));
  });

  // Designrunde 17.11.: Auf dem Start tippt das leere Feld Hot Takes vor. Designrunde 18.11.:
  // Ein Knopf; solange das Feld leer ist, heißt er „Beispiel ausprobieren“ und sucht den Hot Take
  describe('Hot Takes im Feld', () => {
    function mitBeispiel(ruhig: boolean): ComponentFixture<SearchComponent> {
      spyOn(window, 'matchMedia').and.callFake(
        (q: string) => ({ matches: ruhig && q.includes('reduce') }) as MediaQueryList,
      );
      const f = TestBed.createComponent(SearchComponent);
      f.componentRef.setInput('beispielAnimation', true);
      f.detectChanges();
      return f;
    }
    const feld = (f: ComponentFixture<SearchComponent>) => f.nativeElement.querySelector('input') as HTMLInputElement;
    const knopf = (f: ComponentFixture<SearchComponent>) =>
      f.nativeElement.querySelector('.search-button') as HTMLButtonElement;
    const knopfText = (f: ComponentFixture<SearchComponent>) =>
      knopf(f).textContent!.replace('search', '').trim();

    it('heißt „Beispiel ausprobieren“ und sucht den fertig getippten Hot Take', fakeAsync(() => {
      const f = mitBeispiel(false);
      tick(HOT_TAKES[0].text.length * 45 + 10);
      f.detectChanges();

      expect(feld(f).placeholder).toBe(HOT_TAKES[0].text);
      expect(knopfText(f)).toBe('Beispiel ausprobieren');
      expect(knopf(f).getAttribute('aria-label')).toBe('Beispiel ausprobieren: ' + HOT_TAKES[0].text);
      knopf(f).click();
      expect(navigationServiceMock.navigateToResult).toHaveBeenCalledWith(HOT_TAKES[0].text);
      f.detectChanges();
      expect(feld(f).placeholder).toBe('');
      expect(knopfText(f)).toBe('Suchen');
      flush();
    }));

    it('heißt schon mitten im Tippen „Beispiel ausprobieren“ und sucht den ganzen Hot Take', fakeAsync(() => {
      const f = mitBeispiel(false);
      tick(10 * 45);
      f.detectChanges();

      expect(feld(f).placeholder.length).toBeLessThan(HOT_TAKES[0].text.length);
      expect(knopfText(f)).toBe('Beispiel ausprobieren');
      knopf(f).click();
      expect(navigationServiceMock.navigateToResult).toHaveBeenCalledWith(HOT_TAKES[0].text);
      flush();
    }));

    it('Enter im leeren Feld bei laufender Vorführung sucht nicht', fakeAsync(() => {
      const f = mitBeispiel(false);
      tick(HOT_TAKES[0].text.length * 45 + 10);
      f.detectChanges();
      expect(knopfText(f)).toBe('Beispiel ausprobieren');

      // preventDefault verhindert auch das implizite Absenden (ngSubmit) am Desktop mit Autofokus
      const enter = new KeyboardEvent('keydown', { key: 'Enter', cancelable: true });
      feld(f).dispatchEvent(enter);
      tick();

      expect(enter.defaultPrevented).toBeTrue();
      expect(navigationServiceMock.navigateToResult).not.toHaveBeenCalled();
      flush(5000);
    }));

    it('Enter im leeren Feld sucht auch bei reduzierter Bewegung nicht; nur der Knopf sucht den Hot Take', fakeAsync(() => {
      const f = mitBeispiel(true);
      tick();
      f.detectChanges();

      feld(f).dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', cancelable: true }));
      tick();
      expect(navigationServiceMock.navigateToResult).not.toHaveBeenCalled();

      knopf(f).click();
      expect(navigationServiceMock.navigateToResult).toHaveBeenCalledOnceWith(HOT_TAKES[0].text);
      discardPeriodicTasks();
    }));

    it('sucht mit Enter den Feldinhalt, wenn Text im Feld steht', fakeAsync(() => {
      const f = mitBeispiel(false);
      tick(200);
      feld(f).value = 'Tempolimit bringt nichts';
      feld(f).dispatchEvent(new Event('input'));
      f.detectChanges();
      tick();

      feld(f).dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', cancelable: true }));
      tick();

      expect(navigationServiceMock.navigateToResult).toHaveBeenCalledOnceWith('Tempolimit bringt nichts');
      flush();
    }));

    it('heißt nach eigener Eingabe „Suchen“ und sucht den Feldinhalt', fakeAsync(() => {
      const f = mitBeispiel(false);
      tick(200);
      f.detectChanges();
      tick();

      feld(f).value = 'Tempolimit bringt nichts';
      feld(f).dispatchEvent(new Event('input'));
      f.detectChanges();
      tick();
      f.detectChanges();

      expect(knopfText(f)).toBe('Suchen');
      expect(knopf(f).hasAttribute('aria-label')).toBeFalse();
      knopf(f).click();
      expect(navigationServiceMock.navigateToResult).toHaveBeenCalledWith('Tempolimit bringt nichts');
      flush();
    }));

    it('hat keinen eigenen Ausprobieren-Knopf mehr, nur den einen Knopf', fakeAsync(() => {
      const f = mitBeispiel(false);
      tick(HOT_TAKES[0].text.length * 45 + 10);
      f.detectChanges();

      expect(f.nativeElement.querySelectorAll('button').length).toBe(1);
      expect(f.nativeElement.querySelector('.ausprobieren-knopf')).toBeNull();
      expect(f.nativeElement.querySelector('.ausprobieren-zeile')).toBeNull();
      flush(5000);
    }));

    it('hoert auf, sobald man selbst ins Feld tippt', fakeAsync(() => {
      const f = mitBeispiel(false);
      tick(200);
      f.detectChanges();
      expect(feld(f).placeholder).not.toBe('');

      feld(f).value = 'a';
      feld(f).dispatchEvent(new Event('input'));
      tick(10_000);
      f.detectChanges();

      expect(feld(f).placeholder).toBe('');
      expect(knopfText(f)).toBe('Suchen');
      flush();
    }));

    it('laesst Tab den Beispielzustand stehen, damit der Knopf per Tastatur erreichbar bleibt', fakeAsync(() => {
      const f = mitBeispiel(false);
      tick(HOT_TAKES[0].text.length * 45 + 10);
      f.detectChanges();

      feld(f).dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab' }));
      f.detectChanges();

      expect(knopfText(f)).toBe('Beispiel ausprobieren');
      expect(feld(f).placeholder).toBe(HOT_TAKES[0].text);
      flush(5000);
    }));

    it('haelt mit Fokus auf dem Knopf an und zeigt den ganzen Hot Take', fakeAsync(() => {
      const f = mitBeispiel(false);
      tick(10 * 45);
      f.detectChanges();

      knopf(f).dispatchEvent(new FocusEvent('focus'));
      tick(10_000);
      f.detectChanges();

      expect(feld(f).placeholder).toBe(HOT_TAKES[0].text);
      expect(knopfText(f)).toBe('Beispiel ausprobieren');
    }));

    it('bleibt nach zwei Durchlaeufen beim ersten Beispiel stehen (WCAG 2.2.2)', fakeAsync(() => {
      const f = mitBeispiel(false);
      flush(5000);
      f.detectChanges();

      expect(feld(f).placeholder).toBe(HOT_TAKES[0].text);
      expect(knopf(f).getAttribute('aria-label')).toBe('Beispiel ausprobieren: ' + HOT_TAKES[0].text);
    }));

    it('zeigt bei reduzierter Bewegung das Beispiel ohne Tippen', fakeAsync(() => {
      const f = mitBeispiel(true);
      f.detectChanges();

      expect(feld(f).placeholder).toBe(HOT_TAKES[0].text);
      expect(knopfText(f)).toBe('Beispiel ausprobieren');
      discardPeriodicTasks();
    }));

    it('tippt ohne beispielAnimation nichts vor und heißt „Suchen“', () => {
      expect(feld(fixture).placeholder).toBe('');
      expect(knopfText(fixture)).toBe('Suchen');
      expect(knopf(fixture).hasAttribute('aria-label')).toBeFalse();
    });

    it('heißt ueber den Treffern (compactMode) „Suchen“, auch mit beispielAnimation', fakeAsync(() => {
      spyOn(window, 'matchMedia').and.callFake(() => ({ matches: true }) as MediaQueryList);
      const f = TestBed.createComponent(SearchComponent);
      f.componentRef.setInput('compactMode', true);
      f.componentRef.setInput('beispielAnimation', true);
      f.detectChanges();

      expect(knopfText(f)).toBe('Suchen');
      knopf(f).click();
      expect(navigationServiceMock.navigateToResult).not.toHaveBeenCalled();
      discardPeriodicTasks();
    }));
  });

  // Designrunde 18.11.: Am Handy lief der Hot Take aus dem einzeiligen Feld
  describe('am Handy (unter 600 px)', () => {
    function schmal(f: ComponentFixture<SearchComponent> = fixture): void {
      breite$.next({ matches: true, breakpoints: { [SCHMAL]: true } });
      f.detectChanges();
    }
    const textfeld = (f: ComponentFixture<SearchComponent> = fixture) =>
      f.nativeElement.querySelector('textarea') as HTMLTextAreaElement;

    it('wird das Feld mehrzeilig, mit Beschriftung, Hinweis und Kennung', () => {
      fixture.componentRef.setInput('feldId', 'suche');
      schmal();

      expect(fixture.nativeElement.querySelector('input')).toBeNull();
      expect(fixture.debugElement.query(By.directive(CdkTextareaAutosize))).not.toBeNull();
      expect(textfeld().getAttribute('enterkeyhint')).toBe('search');
      expect(textfeld().id).toBe('suche');
      expect(textfeld().getAttribute('aria-describedby')).toBe(fixture.nativeElement.querySelector('.such-hinweis').id);
      expect(fixture.nativeElement.querySelector('mat-label').textContent.trim()).toBe('Worauf willst du antworten? Text einfügen');
    });

    // Review #703: Die Direktive mass die Zeile zu niedrig, der Platzhalter wurde abgeschnitten
    it('ist leer 2 Zeilen hoch und waechst mit langem Text bis 4 Zeilen', fakeAsync(() => {
      schmal();
      tick();
      const zeile = parseFloat(getComputedStyle(textfeld()).lineHeight);
      expect(zeile).toBeGreaterThan(0);
      expect(textfeld().clientHeight).toBeCloseTo(2 * zeile, 0);

      textfeld().value = 'Windräder killen doch massenhaft Vögel und überhaupt '.repeat(8);
      textfeld().dispatchEvent(new Event('input'));
      fixture.detectChanges();
      tick();
      fixture.detectChanges();

      expect(textfeld().clientHeight).toBeCloseTo(4 * zeile, 0);
      expect(textfeld().scrollHeight).toBeGreaterThan(textfeld().clientHeight);
    }));

    it('behaelt beim Drehen (Wechsel der Breite) Text und Fokus, Cursor am Ende', fakeAsync(() => {
      component.searchQuery = 'Tempolimit bringt nichts';
      fixture.detectChanges();
      tick();
      const breit = fixture.nativeElement.querySelector('input') as HTMLInputElement;
      breit.focus();

      schmal();
      tick();

      expect(document.activeElement).toBe(textfeld());
      expect(textfeld().value).toBe('Tempolimit bringt nichts');
      expect(textfeld().selectionStart).toBe('Tempolimit bringt nichts'.length);

      textfeld().blur();
      breite$.next({ matches: false, breakpoints: {} });
      fixture.detectChanges();
      tick();
      expect(document.activeElement).not.toBe(fixture.nativeElement.querySelector('input'));
    }));

    it('laesst Enter waehrend einer IME-Komposition das Zeichen bestaetigen', () => {
      schmal();
      component.searchQuery = 'Tempolimit';
      const komposition = new KeyboardEvent('keydown', { key: 'Enter', isComposing: true, cancelable: true });
      textfeld().dispatchEvent(komposition);
      const ime = new KeyboardEvent('keydown', { key: 'Enter', keyCode: 229, cancelable: true } as KeyboardEventInit);
      textfeld().dispatchEvent(ime);

      expect(komposition.defaultPrevented).toBeFalse();
      expect(ime.defaultPrevented).toBeFalse();
      expect(navigationServiceMock.navigateToResult).not.toHaveBeenCalled();
    });

    it('sucht mit Enter, ohne eine neue Zeile', () => {
      schmal();
      component.searchQuery = 'Tempolimit bringt nichts';
      const enter = new KeyboardEvent('keydown', { key: 'Enter', cancelable: true });
      textfeld().dispatchEvent(enter);

      expect(enter.defaultPrevented).toBeTrue();
      expect(navigationServiceMock.navigateToResult).toHaveBeenCalledWith('Tempolimit bringt nichts');
    });

    it('sucht bei einem Umbruch per beforeinput (Android-Tastatur nach IME-Enter) wie mit Enter', fakeAsync(() => {
      schmal();
      component.searchQuery = 'Tempolimit bringt nichts';
      const ime = new KeyboardEvent('keydown', { key: 'Enter', keyCode: 229, cancelable: true } as KeyboardEventInit);
      textfeld().dispatchEvent(ime);
      const umbruch = new InputEvent('beforeinput', { inputType: 'insertLineBreak', cancelable: true });
      textfeld().dispatchEvent(umbruch);
      const absatz = new InputEvent('beforeinput', { inputType: 'insertParagraph', cancelable: true });
      tick();
      textfeld().dispatchEvent(absatz);

      expect(ime.defaultPrevented).toBeFalse();
      expect(umbruch.defaultPrevented).toBeTrue();
      expect(absatz.defaultPrevented).toBeTrue();
      expect(navigationServiceMock.navigateToResult).toHaveBeenCalledTimes(2);
      expect(navigationServiceMock.navigateToResult).toHaveBeenCalledWith('Tempolimit bringt nichts');
    }));

    it('sucht nicht doppelt, wenn nach Enter noch ein Umbruch per beforeinput kommt', fakeAsync(() => {
      schmal();
      component.searchQuery = 'Tempolimit bringt nichts';
      textfeld().dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', cancelable: true }));
      const umbruch = new InputEvent('beforeinput', { inputType: 'insertLineBreak', cancelable: true });
      textfeld().dispatchEvent(umbruch);
      tick();

      expect(umbruch.defaultPrevented).toBeTrue();
      expect(navigationServiceMock.navigateToResult).toHaveBeenCalledOnceWith('Tempolimit bringt nichts');
    }));

    it('sucht bei einem Umbruch per beforeinput im leeren Feld nicht, auch bei laufender Vorführung', fakeAsync(() => {
      spyOn(window, 'matchMedia').and.callFake(() => ({ matches: false }) as MediaQueryList);
      const f = TestBed.createComponent(SearchComponent);
      f.componentRef.setInput('beispielAnimation', true);
      schmal(f);
      tick(HOT_TAKES[0].text.length * 45 + 10);
      f.detectChanges();

      const umbruch = new InputEvent('beforeinput', { inputType: 'insertLineBreak', cancelable: true });
      textfeld(f).dispatchEvent(umbruch);

      expect(umbruch.defaultPrevented).toBeTrue();
      expect(navigationServiceMock.navigateToResult).not.toHaveBeenCalled();
      flush(5000);
    }));

    it('laesst normale Eingaben per beforeinput durch', () => {
      schmal();
      const tippen = new InputEvent('beforeinput', { inputType: 'insertText', data: 'a', cancelable: true });
      textfeld().dispatchEvent(tippen);

      expect(tippen.defaultPrevented).toBeFalse();
      expect(navigationServiceMock.navigateToResult).not.toHaveBeenCalled();
    });

    it('macht mit Umschalt+Enter keine neue Zeile', () => {
      schmal();
      const enter = new KeyboardEvent('keydown', { key: 'Enter', shiftKey: true, cancelable: true });
      textfeld().dispatchEvent(enter);

      expect(enter.defaultPrevented).toBeTrue();
    });

    it('macht aus Zeilenumbruechen im eingefuegten Text Leerzeichen', fakeAsync(() => {
      schmal();
      tick(); // ngModel meldet sich erst nach einem Mikrotask beim Formular an
      textfeld().value = 'Windräder\r\nkillen  \n\n  doch Vögel';
      textfeld().dispatchEvent(new Event('input'));
      fixture.detectChanges();
      tick();
      fixture.detectChanges();

      expect(component.searchQuery).toBe('Windräder killen doch Vögel');
      expect(textfeld().value).toBe('Windräder killen doch Vögel');
    }));

    it('laesst den Cursor nach dem Einfuegen mit Umbruch an der Einfuegestelle', fakeAsync(() => {
      schmal();
      tick();
      textfeld().value = 'Windräder\nund\n töten Vögel';
      textfeld().setSelectionRange(14, 14); // hinter „und\n“
      textfeld().dispatchEvent(new Event('input'));
      fixture.detectChanges();
      tick();
      fixture.detectChanges();

      expect(textfeld().value).toBe('Windräder und töten Vögel');
      expect(textfeld().selectionStart).toBe('Windräder und '.length);
    }));

    it('tippt den Hot Take als Platzhalter; der eine Knopf darunter sucht ihn', fakeAsync(() => {
      spyOn(window, 'matchMedia').and.callFake(() => ({ matches: false }) as MediaQueryList);
      const f = TestBed.createComponent(SearchComponent);
      f.componentRef.setInput('beispielAnimation', true);
      schmal(f);
      tick(HOT_TAKES[0].text.length * 45 + 10);
      f.detectChanges();

      expect(textfeld(f).placeholder).toBe(HOT_TAKES[0].text);
      expect(f.nativeElement.querySelector('.ausprobieren-knopf')).toBeNull();
      const knopf = f.nativeElement.querySelector('.search-button') as HTMLButtonElement;
      expect(knopf.textContent).toContain('Beispiel ausprobieren');
      knopf.click();
      expect(navigationServiceMock.navigateToResult).toHaveBeenCalledWith(HOT_TAKES[0].text);
      flush();
    }));

    it('hat ueber den Treffern (compactMode) „Suchen“ und das mehrzeilige Feld', () => {
      fixture.componentRef.setInput('compactMode', true);
      schmal();

      expect(textfeld()).not.toBeNull();
      expect(fixture.nativeElement.querySelector('.search-button').textContent).toContain('Suchen');
    });
  });
});
