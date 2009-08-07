#!/usr/bin/python
"""
Bryan Bishop <kanzure@gmail.com>
2009

pymates: part mating for skdb.

things you can do to run this:
    * python pymates.py
    * python rapid-test.py
    * ./shell.sh
        see the notes below (you need to run pymates.start() ASAP once ipython is done initiating)
        it's like running ipython -wthread -c "import pymates" -i
"""
#pymates
#ipython -wthread -c "import pymates" -i
#pymates.start()
#pymates.demo()
#pymates.mate_parts()
##the previous three lines can be replaced with: pymates.supermate_parts()
#pymates.show_interface_arrows()
#optionally, pymates.move(pymates.total_parts[0],x,y,z,i,i,i,j,j,j)

#see ~/local/pythonOCC/samples/Level2/DataExchange/import_step_multi.py
#see ~/local/pythonOCC/samples/Level1/TopologyTransformation/mirror.py

#os.environ['CSF_GraphicShr'] = r"/usr/lib/libTKOpenGl.so"

import yaml
import re
import os
import random
import copy
import numpy
import math
import wx
import OCC.gp
import OCC.BRepPrimAPI
import OCC.BRepBuilderAPI
import OCC.BRepAlgoAPI
import OCC.Utils.DataExchange.STEP
import OCC.GC
import OCC.Geom
import geom
from assembly import Assembly
from skdb import Part, Interface, Mate, Unit

total_parts = []

def compatibility(part1, part2):
    '''find all possible combinations of part1 and part2 (for each interface/port) and check each compatibility'''
    return []

def compatibility(part1port, part2port):
    '''note that an interface/port object refers to what it is on. so you don't have to pass the parts.'''
    return []

def load(foo):
    '''load a yaml string'''
    return yaml.load(foo)

def dump(foo):
    '''dump an object as yaml'''
    return yaml.dump(foo, default_flow_style=False)

def demo(event=None):
    '''standard pymates demo: loads a YAML file, parses it into a skdb.Part(), then gets all the skdb.Interface() objects, etc.
    - also loads up CAD data'''
    print "loading the file .. it looks like this:"
    blockhole = load(open("models/blockhole.yaml"))["blockhole"]
    peg = load(open("models/peg.yaml"))["peg"]
    print "blockhole is = ", dump(blockhole)
    print "peg is = ", dump(peg)
    #load the CAD?
    #load_cad_file(filename=blockhole.files[0])
    shape = blockhole.load_CAD()
    result = OCC.Display.wxSamplesGui.display.DisplayShape(shape)
    blockhole.add_shape(result)
    shape2 = peg.load_CAD()
    result2 = OCC.Display.wxSamplesGui.display.DisplayShape(shape2)
    peg.add_shape(result2)
    total_parts.append(blockhole)
    total_parts.append(peg)

def mate_interfaces(interface1, interface2):
    return mate_parts(part1=interface1.part, part2=interface2.part, interface1=interface1, interface2=interface2)

def convert_interface(interface2):
    '''warning: this manipulates the input object
    first checks if the interface2 has been converted from degrees to radians, or converted from the orientation vector to radians'''
    if not interface2.converted:
        if hasattr(interface2,"x"):
            if type(interface2.x) != Unit:
                interface2.x = Unit(str(interface2.x) + "deg")
            if type(interface2.y) != Unit:
                interface2.y = Unit(str(interface2.y) + "deg")
        
            interface2.x = interface2.x.conv_factor("radians")
            interface2.y = interface2.y.conv_factor("radians")
            interface2.converted = True
        #see x_vec and y_vec .. which would give you orientation (if you take the cross products)
        if hasattr(interface2, "orientation"):
            orientation = interface2.orientation
            (el, az) = point_shape(OCC.gp.gp_Ax1(orientation))
            interface2.x = el
            interface2.y = az
            interface2.converted = True
        elif hasattr(interface2, "x_vec") and hasattr(interface2, "y_vec"):
            x_vec = interface2.x_vec
            y_vec = interface2.y_vec
            x_vec = numpy.array([x_vec[0], x_vec[1], x_vec[2]])
            y_vec = numpy.array([y_vec[0], y_vec[1], y_vec[2]])
            orientation = numpy.cross(x_vec, y_vec)
            interface2.orientation = orientation
            (el, az) = point_shape(OCC.gp.gp_Ax1(OCC.gp.gp_Pnt(0,0,0), OCC.gp.gp_Dir(orientation[0], orientation[1], orientation[2])))
            interface2.x = el
            interface2.y = az
            interface2.converted = True
    return

