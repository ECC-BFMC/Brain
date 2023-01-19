import threading


class MarkerDataSet:
    """ Base class for collecting the detected marker pose. 
    """
    def __init__(self, markerDic={}):
        self._marker_dic = markerDic
        self.locker = threading.Lock()

    def saveitem(self, id, obs, x, y):
        """Save a new position in the marker pose in the data set.
        
        Parameters
        ----------
        id : int
            id of the car
        obs : int 
            Obstacle id, taken from documentation
        x : float
            x coordinate of obstacle
        y : float
            y coordinate of obstacle  
        """
        with self.locker:
            if id in self._marker_dic:
                a = len(self._marker_dic[id]) + 1
                self._marker_dic[id][a] = {'obstacle_id':obs, 'x':x, 'y':y}
            else:
                self._marker_dic[id] = {1:{'obstacle_id':obs, 'x':x, 'y':y}}
    
    def getlist(self):
        """Get timestamp and pose of markerId
        
        Parameters
        ----------
        markerId : int
            The identification number of marker.
        """
        with self.locker:
            return self._marker_dic
            
        