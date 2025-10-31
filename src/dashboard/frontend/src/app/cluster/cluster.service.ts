import { Injectable } from '@angular/core';
import { BehaviorSubject, combineLatest } from 'rxjs';
import { map } from 'rxjs/operators';
import { Platform } from '@angular/cdk/platform';

@Injectable({
  providedIn: 'root'
})
export class ClusterService {

  constructor(private platform: Platform) {}

  private klSubject = new BehaviorSubject<string>('');
  kl$ = this.klSubject.asObservable();

  private drivingModeSubject = new BehaviorSubject<string>('');
  drivingMode$ = this.drivingModeSubject.asObservable();

  private serialConnectionStateSubject = new BehaviorSubject<boolean>(true);
  serialConnectionState$ = this.serialConnectionStateSubject.asObservable();

  private isMobileDevice(): boolean {
    const userAgent = navigator.userAgent || navigator.vendor || (window as any).opera;
    return /android|iPad|iPhone|iPod/i.test(userAgent) && !(window as any).MSStream;
  }

  isMobileDriving$ = combineLatest([this.kl$, this.drivingMode$]).pipe(
    map(([kl, drivingMode]) => 
      kl === '30' && drivingMode === 'manual' && this.isMobileDevice()
    )
  );

  updateKL(value: string) {
    this.klSubject.next(value);
  }

  updateDrivingMode(value: string) {
    this.drivingModeSubject.next(value);
  }

  updateSerialConnectionState(value: boolean) {
    this.serialConnectionStateSubject.next(value);
  }
}
