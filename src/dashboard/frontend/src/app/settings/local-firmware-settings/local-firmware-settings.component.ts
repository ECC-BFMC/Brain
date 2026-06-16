import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService, LocalFirmwareFile } from '../../services/api.service';

@Component({
  selector: 'app-local-firmware-settings',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './local-firmware-settings.component.html',
  styleUrls: ['./local-firmware-settings.component.css']
})
export class LocalFirmwareSettingsComponent implements OnInit, OnDestroy {
  localFirmwareFiles: LocalFirmwareFile[] = [];
  selectedLocalFirmwareName: string = '';
  isLoading: boolean = false;
  isFlashing: boolean = false;
  statusMessage: string = '';
  statusType: 'success' | 'error' | 'info' = 'info';

  private statusTimeout: any;

  constructor(private apiService: ApiService) {}

  ngOnInit(): void {
    this.loadLocalFirmwareFiles(false);
  }

  ngOnDestroy(): void {
    if (this.statusTimeout) {
      clearTimeout(this.statusTimeout);
    }
  }

  loadLocalFirmwareFiles(showStatus: boolean = true): void {
    this.isLoading = true;
    if (showStatus) {
      this.showStatus('Refreshing local firmware files...', 'info');
    }

    this.apiService.listLocalFirmwareFiles().subscribe({
      next: (response) => {
        if (response.success) {
          this.localFirmwareFiles = response.files || [];

          const requestedSelection = this.selectedLocalFirmwareName || response.selected_file || '';
          const selectedStillExists = this.localFirmwareFiles.some(file => file.name === requestedSelection);
          this.selectedLocalFirmwareName = selectedStillExists
            ? requestedSelection
            : (response.selected_file || this.localFirmwareFiles[0]?.name || '');

          if (showStatus) {
            if (this.localFirmwareFiles.length > 0) {
              this.showStatus(`Found ${this.localFirmwareFiles.length} local firmware file${this.localFirmwareFiles.length === 1 ? '' : 's'}.`, 'success');
            } else {
              this.showStatus('No .bin files were found in src/hardware/firmware.', 'info');
            }
          }
        } else {
          this.showStatus(response.error || 'Failed to load local firmware files.', 'error');
        }
        this.isLoading = false;
      },
      error: (err) => {
        const msg = err.error?.error || 'Failed to connect to server';
        this.showStatus(msg, 'error');
        this.isLoading = false;
      }
    });
  }

  flashSelectedFirmware(): void {
    if (!this.selectedLocalFirmwareName) {
      this.showStatus('Select a firmware file first.', 'error');
      return;
    }

    this.isFlashing = true;
    this.showStatus(`Flashing ${this.selectedLocalFirmwareName} to Nucleo...`, 'info', 30000);

    this.apiService.flashSelectedFirmware(this.selectedLocalFirmwareName).subscribe({
      next: (response) => {
        if (response.success) {
          this.showStatus(response.message || 'Firmware flashed successfully!', 'success', 10000);
        } else {
          this.showStatus(response.error || 'Flash failed', 'error');
        }
        this.isFlashing = false;
      },
      error: (err) => {
        const msg = err.error?.error || 'Failed to connect to server';
        this.showStatus(msg, 'error');
        this.isFlashing = false;
      }
    });
  }

  get selectedLocalFirmware(): LocalFirmwareFile | null {
    return this.localFirmwareFiles.find(file => file.name === this.selectedLocalFirmwareName) || null;
  }

  formatDate(isoDate: string): string {
    if (!isoDate) return '';
    try {
      return new Date(isoDate).toLocaleString();
    } catch {
      return isoDate;
    }
  }

  formatFileSize(bytes: number): string {
    if (!Number.isFinite(bytes) || bytes < 0) return '';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
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
