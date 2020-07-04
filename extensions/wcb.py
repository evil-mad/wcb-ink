# wcb.py
# Part of the WaterColorBot driver for Inkscape
# https://github.com/oskay/wcb-ink/
#
# Version 1.5.0, dated 2017-06-19
# 
# Requires Pyserial 2.7.0 or newer. Pyserial 3.0 recommended.
#
# Copyright 2017 Windell H. Oskay, Evil Mad Scientist Laboratories
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

# TODO: Add and honor advisory locking around device open/close for non Win32
 
# TODO: Lead-ins for fewer disruptions when going to get more ink
# TODO: Implement random/ tolerance on auto-ink 
#       It would be nice to go get more paint between painting segments, rather than exactly when "paint runs out"
#       (If length of segment we're currently drawing + distance painted thus far) < 120% of repaint distance,
#           hold off on getting ink until after this segment.

# TODO: Advise user when no layers were found to plot-- from Paint tab

import sys
import gettext
import serial
import string
import time
import math
from array import *

from lxml import etree

from plot_utils_import import from_dependency_import # plotink
simplepath = from_dependency_import('ink_extensions.simplepath')
cubicsuperpath = from_dependency_import('ink_extensions.cubicsuperpath')
simpletransform = from_dependency_import('ink_extensions.simpletransform')
inkex = from_dependency_import('ink_extensions.inkex')
exit_status = from_dependency_import('ink_extensions_utils.exit_status')
message = from_dependency_import('ink_extensions_utils.message')
ebb_serial = from_dependency_import('plotink.ebb_serial')  # Requires v 0.13 in plotink    https://github.com/evil-mad/plotink
ebb_motion = from_dependency_import('plotink.ebb_motion')  # Requires v 0.16 in plotink
plot_utils = from_dependency_import('plotink.plot_utils')  # Requires v 0.15 in plotink


try:
    xrange = xrange  # We have Python 2
except NameError:
    xrange = range  # We have Python 3


import wcb_conf          #Some settings can be changed here.

F_DEFAULT_SPEED = 1
N_PEN_DOWN_DELAY = 400    # delay (ms) for the pen to go down before the next move
N_PEN_UP_DELAY = 400      # delay (ms) for the pen to up down before the next move

N_PEN_UP_POS = 50      # Default pen-up position
N_PEN_DOWN_POS = 40      # Default pen-down position
N_PEN_WASH_POS = 35      # Default pen-wash position

N_SERVOSPEED = 50            # Default pen-lift speed 
N_DEFAULT_LAYER = 1            # Default inkscape layer

