import { Component, ViewChild } from '@angular/core';
import { HeaderComponent } from './header/header.component';
import { ClusterComponent } from './cluster/cluster.component';
import { FormsModule } from '@angular/forms';
import { WebSocketService } from './webSocket/web-socket.service';
import { TableComponent } from './table/table.component';
import { CommonModule } from '@angular/common'
import * as CryptoJS from 'crypto-js'; 

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [HeaderComponent, TableComponent, ClusterComponent, FormsModule, CommonModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent {

  title: string = 'dashboard';
  correctPassword = 'U2FsdGVkX18Lrd7U4IqjmFUNVH7aGbw7SPsLXHb2qlU='; // Encrypted password (AES encrypted "")
  private secretKey = 'ThisIsTheKey'; // Secret key for decryption
  cursorRotationSliderValue: number = 0;
  carPositionSliderValue: number = 0;
  carLeftLaneOn: boolean = false;
  carRightLaneOn: boolean = false;
  clusterLightType: string = '';
  private intervalId: any;

  enteredPassword = ''; // User input password
  
  isAuthenticated = false; // Controls whether the content is displayed or not

  @ViewChild(ClusterComponent) clusterComponent!: ClusterComponent;
  @ViewChild(TableComponent) tableComponent!: TableComponent;

  constructor( private webSocketService: WebSocketService) { }

  ngOnInit() {
    //To enable all the NUCLEO futures uncomment this fc:
    //this.startNUCLEOFunctions()
  }

  ngOnDestroy() {
    this.webSocketService.disconnectSocket();
  }

  submit(): void {
    if (this.clusterComponent) {
      this.clusterComponent.setWarningLightType(this.clusterLightType); 
    }   
  }

  decryptPassword(encryptedPassword: string): string {
    const bytes = CryptoJS.AES.decrypt(encryptedPassword, this.secretKey);
    return bytes.toString(CryptoJS.enc.Utf8); // Return decrypted password
  }

  submitPassword() {
    const decryptedCorrectPassword = this.decryptPassword(this.correctPassword);
    
    console.log('Decrypted Password:', decryptedCorrectPassword);
    if (this.enteredPassword=== decryptedCorrectPassword) {
      this.isAuthenticated = true;
    } else {
      alert('Incorrect password!');
    }
  }

  startInfiniteLoop(): void {
    let speed = 0;
    let steer = 0;
    let speedDirection = 1;  // 1 means increasing, -1 means decreasing
    let steerDirection = 1;
  
    this.intervalId = setInterval(() => {
      // Update speed value
      speed += speedDirection * 10; // Change speed in steps of 10
      if (speed >= 50 || speed <= -50) {
        speedDirection *= -1; // Reverse the direction of change
      }
  
      // Update steer value
      steer += steerDirection * 5; // Change steer in steps of 5
      if (steer >= 20 || steer <= -20) {
        steerDirection *= -1; // Reverse the direction of change
      }
  
      // Send the updated messages
      this.sendMessage(`{"Name": "SpeedMotor", "Value": "${speed.toFixed(1)}"}`);
      this.sendMessage(`{"Name": "SteerMotor", "Value": "${steer.toFixed(1)}"}`);
    }, 1000); // 1000ms = 1 second
  }
  
  startNUCLEOFunctions()
  {
    this.sendMessage("{\"Name\": \"ToggleInstant\", \"Value\": 1}")
    this.sendMessage("{\"Name\": \"ToggleBatteryLvl\", \"Value\": 1}")
    this.sendMessage("{\"Name\": \"ToggleImuData\", \"Value\": 1}")
    this.sendMessage("{\"Name\": \"ToggleResourceMonitor\", \"Value\": 1}")
  }

  sendMessage(message: string) {
    this.webSocketService.sendMessageToFlask(message);
  }
}