import random
def mate_parts(part1=None, part2=None, event=None, interface1=None, interface2=None):
    if part1 == None and part2 == None:
        if len(total_parts) < 1: return #meh
        part1 = total_parts[0]
        part2 = total_parts[1]
    if interface1 == None and interface2 == None:
        #default: first interface on both parts
        interface1 = part1.interfaces[random.randint(0, len(part1.interfaces))].options([part1, part2])
        interface2 = part2.interfaces[random.randint(0, len(part2.interfaces))].options([part1, part2])

    else:
        part1 = interface1.part
        part2 = interface2.part
    point1 = interface1.point
    point2 = interface2.point
    part1.load_CAD()
    part2.load_CAD()

    #some simple checks
    #assert type(interface1.x) == Unit, "interface1.x should be of type skdb.Unit()"
    #assert type(interface1.y) == Unit, "interface1.y should be of type skdb.Unit()"
    #assert type(interface2.x) == Unit, "interface2.x should be of type skdb.Unit()"
    #assert type(interface2.y) == Unit, "interface2.y should be of type skdb.Unit()"
    convert_interface(interface1)
    convert_interface(interface2)

    occ_point1 = OCC.gp.gp_Pnt(point1[0], point1[1], point1[2])
    occ_point2 = OCC.gp.gp_Pnt(point2[0], point2[1], point2[2])
    
    pivot_point = OCC.gp.gp_Pnt(0,0,0) #rotate about the origin
    x_rotation = OCC.gp.gp_Dir(1,0,0) #OCC.gp.gp_Dir(interface2.x[0], interface2.x[1], interface2.x[2])
    y_rotation = OCC.gp.gp_Dir(0,1,0) #OCC.gp.gp_Dir(interface2.j[0], interface2.j[1], interface2.j[2])
    z_rotation = OCC.gp.gp_Dir(0,0,1) #OCC.gp.gp_Dir(interface2.k[0], interface2.k[1], interface2.k[2])
    transformation = OCC.gp.gp_Trsf()
    transformation.SetRotation(OCC.gp.gp_Ax1(pivot_point, x_rotation),interface2.x)
    #transformation.SetRotation(OCC.gp.gp_Ax1(pivot_point, y_rotation),180)
    transformation.SetRotation(OCC.gp.gp_Ax1(pivot_point, y_rotation),interface2.y)
    transformation.SetTranslation(occ_point2, occ_point1)

    brep_transform = OCC.BRepBuilderAPI.BRepBuilderAPI_Transform(transformation)
    brep_transform.Perform(part2.shapes[0]) #shapes[0] is the original shape
    resulting_shape = brep_transform.Shape()

    OCC.Display.wxSamplesGui.display.DisplayShape(resulting_shape)
    return brep_transform

def move(my_part, x, y, z, i1, i2, i3, j1, j2, j3):
    o_point = OCC.gp.gp_Pnt(x,y,z)
    o_n_vec = OCC.gp.gp_Dir(i1,i2,i3)
    o_vx_vec = OCC.gp.gp_Dir(j1,j2,j3)
    ax3 = OCC.gp.gp_Ax3(o_point, o_n_vec, o_vx_vec)
    transform = OCC.gp.gp_Trsf()
    transform.SetTransformation(ax3)
    toploc = OCC.TopLoc.TopLoc_Location(transform)
    OCC.Display.wxSamplesGui.display.Context.SetLocation(my_part.ais_shapes, toploc)
    OCC.Display.wxSamplesGui.display.Context.UpdateCurrentViewer()
    return

def show_new_interface_point(x,y,z,color='RED'):
    '''displays an interface point (sphere) at a certain location, with a certain color'''
    mysphere = OCC.BRepPrimAPI.BRepPrimAPI_MakeSphere(OCC.gp.gp_Pnt(x,y,z), 2.0)
    OCC.Display.wxSamplesGui.display.DisplayColoredShape(mysphere.Shape(), color=color)
    OCC.Display.wxSamplesGui.display.Context.UpdateCurrentViewer()
    return

def show_cone_at(x,y,z,color='YELLOW'):
    '''displays a cone at a certain position'''
    mycone = OCC.BRepPrimAPI.BRepPrimAPI_MakeCone(x,y,z)
    OCC.Display.wxSamplesGui.display.DisplayColoredShape(mycone.Shape(), color=color)
    #OCC.Display.wxSamplesGui.display.Context.UpdateCurrentViewer()
    return

