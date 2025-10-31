import { Component, EventEmitter, Input, Output, OnInit, OnDestroy, OnChanges, SimpleChanges, AfterViewChecked } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CALIBRATION_STEPS, registerFunction } from './calibration-steps.data';
import { WebSocketService } from '../../webSocket/web-socket.service';
import { ClusterService } from '../../cluster/cluster.service';
import { Subscription } from 'rxjs';
import { take } from 'rxjs/operators';

export interface CalibrationButton {
  enable: boolean;
  text: string;
  action?: 'submit' | 'navigateTo' | 'function' | 'functionAndNavigateTo';
  navigateTo?: string;
  function?: (...args: any[]) => void;
  functions?: ((...args: any[]) => void)[];
}

export interface CalibrationStep {
  id: string;
  title?: string;
  description: {
    enable: boolean;
    text: string;
  };
  image: {
    enable: boolean;
    svgPath: string;
  };
  inputs: {
    enable: boolean;
    fields: CalibrationInput[];
  };
  buttons: CalibrationButton[];
  substeps?: CalibrationStep[];
}

export interface CalibrationInput {
  id: string;
  label: string;
  type: 'text' | 'number' | 'select';
  value: any;
  options?: string[];
  required?: boolean;
}

@Component({
  selector: 'app-calibration',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './calibration.component.html',
  styleUrls: ['./calibration.component.css']
})
export class CalibrationComponent implements OnInit, OnDestroy, OnChanges, AfterViewChecked {
  @Input() show: boolean = false;
  @Input() shouldExit: boolean = false;
  @Output() close = new EventEmitter<void>();
  @Output() complete = new EventEmitter<void>();
  @Output() exited = new EventEmitter<void>();

  currentStepIndex: number = 0;
  currentSubstepId: string | null = null;
  calibrationSteps: CalibrationStep[] = CALIBRATION_STEPS;
  private subscriptions: Subscription = new Subscription();
  isCalibrationInProgress: boolean = false;
  currentSteeringAngle: number = 15; // Default steering angle in degrees
  currentSpeed: number = 0; // Default speed in cm/s
  calibrationDoneReceived: boolean = false; // Track if calibration_done message was received
  pendingMeasurementSubmission: { direction: string, navigateTarget: string } | null = null; // Track pending submission
  isCalibrationRunInProgress: boolean = false; // Track if a calibration run is currently executing
  private previousKlValue: string = '0'; // Store KL value before calibration starts
  private previousStepIndex: number = 0;
  private previousSubstepId: string | null = null;
  
  // Track completion status for each calibration type
  leftCompleted: boolean = false;
  rightCompleted: boolean = false;
  backwardCompleted: boolean = false;
  testRunCompleted: boolean = false;
  calibrationSavedSuccessfully: boolean = false;
  
  // Polynomial visualization data
  polynomialDataAvailable: boolean = false;
  speedPolynomialData: any = null;
  steerPolynomialData: any = null;
  limitPointsData: any = null;
  zeroOffsetSplineData: any = null;
  correctedSteer: number | null = null;
  
  // Chart zoom modal
  showChartModal: boolean = false;
  zoomedChartType: string = '';

  constructor(private webSocketService: WebSocketService, private clusterService: ClusterService) {}


  updateSteeringAngle(angle: number): void {
    this.currentSteeringAngle = angle;
  }

  conditionalNavigate(navigationFn: (component: CalibrationComponent) => string): void {
    const target = navigationFn(this);

    if (target === '..parent') {
      this.currentSubstepId = null;
      this.isCalibrationInProgress = false;
    } else {
      this.goToSubstep(target);
    }
  }

  processTextTemplate(text: string): string {
    let processedText = text.replace(/\{steeringAngle\}/g, this.currentSteeringAngle.toString());
    processedText = processedText.replace(/\{speed\}/g, (this.currentSpeed / 10).toString()); // Convert mm/s to cm/s for display
    processedText = processedText.replace(/\{incompleteCalibMessage\}/g, this.getIncompleteCalibMessage());
    processedText = processedText.replace(/\{incompleteBackwardMessage\}/g, this.getIncompleteBackwardMessage());
    processedText = processedText.replace(/\{incompleteSaveMessage\}/g, this.getIncompleteSaveMessage());
    processedText = processedText.replace(/\{visualizationMessage\}/g, this.getVisualizationMessage());
    processedText = processedText.replace(/\{zeroOffsetMessage\}/g, this.getZeroOffsetMessage());
    return processedText;
  }
  
