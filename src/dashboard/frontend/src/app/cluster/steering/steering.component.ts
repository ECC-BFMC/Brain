import { Component } from '@angular/core';
import { Subscription } from 'rxjs';
import { WebSocketService} from '../../webSocket/web-socket.service'


@Component({
  selector: 'app-steering',
  standalone: true,
  imports: [],
  templateUrl: './steering.component.html',
  styleUrl: './steering.component.css'
})
export class SteeringComponent {
  public angle: number = 0;
  private steerSubscription: Subscription | undefined;

  constructor( private  webSocketService: WebSocketService) { }

  ngOnInit()
  {
    // Listen for camera
    this.steerSubscription = this.webSocketService.receiveCurrentSteer().subscribe(
      (message) => {
        this.angle = message.value/10;
      },
      (error) => {
        console.error('Error receiving disk usage:', error);
      }
    );
  }

  ngOnDestroy() {
    if (this.steerSubscription) {
      this.steerSubscription.unsubscribe();
    }
    this.webSocketService.disconnectSocket();
  }
}