def show_interface_points(event=None):
    '''draws spheres for the first interface point on the first interface of all parts'''
    for each in total_parts:
       interface = each.interfaces[0]
       mysphere = OCC.BRepPrimAPI.BRepPrimAPI_MakeSphere(OCC.gp.gp_Pnt(interface.point[0], interface.point[1], interface.point[2]), 2.0)
       OCC.Display.wxSamplesGui.display.DisplayColoredShape(mysphere.Shape(), color='RED')
    OCC.Display.wxSamplesGui.display.Context.UpdateCurrentViewer()
    return

def make_edge(shape):
    '''make an edge from an OCC.Geom.Handle_Geom_Curve'''
    spline = OCC.BRepBuilderAPI.BRepBuilderAPI_MakeEdge(shape)
    spline.Build()
    return spline.Shape()

def make_vertex(pnt):
    '''show a vertex in 3D space based off of either an OCC.gp.gp_Pnt2d() or an OCC.gp.gp_Pnt()'''
    if isinstance(pnt, OCC.gp.gp_Pnt2d):
        vertex = OCC.BrepBuilderAPI.BRepBuilderAPI_MakeVertex( OCC.gp.gp_Pnt(pnt.X(), pnt.Y(), 0)) 
    else: 
        vertex = OCC.BRepBuilderAPI.BRepBuilderAPI_MakeVertex( pnt )
    vertex.Build()
    return vertex.Vertex()

def angle_to(x,y,z):
    '''returns polar coordinates in radians to a point from the origin            
    a rotates around the x-axis; b rotates around the y axis; r is the distance'''
    azimuth = math.atan2(y, x) #longitude                                       
    elevation = math.atan2(z, math.sqrt(x**2 + y**2))    
    radius = math.sqrt(x**2+y**2+z**2)    
    return((azimuth, elevation, radius))

def point_shape(origin):
    '''rotates a shape to point along origin's direction. this function ought to be unnecessary'''
    assert type(origin) == OCC.gp.gp_Ax1
    #ox, oy, oz = origin.Location().X(), origin.Location().Y(), origin.Location().Z() #ffs
    ox, oy, oz = 0, 0, 0
    dx, dy, dz = origin.Direction().X(), origin.Direction().Y(), origin.Direction().Z()
    (az, el, rad) = angle_to(dx-ox, dy-oy, dz-oz)
    print "az: %s, el: %s, rad: %s... dx: %s, dy: %s, dz %s)" % (az, el, rad, dx, dy, dz) 
    #el-math.pi/2
    #az-math.pi/2
    return (el, az)

def show_interface_arrows(event=None,arrow_length=5,rotx2=None,roty2=None):
    '''displays vectors pointing in the mating direction, for every part and every part's interfaces'''
    color_counter = 0
    colors = [
                'RED',
                'GREEN',
                'BLUE',
                'ORANGE',
                #'PURPLE',
             ]
    for part in total_parts:
        for interface in part.interfaces:
            interface.part = part
            try:
                color = colors[color_counter]
            except IndexError:
                color = "RED"
            point = OCC.gp.gp_Pnt(interface.point[0], interface.point[1], interface.point[2])
            point2 = OCC.gp.gp_Pnt(interface.point[0], interface.point[1], interface.point[2]+arrow_length)
            old_pt2 = copy.copy(point2)
            rotx = None
            roty = None
            print "interface = ", interface
            print "interface.converted = ", interface.converted
            if (not interface.converted):
                print "HELLO"
                #convert from degrees to radians
                interface.x = Unit(str(interface.x) + "deg") # + "deg")
                interface.x = interface.x.conv_factor("radian")
                interface.y = Unit(str(interface.y) + "deg") # + "deg")
                interface.y = interface.y.conv_factor("radian")
                interface.converted = True
                #get the value
                rotx, roty = interface.x, interface.y
            elif hasattr(interface, "orientation"):
                #convert from orientation to rotation
                orientation = interface.orientation
                (el, az) = point_shape(OCC.gp.gp_Ax1(orientation))
                rotx = el
                roty = az #er, not quite
            else:
                rotx = interface.x
                roty = interface.y

            if not rotx2 == None and not roty2 == None:
                rotx, roty = rotx2, roty2
            print "rotx = %s\nroty = %s" % (rotx, roty)

            x_dir = OCC.gp.gp_Dir(1,0,0)
            y_dir = OCC.gp.gp_Dir(0,1,0)
            z_dir = OCC.gp.gp_Dir(0,0,1)
            point2.Rotate(OCC.gp.gp_Ax1(point, x_dir), rotx) #rotx) #0
            point2.Rotate(OCC.gp.gp_Ax1(point, y_dir), roty) #rotz) #-90
            print "point = (%d, %d, %d)" % (point.XYZ().X(), point.XYZ().Y(), point.XYZ().Z())
            print "point2 = (%d, %d, %d)" % (point2.XYZ().X(), point2.XYZ().Y(), point2.XYZ().Z())
            #print "hm = (%d, %d, %d)" % (hm.XYZ().X(), hm.XYZ().Y(), hm.XYZ().Z())
            #assert not old_pt2 == point2
            #assert not hm == point2
            #assert not hm == old_pt2
            curve = OCC.GC.GC_MakeSegment(point, point2).Value()
            #my_curve = blah.BasisCurve()
            vert = make_vertex(point2)
            OCC.Display.wxSamplesGui.display.DisplayColoredShape(vert, color)
            OCC.Display.wxSamplesGui.display.DisplayColoredShape(make_edge(OCC.Geom.Handle_Geom_Curve(curve)), color)
            color_counter = color_counter+1
            
    return

