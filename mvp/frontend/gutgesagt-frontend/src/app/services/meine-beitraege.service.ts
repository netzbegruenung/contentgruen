import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { GetContributionsOfUserResponse } from './dtos/contributionDtos';
import { mitCc0Wortlaut } from '../shared/consent-hinweis';

/** Eine Herkunft in der Aenderung: Adresse oder Fundstelle, dazu die Notiz dieses Beitrags. */
export interface HerkunftEingabe {
  reference_string: string;
  description?: string;
}

/**
 * Was der Autor an seinem Beitrag aendert (#299): Titel, Text und Herkunft, je ganz ersetzt.
 * Beim Kommentar auch Kurz- und Langfassung (#551): leer heisst, die Fassung entfaellt;
 * ohne das Feld bleibt sie, wie sie ist.
 */
export interface BeitragAenderung {
  title: string;
  text: string;
  short_text?: string;
  long_text?: string;
  references: HerkunftEingabe[];
}

/** "Meine Beiträge": die eigenen Beiträge der angemeldeten Person, seitenweise. */
@Injectable({
  providedIn: 'root'
})
export class MeineBeitraegeService {
  private apiUrl = `${environment.baseUrl}/api/v1/contribution/getContributionsOfUser`;

  constructor(private http: HttpClient) {}

  meineBeitraege(page: number, pageSize: number): Observable<GetContributionsOfUserResponse> {
    const url = `${this.apiUrl}?page=${page}&page_size=${pageSize}`;

    return this.http.get<GetContributionsOfUserResponse>(url);
  }

  /**
   * Der Autor aendert Titel, Text und Herkunft seines Beitrags (#299), beim Kommentar auch
   * Kurz- und Langfassung (#551). Der Dialog zeigt
   * den CC0-Hinweis; seine Kennung geht mit wie beim Anlegen (#431).
   */
  beitragAendern(id: string, aenderung: BeitragAenderung): Observable<void> {
    return this.http.put<void>(
      `${environment.baseUrl}/api/v1/content/${encodeURIComponent(id)}`,
      mitCc0Wortlaut(aenderung),
    );
  }

  /** Der Autor loescht seinen Beitrag; er bekommt den Zustand "geloescht" (#250). */
  beitragLoeschen(id: string): Observable<void> {
    return this.http.delete<void>(`${environment.baseUrl}/api/v1/content/${encodeURIComponent(id)}`);
  }
}
