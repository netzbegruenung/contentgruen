import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

/** Antwort von `services/kuerzungsvorschlag_service.py`; `null`, wenn kein Satz passt. */
export interface Kuerzungsvorschlag {
  vorschlag: string | null;
}

/** Kürzungsvorschlag (#403): nur auf Klick, nichts davon wird gespeichert. */
@Injectable({ providedIn: 'root' })
export class KuerzungsvorschlagService {
  private url = `${environment.baseUrl}/api/v1/kuerzungsvorschlag`;

  constructor(private http: HttpClient) {}

  vorschlagen(text: string, aussage: string): Observable<Kuerzungsvorschlag> {
    return this.http.post<Kuerzungsvorschlag>(this.url, { text, aussage });
  }
}
