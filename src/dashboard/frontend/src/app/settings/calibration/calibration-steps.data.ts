import { CalibrationStep } from './calibration.component';

// Interface for input values passed to button functions
interface ButtonFunctionInputs {
  [key: string]: any;
}

// Global function registry for button calls
const functionRegistry: { [key: string]: (...args: any[]) => any } = {};

// Simple function caller
const callFunction = (name: string, ...args: any[]) => {
  if (functionRegistry[name]) {
    return functionRegistry[name](...args);
  } else {
    return (...args: any[]) => {/* function not found */};
  }
};

// Function caller that can handle multiple functions
const callFunctions = (functionCalls: Array<{ name: string; args?: any[] }>) => {
  functionCalls.forEach(call => {
    if (functionRegistry[call.name]) {
      functionRegistry[call.name](...(call.args || []));
    } else {
      return;
    }
  });
};

// Export registry setup function
export const registerFunction = (name: string, fn: (...args: any[]) => any) => {
  functionRegistry[name] = fn;
};

// Export the multiple function caller
export { callFunctions };

export const CALIBRATION_STEPS: CalibrationStep[] = [
  {
    id: 'step1',
    title: 'Track',
    description: {
      enable: true,
      text: 'Lay out a straight line with a minimum length of 3 meters. Ensure there is at least 3 meters of unobstructed space on the side where the vehicle will be calibrated.'
    },
    image: {
      enable: true,
      svgPath: '/assets/calibration/track.svg'
    },
    inputs: {
      enable: false,
      fields: [
      ]
    },
    buttons: []
  },
  {
    id: 'step2',
    title: 'Left Calibration',
    description: {
      enable: true,
      text: 'Position the vehicle as illustrated. Ensure it is on a level surface with the wheels aligned straight.'
    },
    image: {
      enable: true,
      svgPath: '/assets/calibration/placement_left.svg'
    },
    inputs: {
      enable: false,
      fields: [
      ]
    },
    buttons: [
      {
        enable: true,
        text: 'Continue',
        action: 'functionAndNavigateTo',
        navigateTo: 'step2_substep1',
        functions: [
          () => callFunction('sendWebSocketMessage', {
            Name: 'Calibration',
            Action: 'continue',
            Direction: 'left'
          }),
          () => callFunction('sendWebSocketMessage', {
            Name: 'Calibration',
            Action: 'current_angle',
            Direction: 'left'
          })
        ]
      }
    ],
    substeps: [
      {
        id: 'step2_substep1',
        description: {
          enable: true,
          text: 'After placing the vehicle correctly, you can start the calibration runs. The vehicle will move forward testing a steering angle of {steeringAngle} degrees.'
        },
        image: {
          enable: false,
          svgPath: ''
        },
        inputs: {
          enable: false,
          fields: []
        },
        buttons: [
          {
            enable: true,
            text: 'Start {steeringAngle}° Run',
            action: 'functionAndNavigateTo',
            navigateTo: 'step2_substep2',
            function: () => {
              callFunction('setCalibrationRunInProgress', true);
              callFunction('sendWebSocketMessage', {
                Name: 'Calibration',
                Action: 'run',
                Direction: 'left'
              });
            }
          }
        ]
      },
      {
        id: 'step2_substep2',
        description: {
          enable: true,
          text: 'After the vehicle has stopped, measure the distances shown in the image and enter them in the fields below for the {steeringAngle}° run.'
        },
        image: {
          enable: true,
          svgPath: '/assets/calibration/measurements_left.svg'
        },
        inputs: {
          enable: true,
          fields: [
            { id: 'distance1', label: 'd1 (mm)', type: 'number', value: 0, required: true },
            { id: 'distance2', label: 'd2 (mm)', type: 'number', value: 0, required: true },
            { id: 'distance3', label: 'd3 (mm)', type: 'number', value: 0, required: true }
          ]
        },
        buttons: [
          {
            enable: true,
            text: 'Re-run',
            action: 'functionAndNavigateTo',
            navigateTo: 'step2_substep1',
            function: () => {
              callFunction('setCalibrationRunInProgress', true);
              callFunction('sendWebSocketMessage', {
                Name: 'Calibration',
                Action: 're-run',
                Direction: 'left'
              });
            }
          },
          {
            enable: true,
            text: 'Submit Measurements',
            action: 'function',
            function: (inputs: ButtonFunctionInputs) => {
              // Use the new submitMeasurements function that handles the race condition
              callFunction('submitMeasurements', inputs, 'left', 'step2_substep1');
            }
          }
        ]
      }
    ]
  },
  {
    id: 'step3',
    title: 'Right Calibration',
    description: {
      enable: true,
      text: 'Position the vehicle as illustrated. Ensure it is on a level surface with the wheels aligned straight.'
    },
    image: {
      enable: true,
      svgPath: '/assets/calibration/placement_right.svg'
    },
    inputs: {
      enable: false,
      fields: [
      ]
    },
    buttons: [
      {
        enable: true,
        text: 'Continue',
        action: 'functionAndNavigateTo',
        navigateTo: 'step3_substep1',
        functions: [
          () => callFunction('sendWebSocketMessage', {
            Name: 'Calibration',
            Action: 'continue',
            Direction: 'right'
          }),
          () => callFunction('sendWebSocketMessage', {
            Name: 'Calibration',
            Action: 'current_angle',
            Direction: 'right'
          })
        ]
      }
    ],
    substeps: [
      {
        id: 'step3_substep1',
        description: {
          enable: true,
          text: 'After placing the vehicle correctly, you can start the calibration runs. The vehicle will move forward testing a steering angle of {steeringAngle} degrees.'
        },
        image: {
          enable: false,
          svgPath: ''
        },
        inputs: {
          enable: false,
          fields: []
        },
        buttons: [
          {
            enable: true,
            text: 'Start {steeringAngle}° Run',
            action: 'functionAndNavigateTo',
            navigateTo: 'step3_substep2',
            function: () => {
              callFunction('setCalibrationRunInProgress', true);
              callFunction('sendWebSocketMessage', {
                Name: 'Calibration',
                Action: 'run',
                Direction: 'right'
              });
            }
          }
        ]
      },
      {
        id: 'step3_substep2',
        description: {
          enable: true,
          text: 'After the vehicle has stopped, measure the distances shown in the image and enter them in the fields below for the {steeringAngle}° run.'
        },
        image: {
          enable: true,
          svgPath: '/assets/calibration/measurements_right.svg'
        },
        inputs: {
          enable: true,
          fields: [
            { id: 'distance1', label: 'd1 (mm)', type: 'number', value: 0, required: true },
            { id: 'distance2', label: 'd2 (mm)', type: 'number', value: 0, required: true },
            { id: 'distance3', label: 'd3 (mm)', type: 'number', value: 0, required: true }
          ]
        },
        buttons: [
          {
            enable: true,
            text: 'Re-run',
            action: 'functionAndNavigateTo',
            navigateTo: 'step3_substep1',
            function: () => {
              callFunction('setCalibrationRunInProgress', true);
              callFunction('sendWebSocketMessage', {
                Name: 'Calibration',
                Action: 're-run',
                Direction: 'right'
              });
            }
          },
          {
            enable: true,
            text: 'Submit Measurements',
            action: 'function',
            function: (inputs: ButtonFunctionInputs) => {
              // Use the new submitMeasurements function that handles the race condition
              callFunction('submitMeasurements', inputs, 'right', 'step3_substep1');
            }
          }
        ]
      }
    ]
  },
  {
    id: 'step4',
    title: 'Test Run',
    description: {
      enable: true,
      text: '{incompleteCalibMessage}'
    },
    image: {
      enable: true,
      svgPath: '/assets/calibration/placement_left.svg'
    },
    inputs: {
      enable: false,
      fields: [
      ]
    },
    buttons: [
      {
        enable: true,
        text: 'Continue',
        action: 'functionAndNavigateTo',
        navigateTo: 'step4_substep1',
        functions: [
          () => callFunction('sendWebSocketMessage', {
            Name: 'Calibration',
            Action: 'continue',
            Direction: 'right'
          }),
          () => callFunction('sendWebSocketMessage', {
            Name: 'Calibration',
            Action: 'current_angle',
            Direction: 'right'
          })
        ]
      }
    ],
    substeps: [
      {
        id: 'step4_substep1',
        description: {
          enable: true,
          text: 'After placing the vehicle correctly, you can start the test run. The vehicle will move forward testing a steering angle of 0 degrees.'
        },
        image: {
          enable: false,
          svgPath: ''
        },
        inputs: {
          enable: false,
          fields: []
        },
        buttons: [
          {
            enable: true,
            text: 'Start 0° Run',
            action: 'functionAndNavigateTo',
            navigateTo: 'step4_substep2',
            function: () => {
              callFunction('setCalibrationRunInProgress', true);
              callFunction('sendWebSocketMessage', {
                Name: 'Calibration',
                Action: 'test_run',
                Direction: 'left'
              });
            }
          }
        ]
      },
      {
        id: 'step4_substep2',
        description: {
          enable: true,
          text: 'After the vehicle has stopped, press one of the buttons below to continue.'
        },
        image: {
          enable: false,
          svgPath: ''
        },
        inputs: {
          enable: false,
          fields: []
        },
        buttons: [
          {
            enable: true,
            text: 'Straight',
            action: 'functionAndNavigateTo',
            navigateTo: '..parent',
            function: () => {
              callFunction('setCalibrationRunInProgress', true);
              callFunction('sendWebSocketMessage', {
                Name: 'Calibration',
                Action: 'test_run_done',
                Direction: 'left'
              });
            }
          },
          {
            enable: true,
            text: 'Left/Right',
            action: 'functionAndNavigateTo',
            navigateTo: 'step4_substep3',
            function: () => {
              callFunction('setCalibrationRunInProgress', true);
            }
          }
        ]
      },
      {
        id: 'step4_substep3',
        description: {
          enable: true,
          text: 'Because the vehicle did not move as expected, please recalibrate the vehicle.'
        },
        image: {
          enable: false,
          svgPath: ''
        },
        inputs: {
          enable: false,
          fields: []
        },
        buttons: [
          {
            enable: true,
            text: 'Recalibrate',
            action: 'functionAndNavigateTo',
            navigateTo: 'step1',
            functions: [
              () => callFunction('sendWebSocketMessage', {
                Name: 'Calibration',
                Action: 'exit'
              }),
              () => callFunction('sendWebSocketMessage', {
                Name: 'Calibration',
                Action: 'start'
              })
            ]
          }
        ]
      },
    ]
  },
  {
    id: 'step5',
    title: '0 Offset Spline Visualization',
    description: {
      enable: true,
      text: '{zeroOffsetMessage}'
    },
    image: {
      enable: false,
      svgPath: ''
    },
    inputs: {
      enable: false,
      fields: []
    },
    buttons: [
      {
        enable: true,
        text: 'Load Plot',
        action: 'function',
        function: () => {
          callFunction('requestZeroOffsetSplineData');
        }
      }
    ]
  },
  {
    id: 'step6',
    title: 'Backward Calibration',
    description: {
      enable: true,
      text: '{incompleteBackwardMessage}'
    },
    image: {
      enable: true,
      svgPath: '/assets/calibration/placement_backwards.svg'
    },
    inputs: {
      enable: false,
      fields: [
      ]
    },
    buttons: [
      {
        enable: true,
        text: 'Continue',
        action: 'functionAndNavigateTo',
        navigateTo: 'step6_substep1',
        functions: [
          () => callFunction('sendWebSocketMessage', {
            Name: 'Calibration',
            Action: 'continue',
            Direction: 'backward'
          }),
          () => callFunction('sendWebSocketMessage', {
            Name: 'Calibration',
            Action: 'current_angle',
            Direction: 'backward'
          })
        ]
      }
    ],
    substeps: [
      {
        id: 'step6_substep1',
        description: {
          enable: true,
          text: 'After placing the vehicle correctly, you can start the calibration runs. The vehicle will move backward in a straight line with a speed of {speed} cm/s.'
        },
        image: {
          enable: false,
          svgPath: ''
        },
        inputs: {
          enable: false,
          fields: []
        },
        buttons: [
          {
            enable: true,
            text: 'Start {speed} cm/s Run',
            action: 'functionAndNavigateTo',
            navigateTo: 'step6_substep2',
            function: () => {
              callFunction('setCalibrationRunInProgress', true);
              callFunction('sendWebSocketMessage', {
                Name: 'Calibration',
                Action: 'run',
                Direction: 'backward'
              });
            }
          }
        ]
      },
      {
        id: 'step6_substep2',
        description: {
          enable: true,
          text: 'After the vehicle has stopped, measure the distance shown in the image and enter it in the field below for the {speed} cm/s backward run.'
        },
        image: {
          enable: true,
          svgPath: '/assets/calibration/measurements_backwards.svg'
        },
        inputs: {
          enable: true,
          fields: [
            { id: 'distance', label: 'd (mm)', type: 'number', value: 0, required: true }
          ]
        },
        buttons: [
          {
            enable: true,
            text: 'Re-run',
            action: 'functionAndNavigateTo',
            navigateTo: 'step6_substep1',
            function: () => {
              callFunction('setCalibrationRunInProgress', true);
              callFunction('sendWebSocketMessage', {
                Name: 'Calibration',
                Action: 're-run',
                Direction: 'backward'
              });
            }
          },
          {
            enable: true,
            text: 'Submit Measurements',
            action: 'function',
            function: (inputs: ButtonFunctionInputs) => {
              // Use the new submitMeasurements function that handles the race condition
              callFunction('submitMeasurements', inputs, 'backward', 'step6_substep1');
            }
          }
        ]
      }
    ]
  },
  {
    id: 'step7',
    title: 'Calibration Visualization',
    description: {
      enable: true,
      text: '{visualizationMessage}'
    },
    image: {
      enable: false,
      svgPath: ''
    },
    inputs: {
      enable: false,
      fields: []
    },
    buttons: [
      {
        enable: true,
        text: 'Load Plots',
        action: 'function',
        function: () => {
          callFunction('requestPolynomialData');
        }
      }
    ]
  },
  {
    id: 'step8',
    title: 'Save New Calibration',
    description: {
      enable: true,
      text: '{incompleteSaveMessage}'
    },
    image: {
      enable: false,
      svgPath: ''
    },
    inputs: {
      enable: false,
      fields: []
    },
    buttons: [
      {
        enable: true,
        text: 'Save & Download',
        action: 'function',
        function: () => {
          callFunction('sendWebSocketMessage', {
            Name: 'Calibration',
            Action: 'save_calibration',
          })
        }
      }
    ]
  }
];
