import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map, shareReplay } from 'rxjs/operators';
import { environment } from '../../environments/environment';
import {
  AussageMitThemen,
  AussagenMitThemenResponse,
  Thema,
  ThemenResponse,
  ThemenTestsetResponse,
  ThemenZuordnenRequest,
  ThemenZuordnenResponse,
} from './dtos/themenDtos';

/** Wie im Backend (domain/themen.py): eine Aussage hat hoechstens zwei Themen. */
export const HOECHSTENS_THEMEN_JE_AUSSAGE = 2;

/**
 * Die Themen: die feste Liste und ihre Zuordnung zu Aussagen. Zuordnen darf jede
 * angemeldete Person; die Liste aller Aussagen zum Zuordnen und das Testset
 * sehen nur Admins.
 */
@Injectable({ providedIn: 'root' })
export class ThemenService {
  private readonly basis = `${environment.baseUrl}/api/v1/statement/themen`;
  private liste$?: Observable<Thema[]>;

  constructor(private http: HttpClient) {}

  /** Die feste Liste, einmal je Sitzung geladen; sie aendert sich nur mit einem Release. */
  liste(): Observable<Thema[]> {
    this.liste$ ??= this.http.get<ThemenResponse>(this.basis).pipe(
      map((antwort) => antwort.themen),
      shareReplay({ bufferSize: 1, refCount: false }),
    );
    return this.liste$;
  }

  /** Die Themen einer Aussage setzen; ersetzt die bisherigen. Liefert, was jetzt gilt. */
  zuordnen(statementId: string, themen: string[]): Observable<Thema[]> {
    const request: ThemenZuordnenRequest = { statement_id: statementId, themen };
    return this.http
      .put<ThemenZuordnenResponse>(`${this.basis}/zuordnen`, request)
      .pipe(map((antwort) => antwort.themen));
  }

  /** Admin: alle Aussagen zum Zuordnen, die ohne Thema zuerst. */
  aussagenZumZuordnen(): Observable<AussageMitThemen[]> {
    return this.http
      .get<AussagenMitThemenResponse>(`${this.basis}/aussagen`)
      .pipe(map((antwort) => antwort.aussagen));
  }

  /** Admin: die Zuordnungen von Hand als Testset. */
  testset(): Observable<ThemenTestsetResponse> {
    return this.http.get<ThemenTestsetResponse>(`${this.basis}/testset`);
  }
}
