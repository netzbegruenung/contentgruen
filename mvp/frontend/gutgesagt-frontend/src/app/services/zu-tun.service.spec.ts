import { TestBed, fakeAsync, tick } from '@angular/core/testing';
import { Subscription, of, throwError } from 'rxjs';

import { ContentReport, Loeschauftrag, ModerationService } from './moderation.service';
import { SuchanfragenFreigabeService } from './suchanfragen-freigabe.service';
import {
  KEINE_SUCHANFRAGEN,
  KOPF_NACHLADEN_MS,
  MELDUNGEN_GRENZE,
  OffeneLoeschauftraege,
  OffeneMeldungen,
  Stand,
  WartendeSuchanfragen,
  ZuTunService,
  suchanfragenText,
  wartetSeit,
} from './zu-tun.service';
import { NACHLADEN_MS } from '../shared/selbst-nachladen';

function meldung(id: string, created: string): ContentReport {
  return {
    id,
    content_id: 'b-' + id,
    content_type: 'commentary',
    reason: 'inappropriate',
    description: null,
    reported_by_user_id: null,
    reported_by_session_id: null,
    created,
    status: 'pending',
  };
}

function auftrag(id: string, ueberfaellig: boolean): Loeschauftrag {
  return {
    id,
    user_id: 'p-' + id,
    anzeigename: null,
    widerrufen_am: '2026-11-01T10:00:00Z',
    angelegt_am: '2026-11-01T10:00:00Z',
    frist: '2026-11-08T10:00:00Z',
    ueberfaellig,
    neu_eingewilligt_am: null,
  };
}

