# wcb_conf.py
# Part of the WaterColorBot driver for Inkscape
# Version 0.1 (Rev A32), dated 8/2/2013
#
# https://github.com/oskay/watercolorbot/
#
# "Change numbers here, not there." :)



N_PAGE_HEIGHT = 720       # Default page height (each unit equiv. to one step)  720 px =  8 inches
N_PAGE_WIDTH = 990       # Default page width (each unit equiv. to one step)    990 px = 11 inches

F_DPI_16X = 896.0       #DPI @ 16X microstepping.  Default: 896.  Used in converting drawing size to motor steps.
F_Speed_Scale = 40.0    #Default 100% speed, divided by 100. If value is 40 (default), 100% speed will be 4000 steps/s.

F_StartPos_X = -270.0   #parking position, in pixels. Default: -270 (-3 inches)
F_StartPos_Y = 0.0      #parking position, in pixels. Default: 0




'''
WaterLoc: (X,Y) coordinates of center brush position in water dish, for each water dish.  
Distances are in pixels, relative to home corner (0,0). Assume 90 px/inch.
'''

WaterLoc = [
(10,45),  # dish 0 (top)
(10,315), # 1
(10,585)  # 2
]


'''
PaintLoc: (X,Y) coordinates of center brush position in water dish, for each paint pan.  
Distances are in pixels, relative to home corner (0,0). Assume 90 px/inch.
X position for Crayola watercolors: 1.7"
Y position for Crayola watercolors: 0.5" - 7.6", evenly spaced.

N_Paint_Count: Length of the array; number of paint colors to use.
'''

PaintLoc = [
(153,45), # pan 0 (top)
(153,136), # 1
(153,228), # 2
(153,319), # 3
(153,410), # 4
(153,501), # 5
(153,593), # 6
(153,684), # 7
]

N_Paint_Count = 8       # Number of paint colors


'''
Brush Washing Details:
WashDelta: Maximum peak-to-peak excursion of brush while washing in water. 
  (Delta-x,Delta-y). Distances in pixels.
'''

WashDelta = (0,80)
WashCycles = 2

'''
Water Dip Details:
WaterDipDelta: Maximum peak-to-peak excursion of brush while dipping brush in water 
  (not washing, just dipping-- typically before or after dipping in paint.)
  (Delta-x,Delta-y). Distances in pixels.  
  A single cycle is assumed.
'''

WaterDipDelta = (2,2)  


'''
Brush Inking Details
InkDelta: Maximum peak-to-peak excursion of brush while swirling in paint 
 (Delta-x,Delta-y). Distances in pixels.
InkCycles: Number of cycles to execute when initially inking brush

InkReCycles: Number of cycles to execute when re-inking brush
InkReDelta: Excursion for re-inking brush
'''

InkDelta = (80,55)
InkCycles = 1

InkReCycles = 1
InkReDelta = (25,20)


 

