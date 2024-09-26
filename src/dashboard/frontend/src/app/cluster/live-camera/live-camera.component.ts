import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { Subscription } from 'rxjs';
import { WebSocketService} from '../../webSocket/web-socket.service'

@Component({
  selector: 'app-live-camera',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './live-camera.component.html',
  styleUrl: './live-camera.component.css'
})
export class LiveCameraComponent {
  public image: string | undefined;
  public loading: boolean = true;
  private canvasSize: number[] = [512, 270];
  private cameraSubscription: Subscription | undefined;

  constructor( private  webSocketService: WebSocketService) { }

  ngOnInit()
  {  
    this.image = this.createBlackImage();

    this.cameraSubscription = this.webSocketService.receiveCamera().subscribe(
      (message) => {
        this.image = `data:image/png;base64,${message.str}`;
        this.loading = false;
      },
      (error) => {
        this.image = this.createBlackImage();
        this.loading = true;
        console.error('Error receiving disk usage:', error);
      }
    );
  }

  ngOnDestroy() {
    if (this.cameraSubscription) {
      this.cameraSubscription.unsubscribe();
    }
    this.webSocketService.disconnectSocket();
  }

  createBlackImage(): string {
    const canvas = document.createElement('canvas');
    canvas.width = this.canvasSize[0]; 
    canvas.height = this.canvasSize[1]; 
    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.fillStyle = 'black'; 
      ctx.fillRect(0, 0, canvas.width, canvas.height);
    }
    return canvas.toDataURL('image/png'); 
  };
}
