import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { LoggingService } from './logging.service';

/**
 * Ein Einwurf in den Fangkorb. Mindestens eines der drei Felder muss gesetzt
 * sein; alles Weitere waere schon Destillieren und passiert spaeter.
 */
export interface AddRawInputRequest {
  content?: string;
  url?: string;
  image_url?: string;
}

export interface AddRawInputResponse {
  id: string;
}

export type RawInputStatus = 'open' | 'in_progress' | 'processed' | 'discarded';

export interface RawInput {
  id: string;
  content: string | null;
  url: string | null;
  image_url: string | null;
  /** Null moeglich: Kanaele ohne Sitzung liefern keine Kennung. */
  submitted_by: string | null;
  source_channel: string;
  status: RawInputStatus;
  created_at: string;
}

export interface GetRawInputsResponse {
  results_count: number;
  results: RawInput[];
  total_records_count: number;
}

@Injectable({
  providedIn: 'root',
})
export class RawInputService {
  private baseApiUrl = `${environment.baseUrl}/api/v1/rawinput`;

  constructor(
    private http: HttpClient,
    private logger: LoggingService,
  ) {}

  addRawInput(request: AddRawInputRequest): Observable<AddRawInputResponse> {
    this.logger.debug('Werfe Rohinput ein');
    return this.http.post<AddRawInputResponse>(`${this.baseApiUrl}/addRawInput`, request);
  }

  getRawInputs(page: number, pageSize: number): Observable<GetRawInputsResponse> {
    const params = new HttpParams().set('page', page).set('page_size', pageSize);
    return this.http.get<GetRawInputsResponse>(`${this.baseApiUrl}/getRawInputs`, {
      params,
    });
  }
}
