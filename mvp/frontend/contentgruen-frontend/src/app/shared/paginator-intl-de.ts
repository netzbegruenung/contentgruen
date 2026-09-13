import { Injectable } from '@angular/core';
import { MatPaginatorIntl } from '@angular/material/paginator';

/**
 * Deutsche Beschriftung fuer mat-paginator.
 *
 * Bewusst nur der Paginator und kein globales LOCALE_ID: das wuerde alle Date- und
 * Number-Pipes der App mit umstellen.
 */
@Injectable()
export class DeutscherPaginatorIntl extends MatPaginatorIntl {
  override itemsPerPageLabel = 'Einträge pro Seite:';
  override nextPageLabel = 'Nächste Seite';
  override previousPageLabel = 'Vorherige Seite';
  override firstPageLabel = 'Erste Seite';
  override lastPageLabel = 'Letzte Seite';

  override getRangeLabel = (page: number, pageSize: number, length: number): string => {
    if (length === 0 || pageSize === 0) {
      return `0 von ${length}`;
    }
    const start = page * pageSize;
    // Wie im Material-Original: steht die Seite hinter dem Ende, nicht auf length kappen.
    const ende = start < length ? Math.min(start + pageSize, length) : start + pageSize;
    return `${start + 1} – ${ende} von ${length}`;
  };
}
