#!/usr/bin/env python
# license removed for brevity
import rospy
from std_msgs.msg import String
import gpstracker
import time
import math

list_cars = []

def listener_car():
    pub = rospy.Publisher('Visual_Data/Car', String, queue_size=10)
    rospy.init_node('Listener_Cars', anonymous=False)
    rate = rospy.Rate(4)
    
    cars = [4]
    for x in cars:
        obj = gpstracker.GpsTracker(x)
        obj.start()
        list_cars.append(obj)
    time.sleep(2)
        
    while not rospy.is_shutdown():
        stringa = "{"
        for child in list_cars:
            try:
                coor = child.coor()
                id = child.ID()
                pos = complex(coor['coor'][0])
#                 print coor['coor'][1]
                x = pos.real
                y = pos.imag
                orientation = coor['coor'][1]
                x_rot = orientation.real
                y_rot = orientation.imag
                theta = math.atan2(y_rot, x_rot)*180/3.14
                theta = theta-90
                if theta < -180: theta = 360+theta
                stringa += '"' + str(id) + '":{"x":' + str(x) + ', "y":' + str(y) + ', "theta":' + str(theta) + '},'
            except: pass
        stringa = stringa[:-1]
        stringa += "}"
        
#         print(coor['coor'], x, y, theta)

        pub.publish(stringa)
        rate.sleep()
        
    print("powering down")
    for child in list_cars:
        
        child.stop()
        child.join()
         
if __name__ == '__main__':
    try:
        listener_car()
    except rospy.ROSInterruptException:
        pass