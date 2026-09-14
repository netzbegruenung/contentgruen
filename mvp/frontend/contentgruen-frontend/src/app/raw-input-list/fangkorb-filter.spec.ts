import {
  FILTER_SCHLUESSEL,
  FangkorbFilter,
  filterLaden,
  filterSpeichern,
  passtZumFilter,
  standardFilter,
} from './fangkorb-filter';
import { RawInput } from '../services/raw-input.service';

function einwurf(overrides: Partial<RawInput> = {}): RawInput {
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

  it('zaehlt zu "nur offene" auch Destilliertes', () => {
    const nurOffene = filter({ nurOffene: true });

    expect(passtZumFilter(einwurf({ status: 'open' }), nurOffene, null)).toBeTrue();
    expect(passtZumFilter(einwurf({ status: 'in_progress' }), nurOffene, null)).toBeTrue();
    expect(passtZumFilter(einwurf({ status: 'processed' }), nurOffene, null)).toBeFalse();
    expect(passtZumFilter(einwurf({ status: 'discarded' }), nurOffene, null)).toBeFalse();
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

describe('Filter im sessionStorage', () => {
  beforeEach(() => sessionStorage.removeItem(FILTER_SCHLUESSEL));
  afterEach(() => sessionStorage.removeItem(FILTER_SCHLUESSEL));

  it('liefert ohne Ablage den Standard', () => {
    expect(filterLaden()).toEqual(standardFilter());
  });

  it('liest zurueck, was gespeichert wurde', () => {
    const gespeichert = filter({ plattformen: ['web'], nurOffene: true, nurMeine: true });

    filterSpeichern(gespeichert);

    expect(filterLaden()).toEqual(gespeichert);
  });

  it('faellt bei unlesbarem Inhalt auf den Standard zurueck', () => {
    sessionStorage.setItem(FILTER_SCHLUESSEL, '{kaputt');

    expect(filterLaden()).toEqual(standardFilter());
  });

  it('wirft unbekannte Plattformen und fremde Werte hinaus', () => {
    sessionStorage.setItem(
      FILTER_SCHLUESSEL,
      JSON.stringify({
        plattformen: ['instagram', 'myspace'],
        bekannte: ['instagram', 'youtube', 'tiktok', 'threads', 'x', 'bluesky', 'web', 'myspace'],
        nurOffene: 'ja',
      }),
    );

    expect(filterLaden()).toEqual(filter({ plattformen: ['instagram'] }));
  });

  it('blendet in einem Filter der Vorversion die neuen Plattformen ein', () => {
    sessionStorage.setItem(
      FILTER_SCHLUESSEL,
      JSON.stringify({ plattformen: ['instagram', 'web'], nurOffene: true, nurMeine: false }),
    );

    expect(filterLaden()).toEqual(
      filter({ plattformen: ['instagram', 'threads', 'x', 'bluesky', 'web'], nurOffene: true }),
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