def start():
    '''call this immediately once opening up pymates in a shell session (like ipython)'''
    import OCC.Display.wxSamplesGui
    OCC.Display.wxSamplesGui.display.Create()

def restart(event=None): #EraseAll
    '''clears the screen/workspace of all objects. also removes all parts (be careful).'''
    total_parts = []
    import OCC.Display.wxSamplesGui
    OCC.Display.wxSamplesGui.display.EraseAll()
    return

def nontransform_point(x,y,z,color='YELLOW'):
    '''plot a sphere in 3D, figure out where objects are going.'''
    return show_new_interface_point(x,y,z,color=color)

def transform_point(x,y,z,color='YELLOW'):
    '''draw a (small) sphere (maybe eventually a cone to show direction if I figure out the correct parameters to OCC.BRepPrimAPI.BRepPrimAPI_MakeCone())
    then transform it in the same way that mate_parts() transforms everything'''
    mysphere = OCC.BRepPrimAPI.BRepPrimAPI_MakeSphere(OCC.gp.gp_Pnt(x,y,z), 1.0)
    transformation = OCC.gp.gp_Trsf()
    interface1 = total_parts[0].interfaces[0]
    interface2 = total_parts[1].interfaces[0]
    point1 = interface1.point
    point2 = interface2.point
    i1, j1, k1 = interface1.i, interface1.j, interface1.k
    i2, j2, k2 = interface2.i, interface2.j, interface2.k
    #fromCoordinateSystem1 = OCC.gp.gp_Ax3(OCC.gp.gp_Pnt(point1[0],point1[1],point1[2]), OCC.gp.gp_Dir(i1[0],i1[1],i1[2]), OCC.gp.gp_Dir(k1[0],k1[1],k1[2]))
    #toCoordinateSystem2 = OCC.gp.gp_Ax3(OCC.gp.gp_Pnt(point2[0],point2[1],point2[2]), OCC.gp.gp_Dir(i2[0],i2[1],i2[2]), OCC.gp.gp_Dir(k2[0],k2[1],k2[2]))
    #transformation.SetTransformation(fromCoordinateSystem1, toCoordinateSystem2)
    #now try: pymates.transform_point(0,0,0)
    occ_point1 = OCC.gp.gp_Pnt(point1[0],point1[1],point1[2])
    occ_point2 = OCC.gp.gp_Pnt(point2[0],point2[1],point2[2])
    transformation.SetTranslation(occ_point2, occ_point1)
    brep_transform = OCC.BRepBuilderAPI.BRepBuilderAPI_Transform(transformation)
    brep_transform.Perform(mysphere.Shape())  #(total_parts[1].shapes[0])
    resulting_shape = brep_transform.Shape()
    OCC.Display.wxSamplesGui.display.DisplayShape(resulting_shape)
    return brep_transform

def supermate_parts(event=None):
    '''a handy shortcut for calling restart(), demo(), and mate_parts() in that order'''
    restart()
    demo()
    mate_parts()
    return

def exit(event=None):
    '''exit this program'''
    import sys; sys.exit()

if __name__ == '__main__':
    start() #import OCC.Display.wxSamplesGui
    OCC.Display.wxSamplesGui.add_menu("do stuff")

    for f in [
                restart,
                demo,
                mate_parts,
                supermate_parts,
                show_interface_points,
                show_interface_arrows,
                exit
            ]:
        OCC.Display.wxSamplesGui.add_function_to_menu('do stuff', f)
    OCC.Display.wxSamplesGui.start_display()