  getVisualizationMessage(): string {
    if (!this.leftCompleted || !this.rightCompleted || !this.testRunCompleted || !this.backwardCompleted) {
      return 'You must complete Left, Right, Test Run and Backward calibration before viewing the polynomial plots. Please go back and complete the calibration runs.';
    }
    
    if (!this.polynomialDataAvailable) {
      return 'Click "Load Plots" to visualize the calibration polynomial functions for Speed and Steering.';
    }
    
    return 'Below are the polynomial functions fitted to your calibration data.';
  }

  getZeroOffsetMessage(): string {
    if (!this.leftCompleted || !this.rightCompleted || !this.testRunCompleted) {
      const incomplete: string[] = [];
      if (!this.leftCompleted) incomplete.push('Left');
      if (!this.rightCompleted) incomplete.push('Right');
      if (!this.testRunCompleted) incomplete.push('Test Run');
      
      let incompleteText: string;
      if (incomplete.length === 1) {
        incompleteText = incomplete[0];
      } else if (incomplete.length === 2) {
        incompleteText = incomplete.join(' and ');
      } else {
        incompleteText = incomplete.slice(0, -1).join(', ') + ' and ' + incomplete[incomplete.length - 1];
      }
      return `You must complete ${incompleteText} calibration before viewing the 0-offset spline.`;
    }
    
    if (!this.zeroOffsetSplineData) {
      return 'Click "Load Plot" to visualize the spline used for the zero offset calculation.';
    }
    
    return 'This plot shows the cubic spline used to determine the steering offset. This helps to correct any mechanical misalignments in the steering assembly.';
  }

  getIncompleteCalibMessage(): string {
    const incomplete: string[] = [];
    if (!this.leftCompleted) incomplete.push('Left');
    if (!this.rightCompleted) incomplete.push('Right');
    
    if (incomplete.length === 0) {
      return 'Position the vehicle as illustrated. Ensure it is on a level surface with the wheels aligned straight.';
    }
    
    let incompleteText: string;
    if (incomplete.length === 1) {
      incompleteText = incomplete[0];
    } else {
      incompleteText = incomplete.join(' and ');
    }
    
    return 'You must complete ' + incompleteText + ' calibration before you can run the test.';
  }

  getIncompleteBackwardMessage(): string {
    const incomplete: string[] = [];
    if (!this.leftCompleted) incomplete.push('Left');
    if (!this.rightCompleted) incomplete.push('Right');
    if (!this.testRunCompleted) incomplete.push('Test Run');
    
    if (incomplete.length === 0) {
      return 'Position the vehicle as illustrated. Ensure it is on a level surface with the wheels aligned straight. The vehicle will move backward at different speeds with straight steering.';
    }
    
    let incompleteText: string;
    if (incomplete.length === 1) {
      incompleteText = incomplete[0];
    } else if (incomplete.length === 2) {
      incompleteText = incomplete.join(' and ');
    } else {
      incompleteText = incomplete.slice(0, -1).join(', ') + ' and ' + incomplete[incomplete.length - 1];
    }
    
    return 'You must complete ' + incompleteText + ' before you can run backward calibration.';
  }

  getIncompleteSaveMessage(): string {
    const incomplete: string[] = [];
    if (!this.leftCompleted) incomplete.push('Left calibration');
    if (!this.rightCompleted) incomplete.push('Right calibration');
    if (!this.backwardCompleted) incomplete.push('Backward calibration');
    if (!this.testRunCompleted) incomplete.push('Test Run');
    
    if (incomplete.length === 0) {
      return 'Save the new calibration settings.';
    }
    
    let incompleteText: string;
    if (incomplete.length === 1) {
      incompleteText = incomplete[0];
    } else if (incomplete.length === 2) {
      incompleteText = incomplete.join(' and ');
    } else {
      incompleteText = incomplete.slice(0, -1).join(', ') + ' and ' + incomplete[incomplete.length - 1];
    }
    
    return 'You must complete ' + incompleteText + ' before you can save.';
  }

  getStepTitle(): string {
    const step = this.calibrationSteps[this.currentStepIndex];
    const title = step.title || '';
    
    if (!this.currentSubstepId) {
      if (this.currentStepIndex === 1 && this.leftCompleted) {
        return title + ' - Completed';
      }
      if (this.currentStepIndex === 2 && this.rightCompleted) {
        return title + ' - Completed';
      }
      if (this.currentStepIndex === 3 && this.testRunCompleted) {
        return title + ' - Completed';
      }
      if (this.currentStepIndex === 5 && this.backwardCompleted) {
        return title + ' - Completed';
      }
    }
    
    return title;
  }

