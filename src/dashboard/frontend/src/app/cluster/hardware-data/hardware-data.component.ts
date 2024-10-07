import { Component } from '@angular/core';
import { Subscription } from 'rxjs';
import { WebSocketService} from '../../webSocket/web-socket.service'
import { IndicatorComponent } from './indicator/indicator.component';

@Component({
  selector: 'app-hardware-data',
  standalone: true,
  imports: [IndicatorComponent],
  templateUrl: './hardware-data.component.html',
  styleUrl: './hardware-data.component.css'
})
export class HardwareDataComponent {
  private cpuSubscription: Subscription | undefined;
  private memorySubscription: Subscription | undefined;
  private resourceSubscription: Subscription | undefined;
  public cpuTemp: number = 0;
  public cpuUsage: number[] = [0, 0, 0, 0];
  public memoryUsage: number = 0;
  public heap: number = 0;
  public stack: number = 0;
  
  constructor( private  webSocketService: WebSocketService) { }

  ngOnInit()
  {
    // Listen for cpu data
    this.cpuSubscription = this.webSocketService.receiveCpuUsage().subscribe(
      (message) => {
        this.cpuTemp = message['data']['temp'];
        this.cpuUsage[0] = parseInt(message['data']['usage'][0]);
        this.cpuUsage[1] = parseInt(message['data']['usage'][1]);
        this.cpuUsage[2] = parseInt(message['data']['usage'][2]);
        this.cpuUsage[3] = parseInt(message['data']['usage'][3]);
      },
      (error) => {
        console.error('Error receiving disk usage:', error);
      }
    );
    
    this.resourceSubscription = this.webSocketService.receiveResourceMonitor().subscribe(
      (message) =>{
        this.heap = message.value["heap"];
        this.stack = message.value["stack"];
      },
      (error) => {
        console.error('Error receiving resource monitor:', error);
      }
    );

    this.memorySubscription = this.webSocketService.receiveMemoryUsage().subscribe(
      (message) => {
        this.memoryUsage = parseInt(message['data']);
      },
      (error) => {
        console.error('Error receiving disk usage:', error);
      }
    );
  }

  ngOnDestroy() {
    if (this.cpuSubscription) {
      this.cpuSubscription.unsubscribe();
    }
    if (this.memorySubscription) {
      this.memorySubscription.unsubscribe();
    }
    if (this.resourceSubscription) {
      this.resourceSubscription.unsubscribe();
    }
    this.webSocketService.disconnectSocket();
  }
}
