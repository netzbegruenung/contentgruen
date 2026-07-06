import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse, HttpHeaders } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { environment } from '../../environments/environment';
import { LoggingService } from './logging.service';
import {
    SearchReferencesRequest,
    SearchReferencesResponse,
    AddReferenceRequest,
    AddReferenceResponse,
    GetReferenceResponse,
    ReferenceSearchItem
} from './dtos/referenceDtos';

@Injectable({
    providedIn: 'root'
})
export class ReferenceService {
    private apiUrl: string;

    constructor(
        private http: HttpClient,
        private logger: LoggingService
    ) {
        this.apiUrl = `${environment.baseUrl}/api/v1/reference`;
    }

    private getHeaders(): HttpHeaders {
        // For now, use a default user. Can be enhanced later with proper auth
        const user = 'testuser';
        return new HttpHeaders({
            'Content-Type': 'application/json',
            'X-User': user || 'anonymous'
        });
    }

    /**
     * Search for references by text
     */
    searchReferences(request: SearchReferencesRequest): Observable<SearchReferencesResponse> {
        const headers = this.getHeaders();

        return this.http.post<SearchReferencesResponse>(
            `${this.apiUrl}/search`,
            request,
            { headers }
        ).pipe(
            catchError(error => this.handleError(error, 'searchReferences'))
        );
    }


    /**
     * Add a new reference or get existing if duplicate
     */
    addReference(request: AddReferenceRequest): Observable<AddReferenceResponse> {
        const headers = this.getHeaders();

        return this.http.post<AddReferenceResponse>(
            `${this.apiUrl}/add`,
            request,
            { headers }
        ).pipe(
            catchError(error => this.handleError(error, 'addReference'))
        );
    }

    /**
     * Get reference by ID
     */
    getReferenceById(id: string): Observable<GetReferenceResponse> {
        const headers = this.getHeaders();

        return this.http.get<GetReferenceResponse>(
            `${this.apiUrl}/getById?reference_id=${id}`,
            { headers }
        ).pipe(
            catchError(error => this.handleError(error, 'getReferenceById'))
        );
    }




    /**
     * Format reference for display
     */
    formatReferenceDisplay(reference: ReferenceSearchItem): string {
        if (reference.text) {
            return `${reference.text}`;
        }
        return reference.reference_string;
    }

    /**
     * Validate URL format
     */
    isValidUrl(string: string): boolean {
        try {
            const url = new URL(string);
            return url.protocol === 'http:' || url.protocol === 'https:';
        } catch {
            return false;
        }
    }


    private handleError(error: HttpErrorResponse, operation: string): Observable<never> {
        let errorMessage = 'Ein unbekannter Fehler ist aufgetreten';

        if (error.error instanceof ErrorEvent) {
            // Client-side error
            errorMessage = `Fehler: ${error.error.message}`;
        } else {
            // Server-side error
            errorMessage = error.error?.detail || error.message || errorMessage;
        }

        this.logger.error(`${operation} failed: ${errorMessage}`, error);

        return throwError(() => new Error(errorMessage));
    }
}
