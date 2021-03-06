"""This module implements some utilities for a
gradient-based coverage algorithm.
"""

import numpy as np
import random as rdm
import tf.transformations as tfm
import geometry_msgs.msg as gms
import quad_control.msg as qms
import matplotlib.pyplot as plt

# For rosparam
import rospy as rp


rdm.seed(890630)


TOLERANCE = 0.005
NUM_LANDMARKS = 400
DOMAIN_SIZE = 2.5

__OPTIMAL_DISTANCE = 0.5
__sq = np.sqrt(NUM_LANDMARKS)






def __square_boundary_function(bounds, position):
    xmin = bounds[0][0]
    xmax = bounds[0][1]
    ymin = bounds[1][0]
    ymax = bounds[1][1]
    x = position[0]
    y = position[1]
    return min([xmax-x, x-xmin, ymax-y, y-ymin])
    



def __square_boundary_function_gradient(bounds, position):
    xmin = bounds[0][0]
    xmax = bounds[0][1]
    ymin = bounds[1][0]
    ymax = bounds[1][1]
    x = position[0]
    y = position[1]
    index = np.argmin([xmax-x, x-xmin, ymax-y, y-ymin])
    if index==0:
        return np.array([-1,0])
    elif index==1:
        return np.array([1,0])
    elif index==2:
        return np.array([0,-1])
    elif index==3:
        return np.array([0,1])
        


def remove_parallel_component(vec1, vec2):
    return vec1 - vec1.dot(vec2)/np.linalg.norm(vec2)**2*vec2

def projection(vec1, vec2):
    return vec1.dot(vec2)/np.linalg.norm(vec2)**2*vec2







def point_2d_array_from_landmarks(landmarks):
    array = qms.Point2DArray()
    for lmk in landmarks:
        array.data.append(lmk.to_point_2d())
    return array
    

def landmarks_from_point_2d_array(array):
    landmarks = []
    for point in array.data:
        landmarks.append(Landmark.from_point_2d(point))
    return landmarks






def versor_gradient(ver):
    return np.array([-ver[1], ver[0]])
    




def distance_factor(distance):
    return (1.0/__OPTIMAL_DISTANCE)/(1.0+(distance/__OPTIMAL_DISTANCE)**2)
     
def distance_factor_derivative_over_distance(distance):
    return -(2.0/__OPTIMAL_DISTANCE**3)/(1.0+(distance/__OPTIMAL_DISTANCE)**2)**2

    
    
    
    
def versor_from_angle(theta):
    return np.array([np.cos(theta), np.sin(theta)])
    
def angle_from_versor(ver):
    return np.arctan2(ver[1], ver[0])
    
    
    
    


class Landmark:


    global DOMAIN_SIZE
    global NUM_LANDMARKS


    def __init__(self, x, y):
        self.__x = x
        self.__y = y


    def copy(self):
        return Landmark(self.__x, self.__y)


    @classmethod
    def from_point_2d(cls, point):
        x = point.x
        y = point.y
        return cls(x=x, y=y)


    def to_point_2d(self):
        return qms.Point2D(x=self.__x, y=self.__y)


    def __str__(self):
        string = ''
        string += '\nx: ' + str(self.__x)
        string += '\ny: ' + str(self.__y)
        return string


    def visibility(self, x, y, theta):
        q = np.array([self.__x, self.__y])
        p = np.array([x, y])
        v = versor_from_angle(theta)
        #if (q-p).dot(v)<=0.0:
        #    return 0.0
        d = np.linalg.norm(p-q)
        return -distance_factor(d)*(p-q).dot(v)


    def position_visibility_gradient(self, x, y, theta):
        q = np.array([self.__x, self.__y])
        p = np.array([x, y])
        v = versor_from_angle(theta)
        #if (q-p).dot(v)<=0.0:
        #    return np.zeros(2)
        d = np.linalg.norm(p-q)
        mat = -distance_factor_derivative_over_distance(d)*np.outer(p-q,p-q) - distance_factor(d)*np.eye(2)
        return mat.dot(v)


    def orientation_visibility_gradient(self, x, y, theta):
        q = np.array([self.__x, self.__y])
        p = np.array([x, y])
        v = versor_from_angle(theta)
        #if (q-p).dot(v)<=0.0:
        #    return 0.0
        d = np.linalg.norm(p-q)
        return -distance_factor(d)*versor_gradient(v).dot(p-q)


    def draw(self, color):
        sq = np.sqrt(NUM_LANDMARKS)
        plt.scatter(self.__x, self.__y,
            color=color,
            s=0.5e4*DOMAIN_SIZE/NUM_LANDMARKS,
            alpha=0.3,
            edgecolor=color,
            linewidth=2,
            marker='o')







