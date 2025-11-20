# Copyright (c) 2019, Bosch Engineering Center Cluj and BFMC orginazers
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.

# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.

# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import copy
import math
import numpy as np
import warnings
import re
import zipfile
import os
import base64
from io import BytesIO
from scipy.interpolate import CubicSpline

from string import Template

from src.utils.messages.allMessages import ControlCalib, CalibPWMData, CalibRunDone
from src.utils.messages.messageHandlerSubscriber import messageHandlerSubscriber
from src.utils.messages.messageHandlerSender import messageHandlerSender


class Calibration():
    def __init__(self, queuesList, socketio, w=20, h=26, eps=0.1, max_angle_tolerance=0.05):
        self.W = w
        self.H = h
        self.EPS = eps

        self.INT64_MAX = 2**63 - 1
        
        self.STEER_SCALING_FACTOR = 10  # scaling factor for steering angles when generating polynomial coefficients for nucleo
                                        # nucleo expects steering values multiplied by 10 (e.g. 5° becomes 50) for integer efficiency
        
        self.MAX_ANGLE_TOLERANCE = max_angle_tolerance  # tolerance for detecting max angle (5% by default)
                                        
        self.queuesList = queuesList

        self.current_step = 0
        self.socketio = socketio
        
        self.valid_angles = []  # store all angles that fall within tolerance range
        self.max_angle_left = None  # store the final max angle for left steering
        self.max_angle_right = None  # store the final max angle for right steering
        self.steering_offset = 0  # store the steering offset from test run (in degrees)
        self.zero_offset_spline_data_for_frontend = None

        self._init_subscribers()
        self._init_senders()

        # {"desiredSpeed": [mm/s], "desiredSteer": [degrees], "time": [deciseconds] , "actualSpeed": [mm/s], "actualSteer": [degrees], "actualSpeedPWM": [μs], "actualSteerPWM": [μs]}
        # steer ∈ [-27.2, 27.2]
        # speed ∈ [-500, 500]
        self.commands_template = {
            "left": [
                {"desiredSpeed": 500, "desiredSteer": 5.0, "time": 20, "actualSpeed": None, "actualSteer": None, "actualSpeedPWM": None, "actualSteerPWM": None},
                {"desiredSpeed": 400, "desiredSteer": 10.0, "time": 25, "actualSpeed": None, "actualSteer": None, "actualSpeedPWM": None, "actualSteerPWM": None},
                {"desiredSpeed": 300, "desiredSteer": 15.0, "time": 30, "actualSpeed": None, "actualSteer": None, "actualSpeedPWM": None, "actualSteerPWM": None},
                {"desiredSpeed": 200, "desiredSteer": 20.0, "time": 35, "actualSpeed": None, "actualSteer": None, "actualSpeedPWM": None, "actualSteerPWM": None},
                {"desiredSpeed": 100, "desiredSteer": 23.2, "time": 40, "actualSpeed": None, "actualSteer": None, "actualSpeedPWM": None, "actualSteerPWM": None},
                {"desiredSpeed": 100, "desiredSteer": 25.0, "time": 40, "actualSpeed": None, "actualSteer": None, "actualSpeedPWM": None, "actualSteerPWM": None},
                {"desiredSpeed": 100, "desiredSteer": 27.2, "time": 40, "actualSpeed": None, "actualSteer": None, "actualSpeedPWM": None, "actualSteerPWM": None}
            ],
            "right": [
                {"desiredSpeed": 500, "desiredSteer": 5.0, "time": 20, "actualSpeed": None, "actualSteer": None, "actualSpeedPWM": None, "actualSteerPWM": None},
                {"desiredSpeed": 400, "desiredSteer": 10.0, "time": 25, "actualSpeed": None, "actualSteer": None, "actualSpeedPWM": None, "actualSteerPWM": None},
                {"desiredSpeed": 300, "desiredSteer": 15.0, "time": 30, "actualSpeed": None, "actualSteer": None, "actualSpeedPWM": None, "actualSteerPWM": None},
                {"desiredSpeed": 200, "desiredSteer": 20.0, "time": 35, "actualSpeed": None, "actualSteer": None, "actualSpeedPWM": None, "actualSteerPWM": None},
                {"desiredSpeed": 100, "desiredSteer": 23.2, "time": 40, "actualSpeed": None, "actualSteer": None, "actualSpeedPWM": None, "actualSteerPWM": None},
                {"desiredSpeed": 100, "desiredSteer": 25.0, "time": 40, "actualSpeed": None, "actualSteer": None, "actualSpeedPWM": None, "actualSteerPWM": None},
                {"desiredSpeed": 100, "desiredSteer": 27.2, "time": 40, "actualSpeed": None, "actualSteer": None, "actualSpeedPWM": None, "actualSteerPWM": None}
            ],
            "backward": [
                {"desiredSpeed": -100, "desiredSteer": 0.0, "time": 40, "actualSpeed": None, "actualSpeedPWM": None},
                {"desiredSpeed": -200, "desiredSteer": 0.0, "time": 35, "actualSpeed": None, "actualSpeedPWM": None},
                {"desiredSpeed": -300, "desiredSteer": 0.0, "time": 30, "actualSpeed": None, "actualSpeedPWM": None},
                {"desiredSpeed": -400, "desiredSteer": 0.0, "time": 25, "actualSpeed": None, "actualSpeedPWM": None},
                {"desiredSpeed": -500, "desiredSteer": 0.0, "time": 20, "actualSpeed": None, "actualSpeedPWM": None},
            ]
        }

        self.test_run = {
            "speed": 350,
            "steer": 0,
            "time": 30
        }

        self.commands = copy.deepcopy(self.commands_template)
        self.current_command = None

        # track completion status for each calibration direction
        self.left_completed = False
        self.right_completed = False
        self.test_run_completed = False
        self.backward_completed = False


    def handle_calibration_signal(self, dataDict, socketId):
        """Handle calibration signals from frontend."""
        
        action = dataDict['Action']

        if action == 'start':
            self.start_calibration_process()

        elif action == 'complete' or action == 'exit':
            self.stop_calibration_process()

        elif action == 'run':
            self.run_procedure(dataDict['Direction'], socketId)

        elif action == 'done' or action == 'continue':
            self.reset_current_step()
            
        elif action == 're-run':
            if self.current_step > 0:
                self.current_step -= 1

        elif action == 'test_run':
            self.run_test_run(socketId)
        
        elif action == 'test_run_done':
            self.test_run_completed = True
            self.socketio.emit('Calibration', {'action': 'test_run_done'}, room=socketId)

        elif action == 'current_angle':
            self.send_current_run_value(dataDict['Direction'], socketId)

        elif action == 'submit_measurements':
            self.handle_measurement_submission(dataDict, socketId)
            
        elif action == 'complete_calibration':
            self.complete_calibration_process(socketId)

        elif action == 'save_calibration':
            self.calculate_polynomial_coefficients("Speed")
            self.calculate_polynomial_coefficients("Steer")

            zip_data = self.create_source_zip()

            self.socketio.emit('Calibration', {
                'action': 'calibration_saved', 
                'success': True,
                'zipData': zip_data
            }, room=socketId)
            print(f"\033[1;97m[ Calibration ] :\033[0m \033[1;92mCalibration files successfully generated and saved\033[0m")

        elif action == 'get_status':
            self.send_calibration_status(socketId)
        
        elif action == 'get_polynomial_data':
            self.send_polynomial_data(socketId)

        elif action == 'get_zero_offset_spline_data':
            self.send_zero_offset_spline_data(socketId)


    def send_calibration_status(self, socketId):
        """Send the current calibration completion status to the frontend."""
        status = {
            'action': 'calibration_status',
            'left': self.left_completed,
            'right': self.right_completed,
            'test_run': self.test_run_completed,
            'backward': self.backward_completed
        }
        self.socketio.emit('Calibration', status, room=socketId)


    def send_polynomial_data(self, socketId):
        """Send spline data and calibration points to frontend for visualization."""
        
        speed_points = self.collect_calibration_points("Speed", use_scaling=True)
        steer_points = self.collect_calibration_points("Steer", use_scaling=True)
        
        response = {
            'action': 'polynomial_data',
            'hasData': len(speed_points) >= 2 and len(steer_points) >= 2,
            'speedData': None,
            'steerData': None
        }
        
        if len(speed_points) >= 2:
            spline_data, err = self.fit_cubic_spline(speed_points, "Speed")
            if spline_data is not None:
                response['speedData'] = {
                    'points': speed_points,
                    'spline': spline_data,
                    'error': err
                }
        
        if len(steer_points) >= 2:
            spline_data, err = self.fit_cubic_spline(steer_points, "Steer")
            if spline_data is not None:
                response['steerData'] = {
                    'points': steer_points,
                    'spline': spline_data,
                    'error': err
                }

                # Evaluate adjusted limit points for display
                limit_points = []
                if self.max_angle_left is not None or self.max_angle_right is not None:
                    # Recreate cs for evaluation
                    grouped_points = {}
                    for x, y in steer_points:
                        if y not in grouped_points:
                            grouped_points[y] = []
                        grouped_points[y].append(x)

                    filtered_points = []
                    for y, x_values in grouped_points.items():
                        avg_x = np.mean(x_values)
                        filtered_points.append([avg_x, y])

                    filtered_points.sort(key=lambda p: p[0])
                    x_all, y_all = zip(*filtered_points)
                    x_all, y_all = np.array(x_all), np.array(y_all)

                    try:
                        cs = CubicSpline(x_all, y_all, bc_type='natural')

                        # Adjust limits by steering offset
                        if self.max_angle_left is not None:
                            adjusted_angle = -self.max_angle_left + self.steering_offset
                            scaled = adjusted_angle * self.STEER_SCALING_FACTOR
                            pwm = cs(scaled)
                            limit_points.append([scaled, int(pwm)])

                        if self.max_angle_right is not None:
                            adjusted_angle = self.max_angle_right + self.steering_offset
                            scaled = adjusted_angle * self.STEER_SCALING_FACTOR
                            pwm = cs(scaled)
                            limit_points.append([scaled, int(pwm)])

                    except Exception as e:
                        print(f"\033[1;97m[ Calibration ] :\033[0m \033[1;91mERROR\033[0m - Could not evaluate limit points: {e}")

                response['limitPointsData'] = {
                    'points': limit_points,
                    'type': 'limit'
                }
        
        self.socketio.emit('Calibration', response, room=socketId)


    def send_zero_offset_spline_data(self, socketId):
        """Send zero offset spline data to frontend for visualization."""
        response = {
            'action': 'zero_offset_spline_data',
            'zeroOffsetData': self.zero_offset_spline_data_for_frontend
        }
        self.socketio.emit('Calibration', response, room=socketId)
        # if self.zero_offset_spline_data_for_frontend:
        #     print(f"\033[1;97m[ Calibration ] :\033[0m \033[1;96mZero offset spline data sent to frontend\033[0m")
        # else:
        #     print(f"\033[1;97m[ Calibration ] :\033[0m \033[1;93mWARNING\033[0m - No zero offset spline data to send")


    def send_current_run_value(self, direction, socketId):
        """Send the current desired steer angle or speed to the frontend."""
        if self.current_step < len(self.commands[direction]):
            command = self.commands[direction][self.current_step]
            if direction == 'backward':
                self.socketio.emit('Calibration', {'action': 'current_speed', 'data': command['desiredSpeed']}, room=socketId)
            else:
                self.socketio.emit('Calibration', {'action': 'current_angle', 'data': command['desiredSteer']}, room=socketId)


    def run_procedure(self, direction, socketId):
        """Run the procedure for the given direction."""
        if self.current_step >= len(self.commands[direction]):
            return

        self.current_command = self.commands[direction][self.current_step]

        self.send_current_run_value(direction, socketId)

        # for backward direction, use the corrected steering offset from test run
        if direction == 'backward':
            steer_value = self.current_command['desiredSteer'] * 10 + self.steering_offset * 10
        else:
            steer_value = self.current_command['desiredSteer'] * 10 * (-1 if direction == 'left' else 1)

        self.controlCalibSender.send({
            'Time': self.current_command['time'], 
            'Speed': self.current_command['desiredSpeed'], 
            'Steer': steer_value
        })
        
        calibPWMData = self.calibPWMDataSubscriber.receive_with_block()
        if calibPWMData is not None:
            self.current_command['actualSpeedPWM'] = calibPWMData['speedPWM']
            self.current_command['actualSteerPWM'] = calibPWMData['steerPWM']
        
        calibRunDone = self.calibRunDoneSubscriber.receive_with_block()
        if calibRunDone is not None:
            self.socketio.emit('Calibration', {'action': 'calibration_run_done'}, room=socketId)

        self.current_step += 1


    def run_test_run(self, socketId, desired_steer=0):
        # new method: use cubic spline interpolation to find the zero-crossing point (offset)
        # this provides a more accurate offset by fitting a smooth curve to points near zero
        desired_to_actual_points = []
        for command_type in ['left', 'right']:
            for command in self.commands[command_type]:
                if command['desiredSteer'] is not None and command['actualSteer'] is not None:
                    signed_desired_steer = command['desiredSteer'] * (-1 if command_type == 'left' else 1)
                    # Correctly sign the actual steer value for left turns
                    signed_actual_steer = command['actualSteer'] * (-1 if command_type == 'left' else 1)
                    new_point = [signed_desired_steer, signed_actual_steer]
                    
                    if new_point not in desired_to_actual_points:
                        desired_to_actual_points.append(new_point)

        # select points around zero desired steer for a focused spline fit
        # taking points with the smallest desired steer values helps focus the fit on the zero-crossing area
        left_points = sorted([p for p in desired_to_actual_points if p[0] < 0], key=lambda x: x[0], reverse=True)
        right_points = sorted([p for p in desired_to_actual_points if p[0] >= 0], key=lambda x: x[0])
        
        num_points_per_side = 2  # Use up to 2 points from each side for a robust spline
        focused_points = left_points[:num_points_per_side] + right_points[:num_points_per_side]

        # a cubic spline requires at least 4 points
        if len(focused_points) < 4:
            print(f"\033[1;97m[ Calibration ] :\033[0m \033[1;93mWARNING\033[0m - Not enough points for cubic spline interpolation ({len(focused_points)} found), using 0° as fallback. At least 4 are needed.")
            corrected_steer = 0
            self.zero_offset_spline_data_for_frontend = None
        else:
            # for interpolation, we need to find desired_steer (y) for actual_steer=0 (x)
            # the points are [desired_steer, actual_steer], so p[1] is x and p[0] is y
            
            actual_steers = [p[1] for p in focused_points]
            if not (any(s < 0 for s in actual_steers) and any(s > 0 for s in actual_steers)):
                print(f"\033[1;97m[ Calibration ] :\033[0m \033[1;93mWARNING\033[0m - Focused calibration points do not bracket actual_steer=0. Cannot interpolate accurately. Using 0° as fallback.")
                corrected_steer = 0
                self.zero_offset_spline_data_for_frontend = None
            else:
                # CubicSpline requires that x-coordinates (actual_steer) are unique and sorted
                # we group by actual_steer and average the desired_steer for any duplicates
                unique_points_dict = {}
                for p in focused_points:
                    actual, desired = p[1], p[0]
                    if actual not in unique_points_dict:
                        unique_points_dict[actual] = []
                    unique_points_dict[actual].append(desired)
                
                unique_points = []
                for actual, desireds in sorted(unique_points_dict.items()):  # sort by actual_steer
                    unique_points.append([sum(desireds) / len(desireds), actual])

                if len(unique_points) < 4:
                    print(f"\033[1;97m[ Calibration ] :\033[0m \033[1;93mWARNING\033[0m - Not enough unique points for cubic spline ({len(unique_points)} found), using 0° as fallback. At least 4 are needed.")
                    corrected_steer = 0
                    self.zero_offset_spline_data_for_frontend = None
                else:
                    x_coords = [p[1] for p in unique_points]  # actual_steer
                    y_coords = [p[0] for p in unique_points]  # desired_steer

                    try:
                        # create the cubic spline: y = f(x) => desired_steer = f(actual_steer)
                        cs = CubicSpline(x_coords, y_coords)
                        
                        # evaluate the spline at actual_steer = 0 to find the desired_steer offset.
                        corrected_steer = float(cs(0))

                        # prepare data for frontend
                        spline_data_for_frontend = {
                            'knots': cs.x.tolist(),
                            'coefficients': cs.c.T.tolist(),
                            'n_segments': len(cs.x) - 1
                        }
                        y_pred = cs(cs.x)
                        err = np.mean((y_coords - y_pred)**2)
                        
                        frontend_points = [[p[1], p[0]] for p in unique_points]

                        self.zero_offset_spline_data_for_frontend = {
                            'points': frontend_points,
                            'spline': spline_data_for_frontend,
                            'error': err
                        }

                    except Exception as e:
                        print(f"\033[1;97m[ Calibration ] :\033[0m \033[1;91mERROR\033[0m - Cubic spline interpolation failed: {e}. Using 0° as fallback.")
                        corrected_steer = 0
                        self.zero_offset_spline_data_for_frontend = None
        
        # store the steering offset for limit adjustment
        self.steering_offset = corrected_steer

        print(f"\033[1;97m[ Calibration ] :\033[0m \033[1;94mCorrected steer: {corrected_steer}\033[0m")
        self.controlCalibSender.send({
            'Time': self.test_run['time'], 
            'Speed': self.test_run['speed'], 
            'Steer': corrected_steer * 10
        })

        # read and consume PWM data to prevent it from being used by the next run (backward calibration)
        calibPWMData = self.calibPWMDataSubscriber.receive_with_block()
        if calibPWMData is not None:
            # dynamically add the test run data to self.commands for polynomial fitting
            if 'zero' not in self.commands:
                self.commands['zero'] = []
            
            test_run_command = {
                "desiredSpeed": self.test_run['speed'],
                "desiredSteer": corrected_steer,
                "time": self.test_run['time'],
                "actualSpeed": 0,
                "actualSteer": 0.0, # the goal of this run is to achieve an actual 0° steer
                "actualSpeedPWM": 1491, # actual speed 0 pwm
                "actualSteerPWM": calibPWMData['steerPWM']
            }
            self.commands['zero'].append(test_run_command)

        calibRunDone = self.calibRunDoneSubscriber.receive_with_block()
        if calibRunDone is not None:
            self.socketio.emit('Calibration', {
                'action': 'calibration_run_done',
                'corrected_steer': corrected_steer
            }, room=socketId)


    def handle_measurement_submission(self, dataDict, socketId):
        direction = dataDict.get('Direction', 'unknown')
        distances = dataDict.get('Distances', {})
        
        # get the command from the PREVIOUS step (since current_step was already incremented in run_procedure)
        # we need to use current_step - 1 to get the command that was just executed
        command_index = self.current_step - 1
        if command_index < 0 or command_index >= len(self.commands[direction]):
            print(f"\033[1;97m[ Calibration ] :\033[0m \033[1;91mERROR\033[0m - Invalid command index {command_index}")
            return
        
        target_command = self.commands[direction][command_index]
        
        # for backward direction, use single distance measurement
        if direction == 'backward':
            # backward only needs one distance measurement (how far it traveled)
            distance_mm = distances.get('d', 0)  # distance in mm
            dt_s = target_command["time"] / 10.0  # convert deciseconds to seconds
            speed = (distance_mm / dt_s) if dt_s > 0 else 0  # speed in mm/s
            # make speed negative since it's backward movement
            speed = -abs(speed)
            target_command['actualSpeed'] = speed
        else:
            # for left/right, use three distance measurements
            steer, speed = self.calculate_actual_steer_speed(distances['d1'], distances['d2'], distances['d3'], target_command["time"])
            
            # collect both steer and speed
            target_command['actualSteer'] = steer
            target_command['actualSpeed'] = speed

            # max angle detection logic (only for left/right directions)
            current_angle = abs(steer)
            
            if len(self.valid_angles) == 0:
                # first angle, just store it
                self.valid_angles.append(current_angle)
            else:
                # check if current angle is within tolerance of stored angles
                avg_stored = sum(self.valid_angles) / len(self.valid_angles)
                tolerance = avg_stored * self.MAX_ANGLE_TOLERANCE
                angle_diff = abs(current_angle - avg_stored)
                
                if angle_diff <= tolerance:
                    # within tolerance, add to the list
                    self.valid_angles.append(current_angle)
                    new_avg = sum(self.valid_angles) / len(self.valid_angles)
                    
                    # store the max angle for the appropriate direction
                    if direction == 'left':
                        self.max_angle_left = new_avg
                    elif direction == 'right':
                        self.max_angle_right = new_avg

                elif current_angle > avg_stored:
                    # current angle is larger and outside tolerance, discard old angles and start fresh
                    # this could be the new max angle
                    old_avg = avg_stored
                    self.valid_angles = [current_angle]
                    
                    # store the max angle for the appropriate direction
                    if direction == 'left':
                        self.max_angle_left = current_angle
                    elif direction == 'right':
                        self.max_angle_right = current_angle

        # check if this direction is completed and finalize max angle if needed
        if self.current_step >= len(self.commands[direction]):
            # finalize max angle for this direction if we have valid angles but haven't set max angle yet
            # (only for left/right directions, not backward)
            if direction != 'backward' and len(self.valid_angles) > 0:
                # if only one angle, use it directly; if multiple, calculate average
                if len(self.valid_angles) == 1:
                    final_max_angle = self.valid_angles[0]
                else:
                    final_max_angle = sum(self.valid_angles) / len(self.valid_angles)
                
                if direction == 'left' and self.max_angle_left is None:
                    self.max_angle_left = final_max_angle
                    
                elif direction == 'right' and self.max_angle_right is None:
                    self.max_angle_right = final_max_angle
            
            # reset valid_angles for the next direction
            self.valid_angles = []
            
            # mark this direction as completed
            if direction == 'left':
                self.left_completed = True
            elif direction == 'right':
                self.right_completed = True
            elif direction == 'backward':
                self.backward_completed = True
        
            self.socketio.emit('Calibration', {'action': 'calibration_done'}, room=socketId)
        else:
            self.socketio.emit('Calibration', {'action': 'measurements_received'}, room=socketId)


    def collect_calibration_points(self, type, use_scaling=False):
        """Collect calibration points from commands.
        
        Args:
            type: Type of calibration ('Steer' or 'Speed')
            use_scaling: If True and type is 'Steer', apply STEER_SCALING_FACTOR to steer values
        """
        points = []

        for command_type in self.commands:
            # skip backward direction when collecting steering data (backward only contributes to speed)
            if type == 'Steer' and command_type == 'backward':
                continue
                
            for command in self.commands[command_type]:
                if command['actual' + type] is not None and command['actual' + type + 'PWM'] is not None:
                    actual_value = command['actual' + type] * (-1 if command_type == 'left' and type == 'Steer' else 1)
                    
                    if use_scaling and type == 'Steer':
                        actual_value *= self.STEER_SCALING_FACTOR
                    
                    new_point = [actual_value, command['actual' + type + 'PWM']]
                    
                    if new_point not in points:
                        points.append(new_point)
                    
        points.sort(key=lambda x: x[0])
        
        for i in range(len(points)):
            points[i][1] = int(points[i][1])
        
        return points


    def _evaluate_scaled_poly(self, coef, scale, x_values):
        """
        Evaluates a polynomial with scaled integer coefficients, checking for overflow.
        This function is optimized for performance by using NumPy vectorization.
        """
        x_values = np.array(x_values, dtype=np.int64)
        res = np.zeros_like(x_values, dtype=np.int64)
        
        for c in coef:
            # check for potential overflow before multiplication
            # this is a vectorized check for all x_values at once
            if np.any(np.abs(res) > self.INT64_MAX // (np.max(np.abs(x_values)) + 1)):
                return None, True # overflow detected

            res = res * x_values + c
            
            # check for overflow after addition
            if np.any(np.abs(res) > self.INT64_MAX):
                return None, True # Overflow detected

        # final division by scale
        return res // scale, False


    def fit_cubic_spline(self, points, type):
        """Fit a cubic spline to the calibration points."""

        if len(points) < 2:
            print(f"\033[1;97m[ Calibration ] :\033[0m \033[1;93mWARNING\033[0m - Not enough points to calculate spline for {type}")
            return None, None

        grouped_points = {}
        for x, y in points:
            if y not in grouped_points:
                grouped_points[y] = []
            grouped_points[y].append(x)
        
        filtered_points = []
        for y, x_values in grouped_points.items():
            avg_x = np.mean(x_values)
            filtered_points.append([avg_x, y])
        
        # sort the points by the x-value after averaging
        filtered_points.sort(key=lambda p: p[0])

        if len(filtered_points) < 2:
            print(f"\033[1;97m[ Calibration ] :\033[0m \033[1;93mWARNING\033[0m - Not enough unique points after filtering to calculate spline for {type}")
            return None, None

        x_all, y_all = zip(*filtered_points)
        x_all, y_all = np.array(x_all), np.array(y_all)

        # create cubic spline interpolation
        # use natural boundary conditions (second derivative = 0 at boundaries)
        try:
            cs = CubicSpline(x_all, y_all, bc_type='natural')
        except Exception as e:
            print(f"\033[1;97m[ Calibration ] :\033[0m \033[1;91mERROR\033[0m - Could not create cubic spline for {type}: {e}")
            return None, None
        
        # extract spline coefficients for each segment
        # CubicSpline stores coefficients in shape (n_segments, 4) where each row is [a, b, c, d]
        # representing: a*(x-xi)^3 + b*(x-xi)^2 + c*(x-xi) + d
        spline_data = {
            'knots': x_all.tolist(),  # the x values (knot points)
            'coefficients': cs.c.T.tolist(),  # transpose to get (n_segments, 4) shape
            'n_segments': len(x_all) - 1
        }
        
        # calculate error by evaluating spline at original points
        y_pred = cs(x_all)
        err = np.mean((y_all - y_pred)**2)
        
        return spline_data, err


    def generate_code_from_spline(self, spline_data, type):
        """Generate C++ code from spline coefficients."""
        variable_name = "speed" if type == "Speed" else "steering"
        knots = spline_data['knots']
        coeffs = spline_data['coefficients']
        n_segments = spline_data['n_segments']
        
        # scale factor for integer arithmetic
        scale = 2**20  # use a fixed scale for splines
        
        # generate knot points array
        knots_str = ", ".join([str(int(k)) for k in knots])
        
        # generate coefficient arrays (scaled to integers)
        # each segment has 4 coefficients: [a, b, c, d] for a*(x-xi)^3 + b*(x-xi)^2 + c*(x-xi) + d
        coeff_arrays = []
        for seg_idx in range(n_segments):
            seg_coeffs = coeffs[seg_idx]
            # scale coefficients to integers
            scaled_coeffs = [int(round(c * scale)) for c in seg_coeffs]
            coeff_str = f"{{{scaled_coeffs[0]}LL, {scaled_coeffs[1]}LL, {scaled_coeffs[2]}LL, {scaled_coeffs[3]}LL}}"
            coeff_arrays.append(coeff_str)
        # add proper indentation for each coefficient line (12 spaces: 8 base + 4 for array contents)
        coeffs_str = ",\n            ".join(coeff_arrays)
        
        new_code = Template("""
        // Cubic spline evaluation with $n_segments segments
        static const int64_t knots[$n_knots] = {$knots_str};
        static const int64_t coeffs[$n_segments][4] = { 
            $coeffs_str
        };
        
        // Find the correct segment
        int segment = -1;
        for (int i = 0; i < $n_segments; i++) {
            if ($var_name >= knots[i] && $var_name <= knots[i + 1]) {
                segment = i;
                break;
            }
        }
        
        // Clamp to boundary segments if out of range
        if (segment == -1) {
            if ($var_name < knots[0]) segment = 0;
            else segment = $n_segments - 1;
        }
        
        // Evaluate cubic polynomial for this segment: a*(x-xi)^3 + b*(x-xi)^2 + c*(x-xi) + d
        int64_t dx = $var_name - knots[segment];
        int64_t dx2 = dx * dx;
        int64_t dx3 = dx2 * dx;
        
        y = (coeffs[segment][0] * dx3 + coeffs[segment][1] * dx2 + 
             coeffs[segment][2] * dx + coeffs[segment][3]) / ${scale}LL;
        
        /* Cubic spline interpolation with $n_segments segments
         * Each segment is defined by: a*(x-xi)^3 + b*(x-xi)^2 + c*(x-xi) + d
         * Coefficients are scaled by $scale for integer arithmetic
         */""").substitute(
            n_segments=n_segments,
            n_knots=len(knots),
            knots_str=knots_str,
            coeffs_str=coeffs_str,
            var_name=variable_name,
            scale=scale
        )
 
        return new_code


    def write_calibration_to_file(self, new_code, type):
        """Write the generated calibration code to the appropriate file."""
        if type == "Speed":
            filename = "calibration/templates/speedingmotor.cpp"
        elif type == "Steer":
            filename = "calibration/templates/steeringmotor.cpp"
        
        start_marker = "// POLYNOMIAL CODE START"
        end_marker = "// POLYNOMIAL CODE END"

        with open(filename, "r") as f:
            content = f.read()

        target_file = filename.split('/')[-1]

        pattern = re.compile(
            f"({start_marker})(.*?)({end_marker})",
            re.DOTALL,
        )
        replacement = r"\1\n" + new_code + r"\n        \3"
        new_content = re.sub(pattern, replacement, content)

        new_content = new_content.replace("#define calibrated 0", "#define calibrated 1")

        # override steering limits with calculated max angles
        if type == "Steer":
            offset_scaled = int(self.steering_offset * self.STEER_SCALING_FACTOR)
            
            if self.max_angle_right is not None:
                sup_limit = int(self.max_angle_right * self.STEER_SCALING_FACTOR)
                adjusted_sup_limit = sup_limit + offset_scaled
                new_content = re.sub(
                    r"#define calib_sup_limit \d+",
                    f"#define calib_sup_limit {adjusted_sup_limit}",
                    new_content
                )
                print(f"\033[1;97m[ Calibration ] :\033[0m \033[1;96mSet calib_sup_limit to {adjusted_sup_limit} (original: {sup_limit}, offset: {offset_scaled})")
            
            if self.max_angle_left is not None:
                inf_limit = int(-self.max_angle_left * self.STEER_SCALING_FACTOR)
                adjusted_inf_limit = inf_limit + offset_scaled
                new_content = re.sub(
                    r"#define calib_inf_limit -?\d+",
                    f"#define calib_inf_limit {adjusted_inf_limit}",
                    new_content
                )
                print(f"\033[1;97m[ Calibration ] :\033[0m \033[1;96mSet calib_inf_limit to {adjusted_inf_limit} (original: {inf_limit}, offset: {offset_scaled})")

        output_dir = "calibration/source/drivers"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        with open(f"{output_dir}/{target_file}", "w") as f:
            f.write(new_content)


    def calculate_polynomial_coefficients(self, type, use_scaling=True):
        """Calculates spline coefficients based on distances and writes to file.
        
        Args:
            type: Type of calibration ('Steer' or 'Speed')
            use_scaling: If True and type is 'Steer', apply STEER_SCALING_FACTOR to steer values
                        (default True for Nucleo deployment, set False for test runs)
        """
        points = self.collect_calibration_points(type, use_scaling=use_scaling)
        if len(points) < 2:
            return

        spline_data, err = self.fit_cubic_spline(points, type)
        if spline_data is None:
            return

        new_code = self.generate_code_from_spline(spline_data, type)
        self.write_calibration_to_file(new_code, type)


    def calculate_actual_steer_speed(self, y_back_right, x_back_right, x_front_right, dt):
        """
        Calculates steering angle and speed based on vehicle position change.
        Assumes W and H are in cm.
        Inputs:
            y_back_right: mm
            x_back_right: mm
            x_front_right: mm
            dt: deciseconds
        Returns:
            (steering_angle_degrees, speed_mm_per_second)
        """
        # convert inputs to cm for calculation, assuming self.W and self.H are in cm.
        y_br_cm = y_back_right / 10.0
        x_br_cm = x_back_right / 10.0
        x_fr_cm = x_front_right / 10.0

        # dt is in deciseconds, convert to seconds for speed calculation later.
        dt_s = dt / 10.0

        # H_vec is the normalized vector from Back-Right (BR) to Front-Right (FR)
        H_vec_x = (x_fr_cm - x_br_cm) / self.H
        
        # prevent math domain error for sqrt if abs(H_vec_x) is slightly > 1.0
        if abs(H_vec_x) > 1.0:
            H_vec_x = math.copysign(1.0, H_vec_x)

        H_vec_y = math.sqrt(1.0 - H_vec_x**2)
        
        # W_vec is the vector from BR to BL (perpendicular to H_vec)
        W_vec_x = H_vec_y
        W_vec_y = -H_vec_x

        x = x_br_cm + (self.W / 2) * W_vec_x
        y = y_br_cm + (self.W / 2) * W_vec_y

        denominator = self.W - 2 * x

        # if denominator is close to zero, it means the car went straight
        if abs(denominator) < self.EPS:
            # y_br_cm is distance in cm, dt_s is time in s. Speed is in cm/s.
            speed_cms = y_br_cm / dt_s if dt_s > 0 else 0
            return 0, speed_cms * 10  # convert to mm/s

        circle_x = (self.W**2 / 4 - x**2 - y**2) / denominator
        r = circle_x - self.W / 2
        
        if abs(r) < self.EPS:
            # cannot determine steering angle if radius is zero. treat as straight.
            speed_cms = y_br_cm / dt_s if dt_s > 0 else 0
            return 0, speed_cms * 10 # convert to mm/s

        theta = math.atan2(y, circle_x - x)
        distance_cm = r * theta
        speed_cms = distance_cm / dt_s if dt_s > 0 else 0
        
        phi = math.atan2(self.H, r)

        return math.degrees(phi), speed_cms * 10 # convert speed to mm/s


    def complete_calibration_process(self, socketId):
        """Complete the calibration process."""
        self.current_step = 0
        self.socketio.emit('Calibration', {'action': 'calibration_done'}, room=socketId)


    def reset_current_step(self):
        """Reset the current step."""
        self.current_step = 0
        self.valid_angles = []


    def start_calibration_process(self):
        """Start the calibration process."""
        self.reset_current_step()
        self.commands = copy.deepcopy(self.commands_template)
        self.left_completed = False
        self.right_completed = False
        self.test_run_completed = False
        self.backward_completed = False
        self.max_angle_left = None
        self.max_angle_right = None
        self.valid_angles = []
        self.steering_offset = 0
        self.zero_offset_spline_data_for_frontend = None


    def stop_calibration_process(self):
        """Stop the current calibration process."""
        self.reset_current_step()
        self.commands = copy.deepcopy(self.commands_template)
        self.left_completed = False
        self.right_completed = False
        self.test_run_completed = False
        self.backward_completed = False
        self.max_angle_left = None
        self.max_angle_right = None
        self.valid_angles = []
        self.steering_offset = 0
        self.zero_offset_spline_data_for_frontend = None


    def create_source_zip(self):
        """Create a zip file of the source folder and return as base64 string."""
        try:
            zip_buffer = BytesIO()
            
            source_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'source')
            source_path = os.path.abspath(source_path)
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for root, dirs, files in os.walk(source_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, os.path.dirname(source_path))
                        zip_file.write(file_path, arcname)
            
            zip_buffer.seek(0)
            zip_base64 = base64.b64encode(zip_buffer.getvalue()).decode('utf-8')
            return zip_base64
            
        except Exception as e:
            print(f"\033[1;97m[ Calibration ] :\033[0m \033[1;91mError creating zip file: {str(e)}\033[0m")
            return None

    
    def _init_subscribers(self):
        """Initialize the subscribers."""
        self.calibPWMDataSubscriber = messageHandlerSubscriber(self.queuesList, CalibPWMData, "lastOnly", True)
        self.calibRunDoneSubscriber = messageHandlerSubscriber(self.queuesList, CalibRunDone, "lastOnly", True)


    def _init_senders(self):
        """Initialize the senders."""
        self.controlCalibSender = messageHandlerSender(self.queuesList, ControlCalib)