  ngOnInit(): void {
    this.previousStepIndex = this.currentStepIndex;
    this.previousSubstepId = this.currentSubstepId;
    registerFunction('sendWebSocketMessage', (message: string) => this.webSocketService.sendMessageToFlask(JSON.stringify(message)));
    registerFunction('updateSteeringAngle', (angle: number) => this.updateSteeringAngle(angle));
    registerFunction('conditionalNavigate', (navigationFn: (component: CalibrationComponent) => string) => this.conditionalNavigate(navigationFn));
    registerFunction('resetCalibrationDoneFlag', () => { this.calibrationDoneReceived = false; });
    registerFunction('submitMeasurements', (inputs: any, direction: string, fallbackTarget: string) => this.submitMeasurements(inputs, direction, fallbackTarget));
    registerFunction('setCalibrationRunInProgress', (inProgress: boolean) => { this.isCalibrationRunInProgress = inProgress; });
    registerFunction('requestPolynomialData', () => this.requestPolynomialData());
    registerFunction('requestZeroOffsetSplineData', () => this.requestZeroOffsetSplineData());

    this.subscriptions.add(
      this.webSocketService.receiveCalibrationData().subscribe(event => {
        if (event.action === 'current_angle') {
          this.currentSteeringAngle = event.data;
        } else if (event.action === 'current_speed') {
          this.currentSpeed = event.data;
        } else if (event.action === 'calibration_done') {
          this.calibrationDoneReceived = true;
          
          if (this.pendingMeasurementSubmission) {
            this.currentSubstepId = null;
            this.isCalibrationInProgress = false;
            this.pendingMeasurementSubmission = null;
            
            this.requestCalibrationStatus();
          }
        } else if (event.action === 'measurements_received') {
          if (this.pendingMeasurementSubmission) {
            this.goToSubstep(this.pendingMeasurementSubmission.navigateTarget);
            this.pendingMeasurementSubmission = null;
          }
        } else if (event.action === 'direction_sequence_done') {
        } else if (event.action === 'calibration_run_done') {
          this.isCalibrationRunInProgress = false;
          
          if (event.corrected_steer !== undefined && event.corrected_steer !== null) {
            this.correctedSteer = event.corrected_steer;
          }
        } else if (event.action === 'calibration_status') {
          this.leftCompleted = event.left || false;
          this.rightCompleted = event.right || false;
          this.backwardCompleted = event.backward || false;
          this.testRunCompleted = event.test_run || false;
        } else if (event.action === 'test_run_done') {
          this.testRunCompleted = true;
          this.isCalibrationRunInProgress = false;
        } else if (event.action === 'calibration_saved') {
          if (event.success) {
            this.calibrationSavedSuccessfully = true;
            
            if (event.zipData) {
              this.downloadZipFile(event.zipData);
            }
            
            setTimeout(() => {
              this.calibrationSavedSuccessfully = false;
            }, 3000);
          }
        } else if (event.action === 'polynomial_data') {
          this.polynomialDataAvailable = event.hasData || false;
          this.speedPolynomialData = event.speedData;
          this.steerPolynomialData = event.steerData;
          this.limitPointsData = event.limitPointsData;
          
          if (this.polynomialDataAvailable) {
            setTimeout(() => {
              this.renderPolynomialCharts();
            }, 100);
          }
        } else if (event.action === 'zero_offset_spline_data') {
          this.zeroOffsetSplineData = event.zeroOffsetData;
          
          if (this.zeroOffsetSplineData) {
            setTimeout(() => {
              this.renderZeroOffsetSplineChart();
            }, 100);
          }
        }
      })
    );
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
  }

  ngAfterViewChecked(): void {
    if (this.previousStepIndex !== this.currentStepIndex || this.previousSubstepId !== this.currentSubstepId) {
      setTimeout(() => {
        if (this.currentStepIndex === 4 && this.zeroOffsetSplineData) {
          this.renderZeroOffsetSplineChart();
        }
        if (this.currentStepIndex === 6 && this.polynomialDataAvailable) {
          this.renderPolynomialCharts();
        }
      }, 0);
      this.previousStepIndex = this.currentStepIndex;
      this.previousSubstepId = this.currentSubstepId;
    }
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['show'] && changes['show'].currentValue === true) {
      this.sendCalibrationStartSignal();
    }