class WCB( inkex.Effect ):

    def __init__( self ):
        inkex.Effect.__init__( self )
        self.OptionParser.add_option( "--tab",
            action="store", type="string",
            dest="tab", default="controls",
            help="The active tab when Apply was pressed" )
            
        self.OptionParser.add_option( "--penUpPosition",
            action="store", type="int",
            dest="penUpPosition", default=N_PEN_UP_POS,
            help="Position of pen when lifted" )
        self.OptionParser.add_option( "--penDownPosition",
            action="store", type="int",
            dest="penDownPosition", default=N_PEN_DOWN_POS,
            help="Position of pen for painting" )
        self.OptionParser.add_option( "--penWashPosition",
            action="store", type="int",
            dest="penWashPosition", default=N_PEN_WASH_POS,
            help="Position of pen for washing" )            
             
        self.OptionParser.add_option( "--setupType",
            action="store", type="string",
            dest="setupType", default="controls",
            help="The active option when Apply was pressed" )
            
        self.OptionParser.add_option( "--penDownSpeed",
            action="store", type="int",
            dest="penDownSpeed", default=F_DEFAULT_SPEED,
            help="Speed (step/sec) while pen is down." )
        self.OptionParser.add_option( "--penUpSpeed",
            action="store", type="int",
            dest="penUpSpeed", default=F_DEFAULT_SPEED,
            help="Speed (step/sec) while pen is up." )
        self.OptionParser.add_option( "--ServoUpSpeed",
            action="store", type="int",
            dest="ServoUpSpeed", default=N_SERVOSPEED,
            help="Rate of lifting pen " )
        self.OptionParser.add_option( "--penUpDelay",
            action="store", type="int",
            dest="penUpDelay", default=N_PEN_UP_DELAY,
            help="Delay after pen up (msec)." )
        self.OptionParser.add_option( "--ServoDownSpeed",
            action="store", type="int",
            dest="ServoDownSpeed", default=N_SERVOSPEED,
            help="Rate of lowering pen " ) 
        self.OptionParser.add_option( "--penDownDelay",
            action="store", type="int",
            dest="penDownDelay", default=N_PEN_DOWN_DELAY,
            help="Delay after pen down (msec)." )
            
        self.OptionParser.add_option( "--revMotor1",
            action="store", type="inkbool",
            dest="revMotor1", default=False,
            help="Reverse motion of X motor." )
        self.OptionParser.add_option( "--revMotor2",
            action="store", type="inkbool",
            dest="revMotor2", default=False,
            help="Reverse motion of Y motor." )
        self.OptionParser.add_option( "--reInkDist",
            action="store", type="float",
            dest="reInkDist", default=10,
            help="Re-ink distance (inches)" ) 
            
        self.OptionParser.add_option( "--smoothness",
            action="store", type="float",
            dest="smoothness", default=.2,
            help="Smoothness of curves" ) 
            
        self.OptionParser.add_option( "--resolution",
            action="store", type="int",
            dest="resolution", default=3,
            help="Resolution factor." )    
            
        self.OptionParser.add_option( "--paintMode",
            action="store", type="string",
            dest="paintMode", default="controls",
            help="The painting mode when Apply was pressed" )
        self.OptionParser.add_option( "--autoChange",
            action="store", type="inkbool",
            dest="autoChange", default=False,
            help="[AutoChange] between colors w/ water wash" )                    
        self.OptionParser.add_option( "--reInkEnable",
            action="store", type="inkbool",
            dest="reInkEnable", default=False,
            help="[Re-Ink] brush after given distance (yes/no)." )            
        self.OptionParser.add_option( "--ReWetOnly",
            action="store", type="inkbool",
            dest="ReWetOnly", default=False,
            help="[Re-Wet] brush after given distance (no ink)." )            
        self.OptionParser.add_option( "--PreDipEnable",
            action="store", type="inkbool",
            dest="PreDipEnable", default=False,
            help="[Pre-Dip] brush in water before re-inking." )            
        self.OptionParser.add_option( "--PostDipEnable",
            action="store", type="inkbool",
            dest="PostDipEnable", default=False,
            help="[Post-Dip] brush in water after re-inking." )                    
            
        self.OptionParser.add_option( "--manualType",
            action="store", type="string",
            dest="manualType", default="controls",
            help="The active option when Apply was pressed" )
        self.OptionParser.add_option( "--WalkDistance",
            action="store", type="float",
            dest="WalkDistance", default=1,
            help="Distance for manual walk" )            
            
        self.OptionParser.add_option( "--resumeType",
            action="store", type="string",
            dest="resumeType", default="controls",
            help="The active option when Apply was pressed" )            
            
        self.OptionParser.add_option( "--layernumber",
            action="store", type="int",
            dest="layernumber", default=N_DEFAULT_LAYER,
            help="Selected layer for multilayer plotting" )            
            
        self.serialPort = None
        self.bPenIsUp = None  #Initial state of pen is neither up nor down, but _unknown_.
        self.virtualPenIsUp = False  #Keeps track of pen postion when stepping through plot before resuming
        self.ignoreLimits = False

        self.fX = None
        self.fY = None 
        self.fCurrX = wcb_conf.F_StartPos_X
        self.fCurrY = wcb_conf.F_StartPos_Y 
        self.ptFirst = ( wcb_conf.F_StartPos_X, wcb_conf.F_StartPos_Y)
        self.bStopped = False
        self.fSpeed = 1
        self.resumeMode = False
        self.nodeCount = int( 0 )        #NOTE: python uses 32-bit ints.
        self.nodeTarget = int( 0 )
        self.pathcount = int( 0 )
        self.LayersFoundToPlot = False
        self.LayerPaintColor = -1
        self.BrushColor = -1

        self.LayerOverrideSpeed = False
        self.LayerOverridePenDownHeight = False
        self.LayerPenDownPosition = -1
        self.LayerPenDownSpeed = -1

        #Values read from file:
        self.svgLayer_Old = int( 0 )
        self.svgNodeCount_Old = int( 0 )
        self.svgDataRead_Old = False
        self.svgLastPath_Old = int( 0 )
        self.svgLastPathNC_Old = int( 0 )
        self.svgLastKnownPosX_Old = float( 0.0 )
        self.svgLastKnownPosY_Old = float( 0.0 )
        self.svgPausedPosX_Old = float( 0.0 )
        self.svgPausedPosY_Old = float( 0.0 )    
        
        #New values to write to file:
        self.svgLayer = int( 0 )
        self.svgNodeCount = int( 0 )
        self.svgDataRead = False
        self.svgLastPath = int( 0 )
        self.svgLastPathNC = int( 0 )
        self.svgLastKnownPosX = float( 0.0 )
        self.svgLastKnownPosY = float( 0.0 )
        self.svgPausedPosX = float( 0.0 )
        self.svgPausedPosY = float( 0.0 )    
        
        self.paintdist = 0.0
        self.ReInkingNow = False
        self.reInkDist = 10
        self.CleaningNow = False
        self.manConfMode = False
        self.PrintFromLayersTab = False
        self.xErr = 0.0
        self.yErr = 0.0

        self.svgWidth = float( wcb_conf.N_PAGE_WIDTH )
        self.svgHeight = float( wcb_conf.N_PAGE_HEIGHT ) 
        
        self.xBoundsMax = wcb_conf.N_PAGE_WIDTH
        self.xBoundsMin = wcb_conf.F_StartPos_X
        self.yBoundsMax = wcb_conf.N_PAGE_HEIGHT
        self.yBoundsMin = wcb_conf.F_StartPos_Y        
        
        self.svgTransform = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
        
        self.stepsPerPx = float( wcb_conf.F_DPI_16X / 90.0 )  
        self.BrushUpSpeed   = float(wcb_conf.F_Speed_Scale) #speed when brush is up
        self.BrushDownSpeed = float(wcb_conf.F_Speed_Scale) #speed when brush is down        
                    
        # So that we only generate a warning once for each
        # unsupported SVG element, we use a dictionary to track
        # which elements have received a warning
        self.warnings = {}

    def effect( self ):
        '''Main entry point: check to see which tab is selected, and act accordingly.'''

        self.svg = self.document.getroot()
        self.CheckSVGforWCBData()
        useOldResumeData = True

        self.options.tab = self.options.tab.strip("\"")
        self.options.setupType = self.options.setupType.strip("\"")
        self.options.manualType = self.options.manualType.strip("\"")
        self.options.resumeType = self.options.resumeType.strip("\"")

        skipSerial = False
        if (self.options.tab == "Help"):
            skipSerial = True
        if (self.options.tab == "options"):
            skipSerial = True        
        if (self.options.tab == "timing"):
            skipSerial = True
        if (self.options.tab == "wcbModes"):
            skipSerial = True
        
        if skipSerial == False:
        
            use_nickname = False
            
            if use_nickname:
                named_port = "WaterColorBot" # "Hard-coded" USB nickname
                the_port = ebb_serial.find_named_ebb(named_port)
                self.serialPort = ebb_serial.testPort(the_port)
            else:
                self.serialPort = ebb_serial.openPort() # Open first-located EBB
            
            
            if self.serialPort is None:
                inkex.errormsg( gettext.gettext( "Failed to connect to WaterColorBot. :(" ) )
            if self.options.tab == "splash": 
                self.LayersFoundToPlot = False
                useOldResumeData = False
                self.PrintFromLayersTab = False
                self.plotCurrentLayer = True
                if self.serialPort is not None:
                    self.svgNodeCount = 0
                    self.svgLastPath = 0
                    unused_button = ebb_motion.QueryPRGButton(self.serialPort)    #Query if button pressed
                    self.svgLayer = 12345;  # indicate (to resume routine) that we are plotting all layers.
                    self.setPaintingMode()
                    self.plotToWCB()
                    
                    if ( self.LayersFoundToPlot == False ):
                        inkex.errormsg( gettext.gettext( 'There are not any numbered layers to paint. Please use the "Snap Colors to Layers" extension, read about layer names in the documentation, or switch to a painting mode (like pen/pencil) that does not require numbered layers.' ) )
                    
                
            elif self.options.tab == "resume":
                if self.serialPort is None:
                    useOldResumeData = True
                else:
                    useOldResumeData = False
                    self.setPaintingMode()
                    unused_button = ebb_motion.QueryPRGButton(self.serialPort)    #Query if button pressed
                    self.resumePlotSetup()
                    if self.resumeMode:
                        self.fX = self.svgPausedPosX_Old + wcb_conf.F_StartPos_X
                        self.fY = self.svgPausedPosY_Old + wcb_conf.F_StartPos_Y
                        self.resumeMode = False
                        
                        
                        self.penUpRapidMove( self.fX, self.fY ) #Special pre-resume move
                        
                        self.resumeMode = True
                        self.nodeCount = 0
                        self.plotToWCB() 
                        
                    elif ( self.options.resumeType == "justGoHome" ):
                        self.fX = wcb_conf.F_StartPos_X
                        self.fY = wcb_conf.F_StartPos_Y 
                        self.penUpRapidMove( self.fX, self.fY ) #Rapid pen-up movements
        
                        #New values to write to file:
                        self.svgNodeCount = self.svgNodeCount_Old
                        self.svgLastPath = self.svgLastPath_Old 
                        self.svgLastPathNC = self.svgLastPathNC_Old 
                        self.svgPausedPosX = self.svgPausedPosX_Old 
                        self.svgPausedPosY = self.svgPausedPosY_Old
                        self.svgLayer = self.svgLayer_Old 
        
                    else:
                        inkex.errormsg( gettext.gettext( "There does not seem to be any in-progress plot to resume." ) )
    
            elif self.options.tab == "layers":
                useOldResumeData = False 
                self.PrintFromLayersTab = True
                self.plotCurrentLayer = False
                self.LayersFoundToPlot = False
                self.svgLastPath = 0
                if self.serialPort is not None:
                    self.setPaintingMode()
                    unused_button = ebb_motion.QueryPRGButton(self.serialPort)    #Query if button pressed
                    self.svgNodeCount = 0;
                    self.svgLayer = self.options.layernumber
                    self.plotToWCB()
                    if ( self.LayersFoundToPlot == False ):
                        inkex.errormsg( gettext.gettext( 'There are not any numbered layers to paint. Please use the "Snap Colors to Layers" extension, read about layer names in the documentation, or switch to a painting mode (like pen/pencil) that does not require numbered layers.' ) )
    
            elif self.options.tab == "setup":
                self.setupCommand()
                
            elif self.options.tab == "manual":
                if self.options.manualType == "strip-data":
                    for node in self.svg.xpath( '//svg:WCB', namespaces=inkex.NSS ):
                        self.svg.remove( node )
                    for node in self.svg.xpath( '//svg:eggbot', namespaces=inkex.NSS ):
                        self.svg.remove( node )
                    inkex.errormsg( gettext.gettext( "I've removed all WaterColorBot data from this SVG file. Have a great day!" ) )
                    return    
                else:    
                    useOldResumeData = False 
                    self.svgNodeCount = self.svgNodeCount_Old
                    self.svgLastPath = self.svgLastPath_Old 
                    self.svgLastPathNC = self.svgLastPathNC_Old 
                    self.svgPausedPosX = self.svgPausedPosX_Old 
                    self.svgPausedPosY = self.svgPausedPosY_Old
                    self.svgLayer = self.svgLayer_Old 
                    self.manualCommand()

        if (useOldResumeData):    #Do not make any changes to data saved from SVG file.
            self.svgNodeCount = self.svgNodeCount_Old
            self.svgLastPath = self.svgLastPath_Old 
            self.svgLastPathNC = self.svgLastPathNC_Old 
            self.svgPausedPosX = self.svgPausedPosX_Old 
            self.svgPausedPosY = self.svgPausedPosY_Old
            self.svgLayer = self.svgLayer_Old                
            self.svgLastKnownPosX = self.svgLastKnownPosX_Old
            self.svgLastKnownPosY = self.svgLastKnownPosY_Old 

        self.svgDataRead = False
        self.UpdateSVGWCBData( self.svg )
        if self.serialPort is not None:
            ebb_motion.doTimedPause(self.serialPort, 10) #Pause a moment for underway commands to finish...
            ebb_serial.closePort(self.serialPort)    
        
    def resumePlotSetup( self ):
        self.LayerFound = False
        if ( self.svgLayer_Old < 101 ) and ( self.svgLayer_Old >= 0 ):
            self.options.layernumber = self.svgLayer_Old 
            self.PrintFromLayersTab = True
            self.plotCurrentLayer = False
            self.LayerFound = True
        elif ( self.svgLayer_Old == 12345 ):  # Plot all layers 
            self.PrintFromLayersTab = False
            self.plotCurrentLayer = True
            self.LayerFound = True    
        if ( self.LayerFound ):
            if ( self.svgNodeCount_Old > 0 ):
                self.nodeTarget = self.svgNodeCount_Old
                self.svgLayer = self.svgLayer_Old
                if self.options.resumeType == "ResumeNow":
                    self.resumeMode = True
                if self.serialPort is None:
                    return
                self.ServoSetup()
                self.penUp() 
                self.EnableMotors() #Set plotting resolution  
                self.fSpeed = self.options.penUpSpeed
                self.fCurrX = self.svgLastKnownPosX_Old + wcb_conf.F_StartPos_X
                self.fCurrY = self.svgLastKnownPosY_Old + wcb_conf.F_StartPos_Y
                 

    def CheckSVGforWCBData( self ):
        self.svgDataRead = False
        self.recursiveWCBDataScan( self.svg )
        if ( not self.svgDataRead ):    #if there is no WCB data, add some:
            WCBlayer = inkex.etree.SubElement( self.svg, 'WCB' )
            WCBlayer.set( 'serialport', '' )
            WCBlayer.set( 'layer', str( 0 ) )
            WCBlayer.set( 'node', str( 0 ) )            #node paused at, if saved in paused state
            WCBlayer.set( 'lastpath', str( 0 ) )        #Last path number that has been fully painted
            WCBlayer.set( 'lastpathnc', str( 0 ) )        #Node count as of finishing last path.
            WCBlayer.set( 'lastknownposx', str( 0 ) )  #Last known position of carriage
            WCBlayer.set( 'lastknownposy', str( 0 ) )
            WCBlayer.set( 'pausedposx', str( 0 ) )       #The position of the carriage when "pause" was pressed.
            WCBlayer.set( 'pausedposy', str( 0 ) )
                        
    def recursiveWCBDataScan( self, aNodeList ):
        if ( not self.svgDataRead ):
            for node in aNodeList:
                if node.tag == 'svg':
                    self.recursiveWCBDataScan( node )
                elif node.tag == inkex.addNS( 'WCB', 'svg' ) or node.tag == 'WCB':
                    try:
                        self.svgLayer_Old = int( node.get( 'layer' ) )
                        self.svgNodeCount_Old = int( node.get( 'node' ) )
                        self.svgLastPath_Old = int( node.get( 'lastpath' ) )
                        self.svgLastPathNC_Old = int( node.get( 'lastpathnc' ) )
                        self.svgLastKnownPosX_Old = float( node.get( 'lastknownposx' ) )
                        self.svgLastKnownPosY_Old = float( node.get( 'lastknownposy' ) ) 
                        self.svgPausedPosX_Old = float( node.get( 'pausedposx' ) )
                        self.svgPausedPosY_Old = float( node.get( 'pausedposy' ) ) 
                        self.svgDataRead = True
                    except:
                        pass

    def UpdateSVGWCBData( self, aNodeList ):
        if ( not self.svgDataRead ):
            for node in aNodeList:
                if node.tag == 'svg':
                    self.UpdateSVGWCBData( node )
                elif node.tag == inkex.addNS( 'WCB', 'svg' ) or node.tag == 'WCB':
                    node.set( 'layer', str( self.svgLayer ) )
                    node.set( 'node', str( self.svgNodeCount ) )
                    node.set( 'lastpath', str( self.svgLastPath ) )
                    node.set( 'lastpathnc', str( self.svgLastPathNC ) )
                    node.set( 'lastknownposx', str( (self.svgLastKnownPosX ) ) )
                    node.set( 'lastknownposy', str( (self.svgLastKnownPosY ) ) )
                    node.set( 'pausedposx', str( (self.svgPausedPosX) ) )
                    node.set( 'pausedposy', str( (self.svgPausedPosY) ) )
                    
                    self.svgDataRead = True
                     
    def setupCommand( self ):
        """Execute commands from the "setup" tab"""

        if self.serialPort is None:
            return

        self.ServoSetupWrapper()

        if self.options.setupType == "align-mode":
            self.penUp()
            ebb_motion.sendDisableMotors(self.serialPort)    

        elif self.options.setupType == "toggle-pen":
            self.CleaningNow = False
            self.ServoSetMode()
            ebb_motion.TogglePen(self.serialPort)

        elif self.options.setupType == "toggle-wash":  
            self.CleaningNow = True 
            self.ServoSetMode()
            ebb_motion.TogglePen(self.serialPort)
            self.CleaningNow = False

            
    def manualCommand( self ):
        """Execute commands from the "manual" tab"""

        if self.options.manualType == "none":
            return
            
        if self.serialPort is None:
            return 

        if self.options.manualType == "raise-pen":
            self.ServoSetupWrapper()
            self.penUp()

        elif self.options.manualType == "lower-pen":
            self.ServoSetupWrapper()
            self.penDown()

        elif self.options.manualType == "enable-motors":
            self.EnableMotors()

        elif self.options.manualType == "disable-motors":
            ebb_motion.sendDisableMotors(self.serialPort)    
            
        elif self.options.manualType == "wash-brush":  #Assuming we start in HOME POSITION.
            self.ServoSetupWrapper() 
            self.EnableMotors() #Set plotting resolution 
            self.CleanBrush()
            self.moveHome()     

        elif self.options.manualType == "version-check":
            strVersion = ebb_serial.query( self.serialPort, 'v\r' )
            inkex.errormsg( 'I asked the EBB for its version info, and it replied:\n ' + strVersion )

        else:  # self.options.manualType is walk motor:
            if self.options.manualType == "walk-y-motor":
                nDeltaX = 0
                nDeltaY = self.options.WalkDistance
            elif self.options.manualType == "walk-x-motor":
                nDeltaY = 0
                nDeltaX = self.options.WalkDistance
            else:
                return
                
            #Query pen position: 1 up, 0 down (followed by OK)
            strVersion = ebb_serial.query( self.serialPort, 'QP\r' )
            if strVersion[0] == '0':
                self.fSpeed = self.options.penDownSpeed
            if strVersion[0] == '1':
                self.fSpeed = self.options.penUpSpeed
                
            self.EnableMotors() #Set plotting resolution 
            self.fCurrX = self.svgLastKnownPosX_Old + wcb_conf.F_StartPos_X
            self.fCurrY = self.svgLastKnownPosY_Old + wcb_conf.F_StartPos_Y
            self.ignoreLimits = True
            self.fX = self.fCurrX + nDeltaX * 90  #Note: Walking motors is STRICTLY RELATIVE TO INITIAL POSITION.
            self.fY = self.fCurrY + nDeltaY * 90  
            self.plotLineAndTime(self.fX, self.fY ) 



    def CleanBrush(self):  
        self.CleaningNow = True
        self.EnableMotors() #Set plotting resolution  
        self.MoveToWater(0)
        self.PaintSwirl(wcb_conf.WashCycles, wcb_conf.WashDelta[0], wcb_conf.WashDelta[1])   
        self.MoveToWater(1)# 
        self.PaintSwirl(wcb_conf.WashCycles, wcb_conf.WashDelta[0], wcb_conf.WashDelta[1])   
        self.MoveToWater(2)    
        self.PaintSwirl(wcb_conf.WashCycles, wcb_conf.WashDelta[0], wcb_conf.WashDelta[1])   
        self.CleaningNow = False
        self.EnableMotors() #Set plotting resolution  


    def MoveDeltaXY(self,xDist,yDist):  
        self.fX = self.fX + xDist   #Todo: Add limit checking?
        self.fY = self.fY + yDist 
        self.plotLineAndTime(self.fX, self.fY )  
        
    def MoveToXY(self,xPos,yPos):  
        self.fX = xPos   #Todo: Add limit checking?
        self.fY = yPos 
        self.plotLineAndTime(self.fX, self.fY )  

    def MoveToWater(self, dish):
        self.penUp()  
        self.xBoundsMin = wcb_conf.F_StartPos_X
        self.yBoundsMin = wcb_conf.F_StartPos_Y
        # Values give X and Y positions of water dish 'dish.' 
        self.fX  = wcb_conf.F_StartPos_X + wcb_conf.WaterLoc[dish][0]
        self.fY  = wcb_conf.F_StartPos_Y + wcb_conf.WaterLoc[dish][1]
        self.penUpRapidMove(self.fX, self.fY )  

    def moveHome(self):
        self.penUp() 
        self.xBoundsMin = wcb_conf.F_StartPos_X
        self.yBoundsMin = wcb_conf.F_StartPos_Y
        self.penUpRapidMove(wcb_conf.F_StartPos_X, wcb_conf.F_StartPos_Y )  


    def PaintSwirl (self, swirlCount, Xpp, Ypp): # Xpp, Ypp: Peak-to-peak deviation in X and Y
        TempInkingState = self.ReInkingNow
        self.ReInkingNow = True   #Part of the "Re-inking" process, so override any desire to go get paint.
        self.EnableMotors() #Set plotting speed to temporary pen-down speed.
        self.ServoSetMode() #Set plotting height to temporary pen-down height for re-inking
        self.penDown()  
        self.MoveDeltaXY( 0, - Ypp / 2)
        for _ in xrange(swirlCount): 
            self.MoveDeltaXY( Xpp / 2,  Ypp / 2)
            self.MoveDeltaXY(-Xpp / 2,  Ypp / 2)
            self.MoveDeltaXY(-Xpp / 2, -Ypp / 2)
            self.MoveDeltaXY( Xpp / 2, -Ypp / 2)                            
        self.MoveDeltaXY( 0, Ypp / 2)         
        self.penUp()  
        self.ReInkingNow = TempInkingState
        self.EnableMotors() # Set pen-down plotting speed back to original
        self.ServoSetMode() # Set pen-down height  back to original


    def MoveToPaint(self, dish):
        self.penUp() 
        self.xBoundsMin = wcb_conf.F_StartPos_X
        self.yBoundsMin = wcb_conf.F_StartPos_Y
        self.fX = wcb_conf.F_StartPos_X + wcb_conf.PaintLoc[dish][0]
        self.fY = wcb_conf.F_StartPos_Y + wcb_conf.PaintLoc[dish][1]
        self.penUpRapidMove(self.fX, self.fY)

    def PaintToolChange(self, color):   # Move Brush to certain paint color and ink the brush
        if (self.options.autoChange):
