import bpy
from speaker_tools.utils import get_driver_settings
# Test script to create a row x col = channels audio-visualiser
'''
To run

Make sure speaker-tools is enabled as an addon
Create the object you want as visualiser unit
Add a single driver to this object

    this will appear as a driver on speaker tools panel
    with a MONKEY icon.  I call this driver a "monkey"
    
Make sure you have the object with one monkey driver selected

Edit the script
    change rows, cols, amplify, offset to suite.
    make sure rows x cols = channels
    where channels is the number of channels baked.

Run the script.
    
    The script will make a rows x col array of the input object
    separate it into separate objects
    and add a driver for each channel.
    
TODO:
    add ability to setup driver on unit first, use amplify and threshold
    smarter indexing after applying array
    multiple drivers / multiple channels.
    
'''
context = bpy.context
object = context.object
location = context.object.location.copy()

scene = context.scene

rows = 1
cols = 16

#modifer settings
row_offset = 1.1
col_offset = 1.1


x_offset = col_offset * object.dimensions.x
y_offset = row_offset * object.dimensions.y

 
'''

Initially I did this with array modifiers.

colmod = object.modifiers.new("Cols", type='ARRAY')
colmod.count = cols
colmod.relative_offset_displace = (col_offset, 0, 0)

rowmod = object.modifiers.new("Rows", type='ARRAY')
rowmod.count = rows
rowmod.relative_offset_displace = (0, row_offset, 0)

# apply the modifiers

bpy.ops.object.modifier_apply(modifier="Cols")
bpy.ops.object.modifier_apply(modifier="Rows")


# go into edit mode and separate LOOSE parts

bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.separate(type='LOOSE')
bpy.ops.object.mode_set(mode='OBJECT')

mesh = context.object.data
'''

# original is active, new objects are selected
amplify = 10
speaker = scene.context_speaker

if speaker:
    objects = []
    action = speaker.animation_data.action
    channel_name = action["channel_name"]
    channels = action["Channels"]    

    for i in range(min(channels, rows * cols)):
        
               
        obj = context.object
        
        objects.append(obj)
        row = i // cols
        col = i % cols
        print(i, col, row)
        obj.location.x = location.x + col * col_offset * obj.dimensions.x
        obj.location.y = location.y + row * row_offset * obj.dimensions.y
        
        channel = "%s%d" % (channel_name, i)
            
        fcurve = obj.animation_data.drivers[0]
        driver = fcurve.driver
        driver.expression = "SoundDrive([%s],amplify=%0.2f)" % (channel, amplify)
        
        
        # to add an offset
        #offset = 1.0 
        #driver.expression = "SoundDrive([%s],amplify=%0.2f) + 1.0" % (channel, amplify)
        
        var = driver.variables[0]
        var.name = channel
        var.type = 'SINGLE_PROP'
        
        target = var.targets[0]
        target.id_type = "SPEAKER" 
        target.id = speaker.id_data
        target.data_path = '["%s"]' % channel
        
        bpy.ops.object.duplicate(linked=True)
        
    if not object.parent:
        parent = bpy.data.objects.new("SOUNDVIS %d x %d", None)
        parent.location = location
        scene.objects.link(parent)
        
        for obj in objects:
            obj.select = True
        scene.objects.active = parent            
        bpy.ops.object.parent_set(type='OBJECT')
    
    #make original active
    scene.objects.active = object   