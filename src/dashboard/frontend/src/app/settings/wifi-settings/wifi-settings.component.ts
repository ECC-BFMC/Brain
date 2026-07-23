import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService, WifiAccessPoint, WifiNetwork } from '../../services/api.service';

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
    availableNetworks: WifiAccessPoint[] = [];
    selectedAccessPoint?: WifiAccessPoint;
    isLoading: boolean = false;
    isScanning: boolean = false;
    scanError: string = '';
    isAdding: boolean = false;
    statusMessage: string = '';
    statusType: 'success' | 'error' | 'info' = 'info';
    private statusTimeout: any;
    private operationPollTimeout: any;

    // Confirmation dialog state
    showConfirmDialog: boolean = false;
    confirmNetworkName: string = '';
    confirmNetworkId: string = '';

    constructor(private apiService: ApiService) { }

    ngOnInit(): void {
        this.loadNetworks();
        this.scanNetworks();
    }

    ngOnDestroy(): void {
        if (this.statusTimeout) {
            clearTimeout(this.statusTimeout);
        }
        if (this.operationPollTimeout) {
            clearTimeout(this.operationPollTimeout);
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

    scanNetworks(): void {
        this.isScanning = true;
        this.scanError = '';
        this.apiService.scanWifiNetworks().subscribe({
            next: (response) => {
                if (response.success) {
                    this.availableNetworks = response.networks || [];
                } else {
                    this.scanError = response.error || 'Failed to scan for networks';
                }
                this.isScanning = false;
            },
            error: (err) => {
                this.scanError = err?.error?.error || 'Failed to scan for networks';
                this.isScanning = false;
            }
        });
    }

    selectNetwork(network: WifiAccessPoint): void {
        if (this.isAdding) {
            return;
        }
        this.selectedAccessPoint = network;
        this.ssid = network.ssid;
        this.password = '';
    }

    onSsidChanged(value: string): void {
        if (this.selectedAccessPoint?.ssid !== value) {
            this.selectedAccessPoint = undefined;
        }
    }

    requiresPassword(): boolean {
        return this.selectedAccessPoint?.secured !== false;
    }

    addWifi(): void {
        if (!this.ssid.trim() || (this.requiresPassword() && !this.password)) {
            this.showStatus(
                this.requiresPassword()
                    ? 'Please enter both SSID and password'
                    : 'Please select or enter a network',
                'error'
            );
            return;
        }

        this.isAdding = true;
        this.apiService.addWifi(
            this.ssid.trim(),
            this.password,
            !this.requiresPassword()
        ).subscribe({
            next: (response) => {
                if (response.success) {
                    this.showStatus(
                        response.message || 'WiFi profile saved; connecting...',
                        'info',
                        60000
                    );
                    this.ssid = '';
                    this.password = '';
                    this.selectedAccessPoint = undefined;
                    if (response.operation_id) {
                        this.watchOperation(response.operation_id);
                    } else {
                        this.isAdding = false;
                        this.loadNetworks();
                        this.scanNetworks();
                    }
                } else {
                    this.showStatus(response.error || 'Failed to add network', 'error');
                    this.isAdding = false;
                }
            },
            error: (err) => {
                const message = err?.error?.error || 'Failed to connect to server';
                this.showStatus(message, 'error');
                this.isAdding = false;
            }
        });
    }

    removeNetwork(network: WifiNetwork): void {
        this.confirmNetworkName = network.name;
        this.confirmNetworkId = network.uuid;
        this.showConfirmDialog = true;
    }

    confirmDelete(): void {
        const name = this.confirmNetworkName;
        const identifier = this.confirmNetworkId;
        this.showConfirmDialog = false;
        this.confirmNetworkName = '';
        this.confirmNetworkId = '';

        this.apiService.removeWifi(identifier).subscribe({
            next: (response) => {
                if (response.success) {
                    if (response.operation_id && response.state !== 'completed') {
                        this.showStatus(
                            response.message || `Removing "${name}"...`,
                            'info',
                            60000
                        );
                        this.watchOperation(response.operation_id);
                    } else {
                        this.showStatus(response.message || 'Network removed', 'success');
                        this.loadNetworks();
                        this.scanNetworks();
                    }
                } else {
                    this.showStatus(response.error || 'Failed to remove network', 'error');
                }
            },
            error: (err) => {
                const message = err?.error?.error || 'Failed to connect to server';
                this.showStatus(message, 'error');
            }
        });
    }

    cancelDelete(): void {
        this.showConfirmDialog = false;
        this.confirmNetworkName = '';
        this.confirmNetworkId = '';
    }

    private watchOperation(operationId: string): void {
        this.isAdding = true;
        if (this.operationPollTimeout) {
            clearTimeout(this.operationPollTimeout);
        }

        this.apiService.getWifiOperation(operationId).subscribe({
            next: (response) => {
                const operation = response.operation;
                if (!response.success || !operation) {
                    this.finishOperation();
                    this.showStatus(response.error || 'WiFi operation could not be read', 'error');
                    return;
                }

                if (operation.state === 'connected' || operation.state === 'completed') {
                    this.finishOperation();
                    this.showStatus(operation.message, 'success', 10000);
                    this.loadNetworks();
                    this.scanNetworks();
                    return;
                }

                if (operation.state === 'failed') {
                    this.finishOperation();
                    this.showStatus(operation.message, 'error', 15000);
                    this.loadNetworks();
                    this.scanNetworks();
                    return;
                }

                this.showStatus(operation.message, 'info', 60000);
                this.operationPollTimeout = setTimeout(
                    () => this.watchOperation(operationId),
                    1000
                );
            },
            error: (err) => {
                if (err?.status === 404) {
                    this.finishOperation();
                    this.showStatus(
                        'The previous WiFi operation is no longer available. Showing the current network state.',
                        'info',
                        10000
                    );
                    this.loadNetworks();
                    this.scanNetworks();
                    return;
                }

                this.showStatus(
                    'The WiFi connection is changing. Reconnect to the car and reopen Settings to see the final result.',
                    'info',
                    60000
                );
                this.operationPollTimeout = setTimeout(
                    () => this.watchOperation(operationId),
                    3000
                );
            }
        });
    }

    private finishOperation(): void {
        this.isAdding = false;
        if (this.operationPollTimeout) {
            clearTimeout(this.operationPollTimeout);
            this.operationPollTimeout = undefined;
        }
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