describe('ZuTunService', () => {
  let moderation: jasmine.SpyObj<ModerationService>;
  let suchanfragen: jasmine.SpyObj<SuchanfragenFreigabeService>;
  let dienst: ZuTunService;
  let sichtbarkeit: DocumentVisibilityState;

  beforeEach(() => {
    sichtbarkeit = 'visible';
    spyOnProperty(document, 'visibilityState', 'get').and.callFake(() => sichtbarkeit);
    moderation = jasmine.createSpyObj('ModerationService', ['getReports', 'getLoeschauftraege']);
    moderation.getReports.and.returnValue(
      of({ total: 2, reports: [meldung('neu', '2026-11-13T09:00:00Z'), meldung('alt', '2026-11-10T09:00:00Z')] }),
    );
    moderation.getLoeschauftraege.and.returnValue(of({ frist_tage: 7, auftraege: [auftrag('a', true), auftrag('b', false)] }));
    suchanfragen = jasmine.createSpyObj('SuchanfragenFreigabeService', ['anzahl']);
    suchanfragen.anzahl.and.returnValue(of({ anzahl: 3 }));
    TestBed.configureTestingModule({
      providers: [
        { provide: ModerationService, useValue: moderation },
        { provide: SuchanfragenFreigabeService, useValue: suchanfragen },
      ],
    });
    dienst = TestBed.inject(ZuTunService);
  });

  it('zaehlt wartende Suchanfragen still und erst, wenn jemand zuhoert (#664)', () => {
    expect(suchanfragen.anzahl).not.toHaveBeenCalled();
    let stand: Stand<WartendeSuchanfragen> | undefined;
    const abo = dienst.suchanfragen$.subscribe((s) => (stand = s));

    expect(suchanfragen.anzahl).toHaveBeenCalledOnceWith(true);
    expect(stand).toEqual({ daten: { anzahl: 3 }, fehler: false });
    abo.unsubscribe();
  });

  it('meldet 401/403 bei den Suchanfragen als abgelaufen und fragt nicht weiter', fakeAsync(() => {
    suchanfragen.anzahl.and.returnValue(throwError(() => ({ status: 403 })));
    let stand: Stand<WartendeSuchanfragen> | undefined;
    const abo = dienst.suchanfragen$.subscribe((s) => (stand = s));

    expect(stand).toEqual({ daten: null, fehler: true, abgelaufen: true });
    tick(KOPF_NACHLADEN_MS * 8);
    expect(suchanfragen.anzahl).toHaveBeenCalledTimes(1);
    abo.unsubscribe();
  }));

  it('suchanfragenText: Einzahl und Mehrzahl wie freigegeben', () => {
    expect(suchanfragenText(1)).toBe('1 Suchanfrage wartet auf Freigabe');
    expect(suchanfragenText(2)).toBe('2 Suchanfragen warten auf Freigabe');
    expect(KEINE_SUCHANFRAGEN).toBe('Keine Suchanfragen zur Freigabe');
  });

  it('zaehlt die offenen Meldungen und nennt die aelteste', () => {
    let stand: Stand<OffeneMeldungen> | undefined;
    const abo = dienst.meldungen$.subscribe((s) => (stand = s));

    // Still: frisch statt aus dem Cache, kein Sprung auf /login bei 401.
    expect(moderation.getReports).toHaveBeenCalledWith('pending', MELDUNGEN_GRENZE, 0, true);
    expect(moderation.getLoeschauftraege).not.toHaveBeenCalled();
    expect(stand).toEqual({ daten: { anzahl: 2, mehr: false, aelteste: '2026-11-10T09:00:00Z' }, fehler: false });
    abo.unsubscribe();
  });

  it('zaehlt die offenen Loeschauftraege und die ueberfaelligen', () => {
    let stand: Stand<OffeneLoeschauftraege> | undefined;
    const abo = dienst.loeschauftraege$.subscribe((s) => (stand = s));

    expect(stand).toEqual({ daten: { anzahl: 2, ueberfaellig: 1 }, fehler: false });
    abo.unsubscribe();
  });

  it('teilt eine Abfrage zwischen Kopf und Zeile', () => {
    const abos = [dienst.meldungen$.subscribe(), dienst.meldungen$.subscribe()];

    expect(moderation.getReports).toHaveBeenCalledTimes(1);
    abos.forEach((abo) => abo.unsubscribe());
  });

  it('laedt ausserhalb von /admin alle 120 s nach und behaelt bei einem Fehler den letzten Stand', fakeAsync(() => {
    const staende: Stand<OffeneMeldungen>[] = [];
    const abo: Subscription = dienst.meldungen$.subscribe((s) => staende.push(s));

    moderation.getReports.and.returnValue(throwError(() => new Error('weg')));
    tick(NACHLADEN_MS);
    expect(moderation.getReports).toHaveBeenCalledTimes(1);
    tick(KOPF_NACHLADEN_MS - NACHLADEN_MS);
    expect(staende[staende.length - 1]).toEqual({
      daten: { anzahl: 2, mehr: false, aelteste: '2026-11-10T09:00:00Z' },
      fehler: true,
    });

    sichtbarkeit = 'hidden';
    tick(KOPF_NACHLADEN_MS * 4);
    expect(moderation.getReports).toHaveBeenCalledTimes(2);

    abo.unsubscribe();
    sichtbarkeit = 'visible';
    tick(KOPF_NACHLADEN_MS * 4);
    expect(moderation.getReports).toHaveBeenCalledTimes(2);
  }));

  it('hoert nach 401 auf zu fragen, bis zur naechsten Anmeldung (neues Abonnement)', fakeAsync(() => {
    moderation.getReports.and.returnValue(throwError(() => ({ status: 401 })));
    let abo = dienst.meldungen$.subscribe();

    tick(KOPF_NACHLADEN_MS * 4);
    document.dispatchEvent(new Event('visibilitychange'));
    expect(moderation.getReports).toHaveBeenCalledTimes(1);
    abo.unsubscribe();

    moderation.getReports.and.returnValue(of({ total: 0, reports: [] }));
    abo = dienst.meldungen$.subscribe();
    expect(moderation.getReports).toHaveBeenCalledTimes(2);
    abo.unsubscribe();
  }));

  it('fragt nicht selbst, solange die Moderation die offenen Meldungen speist', fakeAsync(() => {
    let stand: Stand<OffeneMeldungen> | undefined;
    const abo = dienst.meldungen$.subscribe((s) => (stand = s));
    dienst.meldungenGespeist([meldung('a', '2026-11-12T09:00:00Z')]);
    expect(stand!.daten!.anzahl).toBe(1);

    document.dispatchEvent(new Event('visibilitychange'));
    expect(moderation.getReports).toHaveBeenCalledTimes(1);
    abo.unsubscribe();
  }));

  it('fragt nach Ablauf der Speisung wieder selbst', fakeAsync(() => {
    const abo = dienst.meldungen$.subscribe();
    dienst.meldungenGespeist([meldung('a', '2026-11-12T09:00:00Z')]);
    tick(NACHLADEN_MS + 5_000);
    expect(moderation.getReports).toHaveBeenCalledTimes(1);

    // Der naechste Takt nach Ablauf fragt wieder.
    tick(KOPF_NACHLADEN_MS);
    expect(moderation.getReports).toHaveBeenCalledTimes(2);
    abo.unsubscribe();
  }));

  it('meldet 401 als abgelaufen und fragt nach einem Anstoss wieder', fakeAsync(() => {
    moderation.getReports.and.returnValue(throwError(() => ({ status: 401 })));
    let stand: Stand<OffeneMeldungen> | undefined;
    const abo = dienst.meldungen$.subscribe((s) => (stand = s));
    expect(stand!.abgelaufen).toBeTrue();

    moderation.getReports.and.returnValue(of({ total: 0, reports: [] }));
    dienst.aktualisieren();
    expect(moderation.getReports).toHaveBeenCalledTimes(2);
    expect(stand).toEqual({ daten: { anzahl: 0, mehr: false, aelteste: null }, fehler: false });
    abo.unsubscribe();
  }));

  it('liefert die Liste der Loeschauftraege aus derselben Abfrage wie die Zahl', () => {
    const abos = [dienst.loeschauftraege$.subscribe(), dienst.loeschauftraegeAntwort$.subscribe()];

    expect(moderation.getLoeschauftraege).toHaveBeenCalledOnceWith(true);
    abos.forEach((abo) => abo.unsubscribe());
  });

  it('fragt nach einer Handlung sofort neu', () => {
    const abo = dienst.meldungen$.subscribe();
    dienst.aktualisieren();

    expect(moderation.getReports).toHaveBeenCalledTimes(2);
    abo.unsubscribe();
  });

  it('sagt bei erreichter Grenze, dass es mehr sein koennen', () => {
    const viele = Array.from({ length: MELDUNGEN_GRENZE }, (_, i) => meldung(String(i), '2026-11-13T09:00:00Z'));
    moderation.getReports.and.returnValue(of({ total: viele.length, reports: viele }));
    let stand: Stand<OffeneMeldungen> | undefined;
    const abo = dienst.meldungen$.subscribe((s) => (stand = s));

    expect(stand!.daten!.mehr).toBeTrue();
    abo.unsubscribe();
  });
});

describe('wartetSeit', () => {
  const jetzt = new Date('2026-11-13T12:00:00Z');

  it('nennt unter einer Stunde keine Zahl', () => {
    expect(wartetSeit('2026-11-13T11:30:00Z', jetzt)).toBe('seit unter einer Stunde');
  });

  it('zaehlt bis zwei Tage in Stunden', () => {
    expect(wartetSeit('2026-11-13T11:00:00Z', jetzt)).toBe('seit 1 Stunde');
    expect(wartetSeit('2026-11-12T00:00:00Z', jetzt)).toBe('seit 36 Stunden');
  });

  it('zaehlt danach in Tagen', () => {
    expect(wartetSeit('2026-11-10T12:00:00Z', jetzt)).toBe('seit 3 Tagen');
  });
});
