import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { LoggingService } from './logging.service';

export interface AddImageRequest {
  image: {
    title: string;
    image_url: string;
    text: string;
  };
}

export interface AddImageResponse {
  id: string;
}

export interface SuggestCaptionRequest {
  image_url: string;
}

export interface SuggestCaptionResponse {
  suggested_caption: string;
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
    return this.http.post<AddImageResponse>(`${this.baseApiUrl}/addImage`, request);
  }

  suggestCaption(request: SuggestCaptionRequest): Observable<SuggestCaptionResponse> {
    this.logger.debug('Requesting caption suggestion for:', request.image_url.slice(0, 60));
    return this.http.post<SuggestCaptionResponse>(`${this.baseApiUrl}/suggestCaption`, request);
  }
}
