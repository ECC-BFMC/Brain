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

export interface UpdateConflict {
    files: string[];
    raw: string;
    diverged?: boolean;
    message?: string;
}

export interface UpdateStatusResponse {
    success: boolean;
    is_git_repo?: boolean;
    current_commit?: string;
    current_commit_short?: string;
    remote_commit?: string;
    remote_commit_short?: string;
    update_available?: boolean;
    branch?: string;
    remote?: string;
    remote_branch?: string;
    source?: string;
    configured_branch?: string;
    behind_by?: number;
    deps_changed?: boolean;
    via?: string;
    message?: string;
    auth_required?: boolean;
    error?: string;
}

export interface UpdateActionResponse {
    success: boolean;
    message?: string;
    deps_changed?: boolean;
    conflict?: UpdateConflict;
    is_git_repo?: boolean;
    auth_required?: boolean;
    error?: string;
}

export interface UpdateBranchesResponse {
    success: boolean;
    branches?: string[];
    default_branch?: string;
    selected_branch?: string;
    error?: string;
}

export interface UpdateSourceResponse {
    success: boolean;
    url?: string;
    branch?: string;
    remote_name?: string;
    origin_url?: string;
    is_git_repo?: boolean;
    message?: string;
    error?: string;
}

export interface UpdateKeyResponse {
    success: boolean;
    has_key?: boolean;
    public_key?: string;
    fingerprint?: string;
    message?: string;
    error?: string;
}

export interface CalibrationMeasurementSummary {
    id: string;
    name: string;
    mode: 'basic';
    modeLabel: string;
    measurementMode: 'manual';
    measurementModeLabel: string;
    savedAt?: string;
}

export interface CalibrationMeasurementState {
    mode: 'basic';
    modeLabel: string;
    measurementMode: 'manual';
    measurementModeLabel: string;
    useDummyData?: boolean;
    forward: boolean;
    left: boolean;
    right: boolean;
    backward: boolean;
    testRun: boolean;
    steeringOffset: number;
    maxAngleLeft?: number | null;
    maxAngleRight?: number | null;
}

export interface CalibrationMeasurementsResponse {
    success: boolean;
    measurements?: CalibrationMeasurementSummary[];
    error?: string;
}

export interface CalibrationMeasurementResponse {
    success: boolean;
    measurement?: CalibrationMeasurementSummary;
    calibration?: CalibrationMeasurementState;
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

export interface LocalFirmwareFile {
    name: string;
    size: number;
    modified_at: string;
    is_default: boolean;
}

export interface LocalFirmwareFilesResponse {
    success: boolean;
    files?: LocalFirmwareFile[];
    selected_file?: string;
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

    // Calibration Measurement Persistence
    listCalibrationMeasurements(): Observable<CalibrationMeasurementsResponse> {
        return this.http.get<CalibrationMeasurementsResponse>(`${this.baseUrl}/api/calibration/measurements`);
    }

    saveCalibrationMeasurements(name: string): Observable<CalibrationMeasurementResponse> {
        return this.http.post<CalibrationMeasurementResponse>(
            `${this.baseUrl}/api/calibration/measurements`,
            { name }
        );
    }

    loadCalibrationMeasurements(id: string): Observable<CalibrationMeasurementResponse> {
        return this.http.post<CalibrationMeasurementResponse>(
            `${this.baseUrl}/api/calibration/measurements/load`,
            { id }
        );
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

    forceUpdate(): Observable<UpdateActionResponse> {
        return this.http.post<UpdateActionResponse>(`${this.baseUrl}/api/update/force`, {});
    }

    adoptRepo(): Observable<UpdateActionResponse> {
        return this.http.post<UpdateActionResponse>(`${this.baseUrl}/api/update/adopt`, {});
    }

    listUpdateBranches(): Observable<UpdateBranchesResponse> {
        return this.http.get<UpdateBranchesResponse>(`${this.baseUrl}/api/update/branches`);
    }

    setUpdateBranch(branch: string): Observable<UpdateBranchesResponse> {
        return this.http.post<UpdateBranchesResponse>(`${this.baseUrl}/api/update/branch`, { branch });
    }

    getUpdateSource(): Observable<UpdateSourceResponse> {
        return this.http.get<UpdateSourceResponse>(`${this.baseUrl}/api/update/source`);
    }

    setUpdateSource(url: string): Observable<UpdateSourceResponse> {
        return this.http.post<UpdateSourceResponse>(`${this.baseUrl}/api/update/source`, { url });
    }

    getUpdateKey(): Observable<UpdateKeyResponse> {
        return this.http.get<UpdateKeyResponse>(`${this.baseUrl}/api/update/key`);
    }

    generateUpdateKey(): Observable<UpdateKeyResponse> {
        return this.http.post<UpdateKeyResponse>(`${this.baseUrl}/api/update/key/generate`, {});
    }

    deleteUpdateKey(): Observable<UpdateKeyResponse> {
        return this.http.delete<UpdateKeyResponse>(`${this.baseUrl}/api/update/key`);
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

    listLocalFirmwareFiles(): Observable<LocalFirmwareFilesResponse> {
        return this.http.get<LocalFirmwareFilesResponse>(`${this.baseUrl}/api/firmware/files`);
    }

    flashSelectedFirmware(filename: string): Observable<FirmwareActionResponse> {
        return this.http.post<FirmwareActionResponse>(`${this.baseUrl}/api/firmware/flash-selected`, { filename });
    }
}
