import { TestBed } from '@angular/core/testing';
import { Clipboard } from '@angular/cdk/clipboard';
import { MatSnackBar } from '@angular/material/snack-bar';

import {
  TEILEN_LINK_KOPIERT,
  TEILEN_NAVIGATOR,
  TEILEN_NICHT_KOPIERT,
  TeilenNavigator,
  TeilenService,
  hatGeteilt,
  sucheLink,
} from './teilen.service';

describe('TeilenService (B7)', () => {
  const URL = 'https://gutgesagt.example/beitrag/b-1';
  let nav: TeilenNavigator;
  let clipboard: jasmine.SpyObj<Clipboard>;
  let snackBar: jasmine.SpyObj<MatSnackBar>;
  let service: TeilenService;

  beforeEach(() => {
    nav = {};
    clipboard = jasmine.createSpyObj('Clipboard', ['copy']);
    clipboard.copy.and.returnValue(true);
    snackBar = jasmine.createSpyObj('MatSnackBar', ['open']);
    TestBed.configureTestingModule({
      providers: [
        { provide: TEILEN_NAVIGATOR, useFactory: () => nav },
        { provide: Clipboard, useValue: clipboard },
        { provide: MatSnackBar, useValue: snackBar },
      ],
    });
    service = TestBed.inject(TeilenService);
  });

  it('nimmt das Teilen-Menue des Geraets, wenn es eines gibt', async () => {
    nav.share = jasmine.createSpy('share').and.resolveTo(undefined);

    const ergebnis = await service.teilen({ url: URL, text: 'Text', titel: 'Titel' });

    expect(ergebnis).toBe('geteilt');
    expect(nav.share).toHaveBeenCalledOnceWith({ url: URL, text: 'Text', title: 'Titel' });
    expect(clipboard.copy).not.toHaveBeenCalled();
    expect(snackBar.open).not.toHaveBeenCalled();
  });

  it('laesst leeren Text und Titel weg', async () => {
    nav.share = jasmine.createSpy('share').and.resolveTo(undefined);

    await service.teilen({ url: URL, text: '', titel: undefined });

    expect(nav.share).toHaveBeenCalledOnceWith({ url: URL });
  });

  it('kopiert ohne Web Share API den Link und sagt es', async () => {
    const ergebnis = await service.teilen({ url: URL, text: 'Text' });

    expect(ergebnis).toBe('kopiert');
    expect(clipboard.copy).toHaveBeenCalledOnceWith(URL);
    expect(snackBar.open).toHaveBeenCalledOnceWith(TEILEN_LINK_KOPIERT, 'OK', { duration: 4000 });
  });

  it('kopiert, wenn canShare die Daten ablehnt', async () => {
    nav.share = jasmine.createSpy('share');
    nav.canShare = () => false;

    expect(await service.teilen({ url: URL })).toBe('kopiert');
    expect(nav.share).not.toHaveBeenCalled();
  });

  it('meldet bei einem Abbruch (AbortError) nichts und kopiert nicht', async () => {
    nav.share = jasmine.createSpy('share').and.rejectWith(new DOMException('abgebrochen', 'AbortError'));

    expect(await service.teilen({ url: URL })).toBe('abgebrochen');
    expect(clipboard.copy).not.toHaveBeenCalled();
    expect(snackBar.open).not.toHaveBeenCalled();
  });

  it('kopiert bei einem anderen Fehler des Teilen-Menues', async () => {
    nav.share = jasmine.createSpy('share').and.rejectWith(new DOMException('nein', 'NotAllowedError'));

    expect(await service.teilen({ url: URL })).toBe('kopiert');
    expect(clipboard.copy).toHaveBeenCalledOnceWith(URL);
  });

  it('sagt, wenn auch Kopieren scheitert', async () => {
    clipboard.copy.and.returnValue(false);

    expect(await service.teilen({ url: URL })).toBe('fehlgeschlagen');
    expect(snackBar.open).toHaveBeenCalledOnceWith(TEILEN_NICHT_KOPIERT, 'OK', { duration: 4000 });
  });

  it('zaehlt nur Geteiltes und Kopiertes als geteilt', () => {
    expect(hatGeteilt('geteilt')).toBeTrue();
    expect(hatGeteilt('kopiert')).toBeTrue();
    expect(hatGeteilt('abgebrochen')).toBeFalse();
    expect(hatGeteilt('fehlgeschlagen')).toBeFalse();
  });

  it('baut den Link auf eine Suche mit kodiertem Suchtext', () => {
    expect(sucheLink('Windräder töten Vögel & mehr', 'https://gutgesagt.example')).toBe(
      'https://gutgesagt.example/result?searchQuery=Windr%C3%A4der%20t%C3%B6ten%20V%C3%B6gel%20%26%20mehr',
    );
  });
});
