import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService, UpdateStatusResponse, UpdateActionResponse, FirmwareCheckResponse, FirmwareActionResponse } from '../../services/api.service';

@Component({
    selector: 'app-update-settings',
    standalone: true,
    imports: [CommonModule],
    templateUrl: './update-settings.component.html',
    styleUrls: ['./update-settings.component.css']
})
export class UpdateSettingsComponent implements OnInit, OnDestroy {
    currentCommit: string = '';
    currentCommitShort: string = '';
    remoteCommit: string = '';
    remoteCommitShort: string = '';
    currentBranch: string = '';
    updateRemote: string = '';
    remoteBranch: string = '';
    updateAvailable: boolean = false;
    isChecking: boolean = false;
    isUpdating: boolean = false;
    statusMessage: string = '';
    statusType: 'success' | 'error' | 'info' = 'info';
    lastChecked: string = '';
    validationError: string = '';
    isOfficialClone: boolean = true;
    isValidBranch: boolean = true;
    hasChecked: boolean = false;

    // Firmware state
    fwUpdateAvailable: boolean = false;
    fwHasLocalFile: boolean = false;
    fwRemoteSha: string = '';
    fwRemoteDate: string = '';
    fwRemoteMessage: string = '';
    fwLocalSha: string = '';
    fwLocalDate: string = '';
    fwIsChecking: boolean = false;
    fwIsDownloading: boolean = false;
    fwIsFlashing: boolean = false;
    fwStatusMessage: string = '';
    fwStatusType: 'success' | 'error' | 'info' = 'info';
    fwHasChecked: boolean = false;

    private statusTimeout: any;
    private fwStatusTimeout: any;

    constructor(private apiService: ApiService) { }

    ngOnInit(): void {
        // Optionally auto-check on load
    }

    ngOnDestroy(): void {
        if (this.statusTimeout) clearTimeout(this.statusTimeout);
        if (this.fwStatusTimeout) clearTimeout(this.fwStatusTimeout);
    }

    checkForUpdates(): void {
        this.isChecking = true;
        this.statusMessage = '';
        this.validationError = '';
        
        this.apiService.checkForUpdates().subscribe({
            next: (response) => {
                this.hasChecked = true;
                if (response.success) {
                    this.isOfficialClone = response.is_official_clone !== false;
                    this.isValidBranch = response.valid_branch !== false;
                    this.currentBranch = response.branch || '';

                    if (response.validation_error) {
                        this.validationError = response.validation_error;
                        this.updateAvailable = false;
                        this.isChecking = false;
                        return;
                    }

                    this.currentCommit = response.current_commit || '';
                    this.currentCommitShort = response.current_commit_short || '';
                    this.remoteCommit = response.remote_commit || '';
                    this.remoteCommitShort = response.remote_commit_short || '';
                    this.updateRemote = response.remote || 'origin';
                    this.remoteBranch = response.remote_branch || '';
                    this.updateAvailable = response.update_available || false;
                    this.lastChecked = new Date().toLocaleTimeString();
                    
                    if (response.message) {
                        this.showStatus(response.message, 'info');
                    } else if (this.updateAvailable) {
                        this.showStatus(`New update available from ${this.updateRemote}!`, 'info');
                    } else {
                        this.showStatus('You are up to date.', 'success');
                    }
                } else {
                    this.showStatus(response.error || 'Failed to check for updates', 'error');
                }
                this.isChecking = false;
            },
            error: (err) => {
                this.hasChecked = true;
                this.showStatus('Failed to connect to server', 'error');
                this.isChecking = false;
            }
        });
    }

    performUpdate(): void {
        this.isUpdating = true;
        this.showStatus('Updating codebase... This may take a moment.', 'info', 60000);
        
        this.apiService.performUpdate().subscribe({
            next: (response) => {
                if (response.success) {
                    this.showStatus(response.message || 'Update successful! Please restart the application.', 'success', 10000);
                    this.updateAvailable = false;
                    // Refresh commit info
                    this.checkForUpdates();
                } else {
                    this.showStatus(response.error || 'Update failed', 'error');
                }
                this.isUpdating = false;
            },
            error: (err) => {
                this.showStatus('Failed to connect to server', 'error');
                this.isUpdating = false;
            }
        });
    }

    checkFirmware(): void {
        this.fwIsChecking = true;
        this.fwStatusMessage = '';

        this.apiService.checkFirmware().subscribe({
            next: (response) => {
                this.fwHasChecked = true;
                if (response.success) {
                    this.fwUpdateAvailable = response.update_available || false;
                    this.fwHasLocalFile = response.has_local_file || false;
                    this.fwRemoteSha = response.remote_sha || '';
                    this.fwRemoteDate = response.remote_date || '';
                    this.fwRemoteMessage = response.remote_message || '';
                    this.fwLocalSha = response.local_sha || '';
                    this.fwLocalDate = response.local_date || '';

                    if (this.fwUpdateAvailable) {
                        this.showFwStatus(this.fwHasLocalFile ? 'New firmware version available!' : 'Firmware not yet downloaded.', 'info');
                    } else {
                        this.showFwStatus('Firmware is up to date.', 'success');
                    }
                } else {
                    this.showFwStatus(response.error || 'Failed to check firmware', 'error');
                }
                this.fwIsChecking = false;
            },
            error: () => {
                this.fwHasChecked = true;
                this.showFwStatus('Failed to connect to server', 'error');
                this.fwIsChecking = false;
            }
        });
    }

    downloadFirmware(): void {
        this.fwIsDownloading = true;
        this.showFwStatus('Downloading firmware...', 'info', 60000);

        this.apiService.downloadFirmware().subscribe({
            next: (response) => {
                if (response.success) {
                    this.showFwStatus(response.message || 'Firmware downloaded successfully!', 'success', 10000);
                    this.fwUpdateAvailable = false;
                    this.checkFirmware();
                } else {
                    this.showFwStatus(response.error || 'Download failed', 'error');
                }
                this.fwIsDownloading = false;
            },
            error: () => {
                this.showFwStatus('Failed to connect to server', 'error');
                this.fwIsDownloading = false;
            }
        });
    }

    flashFirmware(): void {
        this.fwIsFlashing = true;
        this.showFwStatus('Flashing firmware to Nucleo...', 'info', 30000);

        this.apiService.flashFirmware().subscribe({
            next: (response) => {
                if (response.success) {
                    this.showFwStatus(response.message || 'Firmware flashed successfully!', 'success', 10000);
                } else {
                    this.showFwStatus(response.error || 'Flash failed', 'error');
                }
                this.fwIsFlashing = false;
            },
            error: () => {
                this.showFwStatus('Failed to connect to server', 'error');
                this.fwIsFlashing = false;
            }
        });
    }

    formatDate(isoDate: string): string {
        if (!isoDate) return '';
        try {
            return new Date(isoDate).toLocaleString();
        } catch {
            return isoDate;
        }
    }

    private showStatus(message: string, type: 'success' | 'error' | 'info', duration: number = 5000): void {
        this.statusMessage = message;
        this.statusType = type;

        if (this.statusTimeout) clearTimeout(this.statusTimeout);
        this.statusTimeout = setTimeout(() => {
            this.statusMessage = '';
        }, duration);
    }

    private showFwStatus(message: string, type: 'success' | 'error' | 'info', duration: number = 5000): void {
        this.fwStatusMessage = message;
        this.fwStatusType = type;

        if (this.fwStatusTimeout) clearTimeout(this.fwStatusTimeout);
        this.fwStatusTimeout = setTimeout(() => {
            this.fwStatusMessage = '';
        }, duration);
    }
}
