import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService, WifiNetwork } from '../../services/api.service';

@Component({
    selector: 'app-wifi-settings',
    standalone: true,
    imports: [CommonModule, FormsModule],
    templateUrl: './wifi-settings.component.html',
    styleUrls: ['./wifi-settings.component.css']
})
export class WifiSettingsComponent implements OnInit, OnDestroy {
    ssid: string = '';
    password: string = '';
    showPassword: boolean = false;
    networks: WifiNetwork[] = [];
    isLoading: boolean = false;
    isAdding: boolean = false;
    statusMessage: string = '';
    statusType: 'success' | 'error' | 'info' = 'info';
    private statusTimeout: any;

    // Confirmation dialog state
    showConfirmDialog: boolean = false;
    confirmNetworkName: string = '';

    constructor(private apiService: ApiService) { }

    ngOnInit(): void {
        this.loadNetworks();
    }

    ngOnDestroy(): void {
        if (this.statusTimeout) {
            clearTimeout(this.statusTimeout);
        }
    }

    loadNetworks(): void {
        this.isLoading = true;
        this.apiService.getWifiList().subscribe({
            next: (response) => {
                if (response.success) {
                    this.networks = response.networks || [];
                } else {
                    this.showStatus(response.error || 'Failed to load networks', 'error');
                }
                this.isLoading = false;
            },
            error: (err) => {
                this.showStatus('Failed to connect to server', 'error');
                this.isLoading = false;
            }
        });
    }

    addWifi(): void {
        if (!this.ssid.trim() || !this.password.trim()) {
            this.showStatus('Please enter both SSID and password', 'error');
            return;
        }

        this.isAdding = true;
        this.apiService.addWifi(this.ssid.trim(), this.password).subscribe({
            next: (response) => {
                if (response.success) {
                    this.showStatus(response.message || 'WiFi network added', 'success', 10000);
                    this.ssid = '';
                    this.password = '';
                    // Reload networks after a short delay
                    setTimeout(() => this.loadNetworks(), 2000);
                } else {
                    this.showStatus(response.error || 'Failed to add network', 'error');
                }
                this.isAdding = false;
            },
            error: (err) => {
                this.showStatus('Failed to connect to server', 'error');
                this.isAdding = false;
            }
        });
    }

    removeNetwork(name: string): void {
        this.confirmNetworkName = name;
        this.showConfirmDialog = true;
    }

    confirmDelete(): void {
        const name = this.confirmNetworkName;
        this.showConfirmDialog = false;
        this.confirmNetworkName = '';

        this.apiService.removeWifi(name).subscribe({
            next: (response) => {
                if (response.success) {
                    this.showStatus(response.message || 'Network removed', 'success');
                    this.loadNetworks();
                } else {
                    this.showStatus(response.error || 'Failed to remove network', 'error');
                }
            },
            error: (err) => {
                this.showStatus('Failed to connect to server', 'error');
            }
        });
    }

    cancelDelete(): void {
        this.showConfirmDialog = false;
        this.confirmNetworkName = '';
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
