import { ComponentFixture, TestBed, discardPeriodicTasks, fakeAsync, tick } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { Subject, of, throwError } from 'rxjs';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { LoeschauftraegeComponent, NACHLADEN_MS } from './loeschauftraege.component';
import { Loeschauftrag, LoeschauftraegeResponse, ModerationService } from '../../services/moderation.service';

function auftrag(overrides: Partial<Loeschauftrag> = {}): Loeschauftrag {
  return {
    id: 'auftrag-1',
    user_id: 'person-1',
    anzeigename: 'Anna B.',
    angelegt_am: '2026-11-10T10:00:00Z',
    frist: '2026-11-17T10:00:00Z',
    ueberfaellig: false,
    ...overrides,
  };
}

function antwort(auftraege: Loeschauftrag[]): LoeschauftraegeResponse {
  return { frist_tage: 7, auftraege };
}

describe('LoeschauftraegeComponent', () => {
  let fixture: ComponentFixture<LoeschauftraegeComponent>;
  let moderation: jasmine.SpyObj<ModerationService>;
  let dialog: jasmine.SpyObj<MatDialog>;
  let snackBar: jasmine.SpyObj<MatSnackBar>;
  let sichtbarkeit: DocumentVisibilityState;

  function element(): HTMLElement {
    return fixture.nativeElement as HTMLElement;
  }

  function knopf(text: string): HTMLButtonElement | undefined {
    const knoepfe = Array.from(element().querySelectorAll('button')) as HTMLButtonElement[];
    return knoepfe.find((b) => b.textContent?.includes(text));
  }

  function dialogAntwort(ja: boolean | undefined) {
    dialog.open.and.returnValue({ afterClosed: () => of(ja) } as any);
  }

  function starten() {
    fixture = TestBed.createComponent(LoeschauftraegeComponent);
    fixture.detectChanges();
  }

  beforeEach(() => {
    moderation = jasmine.createSpyObj('ModerationService', ['getLoeschauftraege', 'loeschauftragAusfuehren']);
    moderation.getLoeschauftraege.and.returnValue(of(antwort([auftrag()])));
    moderation.loeschauftragAusfuehren.and.returnValue(of({ beitraege: 3, einwuerfe: 1, saetze: 2 }));
    dialog = jasmine.createSpyObj('MatDialog', ['open']);
    snackBar = jasmine.createSpyObj('MatSnackBar', ['open']);
    sichtbarkeit = 'visible';
    spyOnProperty(document, 'visibilityState', 'get').and.callFake(() => sichtbarkeit);

    TestBed.configureTestingModule({
      imports: [LoeschauftraegeComponent, NoopAnimationsModule],
      providers: [{ provide: ModerationService, useValue: moderation }],
    });
    TestBed.overrideProvider(MatDialog, { useValue: dialog });
    TestBed.overrideProvider(MatSnackBar, { useValue: snackBar });
  });

  afterEach(() => fixture?.destroy());

  describe('Liste', () => {
    it('zeigt beim ersten Laden einen Spinner mit Text statt einer leeren Seite', () => {
      const unterwegs = new Subject<LoeschauftraegeResponse>();
      moderation.getLoeschauftraege.and.returnValue(unterwegs);

      starten();

      expect(element().querySelector('mat-spinner')).not.toBeNull();
      expect(element().textContent).toContain('Lade Löschaufträge');
      expect(element().textContent).not.toContain('neu laden');
    });

    it('zeigt jeden offenen Auftrag mit Name, Kennung, Widerruf und Frist', () => {
      starten();

      const zeilen = element().querySelectorAll('[data-testid="loeschauftrag"]');
      expect(zeilen.length).toBe(1);
      const text = zeilen[0].textContent!;
      expect(text).toContain('Anna B.');
      expect(text).toContain('(person-1)');
      expect(text).toContain('Widerrufen am');
      expect(text).toContain('Frist bis');
      expect(zeilen[0].classList).not.toContain('ueberfaellig');
    });

    it('hebt überfällige Aufträge hervor', () => {
      moderation.getLoeschauftraege.and.returnValue(of(antwort([auftrag({ ueberfaellig: true })])));

      starten();

      const zeile = element().querySelector('[data-testid="loeschauftrag"]')!;
      expect(zeile.classList).toContain('ueberfaellig');
      expect(zeile.textContent).toContain('Überfällig seit');
    });

    it('zeigt ohne Anzeigenamen die Kennung', () => {
      moderation.getLoeschauftraege.and.returnValue(of(antwort([auftrag({ anzeigename: null })])));

      starten();

      expect(element().querySelector('.person')!.textContent!.trim()).toBe('person-1');
    });

    it('sagt, wenn nichts offen ist', () => {
      moderation.getLoeschauftraege.and.returnValue(of(antwort([])));

      starten();

      expect(element().textContent).toContain('Keine offenen Löschaufträge');
    });

    it('meldet die Zahl der offenen Aufträge nach jedem Laden', () => {
      fixture = TestBed.createComponent(LoeschauftraegeComponent);
      const zahlen: number[] = [];
      fixture.componentInstance.anzahl.subscribe((n) => zahlen.push(n));

      fixture.detectChanges();

      expect(zahlen).toEqual([1]);
    });

    it('zeigt bei einem Ladefehler einen Spinner mit Text, keinen Aufruf zum Neuladen', () => {
      moderation.getLoeschauftraege.and.returnValue(throwError(() => ({ status: 500 })));

      starten();

      expect(element().querySelector('mat-spinner')).not.toBeNull();
      expect(element().textContent).toContain('neuer Versuch in Kürze');
      expect(element().textContent).not.toContain('neu laden');
    });
  });

  describe('Nachladen', () => {
    it('lädt im Takt nach, solange der Reiter sichtbar ist', fakeAsync(() => {
      starten();
      expect(moderation.getLoeschauftraege).toHaveBeenCalledTimes(1);

      tick(NACHLADEN_MS);
      expect(moderation.getLoeschauftraege).toHaveBeenCalledTimes(2);

      sichtbarkeit = 'hidden';
      tick(NACHLADEN_MS);
      expect(moderation.getLoeschauftraege).toHaveBeenCalledTimes(2);

      discardPeriodicTasks();
    }));

    it('lädt sofort nach, wenn der Reiter wieder sichtbar wird', fakeAsync(() => {
      starten();
      sichtbarkeit = 'visible';

      document.dispatchEvent(new Event('visibilitychange'));

      expect(moderation.getLoeschauftraege).toHaveBeenCalledTimes(2);
      discardPeriodicTasks();
    }));

    it('holt nach einem Ladefehler die Liste im nächsten Takt selbst', fakeAsync(() => {
      moderation.getLoeschauftraege.and.returnValue(throwError(() => ({ status: 500 })));
      starten();
      moderation.getLoeschauftraege.and.returnValue(of(antwort([auftrag()])));

      tick(NACHLADEN_MS);
      fixture.detectChanges();

      expect(element().querySelectorAll('[data-testid="loeschauftrag"]').length).toBe(1);
      discardPeriodicTasks();
    }));

    it('hört beim Verlassen auf nachzuladen', fakeAsync(() => {
      starten();
      fixture.destroy();

      tick(NACHLADEN_MS * 2);

      expect(moderation.getLoeschauftraege).toHaveBeenCalledTimes(1);
    }));
  });

  describe('Ausführen', () => {
    it('fragt vorher und führt nach dem Ja aus, dann lädt die Liste selbst nach', () => {
      starten();
      dialogAntwort(true);
      moderation.getLoeschauftraege.and.returnValue(of(antwort([])));

      knopf('Löschablauf ausführen')!.click();
      fixture.detectChanges();

      expect(dialog.open).toHaveBeenCalled();
      expect(moderation.loeschauftragAusfuehren).toHaveBeenCalledWith('auftrag-1');
      expect(snackBar.open.calls.mostRecent().args[0]).toBe(
        'Erledigt: 3 Beiträge anonymisiert, 1 Einwurf gelöscht, 2 Sätze ohne Namen.'
      );
      expect(element().textContent).toContain('Keine offenen Löschaufträge');
    });

    it('führt ohne Ja nichts aus', () => {
      starten();
      dialogAntwort(false);

      knopf('Löschablauf ausführen')!.click();

      expect(moderation.loeschauftragAusfuehren).not.toHaveBeenCalled();
    });

    it('zeigt während des Laufs einen Spinner im Knopf und sperrt die Knöpfe', () => {
      starten();
      dialogAntwort(true);
      moderation.loeschauftragAusfuehren.and.returnValue(new Subject<any>());

      knopf('Löschablauf ausführen')!.click();
      fixture.detectChanges();

      const laufend = knopf('Wird ausgeführt')!;
      expect(laufend.disabled).toBeTrue();
      expect(laufend.querySelector('mat-spinner')).not.toBeNull();
    });

    it('sagt bei einem Fehler, dass der Auftrag offen bleibt', () => {
      starten();
      dialogAntwort(true);
      moderation.loeschauftragAusfuehren.and.returnValue(throwError(() => ({ status: 500 })));

      knopf('Löschablauf ausführen')!.click();
      fixture.detectChanges();

      expect(snackBar.open.calls.mostRecent().args[0]).toContain('der Auftrag bleibt offen');
      expect(knopf('Löschablauf ausführen')!.disabled).toBeFalse();
    });

    it('sagt, wenn ein anderer Admin schneller war', () => {
      starten();
      dialogAntwort(true);
      moderation.loeschauftragAusfuehren.and.returnValue(throwError(() => ({ status: 409 })));

      knopf('Löschablauf ausführen')!.click();

      expect(snackBar.open.calls.mostRecent().args[0]).toBe('Der Löschauftrag ist schon erledigt.');
      expect(moderation.getLoeschauftraege).toHaveBeenCalledTimes(2);
    });
  });
});
