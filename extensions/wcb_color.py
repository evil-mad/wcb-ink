# Copyright 2013, Windell H. Oskay, www.evilmadscientist.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Portions adapted from colloreffect.py Copyright (C) by Jos Hirth, kaioa.com, Aaron C. Spike, Monash University
# and from RoboPaint: https://github.com/techninja/robopaint/
# and from Post Process Trace Bitmap extension by Daniel C. Newman (from the Eggbot project)
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import inkex
import simplestyle
import random
import math
import string
from copy import deepcopy


color_props_fill = ('fill', 'stop-color', 'flood-color', 'lighting-color')
color_props_stroke = ('stroke',)
color_props = color_props_stroke


#Crayola Classic palette: Water (Azure), Black, Red, Orange, Yellow, Green, Blue, Purple, Saddle Brown
# crayola_classic = ["#FFFFFF", "#3E3A39", "#A72611", "#FF6A00", "#F7F756", "#2E6F3A", "#353AAA", "#907DBD", "#844B35"]


#Define palette(s) here, so that we can add a future option to pick the palette used:
crayola_classic = ["#F0FFFF", "#000000", "#FF0000", "#FFA500", "#FFFF00", "#008000", "#0000FF", "#800080", "#8B4513"]
crayola_classic_names = ["0-water wash", "1-black", "2-red", "3-orange", "4-yellow", "5-green", "6-blue", "7-violet", "8-brown"]



class wcbColorSnap( inkex.Effect ):


    def __init__( self ):
        inkex.Effect.__init__( self )
        self.OptionParser.add_option( "--tab",    #NOTE: value is not used for anything. :P
            action="store", type="string",
            dest="tab", default="splash",
            help="The active tab when Apply was pressed" )
        self.OptionParser.add_option( "--snapLayers",
            action="store", type="inkbool",
            dest="snapLayers", default=False,
            help="Move colors to layers." )
        self.paletteRGB = []
        self.paletteYUV = []
        self.layerLabels = []
        self.snappedColor = -1
        
        
    def effect(self):
        
        self.layersProcessed = []
        self.paletteRGB = crayola_classic    #in the future: Offer additional choices
        

        for paintColor in self.paletteRGB: 
            c = simplestyle.parseColor(paintColor) 
            self.paletteYUV.append(self.rgbToYUV(c[0], c[1], c[2]))    
            self.layerLabels.append("layerNotFound")
            
        self.scanForLayerNames(self.document.getroot())    #Recursively scan through document for named layers.
#           inkex.errormsg('layerLabels: ' + str(self.layerLabels)) 

        self.getAttribs(self.document.getroot())    #Recursively scan through file, snap & label things that have color attributes.



        #If option is selected, try to move colors into layers.  Requires that everything is UNGROUPED first. :D
        if (self.options.snapLayers):
            #Now, walk through the palette, adding any new named layers that are needed
            for i in xrange(len(self.paletteRGB)):
                if (self.layerLabels[i] == "layerNotFound"):    
            
                    # Create a group <g> element under the document root
                    layer = inkex.etree.SubElement( self.document.getroot(), inkex.addNS( 'g', 'svg' ) )
        
                    # Add Inkscape layer attributes to this new group
                    layer.set( inkex.addNS('groupmode', 'inkscape' ), 'layer' )
                    layer.set( inkex.addNS( 'label', 'inkscape' ), crayola_classic_names[i] )
                    self.layerLabels[i] = crayola_classic_names[i]

            for child in self.document.getroot():
#                 inkex.errormsg('wcb-color-layer: ' + str(child.get('wcb-color-layer'))) 
                if ( child.get( inkex.addNS( 'groupmode', 'inkscape' ) ) == 'layer' ):         #if it's a layer...    
                    strLayerNameTmp = str(child.get(inkex.addNS( 'label', 'inkscape' )))
