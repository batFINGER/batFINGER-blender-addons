import bpy

context = bpy.context

def listselect(obj_list, select=True):
    for obj in obj_list:
        obj.select = select

obj = context.object
scene = context.scene
location = obj.location.copy()

units = [obj for obj in scene.objects if obj.type == 'MESH']
curves = []

for i, unit in enumerate(units):
    # add a new circle
    bpy.ops.curve.primitive_bezier_circle_add(location=location)
    circle = scene.objects.active
    circle.parent = obj
    
    dist = (unit.location - location).length
    #circle.scale *= 1.1 ** i
    circle.dimensions.xy = (2 * dist, 2 * dist)
    circle.data.use_radius = False
    bpy.ops.object.transform_apply(scale=True)
    #circle.scale *= 0.5
    curves.append(circle)
    # add modifiers
    unit.location = location

    arraymod = unit.modifiers.new("AV_array", type='ARRAY')
    arraymod.fit_type = 'FIT_CURVE'
    arraymod.count = 5
    arraymod.curve = circle
    arraymod.relative_offset_displace = (1.4, 0, 0)
    
    curvemod = unit.modifiers.new("AV_curve", type='CURVE')
    curvemod.object = circle
    curvemod.deform_axis = 'POS_X'

listselect(curves, True)

scene.objects.active = obj
bpy.ops.object.parent_set(type='OBJECT')    
listselect(curves, False)
    