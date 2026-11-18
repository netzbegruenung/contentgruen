import { ComponentFixture, TestBed, discardPeriodicTasks, fakeAsync, flush, tick } from '@angular/core/testing';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideAnimations } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';
import { NavigationService } from '../services/navigation.service';
import { HOT_TAKES } from '../shared/startbeispiel';

import { SUCHANFRAGEN_ABSCHNITT, SUCHHINWEIS, SUCHHINWEIS_KURZ, SearchComponent } from './search.component';

describe('SearchComponent', () => {
  let component: SearchComponent;
  let fixture: ComponentFixture<SearchComponent>;
  let navigationServiceMock: any;

  beforeEach(async () => {
    navigationServiceMock = jasmine.createSpyObj('NavigationService', ['navigateToResult']);

    await TestBed.configureTestingModule({
      imports: [
        SearchComponent,
        MatFormFieldModule,
        MatInputModule,
      ],
      providers: [
        { provide: NavigationService, useValue: navigationServiceMock },
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
    it('sagt, dass nur der Spruch ohne Namen gespeichert wird und geprüft öffentlich werden kann', () => {
      expect(hinweis().textContent!.replace(/\s+/g, ' ').trim()).toBe(
        'Wir speichern nur den Spruch, nie deinen Namen oder Chat. Geprüfte Sprüche können öffentlich werden. Mehr dazu im Datenschutz',
      );
      expect(SUCHHINWEIS).toBe(
        'Wir speichern nur den Spruch, nie deinen Namen oder Chat. Geprüfte Sprüche können öffentlich werden.',
      );
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
  });
});
