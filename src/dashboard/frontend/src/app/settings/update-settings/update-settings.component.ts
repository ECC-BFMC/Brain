import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService, UpdateStatusResponse, UpdateActionResponse, UpdateConflict, FirmwareCheckResponse, FirmwareActionResponse } from '../../services/api.service';

@Component({
    selector: 'app-update-settings',
    standalone: true,
    imports: [CommonModule, FormsModule],
    templateUrl: './update-settings.component.html',
    styleUrls: ['./update-settings.component.css']
})
export class UpdateSettingsComponent implements OnInit, OnDestroy {
    // Brain update state
    isGitRepo: boolean = true;
    source: string = '';
    currentCommit: string = '';
    currentCommitShort: string = '';
    remoteCommit: string = '';
    remoteCommitShort: string = '';
    currentBranch: string = '';
    behindBy: number = 0;
    via: string = '';
    updateAvailable: boolean = false;
    depsChanged: boolean = false;
    isChecking: boolean = false;
    isUpdating: boolean = false;
    isForcing: boolean = false;
    isAdopting: boolean = false;
    statusMessage: string = '';
    statusType: 'success' | 'error' | 'info' = 'info';
    lastChecked: string = '';
    hasChecked: boolean = false;
    needsRestart: boolean = false;

    // Conflict / force state
    conflict: UpdateConflict | null = null;
    showForceConfirm: boolean = false;
    showAdoptConfirm: boolean = false;

    // Branch selection
    branches: string[] = [];
    defaultBranch: string = '';
    selectedBranch: string = '';
    branchesLoading: boolean = false;

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

    // ==================== Brain update ====================

    checkForUpdates(): void {
        this.isChecking = true;
        this.statusMessage = '';
        this.conflict = null;

        this.apiService.checkForUpdates().subscribe({
            next: (response: UpdateStatusResponse) => {
                this.hasChecked = true;
                if (!response.success) {
                    this.showStatus(response.error || 'Failed to check for updates', 'error');
                    this.isChecking = false;
                    return;
                }

                this.isGitRepo = response.is_git_repo !== false;
                this.source = response.source || '';

                if (!this.isGitRepo) {
                    // Not a git clone (e.g. downloaded ZIP) — offer the adopt flow.
                    this.updateAvailable = false;
                    this.isChecking = false;
                    return;
                }

                this.currentCommit = response.current_commit || '';
                this.currentCommitShort = response.current_commit_short || '';
                this.remoteCommit = response.remote_commit || '';
                this.remoteCommitShort = response.remote_commit_short || '';
                this.currentBranch = response.branch || '';
                this.selectedBranch = response.branch || this.selectedBranch;
                this.behindBy = response.behind_by || 0;
                this.depsChanged = response.deps_changed || false;
                this.via = response.via || '';
                this.updateAvailable = response.update_available || false;
                this.lastChecked = new Date().toLocaleTimeString();

                if (response.message) {
                    this.showStatus(response.message, 'info');
                } else if (this.updateAvailable) {
                    this.showStatus(`Update available from ${this.source || 'the configured source'}.`, 'info');
                } else {
                    this.showStatus('You are up to date.', 'success');
                }

                if (!this.branches.length) {
                    this.loadBranches();
                }
                this.isChecking = false;
            },
            error: () => {
                this.hasChecked = true;
                this.showStatus('Failed to connect to server', 'error');
                this.isChecking = false;
            }
        });
    }

    performUpdate(): void {
        this.isUpdating = true;
        this.conflict = null;
        this.showStatus('Updating codebase... This may take a moment.', 'info', 60000);

        this.apiService.performUpdate().subscribe({
            next: (response: UpdateActionResponse) => {
                if (response.success) {
                    this.onUpdateApplied(response);
                } else {
                    this.handlePullFailure(response);
                }
                this.isUpdating = false;
            },
            error: (err) => {
                // A blocked fast-forward returns HTTP 409 with the body in err.error.
                this.handlePullFailure(err?.error);
                this.isUpdating = false;
            }
        });
    }

    forceUpdate(): void {
        this.showForceConfirm = false;
        this.isForcing = true;
        this.showStatus('Discarding local changes and updating...', 'info', 60000);

        this.apiService.forceUpdate().subscribe({
            next: (response: UpdateActionResponse) => {
                if (response.success) {
                    this.conflict = null;
                    this.onUpdateApplied(response);
                } else {
                    this.showStatus(response.error || 'Force update failed', 'error');
                }
                this.isForcing = false;
            },
            error: (err) => {
                this.showStatus(err?.error?.error || 'Force update failed', 'error');
                this.isForcing = false;
            }
        });
    }

    adopt(): void {
        this.showAdoptConfirm = false;
        this.isAdopting = true;
        this.showStatus('Setting up updates... This may take a while.', 'info', 120000);

        this.apiService.adoptRepo().subscribe({
            next: (response: UpdateActionResponse) => {
                if (response.success) {
                    this.showStatus(response.message || 'Updates configured.', 'success', 12000);
                    this.isGitRepo = true;
                    this.needsRestart = true;
                    this.checkForUpdates();
                } else {
                    this.showStatus(response.error || 'Setup failed', 'error', 12000);
                }
                this.isAdopting = false;
            },
            error: (err) => {
                this.showStatus(err?.error?.error || 'Setup failed', 'error', 12000);
                this.isAdopting = false;
            }
        });
    }

    loadBranches(): void {
        this.branchesLoading = true;
        this.apiService.listUpdateBranches().subscribe({
            next: (response) => {
                if (response.success) {
                    this.branches = response.branches || [];
                    this.defaultBranch = response.default_branch || '';
                    this.selectedBranch = response.selected_branch || this.selectedBranch || this.defaultBranch;
                }
                this.branchesLoading = false;
            },
            error: () => {
                this.branchesLoading = false;
            }
        });
    }

    onBranchChange(branch: string): void {
        this.selectedBranch = branch;
        this.apiService.setUpdateBranch(branch).subscribe({
            next: (response) => {
                if (response.success) {
                    this.showStatus(`Now tracking "${branch || this.defaultBranch}".`, 'info');
                    this.updateAvailable = false;
                    this.conflict = null;
                    this.checkForUpdates();
                } else {
                    this.showStatus(response.error || 'Failed to set branch', 'error');
                }
            },
            error: (err) => this.showStatus(err?.error?.error || 'Failed to set branch', 'error')
        });
    }

    private onUpdateApplied(response: UpdateActionResponse): void {
        this.showStatus(response.message || 'Update successful!', 'success', 12000);
        this.updateAvailable = false;
        this.needsRestart = true;
        this.depsChanged = response.deps_changed || false;
        this.checkForUpdates();
    }

    private handlePullFailure(body: any): void {
        if (body && body.conflict) {
            this.conflict = body.conflict as UpdateConflict;
            this.showStatus(body.conflict.message || body.error || 'Update could not be applied.', 'error', 12000);
        } else {
            this.showStatus((body && body.error) || 'Update failed', 'error');
        }
    }

    // ==================== Firmware ====================

    checkFirmware(): void {
        this.fwIsChecking = true;
        this.fwStatusMessage = '';

        this.apiService.checkFirmware().subscribe({
            next: (response: FirmwareCheckResponse) => {
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
            next: (response: FirmwareActionResponse) => {
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
            next: (response: FirmwareActionResponse) => {
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
