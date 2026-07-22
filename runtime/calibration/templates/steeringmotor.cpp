/**
 * Copyright (c) 2019, Bosch Engineering Center Cluj and BFMC organizers
 * All rights reserved.
 * 
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:

 * 1. Redistributions of source code must retain the above copyright notice, this
 *    list of conditions and the following disclaimer.

 * 2. Redistributions in binary form must reproduce the above copyright notice,
 *    this list of conditions and the following disclaimer in the documentation
 *    and/or other materials provided with the distribution.

 * 3. Neither the name of the copyright holder nor the names of its
 *    contributors may be used to endorse or promote products derived from
 *    this software without specific prior written permission.

 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
 * FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
 * DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
 * SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
 * CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
 * OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE
*/

#include <drivers/steeringmotor.hpp>

#define scaling_factor_1 10
#define scaling_factor_2 100
#define calibrated 0
#define calib_sup_limit 250
#define calib_inf_limit -250

namespace drivers{
    /**
     * @brief It initializes the pwm parameters and it sets the steering in zero position, the limits of the input degree value.
     * 
     * @param f_pwm               pin connected to servo motor
     * @param f_inf_limit         inferior limit 
     * @param f_sup_limit         superior limit
     * 
     */
    CSteeringMotor::CSteeringMotor(
            PinName f_pwm_pin, 
            int f_inf_limit, 
            int f_sup_limit,
            UnbufferedSerial& f_serial
        )
        :m_pwm_pin(f_pwm_pin)
        ,m_inf_limit(f_inf_limit)
        ,m_sup_limit(f_sup_limit)
        , m_serial(f_serial)
    {
        // Wait for Nucleo startup stabilization to prevent erratic motor 
        // behavior caused by power-on reset cycles affecting PWM signals
        // potentially resulting in chaotic left/right motor oscillations. 
        ThisThread::sleep_for(chrono::milliseconds(10000));

        m_pwm_pin.pulsewidth_us(zero_default);
    };


    /** @brief  CSteeringMotor class destructor
     */
    CSteeringMotor::~CSteeringMotor()
    {
    };
    
    /**
    * @brief Interpolates values based on steering input.
    *
    * This function interpolates `pwmValues` based on the provided `steering` input.
    * The interpolation is made using `steeringValueP` and `steeringValueN` as reference values.
    *
    * @param steering The input steering value for which the values need to be interpolated.
    * @param steeringValueP Positive reference values for steering (right direction).
    * @param steeringValueN Negative reference values for steering (left direction).
    * @param pwmValuesP PWM values corresponding to steeringValueP
    * @param pwmValuesN PWM values corresponding to steeringValueN
    * @param size The size of the arrays.
    * @return The new value for `pwm_value`
    */
    int16_t CSteeringMotor::interpolate(int steering, const int steeringValueP[], const int steeringValueN[], const int pwmValuesP[], const int pwmValuesN[], int size)
    {
        const int SCALE = 1000; // Precision factor for fixed-point arithmetic

        if(steering == 0) return pwmValuesP[0];
        if(steering >= steeringValueP[size-1]) return pwmValuesP[size-1];
        if(steering <= steeringValueN[size-1]) return pwmValuesN[size-1];

        // For negative steering values
        if(steering < 0){
            for(uint8_t i = 1; i < size; i++)
            {
                if (steering >= steeringValueN[i])
                {
                    int deltaPWM = (pwmValuesN[i] - pwmValuesN[i-1]) * SCALE;
                    int deltaSteering = steeringValueN[i] - steeringValueN[i-1];
                    int slope = deltaPWM / deltaSteering; // Compute slope in fixed-point
                    int interpFixed = pwmValuesN[i-1] * SCALE + slope * (steering - steeringValueN[i-1]);
                    return (int16_t)(interpFixed / SCALE);
                }
            }
        }

        // For positive steering values
        for(uint8_t i = 1; i < size; i++)
        {
            if (steering <= steeringValueP[i])
            {
                int deltaPWM = (pwmValuesP[i] - pwmValuesP[i-1]) * SCALE;
                int deltaSteering = steeringValueP[i] - steeringValueP[i-1];
                int slope = deltaPWM / deltaSteering; // Compute slope in fixed-point
                int interpFixed = pwmValuesP[i-1] * SCALE + slope * (steering - steeringValueP[i-1]);
                return (int16_t)(interpFixed / SCALE);
            }
        }
        
        return pwmValuesP[0];
    }

    /** @brief  It modifies the angle of the servo motor, which controls the steering wheels. 
     *
     *  @param f_angle      angle degree, where the positive value means right direction and negative value the left direction. 
     */
    void CSteeringMotor::setAngle(int f_angle)
    {
        pwm_value = zero_default;

        if(calibrated == 1)
        {
            pwm_value = computePWMPolynomial(f_angle);
        }
        else{
            pwm_value = interpolate(f_angle, steeringValueP, steeringValueN, pwmValuesP, pwmValuesN, 3);
        }

        m_pwm_pin.pulsewidth_us(pwm_value);
        
    };

    /** @brief  It converts angle degree to duty cycle for pwm signal. 
     * 
     *  @param f_angle    angle degree
     *  \return     new `pwm_value`
     */
    int CSteeringMotor::computePWMPolynomial(int steering)
    {
        int64_t y=zero_default;
        // POLYNOMIAL CODE START
        // POLYNOMIAL CODE END
        return (int)y;
    }

    /**
     * @brief It verifies whether a number is in a given range
     * 
     * @param f_angle value 
     * @return inf_limit, if the value is lower than the range's low
     * @return sup_limit, if the value is higher than the range's high
    */
    int CSteeringMotor::inRange(int f_angle){

        if(calibrated == 1){
            if(f_angle < calib_inf_limit) return calib_inf_limit;
            if(f_angle > calib_sup_limit) return calib_sup_limit;
            return f_angle;
        } else{
            if(f_angle < m_inf_limit) return m_inf_limit;
            if(f_angle > m_sup_limit) return m_sup_limit;
            return f_angle;
        }

    };
}; // namespace hardware::drivers