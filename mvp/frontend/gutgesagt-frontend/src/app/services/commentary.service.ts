import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { tap } from 'rxjs/operators';
import { AddCommentaryRequest, AddCommentaryResponse } from './dtos/commentaryDtos';
import { CommentaryResult } from './dtos/searchDtos';
import { environment } from '../../environments/environment';
import { LoggingService } from './logging.service';

@Injectable({
  providedIn: 'root'
})
export class CommentaryService {
  private baseApiUrl = `${environment.baseUrl}/api/v1/commentary`;
  private addCommentaryApiUrl = `${this.baseApiUrl}/addCommentary`;

  constructor(
    private http: HttpClient,
    private logger: LoggingService
  ) { }

  addCommentary(request: AddCommentaryRequest): Observable<AddCommentaryResponse> {
    this.logger.debug('Adding new commentary:', request);
    return this.http.post<AddCommentaryResponse>(this.addCommentaryApiUrl, request).pipe(
      tap(response => {
        this.logger.info('Commentary added successfully:', response);
      })
    );
  }

  getCommentaryById(id: string): Observable<CommentaryResult> {
    this.logger.debug(`Fetching commentary with ID: ${id}`);
    return this.http.get<CommentaryResult>(`${this.baseApiUrl}/getById?commentary_id=${id}`).pipe(
      tap(commentary => {
        this.logger.info('Commentary retrieved:', {
          id: commentary.id,
          title: commentary.title,
          style: commentary.style,
          text: commentary.text.substring(0, 100) + '...',
          references: commentary.references?.length || 0
        });
      })
    );
  }
}
