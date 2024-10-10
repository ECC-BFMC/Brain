import { Injectable } from '@angular/core';
import { Socket } from 'ngx-socket-io';
import { Observable, Subject } from 'rxjs';
@Injectable({
 providedIn: 'root',
})
export class WebSocketService {
  private webSocket: Socket;

  private eventSubject = new Subject<{ channel: string, data: any }>();
  private handledEvents = new Set([
    'memory_channel',
    'cpu_channel',
    'disk_channel',
    'webCamera',
    'Location',
    'Cars',
    'Semaphores',
    'after connect',
    'InstantConsumption',
    'loadBack',
    'WarningSignal',
    'response',
    'BatteryLvl',
    'ResourceMonitor',
    'serialCamera',
    'Recording',
    'CurrentSpeed',
    'CurrentSteer'
  ]);
  
 constructor() {

  this.webSocket = new Socket({
   url: "http://192.168.0.111:5005",
   options: {},
  });

  // Listen for all messages from the WebSocket server
  this.webSocket.onAny((eventName: string, data: any) => {
    if (!this.handledEvents.has(eventName)) {
      this.eventSubject.next({ channel: eventName, data });
    }
  });

 }

  // Method to start connection/handshake with the server
  sendMessageToFlask(message: any) {
    this.webSocket.emit('message', message);
  }

  SaveTable(message: any) {
    this.webSocket.emit('save', message);
  }

  LoadTable(message: any) {
    this.webSocket.emit('load', message);
  }

  // Method to receive memory usage updates
  receiveMemoryUsage(): Observable<any> {
    return this.webSocket.fromEvent('memory_channel');
  }

  receiveResourceMonitor(): Observable<any>{
    return this.webSocket.fromEvent('ResourceMonitor');
  }

  receiveWarningSignal(): Observable<any> {
    return this.webSocket.fromEvent('WarningSignal');
  }

  receiveLoadTable(): Observable<any> {
    return this.webSocket.fromEvent('loadBack');
  }

  // Method to receive CPU usage updates
  receiveCpuUsage(): Observable<any> {
    return this.webSocket.fromEvent('cpu_channel');
  }

  // Method to receive image updates
  receiveCamera(): Observable<any> {
    return this.webSocket.fromEvent('serialCamera');
  }

  // Method to receive location updates
  receiveLocation(): Observable<any> {
    return this.webSocket.fromEvent('Location');
  }

  // Method to receive cars location updates
  receiveCars(): Observable<any> {
    return this.webSocket.fromEvent('Cars');
  }

  // Method to receive instant consumption updates
  receiveInstantConsumption(): Observable<any> {
    return this.webSocket.fromEvent('InstantConsumption');
  }

  // Method to receive battery level updates
  receiveBatteryLevel(): Observable<any> {
    return this.webSocket.fromEvent('BatteryLvl');
  }

  // Method to receive semaphores state updates
  receiveSemaphores(): Observable<any> {
    return this.webSocket.fromEvent('Semaphores');
  }

  // Method to receive current speed state updates
  receiveCurrentSpeed(): Observable<any> {
    return this.webSocket.fromEvent('CurrentSpeed');
  }

  // Method to receive current speed state updates
  receiveCurrentSteer(): Observable<any> {
    return this.webSocket.fromEvent('CurrentSteer');
  }

  // Method to receive the initial connection confirmation
  onConnect(): Observable<any> {
    console.log("connected ")
    return this.webSocket.fromEvent('after connect');
  }

  // Method to end the WebSocket connection
  disconnectSocket() {
    this.webSocket.disconnect();
  }

  // Method to receive any unhandled event
  receiveUnhandledEvents(): Observable<{ channel: string, data: any }> {
    return this.eventSubject.asObservable();
  }
}