#            inkex.errormsg( 'About to clean brush at node#: ' + str( self.nodeCount ) + '.' )  
            self.CleanBrush()
#            inkex.errormsg( 'Begin color change to color#: ' + str( color ) + '.' )  

            if (color != 0):
                self.MoveToPaint(color - 1)
                self.PaintSwirl(wcb_conf.InkCycles, wcb_conf.InkDelta[0], wcb_conf.InkDelta[1]) 
            self.BrushColor = color 
            if ((color != 0) and (self.options.PostDipEnable)):
                    self.MoveToWater(0)
                    self.PaintSwirl(1, wcb_conf.WaterDipDelta[0], wcb_conf.WaterDipDelta[1])
            self.paintdist = 0.0
#            inkex.errormsg( 'Finished ink change at node#: ' + str( self.nodeCount ) + '.' )  

        else: # Cases with autochange off: 
            if (self.BrushColor < 0):  # if we have not previously inked the brush
                self.BrushColor = 0
                
#                inkex.errormsg( 'self.options.reInkEnable: ' + str( self.options.reInkEnable) + '.' )     
#                inkex.errormsg( 'self.options.ReWetOnly: ' + str( self.options.ReWetOnly) + '.' )  
#                inkex.errormsg( 'self.options.PreDipEnable: ' + str( self.options.PreDipEnable) + '.' )     
#                inkex.errormsg( 'self.options.PostDipEnable: ' + str( self.options.PostDipEnable) + '.' )  

                if ((self.options.reInkEnable) and (self.options.ReWetOnly == False)): # if we are using paint
                    if (self.options.PreDipEnable or self.options.PostDipEnable): #Using Paint AND water
                        self.CleanBrush()
                        self.MoveToPaint(0)
                        self.BrushColor = 1        #Color 1, black ink
                        self.PaintSwirl(1, wcb_conf.InkReDelta[0], wcb_conf.InkReDelta[1]) 
                        if (self.options.PostDipEnable):
                            self.MoveToWater(0)
                            self.PaintSwirl(1, wcb_conf.WaterDipDelta[0], wcb_conf.WaterDipDelta[1])                        
                    else: #using paint but not using water    
                        self.MoveToPaint(0)
                        self.BrushColor = 1    #color 1, black ink
                        self.PaintSwirl(1, wcb_conf.InkReDelta[0], wcb_conf.InkReDelta[1])    
#                        inkex.errormsg( 'self.options.paintMode @ Toolchange: ' + str( self.options.paintMode) + '.' )     
#                        inkex.errormsg( 'self.options.ReWetOnly: ' + str( self.options.ReWetOnly) + '.' )  
#                        inkex.errormsg( 'self.BrushColor: ' + str( self.BrushColor) + '.' )   
                                            
                elif ((self.options.reInkEnable) and (self.options.ReWetOnly)): # if we are using only water
                    self.MoveToWater(0)        #water dip only
                    self.PaintSwirl(1, wcb_conf.WaterDipDelta[0], wcb_conf.WaterDipDelta[1])

    def reInkBrush(self):    
        self.ReInkingNow = True
        
        #Redefine movement boundaries to include paint set & water
        returnToXmin = self.xBoundsMin
        returnToYmin = self.yBoundsMin 
        self.xBoundsMin = wcb_conf.F_StartPos_X
        self.yBoundsMin = wcb_conf.F_StartPos_Y
        
        returnToX = self.fCurrX # Save current position, to return to.
        returnToY = self.fCurrY # Save current position, to return to.
        
        
