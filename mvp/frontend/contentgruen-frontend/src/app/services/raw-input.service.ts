import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map, tap } from 'rxjs/operators';
import { environment } from '../../environments/environment';
import { cacheService } from '../auth/cache.interceptor';
import { LoggingService } from './logging.service';

/** Spiegelt RawInputSource im Backend. Ohne Angabe zaehlt der Einwurf als 'web'. */
export type RawInputSource = 'web' | 'share';

/**
 * Der Satz im Destillier-Ablauf wird der Titel des Beitrags und hat deshalb
 * dasselbe Limit wie der Titel von Kommentar und Hintergrundinfo.
 */
export const SATZ_LIMIT = 120;

/**
 * Ein Einwurf in den Fangkorb. Mindestens eines der drei Inhaltsfelder muss
 * gesetzt sein; alles Weitere ist schon Destillieren und passiert spaeter.
 */
export interface AddRawInputRequest {
  content?: string;
  url?: string;
  image_url?: string;
  source_channel?: RawInputSource;
}

export interface AddRawInputResponse {
  id: string;
}

export type RawInputStatus = 'open' | 'in_progress' | 'processed' | 'discarded';

/** Die beiden Ziele, die der Destillier-Ablauf setzen darf. */
export type DestillierStatus = 'discarded' | 'processed';

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
  /** Der eigene Entwurfssatz - nie der anderer. */
  own_draft?: string | null;
  /** Erste Verknuepfung mit einem Beitrag, falls verarbeitet. */
  processed_content_id?: string | null;
  processed_by?: string | null;
  processed_at?: string | null;
}

export interface GetRawInputsResponse {
  results_count: number;
  results: RawInput[];
  total_records_count: number;
}

export interface DraftResponse {
  raw_input_id: string;
  sentence: string | null;
  updated_at: string | null;
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

  /** Der Fangkorb, eigene Einwuerfe zuerst (sortiert der Server). */
  getRawInputs(page: number, pageSize: number): Observable<GetRawInputsResponse> {
    const params = new HttpParams().set('page', page).set('page_size', pageSize);
    return this.http.get<GetRawInputsResponse>(`${this.baseApiUrl}/getRawInputs`, {
      params,
    });
  }

  /** Ein Einwurf mit eigenem Entwurfssatz. */
  getRawInput(id: string): Observable<RawInput> {
    return this.http.get<RawInput>(this.einwurfUrl(id));
  }

  /** Den eigenen Entwurfssatz speichern; ein leerer Satz loescht ihn. */
  saveDraft(id: string, sentence: string): Observable<DraftResponse> {
    return this.http
      .put<DraftResponse>(`${this.einwurfUrl(id)}/draft`, { sentence })
      .pipe(tap(() => this.cacheLeeren()));
  }

  /**
   * Den Entwurfssatz sichern, wenn die Seite gleich eingefroren oder beendet wird.
   *
   * Android raeumt die PWA beim Wechsel in eine andere App weg; ein normaler
   * XHR wird dabei abgebrochen. fetch mit keepalive darf die Seite ueberleben.
   * HttpClient laeuft hier ohne Fetch-Backend und kann das nicht - daher direkt.
   * Fehler werden verschluckt: mehr als versuchen geht in diesem Moment nicht.
   */
  saveDraftKeepalive(id: string, sentence: string): void {
    this.cacheLeeren();
    try {
      fetch(`${this.einwurfUrl(id)}/draft`, {
        method: 'PUT',
        keepalive: true,
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sentence }),
      }).catch((error) => this.logger.warn('Entwurf konnte nicht gesichert werden', error));
    } catch (error) {
      this.logger.warn('Entwurf konnte nicht gesichert werden', error);
    }
  }

  /** Verwerfen oder als verarbeitet markieren (dann mit dem entstandenen Beitrag). */
  updateStatus(id: string, status: DestillierStatus, contentId?: string): Observable<RawInput> {
    const body = contentId ? { status, content_id: contentId } : { status };
    return this.http
      .patch<RawInput>(`${this.einwurfUrl(id)}/status`, body)
      .pipe(tap(() => this.cacheLeeren()));
  }

  /**
   * Der naechste Einwurf fuer den Destillier-Ablauf: offen, ohne eigenen Entwurf.
   *
   * Einwuerfe mit eigenem Entwurf hat man mit "Spaeter" zurueckgestellt; sie
   * bleiben antippbar, werden aber nicht automatisch wieder angeboten. Die
   * Reihenfolge (eigene zuerst, dann neueste) kommt vom Server.
   */
  naechsterOffenerEinwurf(ausser?: string | null): Observable<RawInput | null> {
    return this.getRawInputs(1, 100).pipe(
      map(
        (daten) =>
          daten.results.find(
            (einwurf) => einwurf.status === 'open' && !einwurf.own_draft && einwurf.id !== ausser,
          ) ?? null,
      ),
    );
  }

  private einwurfUrl(id: string): string {
    return `${this.baseApiUrl}/${encodeURIComponent(id)}`;
  }

  /**
   * Der Cache-Interceptor haelt GETs fuenf Minuten und kennt PATCH nicht. Ohne
   * das hier zeigte die Liste nach einem Statuswechsel den alten Stand, und das
   * Weiterspringen boete den gerade erledigten Einwurf erneut an.
   */
  private cacheLeeren(): void {
    cacheService.delete('/api/v1/rawinput');
  }
}