    if (changes['shouldExit'] && changes['shouldExit'].currentValue === true) {
      this.exitCalibration();
      this.exited.emit();
      this.isCalibrationInProgress = false;
    }
  }

  nextStep(): void {
    if (this.currentSubstepId) {
      this.currentSubstepId = null;
      this.isCalibrationInProgress = false;
    }

    if (this.currentStepIndex < this.calibrationSteps.length - 1) {
      this.currentStepIndex++;
      this.resetInputFields();
      
      if (this.currentStepIndex >= 1 && this.currentStepIndex <= 6) {
        this.requestCalibrationStatus();
      }
    }
  }

  previousStep(): void {
    this.currentSubstepId = null;
    this.isCalibrationInProgress = false;

    if (this.currentStepIndex > 0) {
      this.currentStepIndex--;
      this.resetInputFields();
      
      if (this.currentStepIndex >= 1 && this.currentStepIndex <= 6) {
        this.requestCalibrationStatus();
      }
    }
  }

  goToSubstep(stepId: string): void {
    this.currentSubstepId = stepId;

    if (((this.currentStepIndex >= 1 && this.currentStepIndex <= 3) || this.currentStepIndex === 5) && stepId.includes('_substep')) {
      this.isCalibrationInProgress = true;
    }

    this.resetInputFields();
  }

  private sendCalibrationStartSignal(): void {
    this.calibrationDoneReceived = false;
    this.leftCompleted = false;
    this.rightCompleted = false;
    this.backwardCompleted = false;
    this.testRunCompleted = false;
    this.calibrationSavedSuccessfully = false;
    this.correctedSteer = null;

    this.clusterService.kl$.pipe(take(1)).subscribe(currentKl => {
      this.previousKlValue = currentKl;
    });
    
    this.clusterService.updateKL('30');
    this.webSocketService.sendMessageToFlask(`{"Name": "Klem", "Value": "30"}`);

    const calibrationSignal = {
      Name: 'Calibration',
      Action: 'start',
    };

    this.webSocketService.sendMessageToFlask(JSON.stringify(calibrationSignal));
  }

  exitCalibration(): void {
    this.clusterService.updateKL(this.previousKlValue);
    this.webSocketService.sendMessageToFlask(`{"Name": "Klem", "Value": "${this.previousKlValue}"}`);

    const exitSignal = {
      Name: 'Calibration',
      Action: 'exit',
    };

    this.webSocketService.sendMessageToFlask(JSON.stringify(exitSignal));

    this.currentStepIndex = 0;
    this.close.emit();
  }

  completeCalibration(): void {
    this.clusterService.updateKL(this.previousKlValue);
    this.webSocketService.sendMessageToFlask(`{"Name": "Klem", "Value": "${this.previousKlValue}"}`);

    const completionSignal = {
      Name: 'Calibration',
      Action: 'complete',
    };

    this.webSocketService.sendMessageToFlask(JSON.stringify(completionSignal));

    this.isCalibrationInProgress = false;
    this.complete.emit();
    this.currentStepIndex = 0;
  }

  get currentStep(): CalibrationStep {
    if (this.currentSubstepId) {
      const mainStep = this.calibrationSteps[this.currentStepIndex];
      return mainStep.substeps?.find(s => s.id === this.currentSubstepId) || mainStep;
    }
    return this.calibrationSteps[this.currentStepIndex];
  }

  get isFirstStep(): boolean {
    return this.currentStepIndex === 0 && !this.currentSubstepId;
  }

  get isLastStep(): boolean {
    const onLastMainStep = this.currentStepIndex === this.calibrationSteps.length - 1;
    if (!onLastMainStep) return false;

    const mainStep = this.calibrationSteps[this.currentStepIndex];
    if (!mainStep.substeps || mainStep.substeps.length === 0) {
      return true;
    }
    
    if (this.currentSubstepId) {
      const lastSubstep = mainStep.substeps[mainStep.substeps.length - 1];
      return this.currentSubstepId === lastSubstep.id;
    }

    return false;
  }

  get progressPercentage(): number {
    return ((this.currentStepIndex + 1) / this.calibrationSteps.length) * 100;
  }

  isButtonDisabledDuringRun(buttonText: string): boolean {
    return this.isCalibrationRunInProgress &&
           (buttonText.includes('Re-run') ||
            buttonText.includes('Submit Measurements') ||
            buttonText === 'Left' ||
            buttonText === 'Right' ||
            buttonText === 'Straight' ||
            buttonText === 'Left/Right');
  }

  get allCalibrationsCompleted(): boolean {
    return this.leftCompleted && this.rightCompleted && this.testRunCompleted && this.backwardCompleted;
  }

  isSaveButtonDisabled(): boolean {
    return !this.allCalibrationsCompleted;
  }

  isTestRunButtonDisabled(): boolean {
    return !(this.leftCompleted && this.rightCompleted);
  }

  isBackwardButtonDisabled(): boolean {
    return !(this.leftCompleted && this.rightCompleted && this.testRunCompleted);
  }

  isZeroOffsetSplineButtonDisabled(): boolean {
    return !(this.leftCompleted && this.rightCompleted && this.testRunCompleted);
  }

  isVisualizationButtonDisabled(): boolean {
    return !this.allCalibrationsCompleted;
  }

  requestCalibrationStatus(): void {
    this.webSocketService.sendMessageToFlask(JSON.stringify({
      Name: 'Calibration',
      Action: 'get_status'
    }));
  }

  private resetInputFields(): void {
    if (this.currentStep.inputs.enable && this.currentStep.inputs.fields.length > 0) {
      this.currentStep.inputs.fields.forEach(field => {
        if (field.id.includes('distance')) {
          field.value = 0;
        }
      });
    }
  }

  onImageError(event: Event): void {
    const target = event.target as HTMLImageElement;
    if (target) {
      target.style.display = 'none';
    }
  }

  submitStep(button: CalibrationButton, inputFields?: CalibrationInput[]): void {
    if (button.action === 'function' || button.action === 'functionAndNavigateTo') {
      const fieldsToUse = inputFields || this.currentStep.inputs.fields;
      const currentInputs: { [key: string]: any } = fieldsToUse.reduce((acc: { [key: string]: any }, field) => {
        acc[field.id] = field.value;
        return acc;
      }, {});

      if (button.functions && button.functions.length > 0) {
        button.functions.forEach(fn => {
          if (typeof fn === 'function') {
            try {
              fn(currentInputs);
            } catch (error) {
              fn();
            }
          }
        });
      }
      else if (button.function) {
        try {
          button.function(currentInputs);
        } catch (error) {
          button.function();
        }
      }
    }

    if ((button.action === 'navigateTo' || button.action === 'functionAndNavigateTo') && button.navigateTo) {
      if (button.navigateTo === '..parent') {
        this.currentSubstepId = null;
        this.isCalibrationInProgress = false;
      } else {
        const mainStepIndex = this.calibrationSteps.findIndex(step => step.id === button.navigateTo);
        if (mainStepIndex !== -1) {
          this.currentStepIndex = mainStepIndex;
          this.currentSubstepId = null;
          this.isCalibrationInProgress = false;
          
          if (this.currentStepIndex >= 1 && this.currentStepIndex <= 6) {
            this.requestCalibrationStatus();
          }
        } else {
          this.goToSubstep(button.navigateTo);
        }
      }
    }
  }

  onNumberInput(event: Event, field: CalibrationInput): void {
    const inputElement = event.target as HTMLInputElement;
    const originalValue = inputElement.value;
    const sanitizedValue = originalValue.replace(/[^0-9]/g, '');

    if (originalValue !== sanitizedValue) {
      inputElement.value = sanitizedValue;
    }

    field.value = sanitizedValue === '' ? null : Number(sanitizedValue);

    if (field.id === 'steeringAngle' && field.value !== null) {
      this.currentSteeringAngle = field.value;
    }
  }

  submitMeasurements(inputs: any, direction: string, fallbackTarget: string): void {
    this.webSocketService.sendMessageToFlask(JSON.stringify({
      Name: 'Calibration',
      Action: 'current_angle',
      Direction: direction
    }));
    
    let distances: any;
    if (direction === 'backward') {
      distances = {
        d: inputs['distance']
      };
    } else {
      distances = {
        d1: inputs['distance1'],
        d2: inputs['distance2'],
        d3: inputs['distance3']
      };
    }
    
    this.webSocketService.sendMessageToFlask(JSON.stringify({
      Name: 'Calibration',
      Action: 'submit_measurements',
      Distances: distances,
      Direction: direction
    }));

    this.pendingMeasurementSubmission = { direction, navigateTarget: fallbackTarget };
  }

  downloadZipFile(base64Data: string): void {
    try {
      const byteCharacters = atob(base64Data);
      const byteNumbers = new Array(byteCharacters.length);
      for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
      }
      const byteArray = new Uint8Array(byteNumbers);
      const blob = new Blob([byteArray], { type: 'application/zip' });

      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
      link.download = `calibration-source-${timestamp}.zip`;
      
      document.body.appendChild(link);
      link.click();
      
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
    } catch (error) {
      console.error('Error downloading zip file:', error);
    }
  }

  requestPolynomialData(): void {
    this.webSocketService.sendMessageToFlask(JSON.stringify({
      Name: 'Calibration',
      Action: 'get_polynomial_data'
    }));
  }

  requestZeroOffsetSplineData(): void {
    this.webSocketService.sendMessageToFlask(JSON.stringify({
      Name: 'Calibration',
      Action: 'get_zero_offset_spline_data'
    }));
  }

  private evaluateSpline(splineData: any, x: number): number {
    const knots = splineData.knots;
    const coeffs = splineData.coefficients;
    
    let segment = -1;
    for (let i = 0; i < knots.length - 1; i++) {
      if (x >= knots[i] && x <= knots[i + 1]) {
        segment = i;
        break;
      }
    }
    
    if (segment === -1) {
      if (x < knots[0]) {
        segment = 0;
      } else {
        segment = knots.length - 2;
      }
    }
    
    const dx = x - knots[segment];
    const segCoeffs = coeffs[segment];
    
    return segCoeffs[0] * dx * dx * dx + 
           segCoeffs[1] * dx * dx + 
           segCoeffs[2] * dx + 
           segCoeffs[3];
  }

  renderPolynomialCharts(): void {
    if (this.speedPolynomialData) {
      this.renderChart('speedChart', this.speedPolynomialData, 'Speed', 'Actual Speed (cm/s)', 'PWM (μs)');
    }

    if (this.steerPolynomialData) {
      const steerData = { ...this.steerPolynomialData, limitPoints: this.limitPointsData?.points || [] };
      this.renderChart('steerChart', steerData, 'Steering', 'Actual Steering Angle (degrees)', 'PWM (μs)');
    }
  }

  renderZeroOffsetSplineChart(): void {
    if (this.zeroOffsetSplineData) {
      this.renderChart('zeroOffsetSplineChart', this.zeroOffsetSplineData, 'Zero Offset Spline', 'Actual Steer (degrees)', 'Desired Steer (degrees)');
    }
  }

  openChartModal(chartType: string): void {
    this.zoomedChartType = chartType;
    this.showChartModal = true;
    document.body.classList.add('modal-open');
    
    setTimeout(() => {
      if (chartType === 'speed' && this.speedPolynomialData) {
        this.renderChart('zoomedspeedChart', this.speedPolynomialData, 'Speed', 'Actual Speed (cm/s)', 'PWM (μs)');
      } else if (chartType === 'steer' && this.steerPolynomialData) {
        const steerData = { ...this.steerPolynomialData, limitPoints: this.limitPointsData?.points || [] };
        this.renderChart('zoomedsteerChart', steerData, 'Steering', 'Actual Steering Angle (degrees)', 'PWM (μs)');
      } else if (chartType === 'zeroOffsetSpline' && this.zeroOffsetSplineData) {
        this.renderChart('zoomedzeroOffsetSplineChart', this.zeroOffsetSplineData, 'Zero Offset Spline', 'Actual Steer (degrees)', 'Desired Steer (degrees)');
      }
    }, 50);
  }

  closeChartModal(): void {
    this.showChartModal = false;
    this.zoomedChartType = '';
    document.body.classList.remove('modal-open');
  }

  private renderChart(canvasId: string, data: any, title: string, xLabel: string, yLabel: string): void {
    const canvas = document.getElementById(canvasId) as HTMLCanvasElement;
    if (!canvas) {
      console.error(`Canvas element ${canvasId} not found`);
      return;
    }

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const splineData = data.spline;
    const allPoints = data.points;
    const error = data.error;

    if (!allPoints || allPoints.length === 0) {
      console.error(`No points found for chart ${canvasId}`);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = '#000';
      ctx.font = 'bold 16px Arial';
      ctx.textAlign = 'center';
      ctx.fillText('No calibration data available to plot.', canvas.width / 2, canvas.height / 2);
      return;
    }

    if (!splineData) {
      console.error(`No spline data found for chart ${canvasId}`);
      return;
    }

    const width = canvas.width;
    const height = canvas.height;
    const padding = 80;
    const chartWidth = width - 2 * padding;
    const chartHeight = height - 2 * padding;

    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, width, height);

    const xValues = allPoints.map((p: number[]) => p[0]);
    const yValues = allPoints.map((p: number[]) => p[1]);
    const xMin = Math.min(...xValues);
    const xMax = Math.max(...xValues);
    const yMin = Math.min(...yValues);
    const yMax = Math.max(...yValues);

    const xRange = xMax - xMin;
    const yRange = yMax - yMin;
    const xPadding = xRange * 0.1;
    const yPadding = yRange * 0.1;

    const xMinPadded = xMin - xPadding;
    const xMaxPadded = xMax + xPadding;
    const yMinPadded = yMin - yPadding;
    const yMaxPadded = yMax + yPadding;

    const scaleX = (x: number) => padding + ((x - xMinPadded) / (xMaxPadded - xMinPadded)) * chartWidth;
    const scaleY = (y: number) => height - padding - ((y - yMinPadded) / (yMaxPadded - yMinPadded)) * chartHeight;

    ctx.strokeStyle = '#333';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(padding, padding);
    ctx.lineTo(padding, height - padding);
    ctx.lineTo(width - padding, height - padding);
    ctx.stroke();

    ctx.strokeStyle = '#e0e0e0';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 10; i++) {
      const x = padding + (i / 10) * chartWidth;
      const y = height - padding - (i / 10) * chartHeight;
      
      ctx.beginPath();
      ctx.moveTo(x, padding);
      ctx.lineTo(x, height - padding);
      ctx.stroke();
      
      ctx.beginPath();
      ctx.moveTo(padding, y);
      ctx.lineTo(width - padding, y);
      ctx.stroke();
    }

    ctx.strokeStyle = '#0066ff';
    ctx.lineWidth = 3;
    ctx.beginPath();
    const numPoints = 300;
    for (let i = 0; i <= numPoints; i++) {
      const xVal = xMinPadded + (i / numPoints) * (xMaxPadded - xMinPadded);
      const yVal = this.evaluateSpline(splineData, xVal);
      const x = scaleX(xVal);
      const y = scaleY(yVal);
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.stroke();

    ctx.fillStyle = '#0066cc';
    for (const point of allPoints) {
      const x = scaleX(point[0]);
      const y = scaleY(point[1]);
      ctx.beginPath();
      ctx.arc(x, y, 5, 0, 2 * Math.PI);
      ctx.fill();
    }

    // Highlight limit points: vertical dashed line from x-axis (y=0) up to the point
    if (data.limitPoints && data.limitPoints.length > 0) {
      for (let i = 0; i < data.limitPoints.length; i++) {
        const point = data.limitPoints[i];
        const x = scaleX(point[0]);
        const y = scaleY(point[1]);
        // Dotted line from point down to x-axis
        ctx.setLineDash([5, 5]);
        ctx.strokeStyle = '#ff0000';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(x, y);
        ctx.lineTo(x, height - padding);
        ctx.stroke();
        ctx.setLineDash([]);
        // Highlight circle
        ctx.fillStyle = '#ff0000';
        ctx.beginPath();
        ctx.arc(x, y, 8, 0, 2 * Math.PI);
        ctx.fill();
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        ctx.stroke();
        // Add label below point
        ctx.fillStyle = '#000';
        ctx.font = 'bold 12px Arial';
        ctx.textAlign = 'center';
        const label = point[0] < 0 ? 'Max Left' : 'Max Right';
        ctx.fillText(label, x, y - 15);
      }
    }



    if ((title === 'Steering' || title === 'Speed' || title === 'Zero Offset Spline') && xMinPadded <= 0 && xMaxPadded >= 0) {
      const zeroY = this.evaluateSpline(splineData, 0);
      const x = scaleX(0);
      const y = scaleY(zeroY);
      
      ctx.setLineDash([5, 5]);
      ctx.strokeStyle = '#ff0000';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(x, height - padding);
      ctx.lineTo(x, y);
      ctx.stroke();
      ctx.setLineDash([]);
      
      ctx.fillStyle = '#ff0000';
      ctx.beginPath();
      ctx.arc(x, y, 8, 0, 2 * Math.PI);
      ctx.fill();
      
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 2;
      ctx.stroke();
      
      ctx.fillStyle = '#000';
      ctx.font = 'bold 11px Arial';
      ctx.textAlign = 'center';
      if (title === 'Steering' && this.correctedSteer !== null) {
        ctx.fillText(`0° (corrected: ${this.correctedSteer.toFixed(2)}°)`, x, y - 15);
      } else if (title === 'Steering') {
        ctx.fillText('0°', x, y - 15);
      } else if (title === 'Speed') {
        ctx.fillText('0 cm/s', x, y - 15);
      } else if (title === 'Zero Offset Spline') {
        ctx.fillText(`Offset: ${zeroY.toFixed(2)}°`, x, y - 15);
      }
    }

    // --- Render Legend ---
    const legendWidth = 150;
    const legendItemHeight = 20;
    const legendPadding = 10;
    let legendItems = 2; // Spline + Points

    if (title === 'Steering' && data.limitPoints && data.limitPoints.length > 0) {
      legendItems += data.limitPoints.length; // One for each limit point
    }
    if (title === 'Steering' && this.correctedSteer !== null) {
      legendItems++; // Steering Offset
    }
    
    // Recalculate height for non-steering charts to be more compact
    if (title !== 'Steering') {
      legendItems = 2; // Reset for non-steering charts
      if (title === 'Zero Offset Spline') legendItems++; // For offset value
    }

    const legendHeight = legendItems * legendItemHeight + legendPadding;

    let legendX, legendY;

    if (title === 'Steering' || title === 'Zero Offset Spline') {
      // Bottom-right for Steering and Zero Offset charts
      legendX = width - padding - legendWidth - 10;
      legendY = height - padding - legendHeight - 10;
    } else {
      // Top-right for other charts
      legendX = width - padding - legendWidth - 10;
      legendY = padding + 10;
    }

    // Legend Background
    ctx.fillStyle = 'rgba(255, 255, 255, 0.85)';
    ctx.strokeStyle = '#ccc';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.roundRect(legendX, legendY, legendWidth, legendHeight, 5);
    ctx.fill();
    ctx.stroke();

    let legendCurrentY = legendY + legendPadding / 2;
    const legendTextX = legendX + 35;
    const legendSymbolX = legendX + 15;

    ctx.font = 'bold 12px Arial';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';

    // Fitted Spline
    legendCurrentY += legendItemHeight / 2;
    ctx.strokeStyle = '#0066ff';
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(legendSymbolX - 5, legendCurrentY);
    ctx.lineTo(legendSymbolX + 15, legendCurrentY);
    ctx.stroke();
    ctx.fillStyle = '#000';
    ctx.fillText('Fitted Spline', legendTextX, legendCurrentY);
    legendCurrentY += legendItemHeight;

    // Calibration Points
    ctx.fillStyle = '#0066cc';
    ctx.beginPath();
    ctx.arc(legendSymbolX, legendCurrentY, 5, 0, 2 * Math.PI);
    ctx.fill();
    ctx.fillStyle = '#000';
    ctx.fillText('Calibration Points', legendTextX, legendCurrentY);
    legendCurrentY += legendItemHeight;

    // Limit Points (for steer chart)
    if (title === 'Steering' && data.limitPoints && data.limitPoints.length > 0) {
      // Sort points to show left (negative) then right (positive)
      const sortedLimitPoints = [...data.limitPoints].sort((a, b) => a[0] - b[0]);

      for (const point of sortedLimitPoints) {
        const angle = point[0] / 10; // Unscale from backend
        const label = angle < 0 ? 'Max Left' : 'Max Right';

        ctx.fillStyle = '#ff0000';
        ctx.beginPath();
        ctx.arc(legendSymbolX, legendCurrentY, 5, 0, 2 * Math.PI);
        ctx.fill();
        ctx.fillStyle = '#000';
        ctx.fillText(`${label}: ${angle.toFixed(1)}°`, legendTextX, legendCurrentY);
        legendCurrentY += legendItemHeight;
      }
    }

    // Steering Offset for Steering Chart
    if (title === 'Steering' && this.correctedSteer !== null) {
      ctx.fillStyle = '#000';
      ctx.fillText(`Offset: ${this.correctedSteer.toFixed(2)}°`, legendTextX - 20, legendCurrentY);
    }

    // Zero Crossing for Zero Offset Spline Chart
    if (title === 'Zero Offset Spline') {
      const zeroY = this.evaluateSpline(splineData, 0);
      ctx.fillStyle = '#000';
      ctx.fillText(`Offset: ${zeroY.toFixed(2)}°`, legendTextX - 20, legendCurrentY);
    }

    ctx.fillStyle = '#000';
    ctx.font = 'bold 16px Arial';
    ctx.textAlign = 'center';
    
    ctx.fillText(`${title} Calibration`, width / 2, 25);
    
    ctx.font = 'bold 14px Arial';
    ctx.fillText(xLabel, width / 2, height - 15);
    
    ctx.save();
    ctx.translate(15, height / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText(yLabel, 0, 0);
    ctx.restore();

    ctx.font = 'bold 12px Arial';
    ctx.textAlign = 'center';
    ctx.fillStyle = '#000';
    
    for (let i = 0; i <= 10; i++) {
      const xVal = xMinPadded + (i / 10) * (xMaxPadded - xMinPadded);
      const x = scaleX(xVal);
      
      const displayValue = title === 'Steering' ? xVal / 10 : (title === 'Speed' ? xVal / 10 : xVal);
      ctx.fillText(displayValue.toFixed(1), x, height - padding + 20);
    }
    
    if (xMinPadded <= 0 && xMaxPadded >= 0) {
      const x = scaleX(0);
      ctx.fillStyle = '#ff0000';
      ctx.font = 'bold 14px Arial';
      ctx.fillText('0', x, height - padding + 20);
    }
    
    ctx.fillStyle = '#000';
    ctx.textAlign = 'right';
    for (let i = 0; i <= 10; i++) {
      const yVal = yMinPadded + (i / 10) * (yMaxPadded - yMinPadded);
      const y = scaleY(yVal);
      ctx.fillText(yVal.toFixed(0), padding - 10, y + 5);
    }
  }
}