import { Component, Input, OnChanges, SimpleChanges, Output, EventEmitter } from '@angular/core';

@Component({
  selector: 'app-map-cursor',
  standalone: true,
  imports: [],
  templateUrl: './map-cursor.component.html',
  styleUrl: './map-cursor.component.css'
})
export class MapCursorComponent implements OnChanges {
  @Input() cursorRotation: number = 0;
  @Output() cursorLoaded = new EventEmitter<void>();

  ngOnInit(): void {
    this.cursorLoaded.emit();
  }
  
  ngOnChanges(changes: SimpleChanges): void {
    if (changes['cursorRotation']) {
      this.updateRotation();
    }
  }

  updateRotation(): void {
    const cursor = document.getElementById("map-cursor-arrow") as HTMLElement;
    if (cursor) {
      cursor.style.transform = `rotate(${this.cursorRotation}deg)`;
    }
  }
}
