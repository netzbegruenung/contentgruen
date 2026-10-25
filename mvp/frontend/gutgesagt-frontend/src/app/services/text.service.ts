import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class TextService {
  constructor(private http: HttpClient) { }

  saveText(text: string): Observable<void> {
    return this.http.post<void>('/api/text', { text });
  }

  saveComment(comment: string): Observable<any> {
    const saveUrl = `${environment.baseUrl}/api/v1/comments`;
    return this.http.post<any>(saveUrl, { comment });
  }
}
