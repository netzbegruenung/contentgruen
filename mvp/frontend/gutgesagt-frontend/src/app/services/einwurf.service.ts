import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { environment } from '../../environments/environment';
import { LoggingService } from './logging.service';

/** Spiegelt RawInputSource im Backend. Ohne Angabe zaehlt der Einwurf als 'web'. */
export type EinwurfWeg = 'web' | 'share';

/**
 * Der Satz im Destillier-Ablauf wird der Titel des Beitrags und hat deshalb
 * dasselbe Limit wie der Titel von Kommentar und Hintergrundinfo.
 */
export const SATZ_LIMIT = 120;

/**
 * Ein Einwurf in den Fangkorb. Mindestens eines der drei Inhaltsfelder muss
 * gesetzt sein; alles Weitere ist schon Destillieren und passiert spaeter.
 */
export interface EinwerfenRequest {
  content?: string;
  url?: string;
  image_url?: string;
  source_channel?: EinwurfWeg;
}

export interface EinwerfenResponse {
  id: string;
}

/** in_progress heisst im UI "destilliert": mindestens ein Satz, noch kein Beitrag. */
export type EinwurfStatus = 'open' | 'in_progress' | 'processed' | 'discarded';

/** Die beiden Ziele, die der Destillier-Ablauf setzen darf. */
export type DestillierStatus = 'discarded' | 'processed';

/** Die Beitragstypen, die aus dem Destillier-Ablauf entstehen (ContentType im Backend). */
export type BeitragsTyp = 'commentary' | 'generic_text';

/** Ein Satz zu einem Einwurf. Fuer alle Angemeldeten sichtbar. */
export interface Satz {
  id: string;
  user_id: string;
  /** Anzeigename zu user_id ("Anna B."); null ohne gespeicherten Namen. */
  user_name?: string | null;
  sentence: string;
  updated_at: string;
}

/** Die Verknuepfung eines Einwurfs mit einem Beitrag, neu entstanden oder vorhanden. */
export interface Verknuepfung {
  content_id: string;
  /** Null bei Verknuepfungen aus der Zeit vor Fangkorb v2. */
  content_type: string | null;
  /** Der ausformulierte Satz; null, wenn er spaeter geleert wurde. */
  draft_id: string | null;
  /** Der Ausformulierer, nicht zwingend der Autor des Beitrags. */
  processed_by: string | null;
  processed_at: string;
}

export interface Einwurf {
  id: string;
  content: string | null;
  url: string | null;
  image_url: string | null;
  /** Null moeglich: Wege ohne Sitzung liefern keine Kennung. */
  submitted_by: string | null;
  /** Anzeigename zu submitted_by; null ohne gespeicherten Namen. */
  submitted_by_name?: string | null;
  source_channel: string;
  status: EinwurfStatus;
  created_at: string;
  /** Wer als Erste/r einen Satz gespeichert hat. */
  destilled_by?: string | null;
  /** Der eigene Satz aus ``drafts``. */
  own_draft?: string | null;
  /** Erste Verknuepfung mit einem Beitrag, falls ausformuliert. */
  processed_content_id?: string | null;
  processed_by?: string | null;
  processed_at?: string | null;
  /** Alle Saetze aller Personen, aelteste Aenderung zuerst. */
  drafts?: Satz[];
  /** Alle verknuepften Beitraege, aelteste zuerst. */
  links?: Verknuepfung[];
}

export interface FangkorbResponse {
  results_count: number;
  results: Einwurf[];
  total_records_count: number;
}

export interface SatzResponse {
  raw_input_id: string;
  sentence: string | null;
  updated_at: string | null;
}

@Injectable({
  providedIn: 'root',
})
export class EinwurfService {
  private baseApiUrl = `${environment.baseUrl}/api/v1/rawinput`;

  /**
   * Einwuerfe, die in dieser Runde mit "Spaeter" zurueckgestellt wurden.
   *
   * Ohne Satz unterscheidet sich ein zurueckgestellter Einwurf serverseitig nicht
   * von einem unberuehrten - "Spaeter" lief deshalb bei zwei solchen Einwuerfen
   * endlos zwischen beiden hin und her. Die Liste lebt nur im Speicher der
   * laufenden App: nichts davon landet im Browser-Speicher oder auf dem Server.
   */
  private readonly zurueckgestellt = new Set<string>();

  constructor(
    private http: HttpClient,
    private logger: LoggingService,
  ) {}

