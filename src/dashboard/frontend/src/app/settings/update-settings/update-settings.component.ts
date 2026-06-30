import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService, UpdateStatusResponse, UpdateActionResponse, UpdateConflict, UpdateSourceResponse, UpdateKeyResponse, FirmwareCheckResponse, FirmwareActionResponse, FirmwareSourceResponse, FirmwareRepoBinsResponse, FirmwareTokenResponse, FirmwareBranchesResponse } from '../../services/api.service';

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
    remoteDate: string = '';
    currentBranch: string = '';
    behindBy: number = 0;
    via: string = '';
    updateAvailable: boolean = false;
    diverged: boolean = false;
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

    // Repository source (which repo to pull updates from, e.g. a student fork)
    sourceUrl: string = '';
    sourceOriginUrl: string = '';
    showSourceEditor: boolean = false;
    isSavingSource: boolean = false;
    sourceLoaded: boolean = false;

    // Deploy-key popup (private-repo access)
    showKeyModal: boolean = false;
    hasKey: boolean = false;
    publicKey: string = '';
    keyFingerprint: string = '';
    isGeneratingKey: boolean = false;
    keyError: string = '';
    keyCopied: boolean = false;

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
    fwJustDownloaded: boolean = false;   // Flash only after a pull, and only while still current
    fwStatusMessage: string = '';
    fwStatusType: 'success' | 'error' | 'info' = 'info';
    fwHasChecked: boolean = false;

    // Firmware source / file selection
    fwRepo: string = '';
    fwBranch: string = '';
    fwDefaultRepo: string = '';
    fwSourceUrl: string = '';
    fwFilePath: string = '';
    fwFileName: string = '';
    fwShowSourceEditor: boolean = false;
    fwIsSavingSource: boolean = false;
    fwRepoBins: string[] = [];
    fwBinsLoading: boolean = false;
    fwBinsTruncated: boolean = false;
    fwShowFilePicker: boolean = false;

    // Firmware branch selection
    fwBranches: string[] = [];
    fwDefaultBranch: string = '';
    fwSelectedBranch: string = '';
    fwBranchesLoading: boolean = false;

    // Firmware private-repo token
    fwHasToken: boolean = false;
    fwShowTokenModal: boolean = false;
    fwTokenInput: string = '';
    fwIsSavingToken: boolean = false;
    fwTokenError: string = '';

    private statusTimeout: any;
    private fwStatusTimeout: any;

    constructor(private apiService: ApiService) { }

    ngOnInit(): void {
        this.loadSource();
        this.loadKey();
        this.loadFirmwareSource();
        this.loadFirmwareToken();
        // Auto-check both on open so the student sees the current status right away.
        this.checkForUpdates();
        this.checkFirmware();
    }

    ngOnDestroy(): void {
        if (this.statusTimeout) clearTimeout(this.statusTimeout);
        if (this.fwStatusTimeout) clearTimeout(this.fwStatusTimeout);
    }

    // ==================== Brain update ====================

    /** True when the selected branch points at a different commit than what's
     * checked out, but it isn't a clean fast-forward (diverged, or the local
     * copy is ahead). In that case there's no "Pull", but the user can still
     * switch to that branch via a force reset -- even when the checker would
     * otherwise say "up to date". */
    get canSwitchBranch(): boolean {
        return this.isGitRepo && !!this.remoteCommit
            && this.remoteCommit !== this.currentCommit
            && !this.updateAvailable && !this.conflict;
    }

    checkForUpdates(): void {
        this.isChecking = true;
        this.statusMessage = '';
        this.conflict = null;
        this.diverged = false;

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
                this.remoteDate = response.remote_date || '';
                this.currentBranch = response.branch || '';
                this.selectedBranch = response.branch || this.selectedBranch;
                this.behindBy = response.behind_by || 0;
                this.depsChanged = response.deps_changed || false;
                this.via = response.via || '';
                this.updateAvailable = response.update_available || false;
                this.diverged = response.diverged || false;
                this.lastChecked = new Date().toLocaleTimeString();

                this.handleAuthRequired(response);

                if (response.message) {
                    this.showStatus(response.message, 'info');
                } else if (this.updateAvailable) {
                    this.showStatus(`Update available from ${this.source || 'the configured source'}.`, 'info');
                } else if (this.canSwitchBranch) {
                    this.showStatus(`"${this.selectedBranch}" differs from the car's copy. Switch to it to apply.`, 'info');
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
                    this.handleAuthRequired(response);
                    this.showStatus(response.error || 'Force update failed', 'error');
                }
                this.isForcing = false;
            },
            error: (err) => {
                this.handleAuthRequired(err?.error);
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
                    this.handleAuthRequired(response);
                    this.showStatus(response.error || 'Setup failed', 'error', 12000);
                }
                this.isAdopting = false;
            },
            error: (err) => {
                this.handleAuthRequired(err?.error);
                this.showStatus(err?.error?.error || 'Setup failed', 'error', 12000);
                this.isAdopting = false;
            }
        });
    }

    // ==================== Repository source ====================

    loadSource(): void {
        this.apiService.getUpdateSource().subscribe({
            next: (response: UpdateSourceResponse) => {
                if (response.success) {
                    this.sourceUrl = response.url || '';
                    this.sourceOriginUrl = response.origin_url || '';
                    this.sourceLoaded = true;
                }
            },
            error: () => { /* non-fatal; source section just stays hidden */ }
        });
    }

    saveSource(): void {
        const url = (this.sourceUrl || '').trim();
        this.isSavingSource = true;

        this.apiService.setUpdateSource(url).subscribe({
            next: (response: UpdateSourceResponse) => {
                if (response.success) {
                    this.sourceUrl = response.url || '';
                    this.showSourceEditor = false;
                    this.showStatus(response.message || 'Update source saved.', 'success');
                    // The tracked branch and any cached check results depend on the
                    // source, so re-check against the new repo.
                    this.branches = [];
                    this.conflict = null;
                    this.updateAvailable = false;
                    this.checkForUpdates();
                } else {
                    this.showStatus(response.error || 'Failed to save update source', 'error');
                }
                this.isSavingSource = false;
            },
            error: (err) => {
                this.showStatus(err?.error?.error || 'Failed to save update source', 'error');
                this.isSavingSource = false;
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
        if (this.handleAuthRequired(body)) {
            this.showStatus((body && body.error) || 'Update failed', 'error');
            return;
        }
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
                    if (response.source) this.fwRepo = response.source;
                    if (response.branch) { this.fwBranch = response.branch; this.fwSelectedBranch = response.branch; }
                    if (response.file_path) this.fwFilePath = response.file_path;
                    if (response.file_name) this.fwFileName = response.file_name;
                    if (!this.fwBranches.length) this.loadFirmwareBranches();

                    if (this.fwUpdateAvailable) {
                        this.showFwStatus(this.fwHasLocalFile ? 'New firmware version available!' : 'Firmware not yet downloaded.', 'info');
                    } else {
                        this.showFwStatus('Firmware is up to date.', 'success');
                    }
                } else {
                    if (!this.fwHandleAuthRequired(response)) {
                        this.showFwStatus(response.error || 'Failed to check firmware', 'error');
                    }
                }
                this.fwIsChecking = false;
            },
            error: (err) => {
                this.fwHasChecked = true;
                if (!this.fwHandleAuthRequired(err?.error)) {
                    this.showFwStatus(err?.error?.error || 'Failed to connect to server', 'error');
                }
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
                    this.fwJustDownloaded = true;
                    this.checkFirmware();
                } else if (!this.fwHandleAuthRequired(response)) {
                    this.showFwStatus(response.error || 'Download failed', 'error');
                }
                this.fwIsDownloading = false;
            },
            error: (err) => {
                if (!this.fwHandleAuthRequired(err?.error)) {
                    this.showFwStatus(err?.error?.error || 'Failed to connect to server', 'error');
                }
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
            error: (err) => {
                // The server returns the real reason (e.g. Nucleo not detected) in the body.
                this.showFwStatus(err?.error?.error || 'Failed to connect to server', 'error');
                this.fwIsFlashing = false;
            }
        });
    }

    // ==================== Firmware source / file selection ====================

    loadFirmwareSource(): void {
        this.apiService.getFirmwareSource().subscribe({
            next: (response: FirmwareSourceResponse) => {
                if (response.success) {
                    this.fwSourceUrl = response.url || '';
                    this.fwRepo = response.repo || '';
                    this.fwBranch = response.branch || '';
                    this.fwDefaultRepo = response.default_repo || '';
                    this.fwFilePath = response.file_path || '';
                    this.fwFileName = this.fwFilePath ? this.fwFilePath.split('/').pop() || '' : '';
                }
            },
            error: () => { /* non-fatal */ }
        });
    }

    saveFirmwareSource(): void {
        const url = (this.fwSourceUrl || '').trim();
        this.fwIsSavingSource = true;

        this.apiService.setFirmwareSource(url).subscribe({
            next: (response: FirmwareSourceResponse) => {
                if (response.success) {
                    this.fwSourceUrl = response.url || '';
                    this.fwShowSourceEditor = false;
                    // Changing the repo clears the selected file server-side; reflect that
                    // and reopen the picker so the student chooses a .bin from the new repo.
                    this.fwRepoBins = [];
                    this.fwBranches = [];   // new repo -> reload its branches
                    this.fwSelectedBranch = '';
                    this.fwHasChecked = false;
                    this.fwJustDownloaded = false;
                    this.showFwStatus(response.message || 'Firmware source saved.', 'success');
                    this.loadFirmwareSource();
                    this.loadFirmwareBranches();
                    this.openFirmwareFilePicker();
                } else {
                    this.showFwStatus(response.error || 'Failed to save firmware source', 'error');
                }
                this.fwIsSavingSource = false;
            },
            error: (err) => {
                this.showFwStatus(err?.error?.error || 'Failed to save firmware source', 'error');
                this.fwIsSavingSource = false;
            }
        });
    }

    openFirmwareFilePicker(): void {
        this.fwShowFilePicker = true;
        this.loadFirmwareRepoBins();
        if (!this.fwBranches.length) this.loadFirmwareBranches();
    }

    loadFirmwareBranches(): void {
        this.fwBranchesLoading = true;
        this.apiService.listFirmwareBranches().subscribe({
            next: (response: FirmwareBranchesResponse) => {
                if (response.success) {
                    this.fwBranches = response.branches || [];
                    this.fwDefaultBranch = response.default_branch || '';
                    this.fwSelectedBranch = response.selected_branch || this.fwSelectedBranch || this.fwDefaultBranch;
                } else {
                    this.fwHandleAuthRequired(response);
                }
                this.fwBranchesLoading = false;
            },
            error: (err) => {
                this.fwHandleAuthRequired(err?.error);
                this.fwBranchesLoading = false;
            }
        });
    }

    onFirmwareBranchChange(branch: string): void {
        this.fwSelectedBranch = branch;
        this.apiService.setFirmwareBranch(branch).subscribe({
            next: (response: FirmwareBranchesResponse) => {
                if (response.success) {
                    this.fwBranch = branch || this.fwDefaultBranch;
                    this.fwHasChecked = false;
                    this.fwJustDownloaded = false;
                    // The .bin set and latest commit depend on the branch.
                    this.fwRepoBins = [];
                    if (this.fwShowFilePicker) this.loadFirmwareRepoBins();
                    this.showFwStatus(`Now tracking "${branch || this.fwDefaultBranch}".`, 'info');
                } else {
                    this.showFwStatus(response.error || 'Failed to set branch', 'error');
                }
            },
            error: (err) => this.showFwStatus(err?.error?.error || 'Failed to set branch', 'error')
        });
    }

    loadFirmwareRepoBins(): void {
        this.fwBinsLoading = true;
        this.apiService.listFirmwareRepoBins().subscribe({
            next: (response: FirmwareRepoBinsResponse) => {
                if (response.success) {
                    this.fwRepoBins = response.files || [];
                    this.fwBinsTruncated = response.truncated || false;
                    if (response.selected_file) this.fwFilePath = response.selected_file;
                } else if (!this.fwHandleAuthRequired(response)) {
                    this.showFwStatus(response.error || 'Failed to list .bin files', 'error');
                }
                this.fwBinsLoading = false;
            },
            error: (err) => {
                this.fwShowFilePicker = false;
                if (!this.fwHandleAuthRequired(err?.error)) {
                    this.showFwStatus(err?.error?.error || 'Failed to list .bin files', 'error');
                }
                this.fwBinsLoading = false;
            }
        });
    }

    selectFirmwareFile(filePath: string): void {
        this.apiService.setFirmwareFile(filePath).subscribe({
            next: (response: FirmwareSourceResponse) => {
                if (response.success) {
                    this.fwFilePath = response.file_path || filePath;
                    this.fwFileName = this.fwFilePath.split('/').pop() || '';
                    this.fwShowFilePicker = false;
                    this.fwHasChecked = false;
                    this.fwJustDownloaded = false;
                    this.showFwStatus(`Selected ${this.fwFileName}.`, 'info');
                } else {
                    this.showFwStatus(response.error || 'Failed to set firmware file', 'error');
                }
            },
            error: (err) => this.showFwStatus(err?.error?.error || 'Failed to set firmware file', 'error')
        });
    }

    // ==================== Firmware access token (private repos) ====================

    loadFirmwareToken(): void {
        this.apiService.getFirmwareToken().subscribe({
            next: (response: FirmwareTokenResponse) => {
                if (response.success) this.fwHasToken = response.has_token || false;
            },
            error: () => { /* non-fatal */ }
        });
    }

    openFirmwareTokenModal(): void {
        this.fwTokenError = '';
        this.fwTokenInput = '';
        this.fwShowTokenModal = true;
    }

    saveFirmwareToken(): void {
        const tok = (this.fwTokenInput || '').trim();
        if (!tok) {
            this.fwTokenError = 'Paste an access token first.';
            return;
        }
        this.fwIsSavingToken = true;
        this.fwTokenError = '';

        this.apiService.setFirmwareToken(tok).subscribe({
            next: (response: FirmwareTokenResponse) => {
                if (response.success) {
                    this.fwHasToken = true;
                    this.fwTokenInput = '';          // don't keep the secret in the DOM
                    this.fwShowTokenModal = false;
                    this.showFwStatus(response.message || 'Access token saved.', 'success', 8000);
                } else {
                    this.fwTokenError = response.error || 'Failed to save the token.';
                }
                this.fwIsSavingToken = false;
            },
            error: (err) => {
                this.fwTokenError = err?.error?.error || 'Failed to save the token.';
                this.fwIsSavingToken = false;
            }
        });
    }

    removeFirmwareToken(): void {
        this.apiService.deleteFirmwareToken().subscribe({
            next: (response: FirmwareTokenResponse) => {
                if (response.success) {
                    this.fwHasToken = false;
                    this.showFwStatus(response.message || 'Access token removed.', 'info');
                } else {
                    this.fwTokenError = response.error || 'Failed to remove the token.';
                }
            },
            error: (err) => { this.fwTokenError = err?.error?.error || 'Failed to remove the token.'; }
        });
    }

    /** Open the token modal when the server reports a private repo it can't read.
     * Returns true when handled. */
    private fwHandleAuthRequired(body: any): boolean {
        if (body && body.auth_required) {
            this.openFirmwareTokenModal();
            return true;
        }
        return false;
    }

    formatDate(isoDate: string): string {
        if (!isoDate) return '';
        try {
            return new Date(isoDate).toLocaleString();
        } catch {
            return isoDate;
        }
    }

    /** Short "owner/repo" label for the configured Brain source, matching how
     * the firmware card shows its repo (instead of the full git URL). */
    get sourceRepoLabel(): string {
        const raw = (this.sourceUrl || this.sourceOriginUrl || '').trim();
        if (!raw) return 'configured source';
        let path = '';
        const scp = raw.match(/^[^@/]+@[^:]+:(.+)$/);   // git@host:owner/repo.git
        if (scp) {
            path = scp[1];
        } else {
            try {
                path = new URL(raw).pathname;
            } catch {
                return raw;
            }
        }
        path = path.replace(/^\/+/, '').replace(/\.git$/i, '');
        const parts = path.split('/').filter(Boolean);
        return parts.length >= 2 ? `${parts[0]}/${parts[1]}` : (path || raw);
    }

    // ==================== Deploy key (private repos) ====================

    /** Direct link to the "Add deploy key" page of the configured GitHub repo,
     * e.g. https://github.com/owner/repo/settings/keys/new. Empty for non-GitHub
     * sources (we can't know the right URL, so we hide the link). */
    get deployKeysUrl(): string {
        const raw = (this.sourceUrl || this.sourceOriginUrl || '').trim();
        if (!raw) return '';

        let path = '';
        const scp = raw.match(/^git@github\.com:(.+)$/i);
        if (scp) {
            path = scp[1];
        } else {
            try {
                const u = new URL(raw);
                const host = u.hostname.toLowerCase();
                if (host !== 'github.com' && host !== 'www.github.com') return '';
                path = u.pathname.replace(/^\/+/, '');
            } catch {
                return '';
            }
        }

        path = path.replace(/\.git$/i, '');
        const parts = path.split('/').filter(Boolean);
        if (parts.length < 2) return '';
        return `https://github.com/${parts[0]}/${parts[1]}/settings/keys/new`;
    }

    openKeyModal(): void {
        this.keyError = '';
        this.keyCopied = false;
        this.showKeyModal = true;
        this.loadKey();
    }

    generateKey(): void {
        this.isGeneratingKey = true;
        this.keyError = '';

        this.apiService.generateUpdateKey().subscribe({
            next: (response: UpdateKeyResponse) => {
                if (response.success) {
                    this.hasKey = true;
                    this.publicKey = response.public_key || '';
                    this.keyFingerprint = response.fingerprint || '';
                    this.showStatus(response.message || 'Deploy key generated.', 'success', 10000);
                } else {
                    this.keyError = response.error || 'Failed to generate a key.';
                }
                this.isGeneratingKey = false;
            },
            error: (err) => {
                this.keyError = err?.error?.error || 'Failed to generate a key.';
                this.isGeneratingKey = false;
            }
        });
    }

    loadKey(): void {
        this.apiService.getUpdateKey().subscribe({
            next: (response: UpdateKeyResponse) => {
                if (response.success) {
                    this.hasKey = response.has_key || false;
                    this.publicKey = response.public_key || '';
                    this.keyFingerprint = response.fingerprint || '';
                }
            },
            error: () => { /* non-fatal */ }
        });
    }

    removeKey(): void {
        this.apiService.deleteUpdateKey().subscribe({
            next: (response: UpdateKeyResponse) => {
                if (response.success) {
                    this.hasKey = false;
                    this.publicKey = '';
                    this.keyFingerprint = '';
                    this.showStatus(response.message || 'Deploy key removed.', 'info');
                } else {
                    this.keyError = response.error || 'Failed to remove the key.';
                }
            },
            error: (err) => { this.keyError = err?.error?.error || 'Failed to remove the key.'; }
        });
    }

    copyPublicKey(): void {
        if (!this.publicKey) return;
        navigator.clipboard?.writeText(this.publicKey).then(() => {
            this.keyCopied = true;
            setTimeout(() => { this.keyCopied = false; }, 2000);
        }).catch(() => { /* clipboard unavailable; user can select manually */ });
    }

    /** Open the deploy-key popup when the server reports a private repo it can't
     * reach. Returns true when handled. */
    private handleAuthRequired(body: any): boolean {
        if (body && body.auth_required) {
            this.openKeyModal();
            return true;
        }
        return false;
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
