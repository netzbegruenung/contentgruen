import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { mitCc0Wortlaut } from '../shared/consent-hinweis';
import { environment } from '../../environments/environment';
import { LoggingService } from './logging.service';
import { PostResult } from './dtos/searchDtos';

export interface AddPostRequest {
  post: {
    title: string;
    text: string;
    /** Der Name der Plattform, wie die Karte ihn zeigt (etwa "Instagram"). */
    platform: string;
    /** Wer den Post auf der Plattform veroeffentlicht hat - nicht der Autor in Gut gesagt. */
    author: string;
    url: string;
  };
}

export interface AddPostResponse {
  id: string;
}

@Injectable({
  providedIn: 'root',
})
export class PostService {
  private baseApiUrl = `${environment.baseUrl}/api/v1/post`;

  constructor(
    private http: HttpClient,
    private logger: LoggingService,
  ) {}

  addPost(request: AddPostRequest): Observable<AddPostResponse> {
    this.logger.debug('Adding new post:', request.post.title);
    return this.http.post<AddPostResponse>(`${this.baseApiUrl}/addPost`, mitCc0Wortlaut(request));
  }

  /** Ein Post per ID, flach wie bei /commentary/getById - kein Suchergebnis. */
  getPostById(id: string): Observable<PostResult> {
    return this.http.get<PostResult>(`${this.baseApiUrl}/getById`, { params: { post_id: id } });
  }
}
