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

  // Designrunde 17.11.: Auf dem Start tippt das leere Feld Hot Takes vor, daneben „Ausprobieren“
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
      f.nativeElement.querySelector('.ausprobieren-knopf') as HTMLButtonElement | null;

    it('tippt das erste Beispiel ein und sucht mit „Ausprobieren“ genau danach', fakeAsync(() => {
      const f = mitBeispiel(false);
      tick(HOT_TAKES[0].text.length * 45 + 10);
      f.detectChanges();

      expect(feld(f).placeholder).toBe(HOT_TAKES[0].text);
      knopf(f)!.click();
      expect(navigationServiceMock.navigateToResult).toHaveBeenCalledWith(HOT_TAKES[0].text);
      f.detectChanges();
      expect(feld(f).placeholder).toBe('');
      flush();
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
      expect(knopf(f)).toBeNull();
      flush();
    }));

    it('laesst Tab den Knopf stehen, damit er per Tastatur erreichbar bleibt', fakeAsync(() => {
      const f = mitBeispiel(false);
      tick(HOT_TAKES[0].text.length * 45 + 10);
      f.detectChanges();

      feld(f).dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab' }));
      f.detectChanges();

      expect(knopf(f)).not.toBeNull();
      expect(feld(f).placeholder).toBe(HOT_TAKES[0].text);
      flush(5000);
    }));

    it('haelt mit Fokus auf „Ausprobieren“ beim aktuellen Beispiel an', fakeAsync(() => {
      const f = mitBeispiel(false);
      tick(HOT_TAKES[0].text.length * 45 + 10);
      f.detectChanges();

      knopf(f)!.dispatchEvent(new FocusEvent('focus'));
      tick(10_000);
      f.detectChanges();

      expect(feld(f).placeholder).toBe(HOT_TAKES[0].text);
      expect(knopf(f)).not.toBeNull();
    }));

    it('bleibt nach zwei Durchlaeufen beim ersten Beispiel stehen (WCAG 2.2.2)', fakeAsync(() => {
      const f = mitBeispiel(false);
      flush(5000);
      f.detectChanges();

      expect(feld(f).placeholder).toBe(HOT_TAKES[0].text);
      expect(knopf(f)).not.toBeNull();
    }));

    it('zeigt bei reduzierter Bewegung das Beispiel ohne Tippen', fakeAsync(() => {
      const f = mitBeispiel(true);
      f.detectChanges();

      expect(feld(f).placeholder).toBe(HOT_TAKES[0].text);
      expect(knopf(f)).not.toBeNull();
      discardPeriodicTasks();
    }));

    it('tippt ohne beispielAnimation nichts vor (Feld ueber den Treffern)', () => {
      expect(feld(fixture).placeholder).toBe('');
      expect(knopf(fixture)).toBeNull();
    });

    it('zeigt „Ausprobieren“ am Desktop im Feld, nicht darunter', fakeAsync(() => {
      const f = mitBeispiel(false);
      tick(HOT_TAKES[0].text.length * 45 + 10);
      f.detectChanges();

      expect(knopf(f)!.closest('mat-form-field')).not.toBeNull();
      expect(knopf(f)!.classList).not.toContain('ausprobieren-unter-feld');
      flush(5000);
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

    it('wird das Feld mehrzeilig: 2 bis 4 Zeilen, mit Beschriftung, Hinweis und Kennung', () => {
      fixture.componentRef.setInput('feldId', 'suche');
      schmal();

      expect(fixture.nativeElement.querySelector('input')).toBeNull();
      const autosize = fixture.debugElement.query(By.directive(CdkTextareaAutosize)).injector.get(CdkTextareaAutosize);
      expect(autosize.minRows).toBe(2);
      expect(autosize.maxRows).toBe(4);
      expect(textfeld().id).toBe('suche');
      expect(textfeld().getAttribute('aria-describedby')).toBe(fixture.nativeElement.querySelector('.such-hinweis').id);
      expect(fixture.nativeElement.querySelector('mat-label').textContent.trim()).toBe('Worauf willst du antworten? Text einfügen');
    });

    it('sucht mit Enter, ohne eine neue Zeile', () => {
      schmal();
      component.searchQuery = 'Tempolimit bringt nichts';
      const enter = new KeyboardEvent('keydown', { key: 'Enter', cancelable: true });
      textfeld().dispatchEvent(enter);

      expect(enter.defaultPrevented).toBeTrue();
      expect(navigationServiceMock.navigateToResult).toHaveBeenCalledWith('Tempolimit bringt nichts');
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

    it('tippt den Hot Take als Platzhalter und zeigt „Ausprobieren“ unter dem Feld', fakeAsync(() => {
      spyOn(window, 'matchMedia').and.callFake(() => ({ matches: false }) as MediaQueryList);
      const f = TestBed.createComponent(SearchComponent);
      f.componentRef.setInput('beispielAnimation', true);
      schmal(f);
      tick(HOT_TAKES[0].text.length * 45 + 10);
      f.detectChanges();

      expect(textfeld(f).placeholder).toBe(HOT_TAKES[0].text);
      const knopf = f.nativeElement.querySelector('.ausprobieren-knopf') as HTMLButtonElement;
      expect(knopf.classList).toContain('ausprobieren-unter-feld');
      expect(knopf.closest('mat-form-field')).toBeNull();
      knopf.click();
      expect(navigationServiceMock.navigateToResult).toHaveBeenCalledWith(HOT_TAKES[0].text);
      flush();
    }));

    it('hat ueber den Treffern (compactMode) kein „Ausprobieren“, aber das mehrzeilige Feld', () => {
      fixture.componentRef.setInput('compactMode', true);
      schmal();

      expect(textfeld()).not.toBeNull();
      expect(fixture.nativeElement.querySelector('.ausprobieren-zeile')).toBeNull();
      expect(fixture.nativeElement.querySelector('.ausprobieren-knopf')).toBeNull();
    });
  });
});
