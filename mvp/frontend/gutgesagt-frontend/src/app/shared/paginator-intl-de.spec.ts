import { DeutscherPaginatorIntl } from './paginator-intl-de';

describe('DeutscherPaginatorIntl', () => {
  const intl = new DeutscherPaginatorIntl();

  it('beschriftet den Paginator auf Deutsch', () => {
    expect(intl.itemsPerPageLabel).toBe('Einträge pro Seite:');
    expect(intl.nextPageLabel).toBe('Nächste Seite');
    expect(intl.previousPageLabel).toBe('Vorherige Seite');
    expect(intl.firstPageLabel).toBe('Erste Seite');
    expect(intl.lastPageLabel).toBe('Letzte Seite');
  });

  it('zeigt den Bereich mit "von"', () => {
    expect(intl.getRangeLabel(0, 20, 57)).toBe('1 – 20 von 57');
    expect(intl.getRangeLabel(2, 20, 57)).toBe('41 – 57 von 57');
  });

  it('zeigt eine leere Liste als 0 von 0', () => {
    expect(intl.getRangeLabel(0, 20, 0)).toBe('0 von 0');
  });
});
