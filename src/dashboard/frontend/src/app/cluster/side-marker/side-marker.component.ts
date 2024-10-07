import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subscription } from 'rxjs';
import { WebSocketService} from '../../webSocket/web-socket.service'


@Component({
  selector: 'app-side-marker',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './side-marker.component.html',
  styleUrl: './side-marker.component.css'
})
export class SideMarkerComponent {
  public enableLeft: boolean = false;
  public enableRight: boolean = false;
  private steerSubscription: Subscription | undefined;

  constructor( private  webSocketService: WebSocketService) { }

  ngOnInit()
  {
    // Listen for steer
    this.steerSubscription = this.webSocketService.receiveCurrentSteer().subscribe(
      (message) => {
        const angle = message.value / 10;
        
        if (angle > 15) {
          this.enableLeft = false;
          this.enableRight = true;
        }
        else if (angle < -15) {
          this.enableLeft = true;
          this.enableRight = false;
        }
        else {
          this.enableLeft = false;
          this.enableRight = false;
        }
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

