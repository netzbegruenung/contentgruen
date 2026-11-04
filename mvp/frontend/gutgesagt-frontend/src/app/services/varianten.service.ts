import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';
import { BaseContentResult } from './dtos/commonDtos';

/** Ein Beitrag, wie /api/v1/varianten ihn liefert: flach, mit seinem Typ. */
export type VariantenBeitrag = BaseContentResult & { result_type: string } & Record<string, unknown>;

export interface VariantenAntwort {
  original: VariantenBeitrag;
  /** Die sichtbaren Varianten, meistgenutzte zuerst. */
  varianten: VariantenBeitrag[];
}

/** Die Varianten eines Beitrags (#356, api/v1/varianten.py). */
@Injectable({ providedIn: 'root' })
export class VariantenService {
  private readonly apiUrl = `${environment.baseUrl}/api/v1/varianten`;

  constructor(private http: HttpClient) {}

  laden(originalId: string): Observable<VariantenAntwort> {
    return this.http.get<VariantenAntwort>(`${this.apiUrl}/${encodeURIComponent(originalId)}`);
  }
}
