import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideAnimations } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';
import { NavigationService } from '../services/navigation.service';

import { SUCHANFRAGEN_ABSCHNITT, SUCHHINWEIS, SearchComponent } from './search.component';

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
    expect(feld.querySelector('mat-label')!.textContent!.trim()).toBe('Was hast du gelesen? Text oder Post einfügen');
    expect(feld.querySelector('.mat-mdc-form-field-required-marker')).toBeNull();
    expect(feld.querySelector('input')!.hasAttribute('required')).toBeFalse();
  });

  it('nimmt ueber den Treffern (compactMode) die kurze Beschriftung', () => {
    fixture.componentRef.setInput('compactMode', true);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('mat-label').textContent.trim()).toBe('Text oder Post einfügen');
  });

  // Persona-Test Gerd: dass der Suchtext gespeichert wird, stand nur in der Datenschutzerklärung
  describe('Hinweis unter dem Feld', () => {
    function hinweis(): HTMLElement {
      return fixture.nativeElement.querySelector('.such-hinweis');
    }

    it('sagt, dass Suchtexte ohne Namen gespeichert und erst nach Prüfung sichtbar werden', () => {
      const text = hinweis().textContent!.replace(/\s+/g, ' ');
      expect(text).toContain(SUCHHINWEIS);
      expect(SUCHHINWEIS).toContain('ohne deinen Namen');
      expect(SUCHHINWEIS).toContain('nach Prüfung durch das Moderationsteam');
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

    it('steht auch über den Treffern (compactMode)', () => {
      fixture.componentRef.setInput('compactMode', true);
      fixture.detectChanges();
      expect(hinweis()).not.toBeNull();
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
});