class Agent:


    global TOLERANCE


    @classmethod
    def from_pose2d_landmark_array(cls, pose, array):
        x = pose.x
        y = pose.y
        theta = pose.theta
        landmarks = [Landmark.from_point_2d(point) for point in array.data]
        return cls(x, y, theta, landmarks)


    def __init__(self, x, y, theta, landmarks):
        self.__x = x
        self.__y = y
        self.__theta = theta
        self.__landmarks = landmarks


    def __str__(self):
        string = ''
        string += '\nx: ' + str(self.__x)
        string += '\ny: ' + str(self.__y)
        string += '\ntheta: ' + str(self.__theta)
        string += '\nnum landmarks: ' + str(len(self.__landmarks))
        return string


    def get_pose(self):
        return self.__x, self.__y, self.__theta


    def get_pose_2d(self):
        return gms.Pose2D(self.__x, self.__y, self.__theta)
        
        
    def get_landmarks(self):
        return self.__landmarks
        
        
    def get_landmark_array(self):
        return point_2d_array_from_landmarks(self.__landmarks)
        
        
    def set_pose(self, x, y, theta):
        self.__x = x
        self.__y = y
        self.__theta = theta
        
        
    def set_landmarks(self, landmarks):
        self.__landmarks = landmarks


    def coverage(self):
        cov = 0.0
        for lmk in self.__landmarks:
            cov += lmk.visibility(self.__x, self.__y, self.__theta)
        return cov


    def position_coverage_gradient(self):
        grad = np.zeros(2)
        for lmk in self.__landmarks:
            grad += lmk.position_visibility_gradient(self.__x, self.__y, self.__theta)
        return grad
        

    def orientation_coverage_gradient(self):
        grad = 0.0
        for lmk in self.__landmarks:
            grad += lmk.orientation_visibility_gradient(self.__x, self.__y, self.__theta)
        return grad


    def trade(self, x, y, theta, landmarks):
        indexes_i_remove = []
        indexes_you_remove = []
        landmarks_i_add = []
        landmarks_you_add = []
        success = False
        for index, lmk in enumerate(self.__landmarks):
            if lmk.visibility(x, y, theta) > lmk.visibility(self.__x, self.__y, self.__theta) + TOLERANCE:
                indexes_i_remove.append(index)
                landmarks_you_add.append(lmk)
                success = True
        for index, lmk in enumerate(landmarks):
            if lmk.visibility(self.__x, self.__y, self.__theta) > lmk.visibility(x, y, theta) + TOLERANCE:
                indexes_you_remove.append(index)
                landmarks_i_add.append(lmk)
                success = True
        assert len(indexes_i_remove) == len(landmarks_you_add)
        assert len(indexes_you_remove) == len(landmarks_i_add)
        self.update_landmarks(indexes_i_remove, landmarks_i_add)
        return success, indexes_you_remove, landmarks_you_add


    def update_landmarks(self, indexes_i_remove, landmarks_i_add):
        filtered_landmarks = [self.__landmarks[i] for i in filter(lambda i: not i in indexes_i_remove, range(len(self.__landmarks)))]
        self.__landmarks = filtered_landmarks
        for landmark in landmarks_i_add:
            self.__landmarks.append(landmark)


    def draw(self, color):
        x = self.__x
        y = self.__y
        th = self.__theta
        al = 0.2*DOMAIN_SIZE
        plt.scatter(x, y, c=color, marker="o", facecolor='k')
        plt.axes().arrow(x, y, al*np.cos(th), al*np.sin(th),
                 head_width=0.35*al, head_length=0.35*al, fc=color, ec='k')
        for lmk in self.__landmarks:
            lmk.draw(color)







LANDMARKS = []