#        inkex.errormsg( 'self.options.paintMode: ' + str( self.options.paintMode) + '.' )  
#        inkex.errormsg( 'self.options.ReWetOnly: ' + str( self.options.ReWetOnly) + '.' )  
#        inkex.errormsg( 'self.BrushColor: ' + str( self.BrushColor) + '.' )   
        
        
        if ((self.options.ReWetOnly) or (self.BrushColor == 0)): 
            self.MoveToWater(0)
            self.PaintSwirl(1, wcb_conf.WaterDipDelta[0], wcb_conf.WaterDipDelta[1])   
        else:            
            if (self.options.PreDipEnable):
                self.MoveToWater(0)
                self.PaintSwirl(1, wcb_conf.WaterDipDelta[0], wcb_conf.WaterDipDelta[1])        
            self.MoveToPaint( self.BrushColor - 1 )  
            self.PaintSwirl(wcb_conf.InkReCycles, wcb_conf.InkReDelta[0], wcb_conf.InkReDelta[1])
            if (self.options.PostDipEnable):
                self.MoveToWater(0)
                self.PaintSwirl(1, wcb_conf.WaterDipDelta[0], wcb_conf.WaterDipDelta[1])

        self.xBoundsMin = returnToXmin
        self.yBoundsMin = returnToYmin
                            
#        self.MoveToXY(returnToX, returnToY)        #TODO: Add lead-in here
        self.penUpRapidMove( returnToX, returnToY )
        self.ReInkingNow = False
        
        self.EnableMotors() #Set plotting resolution back to normal after re-inking
        self.penDown() 
        self.paintdist = 0

    def setPaintingMode(self):
        #Note: For manual mode, we use the existing options set. Otherwise, override:    
        if self.options.paintMode == "wc":
            self.options.autoChange = True
            self.options.reInkEnable = True
            self.options.ReWetOnly = False
            self.options.PreDipEnable = True
            self.options.PostDipEnable = False
        elif self.options.paintMode == "wc-dip":    #Watercolor + Post-dip
            self.options.autoChange = True
            self.options.reInkEnable = True
            self.options.ReWetOnly = False
            self.options.PreDipEnable = True
            self.options.PostDipEnable = True
        elif self.options.paintMode == "tempera":        
            self.options.autoChange = True
            self.options.reInkEnable = True
            self.options.ReWetOnly = False
            self.options.PreDipEnable = False
            self.options.PostDipEnable = False
        elif self.options.paintMode == "wc-pen":        
            self.options.autoChange = False
            self.options.reInkEnable = True
            self.options.ReWetOnly = True
            self.options.PreDipEnable = False
            self.options.PostDipEnable = False
        elif self.options.paintMode == "dip-pen":        
            self.options.autoChange = False
            self.options.reInkEnable = True
            self.options.ReWetOnly = False
            self.options.PreDipEnable = False
            self.options.PostDipEnable = False
#            self.BrushColor = 1
        elif self.options.paintMode == "pencil":         
            self.options.autoChange = False
            self.options.reInkEnable = False
            self.options.ReWetOnly = False
            self.options.PreDipEnable = False
            self.options.PostDipEnable = False 
        elif self.options.paintMode == "man-mode":
            self.manConfMode = True 
        

    def plotToWCB( self ):
        '''Perform the actual plotting, if selected in the interface:'''
        #parse the svg data as a series of line segments and send each segment to be plotted

        if self.serialPort is None:
            return

#        TODO: Re-enable checking of SVG document width and height
#        if (not self.getDocProps()):
#            # Cannot handle the document's dimensions!!!
#            inkex.errormsg( gettext.gettext(
#            'This document does not have valid dimensions.\r\r' +
#            'Consider starting with the WaterColorBot template, or ' +
#            'setting the document size to 3200 px (wide) x 800 px (tall).\r\r' +
#            'Document dimensions may be set in Inkscape with ' +
#            'File > Document Properties.\r\rThe document dimensions must be unitless or have ' +
#            'units of pixels (px) or percentages (%).   '    ) )
#            return            
#            
#            
        # Viewbox handling
        # Also ignores the preserveAspectRatio attribute
        viewbox = self.svg.get( 'viewBox' )
        if viewbox:
            vinfo = viewbox.strip().replace( ',', ' ' ).split( ' ' )
            if ( vinfo[2] != 0 ) and ( vinfo[3] != 0 ):
                sx = self.svgWidth / float( vinfo[2] )
                sy = self.svgHeight / float( vinfo[3] )
                self.svgTransform = simpletransform.parseTransform( 'scale(%f,%f) translate(%f,%f)' % (sx, sy, -float( vinfo[0] ), -float( vinfo[1])))

        self.ServoSetup()
        self.penUp() 
        self.EnableMotors() #Set plotting resolution

        try:
            # wrap everything in a try so we can for sure close the serial port 
            self.recursivelyTraverseSvg( self.svg, self.svgTransform )
            self.penUp()   #Always end with pen-up
 
            # return to home after end of normal plot
            if ( ( not self.bStopped ) and ( self.ptFirst ) ):
                self.xBoundsMin = wcb_conf.F_StartPos_X
                self.yBoundsMin = wcb_conf.F_StartPos_Y
                self.fX = self.ptFirst[0]
                self.fY = self.ptFirst[1] 
                self.nodeCount = self.nodeTarget    
#                self.plotLineAndTime(self.fX, self.fY )
                self.penUpRapidMove( self.fX, self.fY ) #Rapid pen-up movements
            if ( not self.bStopped ): 
                if (self.options.tab == "splash") or (self.options.tab == "layers") or (self.options.tab == "resume"):
                    self.svgLayer = 0
                    self.svgNodeCount = 0
                    self.svgLastPath = 0
                    self.svgLastPathNC = 0
                    self.svgLastKnownPosX = 0
                    self.svgLastKnownPosY = 0
                    self.svgPausedPosX = 0
                    self.svgPausedPosY = 0
                    #Clear saved position data from the SVG file,
                    #  IF we have completed a normal plot from the splash, layer, or resume tabs.

        finally:
            # We may have had an exception and lost the serial port...
            pass

    def recursivelyTraverseSvg( self, aNodeList,
            matCurrent=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
            parent_visibility='visible' ):
        """
        Recursively traverse the svg file to plot out all of the
        paths.  The function keeps track of the composite transformation
        that should be applied to each path.

        This function handles path, group, line, rect, polyline, polygon,
        circle, ellipse and use (clone) elements.  Notable elements not
        handled include text.  Unhandled elements should be converted to
        paths in Inkscape.
        """
        for node in aNodeList:
            if self.bStopped:
                return
            # Ignore invisible nodes
            v = node.get( 'visibility', parent_visibility )
            if v == 'inherit':
                v = parent_visibility
            if v == 'hidden' or v == 'collapse':
                pass

            # first apply the current matrix transform to this node's transform
            matNew = simpletransform.composeTransform( matCurrent, simpletransform.parseTransform( node.get( "transform" ) ) )

            if (node.getparent() == self.svg):
                #Handle special case of Top-level object found
                if node.tag == inkex.addNS( 'g', 'svg' ) or node.tag == 'g':
                    pass #case handled elsewhere
                elif node.tag == inkex.addNS( 'use', 'svg' ) or node.tag == 'use':
                    pass #case handled elsewhere            
                else:
                    #only paint if we're not auto-changing colors,
                    # and NOT painting from Layers tab. (Pencil: OK. Watercolors, not so much: use numbered layers, please.)

                    self.plotCurrentLayer = False
                    if (self.options.autoChange == False):
                        self.plotCurrentLayer = True
                        
                    if (self.PrintFromLayersTab):
                        self.plotCurrentLayer = False
            
                    if (self.plotCurrentLayer == True):
                        self.LayersFoundToPlot = True
            
            if node.tag == inkex.addNS( 'g', 'svg' ) or node.tag == 'g':

                self.penUp()
                if ( node.get( inkex.addNS( 'groupmode', 'inkscape' ) ) == 'layer' ): 
                    self.sCurrentLayerName = node.get( inkex.addNS( 'label', 'inkscape' ) )
