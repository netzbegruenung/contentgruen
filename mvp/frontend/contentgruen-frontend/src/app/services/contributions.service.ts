import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { GetContributionsOfUserResponse } from './dtos/contributionDtos';

@Injectable({
  providedIn: 'root'
})
export class ContributionsService {
  private contributionsApiUrl = `${environment.baseUrl}/api/v1/contribution/getContributionsOfUser`;

  constructor(private http: HttpClient) {}

  getContributions(page: number, pageSize: number): Observable<GetContributionsOfUserResponse> {
    const url = `${this.contributionsApiUrl}?page=${page}&page_size=${pageSize}`;

    return this.http.get<GetContributionsOfUserResponse>(url);
  }
}