#                      inkex.errormsg('Layer Name: ' + strLayerNameTmp)
                    if (strLayerNameTmp in self.layerLabels):
                        #this is one of the named layers that we're using.
                        layerNumberInt = self.layerLabels.index(strLayerNameTmp)
                        if not (strLayerNameTmp in self.layersProcessed):
                            self.layersProcessed.append(strLayerNameTmp)
#                               inkex.errormsg('Processed Layer Name: ' + strLayerNameTmp)
                            self.MoveColoredNodes(self.document.getroot(), child, layerNumberInt)





    def MoveColoredNodes(self,node,destination,layerNoInt):                
        val = node.get('wcb-color-layer')
        if val:
            if (int(val) == layerNoInt):
                parent = node.getparent()
                if (parent.get(inkex.addNS( 'label', 'inkscape' )) != self.layerLabels[layerNoInt]): # prevent infniite loop
                    destination.append( deepcopy(node) )
#                    destination.append( node )
                    parent.remove(node) # Remove this element
            
        for branch in node:
            self.MoveColoredNodes(branch, destination,layerNoInt)




# 
# 
# # ********
# #  The problem: All of the content is WITHIN a layer--- we have to recursively scan through everything, once for each top-level layer.
# # ********                
#                 
#                     for i in xrange(len(self.paletteRGB)):                                     #find out which one
# #                          inkex.errormsg('id 2: ' + str(child.get(inkex.addNS( 'label', 'inkscape' ))) )        #OK Here        
# #                          inkex.errormsg('id 3: ' + str(self.layerLabels[i] ) )        
# 
#                         if (child.get(inkex.addNS( 'label', 'inkscape' )) == self.layerLabels[i] ):
# #                             inkex.errormsg('id: ' + str(child.get(inkex.addNS( 'label', 'inkscape' )))) 
# 
#                             for node in self.document.getroot():
# #                                 inkex.errormsg('wcb-color-layer: ' + str(node.get("wcb-color-layer"))) 
# 
#                                 if (node.get('wcb-color-layer') == str(i) ):
#                                     parent = node.getparent()
#                                     if (parent.get(inkex.addNS( 'label', 'inkscape' )) != self.layerLabels[i]):
# #                                         child.append( deepcopy(node) )
# #                                         child.append( node )
#                                         parent.remove(node) # Remove this element
# 
# 
# 
# 
# #                         inkex.errormsg('i: ' + str(i)) 
# 



        
        
        
        


        
    def scanForLayerNames(self,node):
        self.parseLayerName(node)
        for child in node:
            self.scanForLayerNames(child)        
        
    def parseLayerName(self,node):    
        if ( node.get( inkex.addNS( 'groupmode', 'inkscape' ) ) == 'layer' ): 

            strLayerName = node.get( inkex.addNS( 'label', 'inkscape' ) )
    #        inkex.errormsg('strLayerName: ' + str(strLayerName)) 
    #        inkex.errormsg('id: ' + str(node.get( 'id'))) 
    
            TempNumString = 'x'
            stringPos = 1    
            layerNameInt = -1 
            
            #Check to see if the layer name begins with a number in the range of palette colors
            strLayerName = string.lstrip( strLayerName ) #remove leading whitespace
            MaxLength = len( strLayerName )
            if MaxLength > 0:
                while stringPos <= MaxLength:
                    if str.isdigit( strLayerName[:stringPos] ):
                        TempNumString = strLayerName[:stringPos] # Store longest numeric string so far
                        stringPos = stringPos + 1
                    else:
                        break
                        
            #If it's the first layer found of that color, add its ID to our layer lookup table.
            if ( str.isdigit( TempNumString ) ):
                layerNameInt = int( float( TempNumString ) )
                if (layerNameInt >= 0) and (layerNameInt < len(self.paletteRGB)):
                    if (self.layerLabels[layerNameInt] == "layerNotFound"):
                        self.layerLabels[layerNameInt] = str(node.get('id'))
        
        
    def getAttribs(self,node):
        self.changeStyle(node)
        for child in node:
            self.getAttribs(child)
                
    def changeStyle(self,node):
        self.snappedColor = -1
        for attr in color_props:
            val = node.get(attr)
            if val:
                new_val = self.process_prop(val)
                if new_val != val:
                    node.set(attr, new_val) 
                if (self.snappedColor != -1):
                    node.attrib["wcb-color-layer"] = str(self.snappedColor)
                    

        

        if node.attrib.has_key('style'):
            # References for style attribute:
            # http://www.w3.org/TR/SVG11/styling.html#StyleAttribute,
            # http://www.w3.org/TR/CSS21/syndata.html
            #
            # The SVG spec is ambiguous as to how style attributes should be parsed.
            # For example, it isn't clear whether semicolons are allowed to appear
            # within strings or comments, or indeed whether comments are allowed to
            # appear at all.
            #
            # The processing here is just something simple that should usually work,
            # without trying too hard to get everything right.
            # (Won't work for the pathological case that someone escapes a property
            # name, probably does the wrong thing if colon or semicolon is used inside
            # a comment or string value.)
            self.snappedColor = -1
            style = node.get('style') # fixme: this will break for presentation attributes!
            if style:
                #inkex.debug('old style:'+style)
                declarations = style.split(';')
                for i,decl in enumerate(declarations):
                    parts = decl.split(':', 2)
                    if len(parts) == 2:
                        (prop, val) = parts
                        prop = prop.strip().lower()
                        if prop in color_props:
                            val = val.strip()
                            new_val = self.process_prop(val)
                            if new_val != val:
                                declarations[i] = prop + ':' + new_val  
                                node.set('style', ';'.join(declarations))
                            if (self.snappedColor != -1):
                                node.attrib["wcb-color-layer"] = str(self.snappedColor)
                                
                
    def process_prop(self,col):
        #debug('got:'+col)
        if simplestyle.isColor(col):
            c=simplestyle.parseColor(col)
            col='#'+self.colmod(c[0],c[1],c[2])
            #debug('made:'+col)
