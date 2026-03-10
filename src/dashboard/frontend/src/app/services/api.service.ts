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
    branch?: string;
    remote?: string;
    remote_branch?: string;
    is_official_clone?: boolean;
    valid_branch?: boolean;
    validation_error?: string;
    message?: string;
    error?: string;
}

export interface UpdateActionResponse {
    success: boolean;
    message?: string;
    error?: string;
}

export interface FirmwareCheckResponse {
    success: boolean;
    update_available?: boolean;
    has_local_file?: boolean;
    remote_sha?: string;
    remote_date?: string;
    remote_message?: string;
    local_sha?: string;
    local_date?: string;
    error?: string;
}

export interface FirmwareActionResponse {
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

    // Firmware Update Management
    checkFirmware(): Observable<FirmwareCheckResponse> {
        return this.http.get<FirmwareCheckResponse>(`${this.baseUrl}/api/firmware/check`);
    }

    downloadFirmware(): Observable<FirmwareActionResponse> {
        return this.http.post<FirmwareActionResponse>(`${this.baseUrl}/api/firmware/download`, {});
    }

    flashFirmware(): Observable<FirmwareActionResponse> {
        return this.http.post<FirmwareActionResponse>(`${this.baseUrl}/api/firmware/flash`, {});
    }
}