for index in range(NUM_LANDMARKS):
    x = 0.4*(float(index//__sq)/__sq*2.0*DOMAIN_SIZE-DOMAIN_SIZE+DOMAIN_SIZE/__sq)
    y = 0.4*(float(np.mod(index, __sq))/__sq*2.0*DOMAIN_SIZE-DOMAIN_SIZE+DOMAIN_SIZE/__sq)
    #x = 0.5*DOMAIN_SIZE*np.cos(2*np.pi*index/NUM_LANDMARKS)
    #y = 0.5*DOMAIN_SIZE*np.sin(2*np.pi*index/NUM_LANDMARKS)
    LANDMARKS.append(Landmark(x, y))


AGENTS_NAMES = 'Axel Bo'.split()
AGENTS_COLORS = {'Axel':'blue', 'Bo':'red', 'Calle':'green', 'David':'yellow', 'Emil':'brown'}

INITIAL_LANDMARKS_LISTS = {}
for name in AGENTS_NAMES:
    INITIAL_LANDMARKS_LISTS[name] = []

for lmk in LANDMARKS:
    name = rdm.choice(AGENTS_NAMES)
    INITIAL_LANDMARKS_LISTS[name].append(lmk)
    
INITIAL_POSES = {}
INITIAL_POSES['Axel'] = (0.0, 2.0, 0.0)
INITIAL_POSES['Bo'] = (0.0, -2.0, 0.0)
INITIAL_POSES['Calle'] = (0.0, 0.0, 0.0)
INITIAL_POSES['David'] = (0.0, 0.0, 2*np.pi/3)
INITIAL_POSES['Emil'] = (0.0, 0.0, -2*np.pi/3)
#idx = 0
#for name in AGENTS_NAMES:
#    INITIAL_POSES[name] = (0.0, 0.0, 2*np.pi*idx/len(AGENTS_NAMES))
#    idx += 1


__BOUNDARIES = {}
__BOUNDARIES['Axel'] = ((-2.5,-2.5), (1.0, 2.5))
__BOUNDARIES['Bo'] = ((-2.5, 2.5), (-2.5, -1.0))
__BOUNDARIES['Calle'] = ((-2.5, 2.5), (-2.5, 2.5))
__BOUNDARIES['David'] = ((-2.5, 2.5), (-2.5, 2.5))
__BOUNDARIES['Emil'] = ((-2.5, 2.5), (-2.5, 2.5))


BOUNDARY_FUNCTIONS = {}
BOUNDARY_FUNCTIONS_GRADIENTS = {}
#for nm in AGENTS_NAMES:
#    BOUNDARY_FUNCTIONS[name] = lambda x: __square_boundary_function(__BOUNDARIES[name], x)
#    BOUNDARY_FUNCTIONS_GRADIENTS[name] = lambda x: __square_boundary_function_gradient(__BOUNDARIES[name], x)

BOUNDARY_FUNCTIONS['Axel'] = lambda x: __square_boundary_function(__BOUNDARIES['Axel'], x)
BOUNDARY_FUNCTIONS_GRADIENTS['Axel'] = lambda x: __square_boundary_function_gradient(__BOUNDARIES['Axel'], x)
BOUNDARY_FUNCTIONS['Bo'] = lambda x: __square_boundary_function(__BOUNDARIES['Bo'], x)
BOUNDARY_FUNCTIONS_GRADIENTS['Bo'] = lambda x: __square_boundary_function_gradient(__BOUNDARIES['Bo'], x)

#'''Test'''
#agents = [Agent(
#*INITIAL_POSES[name],
#landmarks=INITIAL_LANDMARKS_LISTS[name]
#) for name in AGENTS_NAMES]

#plt.figure()
#for agent in agents:
#    agent.draw('blue')
#plt.xlim((-DOMAIN_SIZE, DOMAIN_SIZE))
#plt.ylim((-DOMAIN_SIZE, DOMAIN_SIZE))

#success, remove, add = agents[0].trade(*agents[1].get_pose(), landmarks=agents[1].get_landmarks())
#agents[1].update_landmarks(remove, add)

#plt.figure()
#for agent in agents:
#    agent.draw('blue')
#plt.xlim((-DOMAIN_SIZE, DOMAIN_SIZE))
#plt.ylim((-DOMAIN_SIZE, DOMAIN_SIZE))

#plt.show()
