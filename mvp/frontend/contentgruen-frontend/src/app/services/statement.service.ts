import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { tap, map, catchError, switchMap } from 'rxjs/operators';
import { ParamMap } from '@angular/router';
import {
  AddReplysuggestionToStatementRequest,
  AddReplysuggestionToStatementResponse,
  AddStatementRequest,
  AddStatementResponse,
  ContentType,
  GetStatementByIdResponse,
  SearchStatementByTextRequest,
  StatementSearchResponse,
  StatementSource
} from './dtos/statementDtos';
import { environment } from '../../environments/environment';
import { LoggingService } from './logging.service';
import { AUSSAGE_PARAM, SUCHTEXT_PARAM } from '../shared/formular-adresse';

@Injectable({
  providedIn: 'root'
})
export class StatementService {
  private addReplysuggestionToStatementApiUrl = `${environment.baseUrl}/api/v1/statement/addReplysuggestionToStatement`;
  private addStatementApiUrl = `${environment.baseUrl}/api/v1/statement/addStatement`;
  private searchStatementsApiUrl = `${environment.baseUrl}/api/v1/statement/searchStatements`;
  private getStatementByIdApiUrl = `${environment.baseUrl}/api/v1/statement/getById`;

  constructor(
    private http: HttpClient,
    private logger: LoggingService
  ) { }

  /**
   * Finds an existing statement or creates a new one if it doesn't exist
   *
   * Beide Aufrufsituationen laufen ueber diese eine Methode und denselben
   * Endpunkt; unterschieden werden sie allein ueber `source`. Davon haengt ab,
   * ob die Person als Autorin am Statement haengt - deshalb ist der Parameter
   * verpflichtend und hat keine Voreinstellung.
   *
   * @param text The statement text to find or create
   * @param source Ob der Text aus dem Suchfeld stammt oder ausdruecklich benannt wurde
   * @returns Observable with the statement details
   */
  findOrCreateStatement(text: string, source: StatementSource): Observable<AddStatementResponse> {
    this.logger.debug('Finding or creating statement:', text, source);

    // First, search for an existing statement with high similarity
    return this.searchStatements(text, 1).pipe(
      switchMap(searchResponse => {
        // Check if we found an exact or very similar match (score > 0.9)
        if (searchResponse.results.length > 0 && searchResponse.results[0].score > 0.9) {
          const existingStatement = searchResponse.results[0];
          this.logger.info('Found existing statement with high similarity:', existingStatement);

          // Return a response in the same format as addStatement
          return of({
            statement_was_new: false,
            statement_id: existingStatement.id,
            statement_text: existingStatement.text
          } as AddStatementResponse);
        } else {
          // No similar statement found, create a new one
          this.logger.info('No similar statement found, creating new statement');
          return this.addStatement({
            statement: {
              text: text,
              replysuggestions: []
            },
            source: source
          });
        }
      }),
      catchError(error => {
        this.logger.error('Error in findOrCreateStatement, attempting to create new statement', error);
        // If search fails, try to create a new statement anyway
        return this.addStatement({
          statement: {
            text: text,
            replysuggestions: []
          },
          source: source
        });
      })
    );
  }

  /**
   * Searches for statements by text
   * @param queryText The text to search for
   * @param limit Maximum number of results
   * @returns Observable with search results
   */
  searchStatements(queryText: string, limit: number = 10): Observable<StatementSearchResponse> {
    const request: SearchStatementByTextRequest = {
      query_text: queryText,
      limit: limit
    };

    this.logger.debug('Searching for statements:', request);
    return this.http.post<StatementSearchResponse>(this.searchStatementsApiUrl, request).pipe(
      tap(response => {
        this.logger.debug('Statement search results:', response);
      })
    );
  }

  /**
   * Adds a new statement
   * @param request The statement to add
   * @returns Observable with the created statement details
   */
  addStatement(request: AddStatementRequest): Observable<AddStatementResponse> {
    this.logger.debug('Adding statement:', request);
    return this.http.post<AddStatementResponse>(this.addStatementApiUrl, request).pipe(
      tap(response => {
        this.logger.info('Statement added successfully:', response);
      })
    );
  }

  /**
   * Links a reply suggestion to a statement
   * @param request The linking request
   * @returns Observable with the result
   */
  addReplysuggestionToStatement(request: AddReplysuggestionToStatementRequest): Observable<AddReplysuggestionToStatementResponse> {
    this.logger.debug('Adding reply suggestion to statement:', request);
    return this.http.post<AddReplysuggestionToStatementResponse>(this.addReplysuggestionToStatementApiUrl, request).pipe(
      tap(response => {
        this.logger.info('Reply suggestion added successfully:', response);
      })
    );
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
   * Speichern (alsAntwortVerknuepfen). Ohne beides ist das Ergebnis leer.
   */
  aussageAusAdresse(params: ParamMap): Observable<GetStatementByIdResponse> {
    const aussageId = params.get(AUSSAGE_PARAM);
    if (aussageId) {
      return this.getStatementById(aussageId);
    }
    return of({ statement_id: '', statement_text: params.get(SUCHTEXT_PARAM)?.trim() ?? '' });
  }

  /**
   * Einen gespeicherten Beitrag als Antwort an seine Aussage haengen.
   *
   * Ist die Aussage nur als Text bekannt, wird sie erst jetzt gesucht oder
   * angelegt - so entsteht beim blossen Oeffnen eines Formulars keine Aussage.
   * Scheitert etwas, bleibt der Beitrag gespeichert; das Ergebnis ist dann false.
   */
  alsAntwortVerknuepfen(
    beitragId: string,
    contentType: ContentType,
    relevance: number,
    aussage: { id: string; text: string },
  ): Observable<boolean> {
    const text = aussage.text.trim();
    if (!aussage.id && !text) {
      return of(false);
    }
    const aussageId$ = aussage.id
      ? of(aussage.id)
      : this.findOrCreateStatement(text, 'manually_created').pipe(map((antwort) => antwort.statement_id));

    return aussageId$.pipe(
      switchMap((statementId) =>
        this.addReplysuggestionToStatement({
          statement_id: statementId,
          replysuggestion_id: beitragId,
          content_type: contentType,
          relevance,
        }),
      ),
      map(() => true),
      catchError((error) => {
        this.logger.error('Beitrag gespeichert, aber nicht mit der Aussage verknuepft', error);
        return of(false);
      }),
    );
  }
}
