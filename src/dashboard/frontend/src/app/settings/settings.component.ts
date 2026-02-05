import { Component, EventEmitter, Input, Output, OnChanges, SimpleChanges, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CalibrationComponent, CalibrationStep } from './calibration/calibration.component';
import { WifiSettingsComponent } from './wifi-settings/wifi-settings.component';
import { UpdateSettingsComponent } from './update-settings/update-settings.component';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [CommonModule, CalibrationComponent, WifiSettingsComponent, UpdateSettingsComponent],
  templateUrl: './settings.component.html',
  styleUrls: ['./settings.component.css']
})

export class SettingsComponent implements OnChanges, OnDestroy {
  @Input() open: boolean = false;
  @Output() close = new EventEmitter<void>();

  // Calibration state
  showCalibration: boolean = false;
  requestCalibrationExit: boolean = false;

  // WiFi settings state
  showWifiSettings: boolean = false;

  // Update settings state
  showUpdateSettings: boolean = false;

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['open']) {
      if (this.open) {
        // Disable page scroll when modal opens
        document.body.style.overflow = 'hidden';
      } else {
        // Re-enable page scroll when modal closes
        document.body.style.overflow = '';
        // Reset internal state when modal closes
        this.resetState();
      }
    }
  }

  private resetState(): void {
    // Close any open tabs/sections
    this.showCalibration = false;
    this.showWifiSettings = false;
    this.showUpdateSettings = false;
    this.requestCalibrationExit = false;
    this.pendingClose = false;
  }

  ngOnDestroy(): void {
    // Ensure scroll is re-enabled if component is destroyed while modal is open
    document.body.style.overflow = '';
  }

  // Calibration methods
  startCalibration(): void {
    // Show the calibration modal (WebSocket communication is now handled by the calibration component)
    this.showCalibration = true;
  }

  onCalibrationClose(): void {
    // Request calibration component to exit (this will send exit signal to backend)
    this.requestCalibrationExit = true;
  }

  onCalibrationExited(): void {
    // Reset the exit request and hide the calibration modal
    setTimeout(() => {
      this.requestCalibrationExit = false;
      this.showCalibration = false;

      // If we were waiting to close the settings modal, do it now
      if (this.pendingClose) {
        this.pendingClose = false;
        this.close.emit();
      }
    });
  }

  onCalibrationComplete(): void {
    setTimeout(() => {
      this.showCalibration = false;
    });
  }

  // Track if we're waiting to close the modal after calibration exits
  private pendingClose: boolean = false;

  // Handle modal close - check if calibration is active first
  handleClose(): void {
    if (this.showCalibration) {
      // If calibration is active, request exit first
      this.pendingClose = true;
      this.onCalibrationClose();
    } else {
      // Safe to close immediately
      this.close.emit();
    }
  }
}


