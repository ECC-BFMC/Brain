import { Component, Input, OnChanges, SimpleChanges } from '@angular/core';

@Component({
  selector: 'app-indicator',
  standalone: true,
  imports: [],
  templateUrl: './indicator.component.html',
  styleUrl: './indicator.component.css'
})
export class IndicatorComponent implements OnChanges {
  @Input() value: number | undefined;
  @Input() minValue: number = 0;
  @Input() maxValue: number = 100;
  @Input() title: string = "";
  @Input() titleOffset: number = 0;
  @Input() symbol: string = "";
  public valuePos: number = 0;
  public maxValueOpacity: number = 1;
  public minValueOpacity: number = 1;

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['value']) {
      this.update();
    }
  }

  update(): void { 
    if (this.value) { 
      const currentValue = this.value * 100 / this.maxValue;
      this.valuePos = 80 - (currentValue * 0.85); // * 0.85 because we use only 85%

      if (this.valuePos >= 74) { 
        this.valuePos = 74;
      }

      if (this.valuePos <= 0) { 
        this.valuePos = 0;
      }

      if (this.valuePos <= 16) { 
        this.maxValueOpacity = 0;
      }
      else {
        this.maxValueOpacity = 1;
      }

      if (this.valuePos >= 59) { 
        this.minValueOpacity = 0;
      }
      else {
        this.minValueOpacity = 1;
      }
    }
  }
}
