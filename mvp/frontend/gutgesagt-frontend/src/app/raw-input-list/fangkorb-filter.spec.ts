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
  tabNach,
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
  });

  it('legt einen Einwurf mit Satz, aber ohne Beitrag unter Ausformulieren', () => {
    const roh = einwurf({ status: 'in_progress', drafts: [satz('s-1')] });

    expect(passtZumTab(roh, 'ausformulieren', false)).toBeTrue();
    expect(passtZumTab(roh, 'destillieren', false)).toBeFalse();
  });

  it('zeigt Ausformuliertes in keinem Tab, mit und ohne Satz', () => {
    const mitSatz = einwurf({ status: 'processed', drafts: [satz('s-1')], links: [link('s-1')] });
    const ohneSatz = einwurf({ status: 'processed', links: [link(null)] });

    for (const ausformuliert of [mitSatz, ohneSatz]) {
      for (const verworfenSichtbar of [false, true]) {
        expect(passtZumTab(ausformuliert, 'destillieren', verworfenSichtbar)).toBeFalse();
        expect(passtZumTab(ausformuliert, 'ausformulieren', verworfenSichtbar)).toBeFalse();
      }
    }
  });

  it('zeigt Verworfenes nur mit Filter, im Tab seiner naechsten Arbeit', () => {
    const ohneSatz = einwurf({ status: 'discarded' });
    const mitSatz = einwurf({ status: 'discarded', drafts: [satz('s-1')] });

    expect(passtZumTab(ohneSatz, 'destillieren', false)).toBeFalse();
    expect(passtZumTab(ohneSatz, 'destillieren', true)).toBeTrue();
    expect(passtZumTab(ohneSatz, 'ausformulieren', true)).toBeFalse();
    expect(passtZumTab(mitSatz, 'ausformulieren', false)).toBeFalse();
    expect(passtZumTab(mitSatz, 'ausformulieren', true)).toBeTrue();
    expect(passtZumTab(mitSatz, 'destillieren', true)).toBeFalse();
  });

  it('zeigt Verworfenes mit Beitrag auch mit Filter nicht', () => {
    const verworfen = einwurf({ status: 'discarded', drafts: [satz('s-1')], links: [link('s-1')] });

    expect(passtZumTab(verworfen, 'destillieren', true)).toBeFalse();
    expect(passtZumTab(verworfen, 'ausformulieren', true)).toBeFalse();
  });
});

describe('tabAus', () => {
  it('kennt die beiden Arbeitslisten', () => {
    expect(tabAus('destillieren')).toBe('destillieren');
    expect(tabAus('ausformulieren')).toBe('ausformulieren');
  });

  it('fuehrt die frueheren Tabs "ausformuliert" und "erledigt" auf die erste Arbeitsliste', () => {
    expect(tabAus('ausformuliert')).toBe('destillieren');
    expect(tabAus('erledigt')).toBe('destillieren');
  });

  it('liefert fuer Unbekanntes null', () => {
    expect(tabAus('einwerfen')).toBeNull();
    expect(tabAus(null)).toBeNull();
    expect(tabAus(undefined)).toBeNull();
    expect(tabAus('constructor')).toBeNull();
  });
});

describe('tabNach', () => {
  it('fuehrt nach dem Ausformulieren in die Arbeitsliste "Ausformulieren", sonst in den genannten Tab', () => {
    expect(tabNach('ausformuliert')).toBe('ausformulieren');
    expect(tabNach('destillieren')).toBe('destillieren');
    expect(tabNach('ausformulieren')).toBe('ausformulieren');
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
      tab: 'ausformulieren',
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

    tabMerken('ausformulieren');

    expect(filterLaden()).toEqual(filter({ plattformen: ['web'], nurMeine: true, tab: 'ausformulieren' }));
  });

  it('oeffnet einen in der Sitzung gemerkten frueheren Tab bei "Destillieren", mit dem uebrigen Filter', () => {
    for (const frueher of ['ausformuliert', 'erledigt']) {
      sessionStorage.setItem(
        FILTER_SCHLUESSEL,
        JSON.stringify({ tab: frueher, nurMeine: true, verworfenSichtbar: true }),
      );

      expect(filterLaden()).toEqual(filter({ nurMeine: true, tab: 'destillieren', verworfenSichtbar: true }));
    }
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