  /** Fuer den Rest der Runde nicht mehr automatisch anbieten. */
  zurueckstellen(id: string): void {
    this.zurueckgestellt.add(id);
  }

  /** Neue Runde: Zurueckgestelltes wird wieder angeboten. */
  rundeBeginnen(): void {
    this.zurueckgestellt.clear();
  }

  einwerfen(request: EinwerfenRequest): Observable<EinwerfenResponse> {
    this.logger.debug('Einwurf wird eingeworfen');
    return this.http.post<EinwerfenResponse>(`${this.baseApiUrl}/addRawInput`, request);
  }

  /** Der Fangkorb, eigene Einwuerfe zuerst (sortiert der Server). */
  fangkorbLaden(page: number, pageSize: number): Observable<FangkorbResponse> {
    const params = new HttpParams().set('page', page).set('page_size', pageSize);
    return this.http.get<FangkorbResponse>(`${this.baseApiUrl}/getRawInputs`, {
      params,
    });
  }

  /** Ein Einwurf mit allen Saetzen und dem eigenen als own_draft. */
  einwurfLaden(id: string): Observable<Einwurf> {
    return this.http.get<Einwurf>(this.einwurfUrl(id));
  }

  /** Den eigenen Satz speichern; ein leerer Satz loescht ihn. */
  satzSpeichern(id: string, sentence: string): Observable<SatzResponse> {
    return this.http.put<SatzResponse>(`${this.einwurfUrl(id)}/draft`, { sentence });
  }

  /**
   * Den eigenen Satz sichern, wenn die Seite gleich eingefroren oder beendet wird.
   *
   * Android raeumt die PWA beim Wechsel in eine andere App weg; ein normaler
   * XHR wird dabei abgebrochen. fetch mit keepalive darf die Seite ueberleben.
   * HttpClient laeuft hier ohne Fetch-Backend und kann das nicht - daher direkt.
   * Fehler werden verschluckt: mehr als versuchen geht in diesem Moment nicht.
   */
  satzSpeichernKeepalive(id: string, sentence: string): void {
    try {
      fetch(`${this.einwurfUrl(id)}/draft`, {
        method: 'PUT',
        keepalive: true,
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sentence }),
      }).catch((error) => this.logger.warn('Satz konnte nicht gesichert werden', error));
    } catch (error) {
      this.logger.warn('Satz konnte nicht gesichert werden', error);
    }
  }

  /**
   * Verwerfen oder mit einem Beitrag verknuepfen - dann mit dem verknuepften Beitrag
   * und seinem Typ, nach dem sich die Fangkorb-Karte faerbt.
   */
  updateStatus(
    id: string,
    status: DestillierStatus,
    contentId?: string,
    contentType?: BeitragsTyp,
  ): Observable<Einwurf> {
    const body: Record<string, string> = { status };
    if (contentId) {
      body['content_id'] = contentId;
    }
    if (contentType) {
      body['content_type'] = contentType;
    }
    return this.http.patch<Einwurf>(`${this.einwurfUrl(id)}/status`, body);
  }

  /**
   * Der naechste Einwurf fuer den Destillier-Ablauf: offen oder destilliert, ohne
   * eigenen Satz.
   *
   * Destilliert heisst nur, dass jemand anderes schon einen Satz hat - es gibt
   * keine Sperre, der eigene Satz kann trotzdem kommen. Einwuerfe mit eigenem
   * Satz hat man mit "Spaeter" zurueckgestellt; sie bleiben antippbar, werden
   * aber nicht automatisch wieder angeboten. Dasselbe gilt fuer Einwuerfe, die in
   * dieser Runde ohne Satz zurueckgestellt wurden (``zurueckstellen``). Die
   * Reihenfolge (eigene zuerst, dann neueste) kommt vom Server.
   */
  naechsterOffenerEinwurf(ausser?: string | null): Observable<Einwurf | null> {
    return this.fangkorbLaden(1, 100).pipe(
      map(
        (daten) =>
          daten.results.find(
            (einwurf) =>
              (einwurf.status === 'open' || einwurf.status === 'in_progress') &&
              !einwurf.own_draft &&
              einwurf.id !== ausser &&
              !this.zurueckgestellt.has(einwurf.id),
          ) ?? null,
      ),
    );
  }

  private einwurfUrl(id: string): string {
    return `${this.baseApiUrl}/${encodeURIComponent(id)}`;
  }
}
