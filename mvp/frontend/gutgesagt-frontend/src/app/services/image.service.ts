import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { mitCc0Wortlaut } from '../shared/consent-hinweis';
import { environment } from '../../environments/environment';
import { LoggingService } from './logging.service';
import type { AussageInAnfrage, AussageInAntwort } from '../beitragsformular/aussage-fuer-anfrage';
import { ImageResult } from './dtos/searchDtos';

/** Worauf das Bild antwortet (statement_id, statement_text, themen) ist optional (#619). */
export interface AddImageRequest extends AussageInAnfrage {
  image: {
    title: string;
    image_url: string;
    text: string;
  };
}

/** Die ID und woran das Bild jetzt haengt (#619). */
export interface AddImageResponse extends AussageInAntwort {
  id: string;
}

@Injectable({
  providedIn: 'root',
})
export class ImageService {
  private baseApiUrl = `${environment.baseUrl}/api/v1/image`;

  constructor(
    private http: HttpClient,
    private logger: LoggingService,
  ) {}

  addImage(request: AddImageRequest): Observable<AddImageResponse> {
    this.logger.debug('Adding new image:', request.image.title);
    return this.http.post<AddImageResponse>(`${this.baseApiUrl}/addImage`, mitCc0Wortlaut(request));
  }

  /** Ein Bild per ID, flach wie bei /post/getById - kein Suchergebnis. Fuer die Ergebnisseite. */
  getImageById(id: string): Observable<ImageResult> {
    return this.http.get<ImageResult>(`${this.baseApiUrl}/getById`, { params: { image_id: id } });
  }
}