#         if col.startswith('url(#'):
#             id = col[len('url(#'):col.find(')')]
#             newid = '%s-%d' % (id, int(random.random() * 1000))
#             #inkex.debug('ID:' + id )
#             path = '//*[@id="%s"]' % id
#             for node in self.document.xpath(path, namespaces=inkex.NSS):
#                 self.process_gradient(node, newid)
#             col = 'url(#%s)' % newid
        return col                
    
    def colmod(self,r,g,b):
        #Snap to nearest color
        
        rgb = simplestyle.parseColor(self.paletteRGB[self.closestColor(r,g,b)])
        return '%02x%02x%02x' % (rgb[0], rgb[1], rgb[2])

 

        
        
    def rgbToYUV (self,r, g, b): 
        
        y = r *  .299000 + g *  .587000 + b *  .114000
        u = r * -.168736 + g * -.331264 + b *  .500000 + 128
        v = r *  .500000 + g * -.418688 + b * -.081312 + 128
        
        y = math.floor(y)
        u = math.floor(u)
        v = math.floor(v)
        
        return [y,u,v];
        
    def closestColor(self, r, g, b): 
        yuv = self.rgbToYUV(r,g,b)  # Convert to YUV to better match human perception of colors        
                
        lowestIndex = 0
        lowestValue = 1000 # High value start is replaced immediately below
        distance = 0.0
        
#         for paintColor in paletteRGB:  
        for i in xrange(len(self.paletteRGB)): 
            c = self.paletteYUV[i]         
            # Color distance:
            distance = math.sqrt(  math.pow(c[0] - yuv[0],2) + math.pow(c[1] - yuv[1],2) + math.pow(c[2] - yuv[2],2) )
            
            if (distance < lowestValue): # Lowest value (closest distance) wins!
                lowestValue = distance
                lowestIndex = i
        
        self.snappedColor = lowestIndex
        return lowestIndex        
        
        
        
if __name__ == '__main__':
    e = wcbColorSnap()
    e.affect()
