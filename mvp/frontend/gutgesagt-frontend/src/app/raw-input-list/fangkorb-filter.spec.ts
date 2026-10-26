import {
  FILTER_SCHLUESSEL,
  FangkorbFilter,
  filterLaden,
  filterSpeichern,
  passtZumFilter,
  passtZumTab,
  standardFilter,
  tabAus,
  tabMerken,
  verworfenEinblenden,
} from './fangkorb-filter';
import { Einwurf, Satz, Verknuepfung } from '../services/einwurf.service';

function einwurf(overrides: Partial<Einwurf> = {}): Einwurf {
  return {
    id: 'id-1',
    content: null,
    url: 'https://example.org/post',
    image_url: null,
    submitted_by: 'alice',
    source_channel: 'web',
    status: 'open',
    created_at: '2026-09-13T12:00:00Z',
    ...overrides,
  };
}

function satz(id: string): Satz {
  return { id, user_id: 'bob', sentence: 'Ein Satz', updated_at: '2026-09-13T12:00:00Z' };
}

function link(draft_id: string | null): Verknuepfung {
  return {
    content_id: `c-${draft_id}`,
    content_type: 'commentary',
    draft_id,
    processed_by: 'carol',
    processed_at: '2026-09-13T13:00:00Z',
  };
}

function filter(overrides: Partial<FangkorbFilter> = {}): FangkorbFilter {
  return { ...standardFilter(), ...overrides };
}

describe('passtZumFilter', () => {
  it('laesst im Standard alles durch', () => {
    for (const status of ['open', 'in_progress', 'processed', 'discarded'] as const) {
      expect(passtZumFilter(einwurf({ status }), standardFilter(), 'alice')).toBeTrue();
    }
  });

  it('blendet abgewaehlte Plattformen aus', () => {
    const ohneInstagram = filter({ plattformen: ['youtube', 'tiktok', 'web'] });

    expect(
      passtZumFilter(einwurf({ url: 'https://www.instagram.com/reel/A/' }), ohneInstagram, null),
    ).toBeFalse();
    expect(passtZumFilter(einwurf({ url: 'https://youtu.be/1' }), ohneInstagram, null)).toBeTrue();
  });

  it('blendet Einwuerfe ohne Link nie ueber die Plattform aus', () => {
    expect(
      passtZumFilter(einwurf({ url: null, content: 'nur Text' }), filter({ plattformen: [] }), null),
    ).toBeTrue();
  });

  it('zeigt bei "nur meine" nur selbst Eingeworfenes', () => {
    const nurMeine = filter({ nurMeine: true });

    expect(passtZumFilter(einwurf({ submitted_by: 'alice' }), nurMeine, 'alice')).toBeTrue();
    expect(passtZumFilter(einwurf({ submitted_by: 'bob' }), nurMeine, 'alice')).toBeFalse();
    expect(passtZumFilter(einwurf({ submitted_by: null }), nurMeine, 'alice')).toBeFalse();
  });

  it('zeigt bei "nur meine" ohne eigene Kennung nichts', () => {
    expect(passtZumFilter(einwurf({ submitted_by: null }), filter({ nurMeine: true }), null)).toBeFalse();
  });
});

describe('passtZumTab', () => {
  it('legt einen Einwurf ohne Satz unter Destillieren', () => {
    const roh = einwurf();

    expect(passtZumTab(roh, 'destillieren', false)).toBeTrue();
    expect(passtZumTab(roh, 'ausformulieren', false)).toBeFalse();
    expect(passtZumTab(roh, 'ausformuliert', false)).toBeFalse();
  });

  it('legt einen Einwurf mit Satz, aber ohne Beitrag unter Ausformulieren', () => {
    const roh = einwurf({ status: 'in_progress', drafts: [satz('s-1')] });

    expect(passtZumTab(roh, 'ausformulieren', false)).toBeTrue();
    expect(passtZumTab(roh, 'destillieren', false)).toBeFalse();
  });

  it('legt einen Einwurf mit Beitrag unter Ausformuliert, auch ohne Satz', () => {
    const mitSatz = einwurf({ status: 'processed', drafts: [satz('s-1')], links: [link('s-1')] });
    const ohneSatz = einwurf({ status: 'processed', links: [link(null)] });

    expect(passtZumTab(mitSatz, 'ausformuliert', false)).toBeTrue();
    expect(passtZumTab(ohneSatz, 'ausformuliert', false)).toBeTrue();
    expect(passtZumTab(ohneSatz, 'destillieren', false)).toBeFalse();
  });

  it('zeigt Verworfenes nur unter Ausformuliert und nur mit Chip', () => {
    const verworfen = einwurf({ status: 'discarded', drafts: [satz('s-1')] });

    expect(passtZumTab(verworfen, 'ausformuliert', false)).toBeFalse();
    expect(passtZumTab(verworfen, 'ausformuliert', true)).toBeTrue();
    expect(passtZumTab(verworfen, 'destillieren', true)).toBeFalse();
    expect(passtZumTab(verworfen, 'ausformulieren', true)).toBeFalse();
  });
});

