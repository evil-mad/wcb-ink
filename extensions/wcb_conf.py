# wcb_conf.py
# Part of the WaterColorBot driver for Inkscape
# Version 1.5.0 , dated 2017-06-19
#
# https://github.com/oskay/watercolorbot/
#
# "Change numbers here, not there." :)



N_PAGE_HEIGHT = 768     # Default page height (each unit equiv. to one step), 8 inches
N_PAGE_WIDTH = 1056     # Default page width (each unit equiv. to one step), 11 inches

#F_DPI_16X = 896.0       #DPI @ 16X microstepping.  Default: 896.  Used in converting drawing size to motor steps.

F_DPI_16X = 2032       #DPI @ 16X microstepping for use on AxiDraw

F_Speed_Scale = 40.0    #Default 100% speed, divided by 100. If value is 40 (default), 100% speed will be 4000 steps/s.

F_StartPos_X = -288.0   #parking position, in pixels. Default: -3 inches
F_StartPos_Y = 0.0      #parking position, in pixels. Default: 0

F_Accel_Factor = .3      #Time, in seconds, to reach maximum speed, when using pen-up acceleration. Typ: 0.3 s

'''
WaterLoc: (X,Y) coordinates of center brush position in water dish, for each water dish.  
Distances are in pixels, relative to home corner (0,0). Assume 96 px/inch.
'''

WaterLoc = [
(10, 53),  # dish 0 (top)
(10, 336), # 1, 3.5"
(10, 624)  # 2, 6.5"
]


'''
PaintLoc: (X,Y) coordinates of center brush position in water dish, for each paint pan.  
Distances are in pixels, relative to home corner (0,0). Assume 96 px/inch.
X position for Crayola watercolors: 1.7"
Y position for Crayola watercolors: 0.5" - 7.6", evenly spaced.

N_Paint_Count: Length of the array; number of paint colors to use.
'''

PaintLoc = [
(163, 48), # pan 0 (top)
(163, 145), # 1
(163, 243), # 2
(163, 340), # 3
(163, 437), # 4
(163, 534), # 5
(163, 633), # 6
(163, 730), # 7
]

N_Paint_Count = 8       # Number of paint colors


'''
Brush Washing Details:
WashDelta: Maximum peak-to-peak excursion of brush while washing in water. 
  (Delta-x,Delta-y). Distances in pixels.
'''

WashDelta = (0, 90)
WashCycles = 3

'''
Water Dip Details:
WaterDipDelta: Maximum peak-to-peak excursion of brush while dipping brush in water 
  (not washing, just dipping-- typically before or after dipping in paint.)
  (Delta-x,Delta-y). Distances in pixels.  
  A single cycle is assumed.
'''

WaterDipDelta = (2, 2)  


'''
Brush Inking Details
InkDelta: Maximum peak-to-peak excursion of brush while swirling in paint 
 (Delta-x,Delta-y). Distances in pixels.
InkCycles: Number of cycles to execute when initially inking brush

InkReCycles: Number of cycles to execute when re-inking brush
InkReDelta: Excursion for re-inking brush
'''

InkDelta = (85, 58)
InkCycles = 1

InkReCycles = 1
InkReDelta = (53, 37)
