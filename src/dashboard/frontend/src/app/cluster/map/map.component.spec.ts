import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Subject } from 'rxjs';

import { MapComponent } from './map.component';
import { WebSocketService } from '../../services/web-socket.service';

describe('MapComponent', () => {
  let component: MapComponent;
  let fixture: ComponentFixture<MapComponent>;
  let locations: Subject<{ value: { x?: unknown; y?: unknown } | null } | null>;
  let socket: jasmine.SpyObj<WebSocketService>;

  beforeEach(async () => {
    locations = new Subject();
    socket = jasmine.createSpyObj<WebSocketService>('WebSocketService', [
      'receiveLocation', 'disconnectSocket'
    ]);
    socket.receiveLocation.and.returnValue(locations.asObservable());
    await TestBed.configureTestingModule({
      imports: [MapComponent],
      providers: [{ provide: WebSocketService, useValue: socket }]
    }).compileComponents();

    fixture = TestBed.createComponent(MapComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    await component.imageElementRef.nativeElement.decode();
    expect(component.imageElementRef.nativeElement.naturalWidth).toBe(5800);
    expect(component.imageElementRef.nativeElement.naturalHeight).toBe(3852);
    fixture.detectChanges();
  });

  function loadTrack(): HTMLImageElement {
    const image = component.imageElementRef.nativeElement;
    Object.defineProperty(image, 'naturalWidth', { configurable: true, value: 5800 });
    Object.defineProperty(image, 'naturalHeight', { configurable: true, value: 3852 });
    component.onLoadTrack();
    fixture.detectChanges();
    return image;
  }

  function expectPosition(x: number, y: number): void {
    const image = component.imageElementRef.nativeElement;
    expect(image.style.transform).not.toBe('');
    const transform = component.trackTransform.match(/translate\(([-\d.e]+)%, ([-\d.e]+)%\)/);
    expect(transform).not.toBeNull();
    if (transform) {
      expect(Number(transform[1])).toBeCloseTo(-x * 0.2806 / 5800 * 100, 10);
      expect(Number(transform[2])).toBeCloseTo(-(13759 - y) * 0.27996 / 3852 * 100, 10);
    }
  }

  it('uses the Masterix image and calibrates the bottom-left origin on load', () => {
    const image = loadTrack();
    expect(image.getAttribute('src')).toBe('/assets/Track2023_modified.png');
    expectPosition(0, 0);
  });

  it('renders the track background as transparent', () => {
    const canvas = document.createElement('canvas');
    canvas.width = 1;
    canvas.height = 1;
    const context = canvas.getContext('2d');
    expect(context).not.toBeNull();
    if (context) {
      context.drawImage(component.imageElementRef.nativeElement, 0, 0);
      expect(context.getImageData(0, 0, 1, 1).data[3]).toBe(0);
    }
  });

  it('hides map lines but keeps the car visible until valid coordinates arrive', () => {
    const track: HTMLElement = fixture.nativeElement.querySelector('.map-track-container');
    const cursor: HTMLElement = fixture.nativeElement.querySelector('#map-cursor');
    expect(getComputedStyle(track).visibility).toBe('hidden');
    expect(getComputedStyle(cursor).visibility).toBe('visible');

    const warning = spyOn(console, 'warn');
    for (const value of [null, {}, { x: 100 }, { y: 200 }, { x: '', y: '' }]) {
      locations.next({ value });
      fixture.detectChanges();
      expect(getComputedStyle(track).visibility).toBe('hidden');
    }
    expect(warning).toHaveBeenCalledTimes(5);

    locations.next({ value: { x: 0, y: 0 } });
    fixture.detectChanges();
    expect(getComputedStyle(track).visibility).toBe('visible');
    expectPosition(0, 0);
  });

  it('matches Masterix at the corners and an interior location', () => {
    loadTrack();
    for (const [x, y] of [[0, 13759], [20670, 0], [20670, 13759], [1234, 5678], [-100, 15000]]) {
      locations.next({ value: { x, y } });
      fixture.detectChanges();
      expectPosition(x, y);
    }
  });

  it('keeps the most recent location received before the image loads', () => {
    const image = component.imageElementRef.nativeElement;
    Object.defineProperty(image, 'naturalWidth', { configurable: true, value: 0 });
    Object.defineProperty(image, 'naturalHeight', { configurable: true, value: 0 });
    locations.next({ value: { x: 100, y: 200 } });
    locations.next({ value: { x: '2500', y: '6500' } });
    loadTrack();
    expectPosition(2500, 6500);
  });

  it('keeps the calibrated point centred across viewport sizes without another update', () => {
    const image = loadTrack();
    locations.next({ value: { x: 1234, y: 5678 } });
    fixture.detectChanges();
    const viewport: HTMLElement = fixture.nativeElement.querySelector('.map-container');
    const cursor: HTMLElement = fixture.nativeElement.querySelector('#map-cursor');
    for (const [width, height] of [[300, 200], [600, 200], [220, 400]]) {
      viewport.style.width = `${width}px`;
      viewport.style.height = `${height}px`;
      const viewportRect = viewport.getBoundingClientRect();
      const imageRect = image.getBoundingClientRect();
      const cursorRect = cursor.getBoundingClientRect();
      const pointX = imageRect.left + 1234 * 0.2806 * imageRect.width / 5800;
      const pointY = imageRect.top + (13759 - 5678) * 0.27996 * imageRect.height / 3852;
      expect(imageRect.width).toBeCloseTo(width * 5, 1);
      expect(imageRect.height / imageRect.width).toBeCloseTo(3852 / 5800, 3);
      expect(pointX).toBeCloseTo(viewportRect.left + width / 2, 1);
      expect(pointY).toBeCloseTo(viewportRect.top + height / 2, 1);
      expect(cursorRect.left + cursorRect.width / 2).toBeCloseTo(pointX, 1);
      expect(cursorRect.top + cursorRect.height / 2).toBeCloseTo(pointY, 1);
    }
  });

  it('logs invalid coordinates without moving the map', () => {
    loadTrack();
    locations.next({ value: { x: 1000, y: 2000 } });
    fixture.detectChanges();
    const previousTransform = component.trackTransform;
    const warning = spyOn(console, 'warn');
    const invalid = [undefined, null, '', ' ', true, {}, NaN, Infinity, 'invalid'];
    for (const value of invalid) {
      locations.next({ value: { x: value, y: 0 } });
      locations.next({ value: { x: 0, y: value } });
    }
    locations.next(null);
    locations.next({ value: null });
    expect(warning).toHaveBeenCalledTimes(invalid.length * 2 + 2);
    expect(component.trackTransform).toBe(previousTransform);
    expect(component.hasLocation).toBeTrue();
  });

  it('reports image loading failures', () => {
    const error = spyOn(console, 'error');
    component.imageElementRef.nativeElement.dispatchEvent(new Event('error'));
    expect(error).toHaveBeenCalledWith('[Map] Failed to load the calibrated Masterix track image.');
  });

  it('stops processing locations when destroyed', () => {
    loadTrack();
    const previousTransform = component.trackTransform;
    fixture.destroy();
    locations.next({ value: { x: 1000, y: 2000 } });
    expect(component.trackTransform).toBe(previousTransform);
    expect(socket.disconnectSocket).toHaveBeenCalled();
  });
});
