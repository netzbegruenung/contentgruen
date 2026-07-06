import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { tap, map, catchError, switchMap } from 'rxjs/operators';
import {
  AddReplysuggestionToStatementRequest,
  AddReplysuggestionToStatementResponse,
  AddStatementRequest,
  AddStatementResponse,
  SearchStatementByTextRequest,
  StatementSearchResponse
} from './dtos/statementDtos';
import { environment } from '../../environments/environment';
import { LoggingService } from './logging.service';

@Injectable({
  providedIn: 'root'
})
export class StatementService {
  private addReplysuggestionToStatementApiUrl = `${environment.baseUrl}/api/v1/statement/addReplysuggestionToStatement`;
  private addStatementApiUrl = `${environment.baseUrl}/api/v1/statement/addStatement`;
  private searchStatementsApiUrl = `${environment.baseUrl}/api/v1/statement/searchStatements`;

  constructor(
    private http: HttpClient,
    private logger: LoggingService
  ) { }

  /**
   * Finds an existing statement or creates a new one if it doesn't exist
   * @param text The statement text to find or create
   * @returns Observable with the statement details
   */
  findOrCreateStatement(text: string): Observable<AddStatementResponse> {
    this.logger.debug('Finding or creating statement:', text);

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
            }
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
          }
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
}
