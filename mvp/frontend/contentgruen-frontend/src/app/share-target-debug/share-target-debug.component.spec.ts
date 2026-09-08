import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { ShareTargetDebugComponent } from './share-target-debug.component';

/**
 * Die Komponente liest die Parameter absichtlich aus window.location statt aus
 * der Route (damit auch nicht angemeldete Parameter auftauchen). Getestet wird
 * deshalb gegen einen gesetzten Suchteil, nicht gegen einen Route-Stub.
 */
describe('ShareTargetDebugComponent', () => {
  let fixture: ComponentFixture<ShareTargetDebugComponent>;

  /** Setzt den Query-String, ohne die Seite neu zu laden. */
  function suchteilSetzen(suchteil: string): void {
    window.history.replaceState({}, '', `${window.location.pathname}${suchteil}`);
  }

  const urspruenglicherPfad = window.location.pathname + window.location.search;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ShareTargetDebugComponent],
      providers: [provideNoopAnimations()],
    }).compileComponents();
  });

  afterEach(() => {
    window.history.replaceState({}, '', urspruenglicherPfad);
  });

  function erzeugen(): ShareTargetDebugComponent {
    fixture = TestBed.createComponent(ShareTargetDebugComponent);
    fixture.detectChanges();
    return fixture.componentInstance;
  }

  it('liest title, text und url aus dem Query-String', () => {
    suchteilSetzen('?title=Ein+Post&text=Schau+dir+das+an&url=https%3A%2F%2Fexample.org%2Fp%2F1');
    const komponente = erzeugen();

    expect(komponente.title).toBe('Ein Post');
    expect(komponente.text).toBe('Schau dir das an');
    expect(komponente.url).toBe('https://example.org/p/1');
    expect(komponente.ohneParameter).toBeFalse();
  });

  it('meldet einen Aufruf ohne jeden Parameter', () => {
    suchteilSetzen('');
    const komponente = erzeugen();

    expect(komponente.ohneParameter).toBeTrue();
    expect(komponente.parameter).toEqual([]);
    expect(komponente.zerlegung).toBeNull();
  });

  it('markiert Parameter, die das Manifest nicht angemeldet hat', () => {
    suchteilSetzen('?text=hallo&ueberraschung=42');
    const komponente = erzeugen();

    const unerwartet = komponente.parameter.filter((zeile) => !zeile.erwartet);
    expect(unerwartet.length).toBe(1);
    expect(unerwartet[0].name).toBe('ueberraschung');
  });

  it('zerlegt einen Text mit eingebettetem Link in url und content', () => {
    suchteilSetzen('?text=Guter+Punkt+https%3A%2F%2Fexample.org%2Fp%2F1');
    const komponente = erzeugen();

    expect(komponente.zerlegung).toEqual({
      url: 'https://example.org/p/1',
      content: 'Guter Punkt https://example.org/p/1',
    });
  });

  it('nimmt einen Text ohne Link als reinen Inhalt', () => {
    suchteilSetzen('?text=nur+ein+Gedanke');
    const komponente = erzeugen();

    expect(komponente.zerlegung).toEqual({ content: 'nur ein Gedanke' });
  });

  it('haelt im Bericht auch fest, dass gar nichts ankam', () => {
    suchteilSetzen('');
    const komponente = erzeugen();

    expect(komponente.bericht).toContain('Parameter:\n  (keine)');
    expect(komponente.bericht).toContain('(kein text-Parameter)');
  });
});
