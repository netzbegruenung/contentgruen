import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { tap } from 'rxjs/operators';
import { AddGenericTextRequest, AddGenericTextResponse } from './dtos/generictextDtos';
import { GenerictextResult } from './dtos/searchDtos';
import { environment } from '../../environments/environment';
import { LoggingService } from './logging.service';

@Injectable({
  providedIn: 'root'
})
export class GenericTextService {
  private baseApiUrl = `${environment.baseUrl}/api/v1/generic_text`;
  private addGenericTextApiUrl = `${this.baseApiUrl}/addGenericText`;

  constructor(
    private http: HttpClient,
    private logger: LoggingService
  ) { }

  addGenericText(request: AddGenericTextRequest): Observable<AddGenericTextResponse> {
    this.logger.debug('Adding new generic text:', request);
    return this.http.post<AddGenericTextResponse>(this.addGenericTextApiUrl, request).pipe(
      tap(response => {
        this.logger.info('Generic text added successfully:', response);
      })
    );
  }

  /**
   * Eine Hintergrundinfo per ID.
   *
   * Der Endpunkt liefert den Beitrag flach, nicht als Suchergebnis mit
   * generictext_result - genau wie /commentary/getById. Vorher stand hier der
   * Suchergebnis-Typ, und das Log griff auf das Feld darin zu: Jeder Aufruf waere
   * mit einem TypeError abgebrochen. Aufgerufen hat die Methode bis jetzt niemand.
   */
  getGenericTextById(id: string): Observable<GenerictextResult> {
    this.logger.debug(`Fetching generic text with ID: ${id}`);
    return this.http.get<GenerictextResult>(`${this.baseApiUrl}/getById?generic_text_id=${id}`).pipe(
      tap(genericText => {
        this.logger.info('Generic text retrieved:', {
          id: genericText.id,
          title: genericText.title,
          references: genericText.references?.length || 0
        });
      })
    );
  }
}