describe('tabAus', () => {
  it('kennt die drei Tabs und den frueheren Namen "erledigt"', () => {
    expect(tabAus('destillieren')).toBe('destillieren');
    expect(tabAus('ausformulieren')).toBe('ausformulieren');
    expect(tabAus('ausformuliert')).toBe('ausformuliert');
    expect(tabAus('erledigt')).toBe('ausformuliert');
  });

  it('liefert fuer Unbekanntes null', () => {
    expect(tabAus('einwerfen')).toBeNull();
    expect(tabAus(null)).toBeNull();
    expect(tabAus(undefined)).toBeNull();
    expect(tabAus('constructor')).toBeNull();
  });
});

describe('Filter im sessionStorage', () => {
  beforeEach(() => sessionStorage.removeItem(FILTER_SCHLUESSEL));
  afterEach(() => sessionStorage.removeItem(FILTER_SCHLUESSEL));

  it('beginnt ohne Ablage beim Destillieren, ohne Verworfenes', () => {
    expect(filterLaden()).toEqual(standardFilter());
    expect(standardFilter().tab).toBe('destillieren');
    expect(standardFilter().verworfenSichtbar).toBeFalse();
  });

  it('liest zurueck, was gespeichert wurde', () => {
    const gespeichert = filter({
      plattformen: ['web'],
      nurMeine: true,
      tab: 'ausformuliert',
      verworfenSichtbar: true,
    });

    filterSpeichern(gespeichert);

    expect(filterLaden()).toEqual(gespeichert);
  });

  it('blendet Verworfenes ein, ohne Tab und Plattformen anzufassen', () => {
    filterSpeichern(filter({ plattformen: ['web'], tab: 'ausformulieren' }));

    verworfenEinblenden();

    expect(filterLaden()).toEqual(
      filter({ plattformen: ['web'], tab: 'ausformulieren', verworfenSichtbar: true }),
    );
  });

  it('merkt einen Tab, ohne den uebrigen Filter anzufassen', () => {
    filterSpeichern(filter({ plattformen: ['web'], nurMeine: true }));

    tabMerken('ausformuliert');

    expect(filterLaden()).toEqual(filter({ plattformen: ['web'], nurMeine: true, tab: 'ausformuliert' }));
  });

  it('oeffnet einen in der Sitzung gemerkten Tab "erledigt" als "Ausformuliert"', () => {
    sessionStorage.setItem(FILTER_SCHLUESSEL, JSON.stringify({ tab: 'erledigt' }));

    expect(filterLaden().tab).toBe('ausformuliert');
  });

  it('faellt bei unlesbarem Inhalt auf den Standard zurueck', () => {
    sessionStorage.setItem(FILTER_SCHLUESSEL, '{kaputt');

    expect(filterLaden()).toEqual(standardFilter());
  });

  it('wirft unbekannte Plattformen, fremde Werte und einen unbekannten Tab hinaus', () => {
    sessionStorage.setItem(
      FILTER_SCHLUESSEL,
      JSON.stringify({
        plattformen: ['instagram', 'myspace'],
        bekannte: ['instagram', 'youtube', 'tiktok', 'threads', 'x', 'bluesky', 'web', 'myspace'],
        tab: 'einwerfen',
        verworfenSichtbar: 'ja',
      }),
    );

    expect(filterLaden()).toEqual(filter({ plattformen: ['instagram'] }));
  });

  it('uebergeht das frueher gespeicherte "nur offene"', () => {
    sessionStorage.setItem(
      FILTER_SCHLUESSEL,
      JSON.stringify({ plattformen: ['instagram', 'web'], nurOffene: true, nurMeine: false }),
    );

    expect(filterLaden()).toEqual(
      filter({ plattformen: ['instagram', 'threads', 'x', 'bluesky', 'web'] }),
    );
  });

  it('blendet eine Plattform ein, die der gespeicherte Filter noch nicht kannte', () => {
    sessionStorage.setItem(
      FILTER_SCHLUESSEL,
      JSON.stringify({
        plattformen: ['youtube'],
        bekannte: ['instagram', 'youtube', 'tiktok', 'threads', 'x', 'web'],
      }),
    );

    expect(filterLaden().plattformen).toEqual(['youtube', 'bluesky']);
  });

  it('laesst abgewaehlte Plattformen abgewaehlt, die der Filter schon kannte', () => {
    filterSpeichern(filter({ plattformen: ['x'] }));

    expect(filterLaden().plattformen).toEqual(['x']);
  });
});
