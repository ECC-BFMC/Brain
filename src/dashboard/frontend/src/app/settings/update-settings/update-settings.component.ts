import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService, UpdateStatusResponse, UpdateActionResponse } from '../../services/api.service';

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
    updateAvailable: boolean = false;
    isChecking: boolean = false;
    isUpdating: boolean = false;
    statusMessage: string = '';
    statusType: 'success' | 'error' | 'info' = 'info';
    lastChecked: string = '';
    private statusTimeout: any;

    constructor(private apiService: ApiService) { }

    ngOnInit(): void {
        // Optionally auto-check on load
    }

    ngOnDestroy(): void {
        if (this.statusTimeout) {
            clearTimeout(this.statusTimeout);
        }
    }

    checkForUpdates(): void {
        this.isChecking = true;
        this.statusMessage = '';
        
        this.apiService.checkForUpdates().subscribe({
            next: (response) => {
                if (response.success) {
                    this.currentCommit = response.current_commit || '';
                    this.currentCommitShort = response.current_commit_short || '';
                    this.remoteCommit = response.remote_commit || '';
                    this.remoteCommitShort = response.remote_commit_short || '';
                    this.updateAvailable = response.update_available || false;
                    this.lastChecked = new Date().toLocaleTimeString();
                    
                    if (this.updateAvailable) {
                        this.showStatus('New update available!', 'info');
                    } else {
                        this.showStatus('You are up to date.', 'success');
                    }
                } else {
                    this.showStatus(response.error || 'Failed to check for updates', 'error');
                }
                this.isChecking = false;
            },
            error: (err) => {
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

    private showStatus(message: string, type: 'success' | 'error' | 'info', duration: number = 5000): void {
        this.statusMessage = message;
        this.statusType = type;

        if (this.statusTimeout) {
            clearTimeout(this.statusTimeout);
        }

        this.statusTimeout = setTimeout(() => {
            this.statusMessage = '';
        }, duration);
    }
}
