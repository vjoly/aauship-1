'''
Created on 2012.11.12.

@author: Fodi
'''

import math
import numpy
import scipy
import matplotlib.pyplot as plt
import FunctionLibrary as FL
import ObjectLibrary as OL
import KalmanFilter as KF
import time

'''
#############################################
# General Ship class
#############################################
'''   
class O_Ship:
    def __init__(self, init_position, statelog, swplog):
        '''
        Initializes the parameters of the ship
        - Parameters to calculate proper turn paths
        - Initial sensor parameters for the control
        - Initial start waypoint
        - Navigation parameters (FollowDistance)
        '''
        self.log = statelog
        self.swplog = swplog
        self.Pos = init_position
        
        self.retpos = self.Pos
        
        self.NextSWP = self.Pos
        
        self.Speed = 0;
        self.Sigma_max = 0.3;
        self.Kappa_max = 0.3;
        
        self.counter1 = 0;
        
        self.LastWP = 3;
        self.SWP = 0;
        self.SegmentCoords = 0;
        self.Current_SWP = 0;
        
        self.NextSWP_No = 0;
        self.NextSWP_validity = 0;
        
        self.FollowDistance = 2
        
        self.v = 0
        self.omega = 0
        self.Theta = 0
        
        self.x = numpy.matrix([[0],[0],[0]])
        
        self.mark = 0
        self.EndPath = 0
        self.WPsEnded = 0
        
        self.Filter = KF.Filter()
        
        self.correction = 0
        
        self.mp = OL.O_PosData(0,0,1,1)
        self.MP = []
        self.flip = 1
        '''
        The control matrices
        '''
        
        self.N = numpy.matrix([[2.1366547e+001, 1.5569542e-016], [ 8.3542070e-016, 2.2764131]])
        
        self.N = numpy.matrix([[19.5956,0],[0,2.2743]]) # ts = 0.33
        
        self.F = numpy.matrix([[1.6012147e+001, 1.5569542e-016, 3.3824418e-016], [8.3542070e-016, 2.2764131e+000, 2.2219859e+000]])
        
        self.F = numpy.matrix([[10.6956, 0, 0],[0, 2.2743, 0.6681]]) # ts = 0.33
        
        self.states = numpy.matrix([[0],[0],[0],[0],[0]])
        
    def SetWaypoints(self, WPC):
        '''
        A method to hand-set the required waypoints
        
        Accepts a 2*n shaped numpy array
        where A[0,n] is the X, A[1,n] is the Y coordinate
        '''
        WP_Planner = OL.O_PathWayPoints();
        WP_Planner.SetWP(WPC)
        self.Waypoints = WP_Planner
        
        self.EndPath = 0
    
    def Plan_WP(self, coastline, decimation, safety):
        
        '''
        Plans Waypoints in a snake-way if the coastline parameter is known
        '''
        
        WP_Planner = OL.O_PathWayPoints();
        WP_Planner.PlanWP(coastline, len(coastline), decimation, safety);
        self.Waypoints = WP_Planner
        self.AddRelativeCourse(self.retpos)
        
    def Plan_FullPath(self, plotit = 0):
        
        '''
        # Plans and plots all of the Sub-WayPoints of the system.
        # Should not be used under normal circumstances
        '''
        
        PrevRange = 0;
        i = 0;
        data = self.Waypoints.get_WayPoints();
        FullPathLength = len(data[0]) - self.LastWP;
        self.Lines = numpy.zeros(FullPathLength);
        self.Turns = numpy.zeros(FullPathLength);
        
        while i < FullPathLength:
            skip = self.Plan_LocalPath(PrevRange);
            
            if skip == 'Path ended':
                print('The coast-information is missing, no further path can be calculated');
                break;
            
            if plotit == 'Plot':
                self.PlotPath('k');
        
            PrevRange = self.Path.Range;
            i = i + 1;
            self.LastWP = self.LastWP + skip;
        
    def Plan_LocalPath(self, PrevRange):
        
        '''
        Plans the local course over the next waypoint
        Contains a straight path and the required turn
        Outputs a list of SWP-s
        '''
        
        self.Current_SWP = self.SegmentCoords;
            
        self.NextSWP_No = 0;
        self.NextSWP_validity = 0;
        
        gamma = 0;
        i = 0;
        
        while gamma <= 0 or gamma >= math.pi:
        
            i = i + 1;
            
            '''Turning waypoint''' 
            n = self.LastWP + 1 + i; 
            
            wpnum = len(self.Waypoints.get_WayPoints()[0])
            print (wpnum,n)
            
            try:
                
                if n+1 >= wpnum:
                    
                    Nm = self.Waypoints.get_SingleWayPoint(n - i);
                    Nt = self.Waypoints.get_SingleWayPoint(n);
                    Np = self.retpos;
                    
                else:
                    
                    Nm = self.Waypoints.get_SingleWayPoint(n - i);
                    Nt = self.Waypoints.get_SingleWayPoint(n);
                    Np = self.Waypoints.get_SingleWayPoint(n + 1);
                
            except IndexError:

                return(-1);

            
            
            gamma = FL.CosLaw(Nm, Nt, Np);
            
        
        
        self.Path = OL.O_LocalPath(gamma, self.Sigma_max, self.Kappa_max);
        
        definition = 20;
        self.Path.FitPath(definition/4);
        self.Path.PositionPoly(Nm, Nt, Np);

        '''fitline'''
        Range = self.Path.get_Range();
        self.Straight = OL.O_StraightPath(Nt, Nm, Range, PrevRange);
        self.Straight.FitLine(0.07);
        
        return i;
    
    def get_PathSegment(self):
        
        '''
        Forms the calculates Straight path and Turn path into an ordered list of points
        If WPsEnded == 1 the only SWP is the starting point
        '''
        
        
        
            
        try:
            LS = OL.O_PosData(self.Straight.SubWP[0,0], self.Straight.SubWP[1,0], float('NaN'), float('NaN'))
            LF = OL.O_PosData(self.Straight.SubWP[0,len(self.Straight.SubWP)-1], self.Straight.SubWP[1,len(self.Straight.SubWP)-1], float('NaN'), float('NaN'))
            CS = OL.O_PosData(self.Path.TurnSWP[0,0], self.Path.TurnSWP[1,0], float('NaN'), float('NaN'))
            CF = OL.O_PosData(self.Path.TurnSWP[0,len(self.Path.TurnSWP)-1], self.Straight.SubWP[1,len(self.Path.TurnSWP)-1], float('NaN'), float('NaN'))
            '''
            The Turn and Straight is received as a list of points.
            The method checks, whether the start or end point of the Straight is closer to the
            position of the Ship. If required, the order of the Straight is mirrored.
            '''
            if FL.Distance(self.Pos, LS) > FL.Distance(self.Pos, LF):
                line = numpy.fliplr(self.Straight.SubWP);
                LF = LS
            else:
                line = self.Straight.SubWP
            '''
            Then the method checks the relation of the Turn path Start and End points
            to the (new) End point of the Straight. If required, the Turn is mirrored as well.
            ''' 
            if FL.Distance(LF, CS) > FL.Distance(LF, CF):
                curve = numpy.fliplr(self.Path.TurnSWP)
            else:
                curve = self.Path.TurnSWP
        except:
            line = self.Straight.SubWP
            curve = self.Path.TurnSWP
        '''
        Last, the method joins the two ordered array of points to a single list of points
        '''
        self.SegmentCoords = numpy.append(line, curve, 1)

    def PlotPath(self, color):
        '''
        Plotting current path. Should not be used under normal circumstances
        '''
        self.Path.PlotTurn(color);
        self.Straight.PlotLine(color);
        
    def FlushPath(self, restart):
        '''
        Flushes all the current SWP data and resets the path to the specified WP
        Should be initialized by operator only
        '''
        self.SegmentCoords = []
        self.LastWP = restart
        self.Plan_LocalPath(0)
        self.get_PathSegment()
        
    def Control_Step(self):
        
        '''
        Outputs the calculated motor speeds based on the sensor inputs
        '''

        
        while 1:
            '''
            Gets the current destination point
            '''
            if self.WPsEnded == 0:
            
                if len(self.SegmentCoords)>0 and self.NextSWP_No < len(self.SegmentCoords[0]):
                    self.NextSWP = OL.O_PosData(self.SegmentCoords[0, self.NextSWP_No], self.SegmentCoords[1, self.NextSWP_No], float('NaN'), float('NaN'))
                    if self.mark == 0:
                    	self.swplog.write(str(self.NextSWP.get_Pos_X()) + ", " + str(self.NextSWP.get_Pos_Y()) + "\r\n")
                        plt.plot(self.NextSWP.get_Pos_X(), self.NextSWP.get_Pos_Y(), marker = 'o') 
                        self.mark = 1
                
                else:
                    '''
                    If there is no current destination point, the method requests a new path
                    '''
                    self.LastWP = self.LastWP + 1
                    
                    ret = self.Plan_LocalPath(self.Path.Range)
                    if ret == -1:
                        self.WPsEnded = 1
                        self.NextSWP_No = 100000
                        
                        #self.NextSWP = self.Waypoints.get_SingleWayPoint(self.LastWP + 1)
                        self.NextSWP = self.retpos
                    self.get_PathSegment()
                    
            else:
                self.NextSWP = self.retpos
                
                
            '''
            Calculation of the required heading
            and the current deviation from required heading
            '''
            
            Theta_r = self.get_Thera_r()
            delta = self.get_Delta(Theta_r)
            
            '''
            Checks the validity of the current destination point.
            If the Distance < FollowDistance the
            navigation procedure jumps to the next Sub-Waypoint
            '''
            valid = (FL.Distance(self.Pos, self.NextSWP) > self.FollowDistance);
            #self.swplog.write(str(self.NextSWP.get_Pos_X()) + ", " + str(self.NextSWP.get_Pos_Y()) + ", " + str(time.time()) + "\r\n")
            
            if valid == 0 and self.WPsEnded == 1:
                self.EndPath = 1
                break

            if valid == 1:
                break
            if self.WPsEnded == 0:
                self.NextSWP_No = self.NextSWP_No + 1
                self.mark = 0
                
            
        
            
        '''
        #############################################
        # RUN CONTROL ALGORITHM HERE
        '''
       
        Ref = numpy.matrix([[1], [self.x[1]-delta]])

        
        N = -self.F * self.x + self.N * Ref

        
        '''
        #############################################
        '''
            
        '''
        Results of the control step in the following format:
        Vertical(!) numpy Matrix(!)
        '''
        
        if self.EndPath == 0:
            return N;
        else:
            return numpy.matrix([[0], [0]])
    
    def ReadStates(self, input_m, input_f):
        
        '''
        Reads systems states from sensors (processed data)
        '''
        
        y = input_m[0,0]
        xd = input_m[1,0]
        xdd = input_m[2,0]
        x	 = input_m[3,0]
        yd = input_m[4,0]
        ydd = input_m[5,0]
        theta = input_m[6,0]
        omega = input_m[7,0]
        angacc = input_m[8,0]
        
        Measured_Pos = OL.O_PosData(x, y, 1, 1)
        BodyXY = FL.NEDtoBody(Measured_Pos, self.Pos, theta)
        
        
        
        PathFrameXY = list([BodyXY[0] + numpy.sum(self.states[0]), BodyXY[1] + numpy.sum(self.states[1])])
        
        Measured_Speed = OL.O_PosData(xd, yd, 1, 1)
        BodySpeed = FL.NEDtoBody(Measured_Speed, OL.O_PosData(0,0,1,1), theta)
    
    
        '''
        Wn = numpy.matrix([[PathFrameXY[0]], [BodySpeed[0]], [BodyAcc[0]], [PathFrameXY[1]], [BodySpeed[1]], [BodyAcc[1]], [theta], [omega], [angacc]])
        '''
        Wn = numpy.matrix([[PathFrameXY[0]], [xd], [xdd], [BodyXY[1]], [0], [ydd], [theta], [omega], [angacc]])
       # print numpy.transpose(Wn)
       #	print self.Pos
        
        prev_fx = numpy.sum(self.states[0])
        prev_fy = numpy.sum(self.states[1])
        
        '''Kalman'''
        
        Validity_matrix = input_m[:,1]
        
        if input_m[0,1] == 1:
        	self.flip = -self.flip
	        self.MP = [input_m[0][0],input_m[3][0], self.flip]
	    
        self.states = self.Filter.FilterStep(input_f, Wn, Validity_matrix)
       # print self.states[0]
       # print self.states[1]
        self.Ts = 0.1
        self.v = numpy.sum(self.states[2])
        self.omega = numpy.sum(self.states[4])
        self.Theta = math.atan2(math.sin(numpy.sum(self.states[3])), math.cos(numpy.sum(self.states[3])))
        
        self.x = numpy.matrix([[self.v],[self.Theta],[omega]])
        
        
        curpos = self.Pos.get_Pos()
        '''
        x_next = numpy.sum(self.Ts * self.v * math.sin(self.Theta) + curpos[0])
        y_next = numpy.sum(self.Ts * self.v * math.cos(self.Theta) + curpos[1])
        self.Pos = OL.O_PosData(x_next, y_next, math.cos(self.x[1]), math.sin(self.x[1]))
        
        0 Yd 1 Y 2 V 3 Th 4 Om
        '''
        
        
        
        V = numpy.sum(self.states[2])
        X = numpy.sum(self.states[0])
        Y = numpy.sum(self.states[1])
        Th = numpy.sum(self.states[3])
        self.Theta = math.atan2(math.sin(numpy.sum(self.states[3])), math.cos(numpy.sum(self.states[3])))
        #self.Theta = theta
        Th = theta
        #self.states[1] = PathFrameXY[1]
        
        if numpy.sum(Validity_matrix[0]):
			self.correction = BodyXY[1]
			
			
			
			
			
			x_next = ((X - prev_fx) * math.sin(Th)) + curpos[0] + self.correction * math.cos(Th)
			y_next = ((X - prev_fx) * math.cos(Th)) + curpos[1] - self.correction * math.sin(Th)
        
        else:
        	self.correction = 0
        	
        	x_next = ((X - prev_fx) * math.sin(Th)) + curpos[0]
        	y_next = ((X - prev_fx) * math.cos(Th)) + curpos[1]
        #self.filterlog.write(str(float(self.Pos.get_Pos_X())) + ", " + str(float(self.Pos.get_Pos_Y())) + "\r\n")
        #print x_next, y_next
        #x_next = ((V * self.Ts) * math.sin(Th)) + curpos[0] + self.correction * 0.1* math.cos(Th)
        #y_next = ((V * self.Ts) * math.cos(Th)) + curpos[1] - self.correction * 0.1* math.sin(Th)
        #print('FX', x_next, 'FY', y_next, 'FV', numpy.sum(self.states[2]), 'FT', numpy.sum(self.states[3]), 'FO', numpy.sum(self.states[4]))
        self.log.write(str(x_next) + ', ' + str(y_next) + ', ' + str(numpy.sum(self.states[2])) + ', ' + str(numpy.sum(self.states[3])) + ', ' + str(numpy.sum(self.states[4])) + ", " + str(time.time()) + "\r\n")
        self.Pos = OL.O_PosData(x_next, y_next, math.cos(self.x[1]), math.sin(self.x[1]))
        
    def get_Thera_r(self):
        
        '''
        Calculates the required heading
        '''
        Theta_r = FL.CosLaw(self.Pos.Extend_Zero(), self.Pos, self.NextSWP)
        '''
        The CosLaw function returns a positive angle
        If the ship must turn left, the X coordinate of the Next SWP < X coordinate of Ship
        In that case, Theta_r is in the negative angle-space, therefore must be negated
        '''
        if self.NextSWP.get_Pos_X() < self.Pos.get_Pos_X():
            Theta_r *= -1
        return Theta_r
        
    def get_Delta(self, Theta_r):
        
        '''
        Calculates the current deviation from heading
        '''
        
        delta = self.Theta-Theta_r
        '''
        Until this point, nothing ensures, that -pi < Theta-Theta_r < pi.
        With this method we make sure, that -pi < delta < pi
        IF later the control is based on Theta_r and Theta, the same
        adjustment of values must be implemented!
        '''
        delta = math.atan2(math.sin(delta), math.cos(delta))
        return delta
         
    def AddRelativeCourse(self, WPC):
        '''
        Sets a 
        '''
        #Parameters: self, list of WP-s
        '''
        R = 6371080
        
        lon = math.degrees(WPC.get_Pos_X() / R)
        lat = math.degrees(WPC.get_Pos_Y() / R)
        
        
        
        xy = numpy.array([[lon],[lat]])
        self.Waypoints.AddWP(xy)
        self.WPsEnded = 0
        self.EndPath = 0
        '''
        X = self.Pos.get_Pos_X() + WPC.get_Pos_X()
        Y = self.Pos.get_Pos_Y() + WPC.get_Pos_Y()
        xy = numpy.array([[X],[Y]])
        self.Waypoints.AddWP(xy)
        self.WPsEnded = 0
        self.EndPath = 0
        
    def AddCourse(self, WPC):
        
        '''
        Sets a 
        '''
        #Parameters: self, list of WP-s
        xy = numpy.array([[WPC.get_Pos_X()],[WPC.get_Pos_Y()]])
        self.Waypoints.AddWP(xy)
        self.WPsEnded = 0
        self.EndPath = 0
        
    def FtoM(self, motor):

        K = math.pow(0.05,4)*0.5*1000;
        theta = math.pi/16;
        C1 = 0.5*math.sin(theta);
        C2 = 0.5*math.sin(-theta);
        
        L = numpy.matrix([[K, K],[K*C1, K*C2]])
        L_inv = numpy.linalg.inv(L)
        temp = numpy.array(L_inv*motor)
        N = numpy.sqrt(numpy.abs(temp))*numpy.sign(temp)
        return N
        
    def get_vel(self):
    	return self.v
    
    def get_mp(self):
    	return self.MP
    
    def Return(self, retpos):
        
        self.retpos = retpos
