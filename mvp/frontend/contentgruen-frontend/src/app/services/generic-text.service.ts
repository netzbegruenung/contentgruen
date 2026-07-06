import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { tap } from 'rxjs/operators';
import { AddGenericTextRequest, AddGenericTextResponse } from './dtos/generictextDtos';
import { GenerictextSearchResult } from './dtos/searchDtos';
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

  getGenericTextById(id: string): Observable<GenerictextSearchResult> {
    this.logger.debug(`Fetching generic text with ID: ${id}`);
    return this.http.get<GenerictextSearchResult>(`${this.baseApiUrl}/getById?generic_text_id=${id}`).pipe(
      tap(genericText => {
        this.logger.info('Generic text retrieved:', {
          id: genericText.generictext_result.id,
          title: genericText.generictext_result.title,
          text: genericText.generictext_result.text.substring(0, 100) + '...',
          references: genericText.generictext_result.references?.length || 0
        });
      })
    );
  }
}