#                    self.DoWePlotLayer( node.get( inkex.addNS( 'label', 'inkscape' ) ) )
                    self.DoWePlotLayer( self.sCurrentLayerName )


                self.recursivelyTraverseSvg( node, matNew, parent_visibility=v )            
            
            elif node.tag == inkex.addNS( 'use', 'svg' ) or node.tag == 'use':

                # A <use> element refers to another SVG element via an xlink:href="#blah"
                # attribute.  We will handle the element by doing an XPath search through
                # the document, looking for the element with the matching id="blah"
                # attribute.  We then recursively process that element after applying
                # any necessary (x,y) translation.
                #
                # Notes:
                #  1. We ignore the height and width attributes as they do not apply to
                #     path-like elements, and
                #  2. Even if the use element has visibility="hidden", SVG still calls
                #     for processing the referenced element.  The referenced element is
                #     hidden only if its visibility is "inherit" or "hidden".

                refid = node.get( inkex.addNS( 'href', 'xlink' ) )
                if refid:
                    # [1:] to ignore leading '#' in reference
                    path = '//*[@id="%s"]' % refid[1:]
                    refnode = node.xpath( path )
                    if refnode:
                        x = float( node.get( 'x', '0' ) )
                        y = float( node.get( 'y', '0' ) )
                        # Note: the transform has already been applied
                        if ( x != 0 ) or (y != 0 ):
                            matNew2 = simpletransform.composeTransform( matNew, simpletransform.parseTransform( 'translate(%f,%f)' % (x,y) ) )
                        else:
                            matNew2 = matNew
                        v = node.get( 'visibility', v )
                        self.recursivelyTraverseSvg( refnode, matNew2, parent_visibility=v )
                    else:
                        pass
                else:
                    pass

            elif node.tag == inkex.addNS( 'path', 'svg' ):

                # if we're in resume mode AND self.pathcount < self.svgLastPath,
                #    then skip over this path.
                # if we're in resume mode and self.pathcount = self.svgLastPath,
                #    then start here, and set self.nodeCount equal to self.svgLastPathNC
                
                doWePlotThisPath = False 
                if (self.resumeMode): 
                    if (self.pathcount < self.svgLastPath_Old ): 
                        #This path was *completely plotted* already; skip.
                        self.pathcount += 1 
                    elif (self.pathcount == self.svgLastPath_Old ): 
                        #this path is the first *not completely* plotted path:
                        self.nodeCount =  self.svgLastPathNC_Old    #Nodecount after last completed path
                        doWePlotThisPath = True 
                else:
                    doWePlotThisPath = True
                if (doWePlotThisPath):
                    self.pathcount += 1
                    self.plotPath( node, matNew )
                
            elif node.tag == inkex.addNS( 'rect', 'svg' ) or node.tag == 'rect':

                # Manually transform 
                #    <rect x="X" y="Y" width="W" height="H"/> 
                # into 
                #    <path d="MX,Y lW,0 l0,H l-W,0 z"/> 
                # I.e., explicitly draw three sides of the rectangle and the
                # fourth side implicitly

                 
                # if we're in resume mode AND self.pathcount < self.svgLastPath,
                #    then skip over this path.
                # if we're in resume mode and self.pathcount = self.svgLastPath,
                #    then start here, and set
                # self.nodeCount equal to self.svgLastPathNC
                
                doWePlotThisPath = False 
                if (self.resumeMode): 
                    if (self.pathcount < self.svgLastPath_Old ): 
                        #This path was *completely plotted* already; skip.
                        self.pathcount += 1 
                    elif (self.pathcount == self.svgLastPath_Old ): 
                        #this path is the first *not completely* plotted path:
                        self.nodeCount =  self.svgLastPathNC_Old    #Nodecount after last completed path
                        doWePlotThisPath = True 
                else:
                    doWePlotThisPath = True
                if (doWePlotThisPath):
                    self.pathcount += 1
                    # Create a path with the outline of the rectangle
                    newpath = inkex.etree.Element( inkex.addNS( 'path', 'svg' ) )
                    x = float( node.get( 'x' ) )
                    y = float( node.get( 'y' ) )
                    w = float( node.get( 'width' ) )
                    h = float( node.get( 'height' ) )
                    s = node.get( 'style' )
                    if s:
                        newpath.set( 'style', s )
                    t = node.get( 'transform' )
                    if t:
                        newpath.set( 'transform', t )
                    a = []
                    a.append( ['M ', [x, y]] )
                    a.append( [' l ', [w, 0]] )
                    a.append( [' l ', [0, h]] )
                    a.append( [' l ', [-w, 0]] )
                    a.append( [' Z', []] )
                    newpath.set( 'd', simplepath.formatPath( a ) )
                    self.plotPath( newpath, matNew )
                    
            elif node.tag == inkex.addNS( 'line', 'svg' ) or node.tag == 'line':

                # Convert
                #
                #   <line x1="X1" y1="Y1" x2="X2" y2="Y2/>
                #
                # to
                #
                #   <path d="MX1,Y1 LX2,Y2"/>

                # if we're in resume mode AND self.pathcount < self.svgLastPath,
                #    then skip over this path.
                # if we're in resume mode and self.pathcount = self.svgLastPath,
                #    then start here, and set
                # self.nodeCount equal to self.svgLastPathNC

                doWePlotThisPath = False 
                if (self.resumeMode): 
                    if (self.pathcount < self.svgLastPath_Old ): 
                        #This path was *completely plotted* already; skip.
                        self.pathcount += 1 
                    elif (self.pathcount == self.svgLastPath_Old ): 
                        #this path is the first *not completely* plotted path:
                        self.nodeCount =  self.svgLastPathNC_Old    #Nodecount after last completed path
                        doWePlotThisPath = True 
                else:
                    doWePlotThisPath = True
                if (doWePlotThisPath):
                    self.pathcount += 1
                    # Create a path to contain the line
                    newpath = inkex.etree.Element( inkex.addNS( 'path', 'svg' ) )
                    x1 = float( node.get( 'x1' ) )
                    y1 = float( node.get( 'y1' ) )
                    x2 = float( node.get( 'x2' ) )
                    y2 = float( node.get( 'y2' ) )
                    s = node.get( 'style' )
                    if s:
                        newpath.set( 'style', s )
                    t = node.get( 'transform' )
                    if t:
                        newpath.set( 'transform', t )
                    a = []
                    a.append( ['M ', [x1, y1]] )
                    a.append( [' L ', [x2, y2]] )
                    newpath.set( 'd', simplepath.formatPath( a ) )
                    self.plotPath( newpath, matNew )
                    

            elif node.tag == inkex.addNS( 'polyline', 'svg' ) or node.tag == 'polyline':

                # Convert
                #  <polyline points="x1,y1 x2,y2 x3,y3 [...]"/> 
                # to 
                #   <path d="Mx1,y1 Lx2,y2 Lx3,y3 [...]"/> 
                # Note: we ignore polylines with no points

                pl = node.get( 'points', '' ).strip()
                if pl == '':
                    pass

                #if we're in resume mode AND self.pathcount < self.svgLastPath, then skip over this path.
                #if we're in resume mode and self.pathcount = self.svgLastPath, then start here, and set
                # self.nodeCount equal to self.svgLastPathNC
                
                doWePlotThisPath = False 
                if (self.resumeMode): 
                    if (self.pathcount < self.svgLastPath_Old ): 
                        #This path was *completely plotted* already; skip.
                        self.pathcount += 1 
                    elif (self.pathcount == self.svgLastPath_Old ): 
                        #this path is the first *not completely* plotted path:
                        self.nodeCount =  self.svgLastPathNC_Old    #Nodecount after last completed path
                        doWePlotThisPath = True 
                else:
                    doWePlotThisPath = True
                if (doWePlotThisPath):
                    self.pathcount += 1
                    
                    pa = pl.split()
                    if not len( pa ):
                        continue
                    # Issue 29: pre 2.5.? versions of Python do not have
                    #    "statement-1 if expression-1 else statement-2"
                    # which came out of PEP 308, Conditional Expressions
                    #d = "".join( ["M " + pa[i] if i == 0 else " L " + pa[i] for i in range( 0, len( pa ) )] )
                    d = "M " + pa[0]
                    for i in range( 1, len( pa ) ):
                        d += " L " + pa[i]
                    newpath = inkex.etree.Element( inkex.addNS( 'path', 'svg' ) )
                    newpath.set( 'd', d );
                    s = node.get( 'style' )
                    if s:
                        newpath.set( 'style', s )
                    t = node.get( 'transform' )
                    if t:
                        newpath.set( 'transform', t )
                    self.plotPath( newpath, matNew )

            elif node.tag == inkex.addNS( 'polygon', 'svg' ) or node.tag == 'polygon':

                # Convert 
                #  <polygon points="x1,y1 x2,y2 x3,y3 [...]"/> 
                # to 
                #   <path d="Mx1,y1 Lx2,y2 Lx3,y3 [...] Z"/> 
                # Note: we ignore polygons with no points

                pl = node.get( 'points', '' ).strip()
                if pl == '':
                    pass

                #if we're in resume mode AND self.pathcount < self.svgLastPath, then skip over this path.
                #if we're in resume mode and self.pathcount = self.svgLastPath, then start here, and set
                # self.nodeCount equal to self.svgLastPathNC

                doWePlotThisPath = False 
                if (self.resumeMode): 
                    if (self.pathcount < self.svgLastPath_Old ): 
                        #This path was *completely plotted* already; skip.
                        self.pathcount += 1 
                    elif (self.pathcount == self.svgLastPath_Old ): 
                        #this path is the first *not completely* plotted path:
                        self.nodeCount =  self.svgLastPathNC_Old    #Nodecount after last completed path
                        doWePlotThisPath = True 
                else:
                    doWePlotThisPath = True
                if (doWePlotThisPath):
                    self.pathcount += 1
                    
                    pa = pl.split()
                    if not len( pa ):
                        continue
                    # Issue 29: pre 2.5.? versions of Python do not have
                    #    "statement-1 if expression-1 else statement-2"
                    # which came out of PEP 308, Conditional Expressions
                    #d = "".join( ["M " + pa[i] if i == 0 else " L " + pa[i] for i in range( 0, len( pa ) )] )
                    d = "M " + pa[0]
                    for i in range( 1, len( pa ) ):
                        d += " L " + pa[i]
                    d += " Z"
                    newpath = inkex.etree.Element( inkex.addNS( 'path', 'svg' ) )
                    newpath.set( 'd', d );
                    s = node.get( 'style' )
                    if s:
                        newpath.set( 'style', s )
                    t = node.get( 'transform' )
                    if t:
                        newpath.set( 'transform', t )
                    self.plotPath( newpath, matNew )
                    
            elif node.tag == inkex.addNS( 'ellipse', 'svg' ) or \
                node.tag == 'ellipse' or \
                node.tag == inkex.addNS( 'circle', 'svg' ) or \
                node.tag == 'circle':

                    # Convert circles and ellipses to a path with two 180 degree arcs.
                    # In general (an ellipse), we convert 
                    #   <ellipse rx="RX" ry="RY" cx="X" cy="Y"/> 
                    # to 
                    #   <path d="MX1,CY A RX,RY 0 1 0 X2,CY A RX,RY 0 1 0 X1,CY"/> 
                    # where 
                    #   X1 = CX - RX
                    #   X2 = CX + RX 
                    # Note: ellipses or circles with a radius attribute of value 0 are ignored

                    if node.tag == inkex.addNS( 'ellipse', 'svg' ) or node.tag == 'ellipse':
                        rx = float( node.get( 'rx', '0' ) )
                        ry = float( node.get( 'ry', '0' ) )
                    else:
                        rx = float( node.get( 'r', '0' ) )
                        ry = rx
                    if rx == 0 or ry == 0:
                        pass

                    
                    #if we're in resume mode AND self.pathcount < self.svgLastPath, then skip over this path.
                    #if we're in resume mode and self.pathcount = self.svgLastPath, then start here, and set
                    # self.nodeCount equal to self.svgLastPathNC
                    
                    doWePlotThisPath = False 
                    if (self.resumeMode): 
                        if (self.pathcount < self.svgLastPath_Old ): 
                            #This path was *completely plotted* already; skip.
                            self.pathcount += 1 
                        elif (self.pathcount == self.svgLastPath_Old ): 
                            #this path is the first *not completely* plotted path:
                            self.nodeCount =  self.svgLastPathNC_Old    #Nodecount after last completed path
                            doWePlotThisPath = True 
                    else:
                        doWePlotThisPath = True
                    if (doWePlotThisPath):
                        self.pathcount += 1
                    
                        cx = float( node.get( 'cx', '0' ) )
                        cy = float( node.get( 'cy', '0' ) )
                        x1 = cx - rx
                        x2 = cx + rx
                        d = 'M %f,%f ' % ( x1, cy ) + \
                            'A %f,%f ' % ( rx, ry ) + \
                            '0 1 0 %f,%f ' % ( x2, cy ) + \
                            'A %f,%f ' % ( rx, ry ) + \
                            '0 1 0 %f,%f' % ( x1, cy )
                        newpath = inkex.etree.Element( inkex.addNS( 'path', 'svg' ) )
                        newpath.set( 'd', d );
                        s = node.get( 'style' )
                        if s:
                            newpath.set( 'style', s )
                        t = node.get( 'transform' )
                        if t:
                            newpath.set( 'transform', t )
                        self.plotPath( newpath, matNew )
                        
                            
            elif node.tag == inkex.addNS( 'metadata', 'svg' ) or node.tag == 'metadata':
                pass
            elif node.tag == inkex.addNS( 'defs', 'svg' ) or node.tag == 'defs':
                pass
            elif node.tag == inkex.addNS( 'namedview', 'sodipodi' ) or node.tag == 'namedview':
                pass
            elif node.tag == inkex.addNS( 'WCB', 'svg' ) or node.tag == 'WCB':
                pass
            elif node.tag == inkex.addNS( 'eggbot', 'svg' ) or node.tag == 'eggbot':
                pass            
            elif node.tag == inkex.addNS( 'title', 'svg' ) or node.tag == 'title':
                pass
            elif node.tag == inkex.addNS( 'desc', 'svg' ) or node.tag == 'desc':
                pass
            elif (node.tag == inkex.addNS( 'text', 'svg' ) or node.tag == 'text' or
                node.tag == inkex.addNS( 'flowRoot', 'svg' ) or node.tag == 'flowRoot'):
                if ('text' not in self.warnings) and (self.plotCurrentLayer):
                    inkex.errormsg( gettext.gettext( 'Warning: in layer "' + 
                        self.sCurrentLayerName + '" unable to draw text; ' +
                        'Please convert text to a path before drawing, using ' +
                        'Path > Object to Path. Or, use the Hershey Text extension, '+
                        'which can be found under Extensions > Render.' ) )
                    self.warnings['text'] = 1
                pass
            elif node.tag == inkex.addNS( 'image', 'svg' ) or node.tag == 'image':
                if ('image' not in self.warnings) and (self.plotCurrentLayer):
                    inkex.errormsg( gettext.gettext( 'Warning: in layer "' + 
                        self.sCurrentLayerName + '" unable to draw bitmap images; ' +
                        'Please convert images to line art before drawing. ' +
                        ' Consider using the Path > Trace bitmap tool. ' ) )
                    self.warnings['image'] = 1
                pass
            elif node.tag == inkex.addNS( 'pattern', 'svg' ) or node.tag == 'pattern':
                pass
            elif node.tag == inkex.addNS( 'radialGradient', 'svg' ) or node.tag == 'radialGradient':
                # Similar to pattern
                pass
            elif node.tag == inkex.addNS( 'linearGradient', 'svg' ) or node.tag == 'linearGradient':
                # Similar in pattern
                pass
            elif node.tag == inkex.addNS( 'style', 'svg' ) or node.tag == 'style':
                # This is a reference to an external style sheet and not the value
                # of a style attribute to be inherited by child elements
                pass
            elif node.tag == inkex.addNS( 'cursor', 'svg' ) or node.tag == 'cursor':
                pass
            elif node.tag == inkex.addNS( 'color-profile', 'svg' ) or node.tag == 'color-profile':
                # Gamma curves, color temp, etc. are not relevant to single color output
                pass
            elif not isinstance( node.tag, basestring ):
                # This is likely an XML processing instruction such as an XML
                # comment.  lxml uses a function reference for such node tags
                # and as such the node tag is likely not a printable string.
                # Further, converting it to a printable string likely won't
                # be very useful.
                pass
            else:
                if (str( node.tag ) not in self.warnings and (self.plotCurrentLayer):
                    t = str( node.tag ).split( '}' )
                    inkex.errormsg( gettext.gettext( 'Warning: in layer "' + 
                        self.sCurrentLayerName + '" unable to draw <' + str( t[-1] ) +
                        '> object, please convert it to a path first.' ) )
                    self.warnings[str( node.tag )] = 1
                pass



    def DoWePlotLayer( self, strLayerName ):
        """
        Logic for this section:
        We plot a layer...
            From the Paint tab,  if (autoChange is false) OR (layer number is 0-8)
            From the Layers tab, if ((autoChange is false) OR (layer number is 0-8)) AND
                                  (layer name == (i.e., begins with) self.svgLayer). 

        Parse layer name for layer number and other properties.
        
        First: scan layer name for first non-numeric character,
        and scan the part before that (if any) into a number
        Then, (if not printing in all-layers mode)
        see if the number matches the layer number that we are printing.
        
        Secondary function: Parse characters following the layer number (if any) to see if
        there is a "+H" or "+S" escape code, that indicates that overrides the pen-down
        height or speed for the given layer. We also check for the "%" leading character,
        which indicates a layer that should be skipped.
        """
        #self.options.autoChange
        #inkex.errormsg('Plotting layer named: ' + node.get(inkex.addNS('label', 'inkscape'))) 

        # Look at layer name.  Sample first character, then first two, and
        # so on, until the string ends or the string no longer consists of digit characters only.
        TempNumString = 'x'
        stringPos = 1    
        layerNameInt = -1
        layerMatch = False    
        if sys.version_info < (3,): #Yes this is ugly. More elegant suggestions welcome. :)
            CurrentLayerName = strLayerName.encode( 'ascii', 'ignore' ) #Drop non-ascii characters    
        else:
            CurrentLayerName=str(strLayerName)        
        CurrentLayerName.lstrip #remove leading whitespace
        self.plotCurrentLayer = True    #Temporarily assume that we are plotting the layer

        MaxLength = len( CurrentLayerName )
        if MaxLength > 0:
            if CurrentLayerName[0] == '%':
                self.plotCurrentLayer = False    #First character is "%" -- skip this layer
            while stringPos <= MaxLength:
                LayerNameFragment = CurrentLayerName[:stringPos]
                if (LayerNameFragment.isdigit()):
                    TempNumString = CurrentLayerName[:stringPos] # Store longest numeric string so far
                    stringPos = stringPos + 1
                else:
                    break

        if ( str.isdigit( TempNumString ) ):
            layerNameInt = int( float( TempNumString ) )
            if ( self.svgLayer == layerNameInt ):
                layerMatch = True    #Match! The current layer IS named.

        if (self.options.autoChange == False) or (( layerNameInt >= 0) and (layerNameInt <= wcb_conf.N_Paint_Count )):
            self.plotCurrentLayer = True
            
        if ((self.PrintFromLayersTab) and (layerMatch == False)):
            self.plotCurrentLayer = False

        if (self.plotCurrentLayer == True):
            self.LayersFoundToPlot = True
            self.LayerPaintColor = layerNameInt

            #End of part 1, current layer to see if we print it.
            #Now, check to see if there is additional information coded here.

            oldPenDown = self.LayerPenDownPosition
            oldSpeed = self.LayerPenDownSpeed
                
            #set default values before checking for any overrides:    
            self.LayerOverridePenDownHeight = False
            self.LayerOverrideSpeed = False
            self.LayerPenDownPosition = -1
            self.LayerPenDownSpeed = -1

            if (stringPos > 0):
                stringPos = stringPos - 1

            if MaxLength > stringPos + 2:
                while stringPos <= MaxLength:    
                    EscapeSequence = CurrentLayerName[stringPos:stringPos+2].lower()
                    if (EscapeSequence == "+h") or (EscapeSequence == "+s"):
                        paramStart = stringPos + 2
                        stringPos = stringPos + 3
                        TempNumString = 'x'
                        if MaxLength > 0:
                            while stringPos <= MaxLength:
                                if str.isdigit( CurrentLayerName[paramStart:stringPos] ):
                                    TempNumString = CurrentLayerName[paramStart:stringPos] # Longest numeric string so far
                                    stringPos = stringPos + 1
                                else:
                                    break
                        if ( str.isdigit( TempNumString ) ):
                            parameterInt = int( float( TempNumString ) )
                    
                            if (EscapeSequence == "+h"):
                                if ((parameterInt >= 0) and (parameterInt <= 100)):
                                    self.LayerOverridePenDownHeight = True
                                    self.LayerPenDownPosition = parameterInt
                                
                            if (EscapeSequence == "+s"):
                                if ((parameterInt > 0) and (parameterInt <= 100)):
                                    self.LayerOverrideSpeed = True
                                    self.LayerPenDownSpeed = parameterInt
                                    
                        stringPos = paramStart + len(TempNumString)
                    else:
                        break #exit loop. 
            
            if (self.LayerPenDownSpeed != oldSpeed):
                self.EnableMotors()    #Set speed value variables for this layer.
            if (self.LayerPenDownPosition != oldPenDown):
                self.ServoSetup()    #Set pen height value variables for this layer.




    def plotPath( self, path, matTransform ):
        '''
        Plot the path while applying the transformation defined
        by the matrix [matTransform].
        '''
        # turn this path into a cubicsuperpath (list of beziers)...

        d = path.get( 'd' )
        if len( simplepath.parsePath( d ) ) == 0:
            return

        if self.plotCurrentLayer:
            if (self.BrushColor != self.LayerPaintColor) or (self.BrushColor < 0):
                self.PaintToolChange(self.LayerPaintColor)
                
            # reset page bounds for plotting:
            self.xBoundsMax = wcb_conf.N_PAGE_WIDTH
            self.xBoundsMin = 0
            self.yBoundsMax = wcb_conf.N_PAGE_HEIGHT
            self.yBoundsMin = 0
    
            p = cubicsuperpath.parsePath( d )
    
            # ...and apply the transformation to each point
            simpletransform.applyTransformToPath( matTransform, p )
    
            # p is now a list of lists of cubic beziers [control pt1, control pt2, endpoint]
            # where the start-point is the last point in the previous segment.
            for sp in p:
            
                plot_utils.subdivideCubicPath( sp, self.options.smoothness )
                nIndex = 0
    
                for csp in sp:
    
                    if self.bStopped:
                        return
    
                    if self.plotCurrentLayer:
                        if nIndex == 0:
                            self.penUp()
                            self.virtualPenIsUp = True
                        elif nIndex == 1:
                            self.penDown()
                            self.virtualPenIsUp = False
    
                    nIndex += 1
    
                    self.fX = float( csp[1][0] )    # Set move destination
                    self.fY = float( csp[1][1] )  
                    

                    if ( self.virtualPenIsUp ):        
                        self.penUpRapidMove( self.fX, self.fY ) #Rapid pen-up movements
                    else:
                        self.plotLineAndTime( self.fX, self.fY ) #Draw a segment

                        
            if ( not self.bStopped ):    #an "index" for resuming plots quickly-- record last complete path
                self.svgLastPath = self.pathcount #The number of the last path completed
                self.svgLastPathNC = self.nodeCount #the node count after the last path was completed.            
            

    def plotLineAndTime( self, xDest, yDest ):
        '''
        Send commands out the com port as a line segment (dx, dy) and a time (ms) the segment
        should take to implement.  
        Important note: Everything up to this point uses *pixel* scale. 
        Here, we convert from floating-point pixel scale to actual motor steps, w/ present DPI.
        '''
        
        maxSegmentDuration = 250.0  # Maximum time to spend painting a given segment

        if (self.ignoreLimits == False):
            if (xDest > self.xBoundsMax):    #Check machine size limit; truncate at edges
                xDest = self.xBoundsMax
            if (xDest < self.xBoundsMin):    #Check machine size limit; truncate at edges
                xDest = self.xBoundsMin            
            if (yDest > self.yBoundsMax):    #Check machine size limit; truncate at edges
                yDest = self.yBoundsMax
            if (yDest < self.yBoundsMin):    #Check machine size limit; truncate at edges
                yDest = self.yBoundsMin
            
        if self.bStopped:
            return
        if ( self.fCurrX is None ):
            return
        
        xTemp = self.stepsPerPx * ( xDest - self.fCurrX ) + self.xErr
        yTemp = self.stepsPerPx * ( yDest - self.fCurrY ) + self.yErr

        nDeltaX = int (round(xTemp)) # Number of motor steps required
        nDeltaY = int (round(yTemp)) 

        self.xErr = xTemp - float(nDeltaX)  # Keep track of rounding errors, so that they do not accumulate.
        self.yErr = yTemp - float(nDeltaY)

        self.fSpeed = self.BrushDownSpeed

        if ( plot_utils.distance( nDeltaX, nDeltaY ) > 0 ):
            self.nodeCount += 1

            if self.resumeMode:
                if ( self.nodeCount >= self.nodeTarget ):
                    self.resumeMode = False
                    self.paintdist = 0

                    if ( not self.virtualPenIsUp ):
                        self.penDown()
                        self.fSpeed = self.BrushDownSpeed

            nTime =  10000.00 / self.fSpeed * plot_utils.distance( nDeltaX, nDeltaY )
            nTime = int( math.ceil(nTime / 10.0))

            while ( ( abs( nDeltaX ) > 0 ) or ( abs( nDeltaY ) > 0 ) ):
            
                # Put re-inking *before* the movement here, so that we only do it if there's more painting. 
                if (self.ReInkingNow == False):
                    if ((self.bPenIsUp == False) and (self.options.reInkEnable)):
                        if (self.paintdist > self.reInkDist):
                            self.reInkBrush() 
            
                xd = 0
                yd = 0
                                
                if ( nTime > maxSegmentDuration ):
                    xd = int( math.floor( ( maxSegmentDuration * nDeltaX ) / nTime ) )
                    yd = int( math.floor( ( maxSegmentDuration * nDeltaY ) / nTime ) )
                    td = int( maxSegmentDuration )
                else:
                    xd = nDeltaX
                    yd = nDeltaY
                    td = nTime
                    if ( td < 1 ):
                       td = 1        # don't allow zero-time moves.

                if (not self.resumeMode) and (not self.bStopped):
                    if ( self.options.revMotor1 ):
                        xd2 = -xd
                    else:
                        xd2 = xd
                    if ( self.options.revMotor2):
                        yd2 = -yd
                    else:
                        yd2 = yd 
                        
                    strOutput = ','.join( ['SM', str( td ), str( xd2 ), str( yd2 )] ) + '\r' #Move the motors!  WaterColorBot

                    ebb_serial.command( self.serialPort, strOutput )        
                    self.fCurrX += xd / self.stepsPerPx   # Update current position
                    self.fCurrY += yd / self.stepsPerPx        

                    self.svgLastKnownPosX = self.fCurrX - wcb_conf.F_StartPos_X
                    self.svgLastKnownPosY = self.fCurrY - wcb_conf.F_StartPos_Y    
                    
                    if (self.ReInkingNow == False):
                        if ((self.bPenIsUp == False) and (self.options.reInkEnable)):
                            self.paintdist += plot_utils.distance( xd, yd )
                                            
                nDeltaX -= xd
                nDeltaY -= yd 
                nTime -= td
            strButton = ebb_motion.QueryPRGButton(self.serialPort)    #Query if button pressed    
            if strButton[0] != '0':
                self.svgNodeCount = self.nodeCount;
                self.svgPausedPosX = self.fCurrX - wcb_conf.F_StartPos_X    #self.svgLastKnownPosX
                self.svgPausedPosY = self.fCurrY - wcb_conf.F_StartPos_Y    #self.svgLastKnownPosY
            
                inkex.errormsg( 'Plot paused by button press after segment number ' + str( self.nodeCount ) + '.' )
                inkex.errormsg( 'Use the "Resume" feature to continue.' )
                self.bStopped = True
                return
                    


    def penUpRapidMove( self, xDest, yDest ):
        '''
        Like plotLineAndTime, but for use with a single straight line, with pen up.
        Implement basic "trapezoid" acceleration and deceleration
        '''

        if (self.ignoreLimits == False):
            xDest, xBounded = plot_utils.checkLimits( xDest, self.xBoundsMin, self.xBoundsMax )
            yDest, yBounded = plot_utils.checkLimits( yDest, self.yBoundsMin, self.yBoundsMax )
            if (xBounded or yBounded):
                self.warnOutOfBounds = True

        if self.bStopped:
            return
        if ( self.fCurrX is None ):
            return
        
#        Distances to move:
        xMovementIdeal = self.stepsPerPx * ( xDest - self.fCurrX )    
        yMovementIdeal = self.stepsPerPx * ( yDest - self.fCurrY )

#        Look at distance to move along 45-degree axes, for native motor steps:
        motorSteps1 = int (round(xMovementIdeal)) # Number of native motor steps required, Axis 1
        motorSteps2 = int (round(yMovementIdeal)) # Number of native motor steps required, Axis 2

        plotDistance = plot_utils.distance( motorSteps1, motorSteps2 )
        
        if (plotDistance < 1.0): #if total movement is less than one step, skip this movement.
            return

        speedLimit = self.BrushUpSpeed
        accelRate = self.BrushUpSpeed/wcb_conf.F_Accel_Factor     # acceleration/deceleration rate: Maximum speed/time to reach that speed
        timeSlice = 0.030    #(seconds): Slice travel into slices of time that are at least 0.030 seconds (30 ms) long

        # Choose top speed by _estimating_ what it would be if we had continuous acceleration
        #    
        # Total travel distance is _plotDistance_
        # Question: How fast can we get in half of this distance?
        #     Set (plotDistance/2) equal to (1/2) * a * (tAccel)^2 , and solve for t_accel:
        #     Then, t_accel = sqrt( plotDistance / a)
        
        tAccel = math.sqrt( plotDistance / accelRate)   #time interval for acceleration or deceleration
        
        if ( tAccel <= (3 * timeSlice )):
            self.plotLineAndTime( xDest, yDest )    # Short move (less than three timeSlices): Use constant-velocity routine.
            return

        self.nodeCount += 1        # This whole rapid move counts as ONE node, for our purposes.
        if self.resumeMode:
            if ( self.nodeCount >= self.nodeTarget ):
                self.resumeMode = False
                if ( not self.virtualPenIsUp ):
                    self.penDown()    

        # Declare arrays, all integers. 
        # These are _normally_ 4-byte integers, but could (theoretically) be 2-byte integers on some systems.
        #   if so, this could cause errors in rare cases (very large/long moves, etc.). 
        # Set up an alert system, just in case!

        durationArray = array('I') # unsigned integer for duration -- up to 65 seconds for a move if only 2 bytes.
        distArray = array('f')    #float
        destArray1 = array('i')    #signed integer
        destArray2 = array('i')    #signed integer

        if (destArray2.itemsize < 4):
            self.warnDataSize = True

        velocity = 0.0
        timeElapsed = 0.0        
        position = 0.0

        # Speed _after_ acceleration interval:            
        speedMax = accelRate * tAccel        
        if ( speedMax > speedLimit ):
            speedMax = speedLimit    # This move is longer than 2*tAccel; We will reach _full cruising speed_!
            
            intervals = int(math.floor(tAccel / timeSlice))    # Number of intervals each, during acceleration OR deceleration 
            timePerInterval = tAccel / intervals            
            #Add a center "cruising" speed interval if there is time for it only.
            
            velocityStepSize = speedMax/(intervals + 1.0)    
            # For six time intervals of acceleration, first interval is at velocity (max/7)
            # 6th (last) time interval is at 6*max/7
            # after this interval, we are at full speed.
            
            for index in range(0, intervals):        #Calculate acceleration phase
                velocity += velocityStepSize
                timeElapsed += timePerInterval
                position += velocity * timePerInterval
                durationArray.append(int(round(timeElapsed * 1000.0)))
                distArray.append(position)        #Estimated distance along direction of travel

            coastingDistance = plotDistance - (2 * position)    
            
            if (coastingDistance > (timePerInterval * speedMax)):
                # There is enough time for (at least) one interval at full cruising speed.
                velocity = speedMax
                cruisingTime = coastingDistance / velocity
                timeElapsed += cruisingTime
                durationArray.append(int(round(timeElapsed * 1000.0)))
                position += velocity * cruisingTime
                distArray.append(position)        #Estimated distance along direction of travel                
#                inkex.errormsg( 'FullSpeed duration: ' + str( cruisingTime ) )                
#                inkex.errormsg( 'FullSpeed distance: ' + str( velocity * cruisingTime ) )                

            for index in range(0, intervals):        #Calculate deceleration phase
                velocity -= velocityStepSize
                timeElapsed += timePerInterval
                position += velocity * timePerInterval
                durationArray.append(int(round(timeElapsed * 1000.0)))
                distArray.append(position)        #Estimated distance along direction of travel
                
        else:
            # We will _not_ reach full cruising speed.
            intervals = int(math.floor( 2 *    tAccel / timeSlice))    #TOTAL number of intervals, including acceleration and deceleration
            if (intervals % 2 == 0):  # Even number of intervals:
                intervals += 1    # Guarantee an odd number of intervals -- possibly a little shorter.
                
            timePerInterval = (2 * tAccel) / intervals

            accelIntervals = int(math.ceil(intervals / 2.0))
            velocityStepSize = speedMax / accelIntervals    

            for index in range(0, accelIntervals):        #Calculate acceleration phase
                velocity += velocityStepSize
                timeElapsed += timePerInterval
                position += velocity * timePerInterval
                durationArray.append(int(round(timeElapsed * 1000.0)))
                distArray.append(position)        #Estimated distance along direction of travel
                
            for index in range(0, intervals - accelIntervals):        #Calculate deceleration phase
                velocity -= velocityStepSize
                timeElapsed += timePerInterval
                position += velocity * timePerInterval
                durationArray.append(int(round(timeElapsed * 1000.0)))
                distArray.append(position)        #Estimated distance along direction of travel

        for index in range (0, len(distArray) ):
            fractionalDistance = distArray[index] / position # Fractional position along the intended path
            destArray1.append ( int(round( fractionalDistance * motorSteps1)))
            destArray2.append ( int(round( fractionalDistance * motorSteps2)))

        prevMotor1 = 0
        prevMotor2 = 0
        prevTime = 0
        
        for index in range (0, len(destArray1) ):
            moveSteps1 = destArray1[index] - prevMotor1
            moveSteps2 = destArray2[index] - prevMotor2
            moveTime = durationArray[index] - prevTime
            prevTime = durationArray[index]

            
            if ( moveTime < 1 ):
                moveTime = 1        # don't allow zero-time moves.
    
            if (abs((float(moveSteps1) / float(moveTime))) < 0.002):    
                moveSteps1 = 0        #don't allow too-slow movements of this axis
            if (abs((float(moveSteps2) / float(moveTime))) < 0.002):    
                moveSteps2 = 0        #don't allow too-slow movements of this axis
    
            prevMotor1 += moveSteps1
            prevMotor2 += moveSteps2

            xSteps = moveSteps1 # Result will be a float.
            ySteps = moveSteps2    

            if ((moveSteps1 != 0) or (moveSteps2 != 0)): # if at least one motor step is required for this move....
    
                if (not self.resumeMode) and (not self.bStopped):
                    if ( self.options.revMotor1 ):
                        moveSteps1Copy = -moveSteps1
                    else:
                        moveSteps1Copy = moveSteps1
                    if ( self.options.revMotor2):
                        moveSteps2Copy = -moveSteps2
                    else:
                        moveSteps2Copy = moveSteps2 
                    
                    ebb_motion.doXYMove( self.serialPort, moveSteps2Copy, moveSteps1Copy, moveTime )            
                    if (moveTime > 15):
                        if self.options.tab != "manual":
                            time.sleep(float(moveTime - 10)/1000.0)  #pause before issuing next command
                    else:
                        self.warnShortMoves = True

                    self.fCurrX += xSteps / self.stepsPerPx   # Update current position
                    self.fCurrY += ySteps / self.stepsPerPx        
    
                    self.svgLastKnownPosX = self.fCurrX -  wcb_conf.F_StartPos_X
                    self.svgLastKnownPosY = self.fCurrY -  wcb_conf.F_StartPos_Y

        strButton = ebb_motion.QueryPRGButton(self.serialPort)    #Query if button pressed
        if strButton[0] == '1': #button pressed
            self.svgNodeCount = self.nodeCount;
            self.svgPausedPosX = self.fCurrX - wcb_conf.F_StartPos_X    #self.svgLastKnownPosX
            self.svgPausedPosY = self.fCurrY - wcb_conf.F_StartPos_Y    #self.svgLastKnownPosY            
            inkex.errormsg( 'Plot paused by button press after node number ' + str( self.nodeCount ) + '.' )
            inkex.errormsg( 'Use the "resume" feature to continue.' )
            self.bStopped = True
            return

    def EnableMotors( self ):
        # Enable motors, set native motor resolution, and set speed scales.

        if ((self.CleaningNow == True) or (self.ReInkingNow == True)):
            LocalPenDownSpeed = self.options.penDownSpeed
        else:        
            if (self.LayerOverrideSpeed):
                LocalPenDownSpeed = self.LayerPenDownSpeed
            else:    
                LocalPenDownSpeed = self.options.penDownSpeed

        if ( self.options.resolution == 1 ):
            ebb_motion.sendEnableMotors(self.serialPort, 1) # 16X microstepping
            self.stepsPerPx = float( wcb_conf.F_DPI_16X / 90.0 )
            self.BrushUpSpeed   = self.options.penUpSpeed * wcb_conf.F_Speed_Scale
            self.BrushDownSpeed = LocalPenDownSpeed * wcb_conf.F_Speed_Scale
        elif ( self.options.resolution == 2 ):
            ebb_motion.sendEnableMotors(self.serialPort, 2) # 8X microstepping
            self.stepsPerPx = float( wcb_conf.F_DPI_16X / 180.0 )  
            self.BrushUpSpeed   = self.options.penUpSpeed * wcb_conf.F_Speed_Scale / 2
            self.BrushDownSpeed = LocalPenDownSpeed * wcb_conf.F_Speed_Scale / 2
        else:
            ebb_motion.sendEnableMotors(self.serialPort, 3) # 4X microstepping  
            self.stepsPerPx = float( wcb_conf.F_DPI_16X / 360.0 )
            self.BrushUpSpeed   = self.options.penUpSpeed * wcb_conf.F_Speed_Scale / 4
            self.BrushDownSpeed = LocalPenDownSpeed * wcb_conf.F_Speed_Scale / 4
        self.reInkDist = self.options.reInkDist * 90 * self.stepsPerPx # in motor steps

    def penUp( self ):
        self.virtualPenIsUp = True  # Virtual pen keeps track of state for resuming plotting.
        if ( not self.resumeMode) and (not self.bPenIsUp):    # skip if pen is already up, or if we're resuming.
            ebb_motion.sendPenUp(self.serialPort, self.options.penUpDelay )                
            self.bPenIsUp = True

    def penDown( self ):
        self.virtualPenIsUp = False  # Virtual pen keeps track of state for resuming plotting.
        if (self.bPenIsUp != False):  # skip if pen is already down
            if ((not self.resumeMode) and ( not self.bStopped )): #skip if resuming or stopped
                self.ServoSetMode()
                ebb_motion.sendPenDown(self.serialPort, self.options.penDownDelay )                        
                self.bPenIsUp = False

    def ServoSetupWrapper( self ):
        # Assert what the defined "up" and "down" positions of the servo motor should be,
        #    and determine what the pen state is.
        self.ServoSetup()
        strVersion = ebb_serial.query( self.serialPort, 'QP\r' )
        if strVersion[0] == '0':
            self.bPenIsUp = False
        else:
            self.bPenIsUp = True

    def ServoSetup( self ):
        ''' Pen position units range from 0% to 100%, which correspond to
            a timing range of 7500 - 25000 in units of 1/(12 MHz).
            1% corresponds to ~14.6 us, or 175 units of 1/(12 MHz).
        '''
    
        if (self.LayerOverridePenDownHeight):
            penDownPos = self.LayerPenDownPosition
        else:    
            penDownPos = self.options.penDownPosition

        intTemp = 7500 + 175 * self.options.penUpPosition
        ebb_serial.command( self.serialPort,  'SC,4,' + str( intTemp ) + '\r' )    
                
        intTemp = 7500 + 175 * penDownPos
        ebb_serial.command( self.serialPort,  'SC,5,' + str( intTemp ) + '\r' )

        ''' Servo speed units are in units of %/second, referring to the
            percentages above.  The EBB takes speeds in units of 1/(12 MHz) steps
            per 21 ms.  Scaling as above, 1% in 1 second corresponds to
            175 steps/s, or 0.175 steps/ms, which corresponds
            to ~3.6 steps/21 ms.  Rounding this to 4 steps/21 ms is sufficient.        '''
        
        intTemp = 4 * self.options.ServoUpSpeed
        ebb_serial.command( self.serialPort, 'SC,11,' + str( intTemp ) + '\r' )

        intTemp = 4 * self.options.ServoDownSpeed
        ebb_serial.command( self.serialPort,  'SC,12,' + str( intTemp ) + '\r' )


    def ServoSetMode (self):

        if (self.CleaningNow):
            penDownPos = self.options.penWashPosition
        elif (self.ReInkingNow == True):
            penDownPos = self.options.penDownPosition
        elif (self.LayerOverridePenDownHeight):
            penDownPos = self.LayerPenDownPosition
        else:    
            penDownPos = self.options.penDownPosition
        
        intTemp = 7500 + 175 * penDownPos
        ebb_serial.command( self.serialPort,  'SC,5,' + str( intTemp ) + '\r' )        

    def stop( self ):
        self.bStopped = True

    def getDocProps( self ):
        '''
        Get the document's height and width attributes from the <svg> tag.
        Use a default value in case the property is not present or is
        expressed in units of percentages.
        '''
        self.svgHeight = plot_utils.getLength( self, 'height', float( wcb_conf.N_PAGE_HEIGHT )  )
        self.svgWidth = plot_utils.getLength( self, 'width', float( wcb_conf.N_PAGE_WIDTH )  )
        if ( self.svgHeight == None ) or ( self.svgWidth == None ):
            return False
        else:
            return True

e = WCB()
#e.affect(output=False)
e.affect()
