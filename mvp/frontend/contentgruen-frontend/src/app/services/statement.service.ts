import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { tap, map } from 'rxjs/operators';
import { ParamMap } from '@angular/router';
import {
  GetStatementByIdResponse,
  SearchStatementByTextRequest,
  StatementSearchResponse,
  StatementSearchResult,
} from './dtos/statementDtos';
import { environment } from '../../environments/environment';
import { LoggingService } from './logging.service';
import { AUSSAGE_PARAM, SUCHTEXT_PARAM } from '../shared/formular-adresse';

/** Hinweis auf der Ergebnisseite, wenn der Beitrag steht, die Verknuepfung aber nicht. */
export const VERKNUEPFUNG_FEHLGESCHLAGEN =
  'Dein Beitrag ist gespeichert, konnte aber nicht mit der Aussage verknüpft werden.';

/** Hoechstlaenge einer Aussage, wie im Backend (statement_text). */
export const AUSSAGE_MAX_ZEICHEN = 1000;

/** Wie viele vorhandene Aussagen das Antwort-auf-Feld hoechstens vorschlaegt. */
export const VORSCHLAG_ANZAHL = 3;

/**
 * Ab diesem Aehnlichkeitswert (0-1) gilt eine Aussage als Vorschlag. Gemessen fuer
 * intfloat/multilingual-e5-base (passende Aussagen 0,892-0,940, unpassende meist
 * darunter); bei einem Modellwechsel neu messen.
 */
export const VORSCHLAG_MIN_AEHNLICHKEIT = 0.885;

@Injectable({
  providedIn: 'root'
})
export class StatementService {
  private searchStatementsApiUrl = `${environment.baseUrl}/api/v1/statement/searchStatements`;
  private getStatementByIdApiUrl = `${environment.baseUrl}/api/v1/statement/getById`;

  constructor(
    private http: HttpClient,
    private logger: LoggingService
  ) { }

  /**
   * Searches for statements by text
   * @param queryText The text to search for
   * @param limit Maximum number of results
   * @returns Observable with search results
   */
  searchStatements(
    queryText: string,
    limit: number = 10,
    filter: Pick<SearchStatementByTextRequest, 'nur_kuratiert' | 'min_similarity'> = {},
  ): Observable<StatementSearchResponse> {
    const request: SearchStatementByTextRequest = {
      query_text: queryText,
      limit: limit,
      ...filter,
    };

    this.logger.debug('Searching for statements:', request);
    return this.http.post<StatementSearchResponse>(this.searchStatementsApiUrl, request).pipe(
      tap(response => {
        this.logger.debug('Statement search results:', response);
      })
    );
  }

  /**
   * Vorhandene Aussagen, die zum Getippten passen - fuer die Vorschlaege im
   * Antwort-auf-Feld. Nur gepflegte Aussagen und nur hinreichend aehnliche.
   */
  aussageVorschlaege(text: string): Observable<StatementSearchResult[]> {
    return this.searchStatements(text, VORSCHLAG_ANZAHL, {
      nur_kuratiert: true,
      min_similarity: VORSCHLAG_MIN_AEHNLICHKEIT,
    }).pipe(map((antwort) => antwort.results));
  }

  getStatementById(statementId: string): Observable<GetStatementByIdResponse> {
    return this.http.get<GetStatementByIdResponse>(this.getStatementByIdApiUrl, {
      params: { statement_id: statementId },
    });
  }

  /**
   * Die Aussage, auf die ein Beitragsformular antwortet, aus seiner Adresse.
   *
   * Mit ?aussage=<id> wird sie geladen. Mit ?searchQuery= steht nur ihr Text fest:
   * Die ID bleibt leer, und angelegt wird nichts - das geschieht erst beim
   * Speichern, im Backend mit der Speicher-Anfrage. Ohne beides ist das Ergebnis leer.
   */
  aussageAusAdresse(params: ParamMap): Observable<GetStatementByIdResponse> {
    const aussageId = params.get(AUSSAGE_PARAM);
    if (aussageId) {
      return this.getStatementById(aussageId);
    }
    // Wie im Backend (statement_text) hoechstens AUSSAGE_MAX_ZEICHEN - eine lange
    // Suchanfrage wuerde sonst beim Speichern abgelehnt.
    const text = (params.get(SUCHTEXT_PARAM)?.trim() ?? '').slice(0, AUSSAGE_MAX_ZEICHEN).trim();
    return of({ statement_id: '', statement_text: text });
  }
}
