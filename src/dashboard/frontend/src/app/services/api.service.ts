import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface WifiNetwork {
    name: string;
}

export interface WifiListResponse {
    success: boolean;
    networks?: WifiNetwork[];
    error?: string;
}

export interface WifiActionResponse {
    success: boolean;
    message?: string;
    error?: string;
}

export interface TableResponse {
    success: boolean;
    data?: any;
    message?: string;
    error?: string;
}

export interface SerialStatusResponse {
    success: boolean;
    connected: boolean;
}

export interface UpdateStatusResponse {
    success: boolean;
    current_commit?: string;
    current_commit_short?: string;
    remote_commit?: string;
    remote_commit_short?: string;
    update_available?: boolean;
    error?: string;
}

export interface UpdateActionResponse {
    success: boolean;
    message?: string;
    error?: string;
}

@Injectable({
    providedIn: 'root'
})
export class ApiService {
    private baseUrl = `http://${window.location.hostname}:5005`;

    constructor(private http: HttpClient) { }

    // WiFi Management
    getWifiList(): Observable<WifiListResponse> {
        return this.http.get<WifiListResponse>(`${this.baseUrl}/api/wifi`);
    }

    addWifi(ssid: string, password: string): Observable<WifiActionResponse> {
        return this.http.post<WifiActionResponse>(`${this.baseUrl}/api/wifi`, { ssid, password });
    }

    removeWifi(name: string): Observable<WifiActionResponse> {
        return this.http.delete<WifiActionResponse>(`${this.baseUrl}/api/wifi/${encodeURIComponent(name)}`);
    }

    // Table State Management
    loadTableState(): Observable<TableResponse> {
        return this.http.get<TableResponse>(`${this.baseUrl}/api/table`);
    }

    saveTableState(data: any): Observable<TableResponse> {
        return this.http.post<TableResponse>(`${this.baseUrl}/api/table`, data);
    }

    // Serial Connection Status
    getSerialStatus(): Observable<SerialStatusResponse> {
        return this.http.get<SerialStatusResponse>(`${this.baseUrl}/api/serial/status`);
    }

    // Codebase Update Management
    checkForUpdates(): Observable<UpdateStatusResponse> {
        return this.http.get<UpdateStatusResponse>(`${this.baseUrl}/api/update/check`);
    }

    performUpdate(): Observable<UpdateActionResponse> {
        return this.http.post<UpdateActionResponse>(`${this.baseUrl}/api/update/pull`, {});
    }
}
