import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, of } from 'rxjs';
import { catchError, map, tap } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import { LoggingService } from '../../services/logging.service';
import { merkerEntfernen } from '../../meine-beitraege/meilenstein-merker';

/** Die Einwilligung „Punkte und Meilensteine“ der Person (#351) und der Wortlaut fürs Häkchen. */
export interface PunkteEinwilligungStand {
  eingewilligt: boolean;
  wortlaut: string | null;
  aktueller_wortlaut: { kennung: string; text: string };
}

/**
 * Die eigene, freiwillige Einwilligung „Punkte und Meilensteine“ (#351): getrennt von
 * der Art.-9-Einwilligung zur Mitwirkung, nichts ist vorausgewählt. Ohne eingeschaltete
 * Punkte antwortet der Server 404; dann ist der Stand null und das Häkchen wird nicht
 * angeboten.
 *
 * Ein gemeinsamer Stand für „Meine Beiträge“ und die Datenschutz-Einstellungen: Ändert
 * die Person ihn an einer Stelle, sieht die andere es sofort, ohne Neuladen.
 */
@Injectable({ providedIn: 'root' })
export class PunkteEinwilligungService {
  private readonly url = `${environment.baseUrl}/api/v1/usage/users/me/punkte-einwilligung`;
  /** undefined: noch nicht geladen; null: nicht angeboten (Punkte aus, Fehler). */
  private stand = new BehaviorSubject<PunkteEinwilligungStand | null | undefined>(undefined);
  readonly stand$ = this.stand.asObservable();

  constructor(
    private http: HttpClient,
    private logger: LoggingService,
  ) {}

  /** Den Stand frisch holen; jeder Aufruf fragt den Server. */
  laden(): Observable<PunkteEinwilligungStand | null> {
    return this.http.get<PunkteEinwilligungStand>(this.url).pipe(
      catchError((error) => {
        if (error?.status !== 404) {
          this.logger.error('Einwilligung Punkte nicht geladen', error);
        }
        return of(null);
      }),
      tap((stand) => this.stand.next(stand)),
    );
  }

  /** Einwilligen oder widerrufen; true, wenn es gespeichert ist. */
  setzen(eingewilligt: boolean): Observable<boolean> {
    const stand = this.stand.value;
    if (!stand) {
      return of(false);
    }
    return this.http.put(this.url, { eingewilligt, wortlaut: stand.aktueller_wortlaut.kennung }).pipe(
      map(() => true),
      tap(() => {
        if (!eingewilligt) {
          // Nach dem Widerruf gibt es keine Meilensteine mehr: ihr Merker im Browser geht mit.
          merkerEntfernen();
        }
        this.stand.next({ ...stand, eingewilligt, wortlaut: stand.aktueller_wortlaut.kennung });
      }),
      catchError((error) => {
        this.logger.error('Einwilligung Punkte nicht gespeichert', error);
        return of(false);
      }),
    );
  }
}
