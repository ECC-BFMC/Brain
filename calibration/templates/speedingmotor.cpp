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

#include <drivers/speedingmotor.hpp>

#define calibrated 0
#define calib_sup_limit 500
#define calib_inf_limit -500

namespace drivers{
    /**
     * @brief It initializes the pwm parameters and it sets the speed reference to zero position, and the limits of the car speed.
     * 
     * @param f_pwm_pin               pin connected to servo motor
     * @param f_inf_limit         inferior limit 
     * @param f_sup_limit         superior limit
     * 
     */
    CSpeedingMotor::CSpeedingMotor(
            PinName f_pwm_pin, 
            int f_inf_limit, 
            int f_sup_limit,
            UnbufferedSerial& f_serial
        )
        : m_pwm_pin(f_pwm_pin)
        , m_inf_limit(f_inf_limit)
        , m_sup_limit(f_sup_limit)
        , m_serial(f_serial)
    {
        // Set the ms_period on the pwm_pin
        m_pwm_pin.period_ms(ms_period); 
        // Set position to zero
        m_pwm_pin.pulsewidth_us(zero_default);
    };

    /** @brief  CSpeedingMotor class destructor
     */
    CSpeedingMotor::~CSpeedingMotor()
    {
    };

    /** @brief  It modifies the speed reference of the brushless motor, which controls the speed of the wheels. 
     *
     *  @param f_speed      speed in mm/s, where the positive value means forward direction and negative value the backward direction. 
     */
    void CSpeedingMotor::setSpeed(int f_speed)
    {
        pwm_value = zero_default;

        if (f_speed != 0) {
            if (calibrated == 1)
            {
                pwm_value = computePWMPolynomial(f_speed);
            }
            else {
                pwm_value = interpolate(-f_speed, speedValuesP, speedValuesN, pwmValuesP, pwmValuesN, 25);
            }
        }
        
        m_pwm_pin.pulsewidth_us(pwm_value);
    };

    /** @brief  It converts speed reference to duty cycle for pwm signal. 
     * 
     *  @param f_speed    speed
     *  \return        new `pwm_value`
    */
    int CSpeedingMotor::computePWMPolynomial(int speed)
    {
        int64_t y=zero_default;
        // POLYNOMIAL CODE START
        // POLYNOMIAL CODE END
        return (int)y;
    }

    /** @brief  It puts the brushless motor into brake state, 
     */
    void CSpeedingMotor::setBrake()
    {
        m_pwm_pin.write(zero_default);
    };

    /**
    * @brief Interpolates values based on speed input.
    *
    * This function interpolates `pwmValues` based on the provided `speed` input.
    * The interpolation is made using `speedValuesP` and `speedValuesN` as reference values.
    *
    * @param speed The input speed value for which the values need to be interpolated.
    * @param speedValuesP Positive reference values for speed.
    * @param speedValuesN Negative reference values for speed.
    * @param pwmValuesP PWM values corresponding to speedValueP
    * @param pwmValuesN PWM values corresponding to speedValueN
    * @param size The size of the arrays.
    * @return The new value for `pwm_value`
    */
    int16_t CSpeedingMotor::interpolate(int speed, const int speedValuesP[], const int speedValuesN[], const int pwmValuesP[], const int pwmValuesN[], int size)
    {
        const int SCALE = 1000; // Precision factor for fixed-point arithmetic

        if(speed == 0) return zero_default;
        if(speed >= speedValuesP[size-1]) return pwmValuesP[size-1];
        if(speed <= speedValuesN[size-1]) return pwmValuesN[size-1];

        // For negative speed values
        if(speed <= speedValuesP[0]){
            if(speed > 0) return pwmValuesP[0];
            if (speed >= speedValuesN[0])
            {
                return pwmValuesN[0];
            }
            else {
                for(uint8_t i = 1; i < size; i++)
                {
                    if (speed >= speedValuesN[i])
                    {
                        int deltaPWM = (pwmValuesN[i] - pwmValuesN[i-1]) * SCALE;
                        int deltaSpeed = speedValuesN[i] - speedValuesN[i-1];
                        int slope = deltaPWM / deltaSpeed; // Compute slope in fixed-point
                        int interpFixed = pwmValuesN[i-1] * SCALE + slope * (speed - speedValuesN[i-1]);
                        return (int16_t)(interpFixed / SCALE);
                    }
                }
            }
        }

        // For positive speed values
        for(uint8_t i = 1; i < size; i++)
        {
            if (speed <= speedValuesP[i])
            {
                int deltaPWM = (pwmValuesP[i] - pwmValuesP[i-1]) * SCALE;
                int deltaSpeed = speedValuesP[i] - speedValuesP[i-1];
                int slope = deltaPWM / deltaSpeed; // Compute slope in fixed-point
                int interpFixed = pwmValuesP[i-1] * SCALE + slope * (speed - speedValuesP[i-1]);
                return (int16_t)(interpFixed / SCALE);
            }
        }
        
        return zero_default;
    }

    /**
     * @brief It verifies whether a number is in a given range
     * 
     * @param f_speed value 
     * @return inf_limit, if the value is lower than the range's low
     * @return sup_limit, if the value is higher than the range's high
    */
    int CSpeedingMotor::inRange(int f_speed){

        if(calibrated == 1){
            if(f_speed < calib_inf_limit) return calib_inf_limit;
            if(f_speed > calib_sup_limit) return calib_sup_limit;
            return f_speed;
        } else{
            if(f_speed < m_inf_limit) return m_inf_limit;
            if(f_speed > m_sup_limit) return m_sup_limit;
            return f_speed;
        }

    };
}; // namespace hardware::drivers