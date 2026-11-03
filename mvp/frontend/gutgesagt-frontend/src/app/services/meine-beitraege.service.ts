import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { GetContributionsOfUserResponse } from './dtos/contributionDtos';

/** Eine Herkunft in der Aenderung: Adresse oder Fundstelle, dazu die Notiz dieses Beitrags. */
export interface HerkunftEingabe {
  reference_string: string;
  description?: string;
}

/** Was der Autor an seinem Beitrag aendert (#299): Titel, Text und Herkunft, je ganz ersetzt. */
export interface BeitragAenderung {
  title: string;
  text: string;
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

  /** Der Autor aendert Titel, Text und Herkunft seines Beitrags (#299). */
  beitragAendern(id: string, aenderung: BeitragAenderung): Observable<void> {
    return this.http.put<void>(`${environment.baseUrl}/api/v1/content/${encodeURIComponent(id)}`, aenderung);
  }

  /** Der Autor loescht seinen Beitrag; er bekommt den Zustand "geloescht" (#250). */
  beitragLoeschen(id: string): Observable<void> {
    return this.http.delete<void>(`${environment.baseUrl}/api/v1/content/${encodeURIComponent(id)}`);
  }
}
