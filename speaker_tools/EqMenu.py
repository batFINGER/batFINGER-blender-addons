import bpy
import re
from math import sqrt
from mathutils import Vector, Color, Euler, Quaternion
from random import random
from bpy.props import \
        StringProperty, IntProperty, EnumProperty, FloatProperty, \
        BoolVectorProperty, BoolProperty

from bl_operators.wm import WM_OT_doc_view

from speaker_tools.Equalizer import \
        showEqualiser, getAction, getSpeaker, SoundActionMenuRow

from speaker_tools.utils import \
        get_driver_settings, create_drivers_list, AllDriversPanel, \
        icon_from_bpy_datapath, format_data_path

# <pep8-80 compliant>


def dprint(str):
    DEBUG = False
    if bpy.app.debug or DEBUG:
        print(str)


def finddriver(self, context):
    channel = self.channel
    driver = None
    dprint("CONTEXT %s" % context.space_data.type)
    #tempted to ust bpy.data.objects meshes ...
    search_list = [context.scene]
    try:
        if context.world is not None:
            search_list.append(context.world)
    except:
        dprint("NO CONTEXT WORLD")

    if context.object is not None:
        search_list.append(context.object)
        if context.object.data is not None:
            search_list.append(context.object.data)
        for mat in context.object.material_slots:
            search_list.append(mat)
    for search in search_list:
        #search list could be extended for texture_slots[...].texture etc
        try:
            driver = search.animation_data.drivers[-1]
            clip = context.window_manager.clipboard
            if driver.select and driver.data_path.find(clip) > -1:
                return(len(search.animation_data.drivers) - 1, driver)
        except:
            continue
    self.report({'WARNING'}, "No Driver found ... REMOVED")
    return(-1, None)


def main(self, context, speaker, action, channel_list):
    if context is None or len(channel_list) == 0:
        return False

    space = context.space_data
    search = True
    if action  is not None:
        channel = action["channel_name"]
    SVP = bpy.types.SoundVisualiserPanel
    drivername = "Driver%d" % self.driver_index
    xlist = create_drivers_list()
    driver = [driver for xx in xlist for driver in
              xlist[xx]][self.driver_index]

    if driver:
        all_channels, args = get_driver_settings(driver, speaker)
        speaker_channels = [ch for ch in all_channels if
                            ch.startswith(channel)]

        diff = set(all_channels) - set(speaker_channels)
        driver = driver.driver
        # remove vars
        for ch in set(speaker_channels) - set(channel_list):
            var = driver.variables.get(ch)
            if var:
                driver.variables.remove(var)

        extravars = ""
        if self.amplify != 1.0:
            extravars += ",amplify=%0.4f" % self.amplify
        if self.threshold != 0.0:
            extravars += ",threshold=%0.4f" % self.threshold
        channels = diff | set(channel_list)
        channels_list = list(sorted(channels))
        #channels_list = channels_list.sort()
        ctxt = str(channels_list).replace("'", "").replace(" ", "")
        new_expr = 'SoundDrive(%s%s)' % (ctxt, extravars)
        if len(new_expr) < 256:
            driver.expression = new_expr
            for channel in channel_list:
                var = driver.variables.get(channel)
                if var is None:
                    var = driver.variables.new()
                var.type = "SINGLE_PROP"
                var.name = channel
                target = var.targets[0]
                target.id_type = "SPEAKER"
                target.id = speaker.id_data
                target.data_path = '["%s"]' % channel


def glipglip(self, context):
    if self.mode == 0:
        return None
    self.slider = self.mode
    speaker = bpy.types.Scene.context_speaker
    if speaker is None:
        return None
    '''
    if context.object is None:
       if space.use_pin_id:
           speaker = space.pin_id

    elif context.object.type == "SPEAKER":
        speaker = context.object.data
    else:
        speaker = bpy.types.Scene.context_speaker
    '''
    #self.channel = "Channel%d"%10
    action = getAction(speaker)
    channel_name = "CH"  # default
    if action is not None:
        channels = action["Channels"]
        channel_name = action["channel_name"]

    channel_list = []
    glips = [self.glip0, self.glip1, self.glip2]
    for i in range(0, channels):
        glip_index = i // 32
        j = i % 32
        if glips[glip_index][j]:
            channel_list.append("%s%d" % (channel_name, i))
    main(self, context, speaker, action, channel_list)
    if self.filter_sound:
        print("filtersound")
        filter_sound(self, context)
    return None


def speaker_filter_sound(self, context):
    self.muted = self.filter_sound
    return None


def get_sound_channel(scene, name):
    sound_channel = scene.sound_channels.get(name)
    if not sound_channel:
        sound_channel = scene.sound_channels.add()
        sound_channel.name = name
    return sound_channel


def filter_sound(self, context):
    #print(type(self))
    print(dir(self))
    print("FILTER SOUND", self.filter_sound)
    scene = context.scene

    name = AddCustomSoundDriverToChannel.idname
    speaker_name, action_name = name.split("__@__")
    speaker = bpy.data.speakers.get(speaker_name)
    speaker.filter_sound = self.filter_sound
    speaker_filter_sound(speaker, context)
    glips = (self.glip0, self.glip1, self.glip2)
    #print(AddCustomSoundDriverToChannel.idname)
    if self.filter_sound:

        sound_channel = get_sound_channel(scene, name)
        action = bpy.data.actions.get(action_name)
        if scene.use_preview_range:
            frame_start = scene.frame_preview_start
            frame_end = scene.frame_preview_end
        else:
            frame_start = scene.frame_start
            frame_end = scene.frame_end
        fs = max(action.frame_range.x, frame_start)
        # have to go back to start to enable effect
        scene.frame_set(fs)

        for i in range(92):
            glip = glips[i // 32]
            setattr(sound_channel, "channel%02d" % i, glip[i % 32])


def sync_play(self, context):
    screen = context.screen
    if screen.is_animation_playing:
        if not self.sync_play:
            # this will stop it
            bpy.ops.screen.animation_play()
            return None
    else:
        if self.sync_play:
            # this will start it
            bpy.ops.screen.animation_play()

    return None


class AddCustomSoundDriverToChannel(bpy.types.Operator):
    '''Add Custom Sound Drivers'''
    bl_idname = "speaker.add_driver_channel"
    bl_label = "Add Custom Sound Driver"
    # Registered ops and update methods = CRASH for me
    #bl_options = { 'REGISTER','UNDO','PRESET' }
    channel = StringProperty(default="Menu")
    contextspeakername = StringProperty(default="None", options={'SKIP_SAVE'})
    driver_index = IntProperty(default=-1, options={'SKIP_SAVE'})
    sync_play = BoolProperty(default=False, update=sync_play)
    filter_sound = BoolProperty(default=False, update=filter_sound,
                      description="Filter Sound to Selected Channels")
    delete_index = IntProperty(default=-1, options={'SKIP_SAVE'})
    fcurve_index = IntProperty(default=-1, options={'SKIP_SAVE'})

    amplify = FloatProperty(name="Amplify",
                            default=1.0,
                            min=0.0001,
                            max=1000,
                            description="Amplify the output",
                            update=glipglip,
                            soft_max=10.0)

    threshold = FloatProperty(name="Threshold",
                            default=0.0,
                            min=0.0,
                            max=1000,
                            description="Only calculate when input is greater\
                              than threshold",
                            update=glipglip,
                            soft_max=10.0)

    normalise = BoolProperty(name="Normalise",
                              default=False,)

    slider = FloatProperty(name="Slider",
                           default=1.0,
                           min=0.0,
                           max=1.0)

    glip0 = BoolVectorProperty(name="glip0",
                               update=glipglip,
                               size=32,
                               default=(False for i in range(0, 32)))

    glip1 = BoolVectorProperty(name="glip1",
                               update=glipglip,
                               size=32,
                               default=(False for i in range(0, 32)))

    glip2 = BoolVectorProperty(name="glip2",
                               update=glipglip,
                               size=32,
                               default=(False for i in range(0, 32)))

    mode = IntProperty(default=0)
    idname = ""

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def invoke(self, context, event):
        sce = context.scene
        scene = context.scene
        screen = context.screen
        speaker = None
        self.sync_play = screen.is_animation_playing

        # set the context speaker
        if self.contextspeakername != "None":
            setcontextspeaker(self.contextspeakername)
            self.contextspeakername = "None"
            return {'FINISHED'}
            #speaker = bpy.data.speakers[self.contextspeakername]
            #bpy.types.Scene.context_speaker = speaker

        xlist = {}
        xlist = create_drivers_list(xlist)

        if self.delete_index != -1:
            driver, bpy_path = [(driver, xx) for xx in xlist
                                for driver in xlist[xx]][self.delete_index]
            obj = eval(bpy_path)
            try:
                try:
                    driver.is_valid = False
                    obj["xxx"] = 1
                    driver.data_path = '["xxx"]'
                    driver.array_index = 0
                    print("try and remove %s %d"\
                          % (driver.data_path, driver.array_index))
                    obj.driver_remove(driver.data_path, driver.array_index)
                except:
                    obj.driver_remove(driver.data_path)
                #put the obj in context and remove the dummy
                ob = context.active_object
                context.scene.objects.active = obj

                bpy.ops.wm.properties_remove(data_path="object",
                                             property='xxx')

                context.scene.objects.active = ob
            except:
                pass

            #self.delete_index = -1 #  SKIP_SAVE
            return {'FINISHED'}

        speaker = getSpeaker(context)
        action = getAction(speaker)

        if self.fcurve_index != -1:
            driver, bpy_path = [(driver, xx) for xx in xlist
                                 for driver in xlist[xx]][self.fcurve_index]
            #make an unbaked fcurve for the driver.
            # check whether there is already an fcurve
            if driver.id_data.animation_data.action:
                raction = driver.id_data.animation_data.action
                fcurves = [fcurve for fcurve in raction.fcurves
                           if fcurve.data_path == driver.data_path
                           and fcurve.array_index == driver.array_index]
                if len(fcurves):
                    # remove the fcurve and return
                    raction.fcurves.remove(fcurves[0])
                    # remove the action if empty
                    if not len(action.fcurves):
                        bpy.data.actions.remove(raction)
                    return{'FINISHED'}
            scene_frame = scene.frame_current
            frame = action.frame_range[0]
            frame_end = action.frame_range[1]
            print("BAKING", driver.id_data, driver.data_path,
                  driver.array_index)
            while frame <= frame_end:
                scene.frame_set(frame)
                # quick fix try array, then without
                #print(type(driver.id_data))
                try:
                    driver.id_data.keyframe_insert(driver.data_path,
                                               index=driver.array_index)
                except:
                    driver.id_data.keyframe_insert(driver.data_path)
                finally:
                    frame = frame + 1

            scene.frame_set(scene_frame)
            return {'FINISHED'}

        driver, bpy_path = [(driver, xx) for xx in xlist
                  for driver in xlist[xx]][self.driver_index]
        if driver is None:
            #wierd bug
            return {'CANCELLED'}

        '''
        scene.frame_preview_start = action.frame_range[0]
        scene.frame_preview_end = action.frame_range[1]
        '''

        channels, args = get_driver_settings(driver, speaker)
        action_channels = [channel for channel in channels
                           if channel.startswith(action["channel_name"])]
        glips = [self.glip0, self.glip1, self.glip2]
        for arg in args:
            try:
                #print("new code to remove exec")
                name, value = arg.split("=")

                setattr(self, name, eval(value))
                #exec("self.%s" % arg)
            except:
                print("arg not working")
                pass

        for channel in action_channels:
            xx = [int(i) for i in re.findall(r'\d+', str(action_channels))]
            for i in xx:
                glip = glips[i // 32]
                glip[i % 32] = True

        self.contextspeakername = speaker.name

        self.mode = 1
        AddCustomSoundDriverToChannel.idname = "%s__@__%s"\
                                             % (speaker.name, action.name)
        wm = context.window_manager

        return wm.invoke_popup(self)
        #return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        speaker = bpy.data.speakers[self.contextspeakername]
        xlist = create_drivers_list()
        (driver, bpy_path) = [(driver, xx) for xx in xlist
                  for driver in xlist[xx]][self.driver_index]

        if driver is None:
            # put in some message that driver not found
            return None

        space = context.space_data
        obj = eval(bpy_path)
        sp = driver.data_path.split(".")
        prop = sp.pop()
        path = ".".join(sp)
        bpy_data_path = "%s.%s" % (bpy_path, path)
        if bpy_data_path[-1] == '.':
            bpy_data_path = bpy_data_path[:-1]
        do = eval(bpy_data_path)
        mo = do.path_resolve(prop)
        row = layout.row()
        row.label("", icon=icon_from_bpy_datapath(bpy_path))
        row.prop(obj, "name", text="")
        col = row.column()
        col.alignment = 'RIGHT'
        col.prop(driver.driver, "is_valid", text="OK")
        #layout.prop(driver, "data_path")
        row = layout.row()
        format_data_path(row, driver.data_path)
        #row.label(text=driver.data_path)
        row = layout.row()

        if isinstance(mo, Color):
            #row = layout.row()
            row.prop(do, prop, text="")
            row = layout.row()
            axis = "RGB"[driver.array_index]
            text = "%s %s" % (axis, do.bl_rna.properties[prop].name)
            row.prop(do, prop, text=text,
                     index=driver.array_index, slider=True)
        elif isinstance(mo, Vector):
            #row = layout.row()
            axis = "XYZ"[driver.array_index]
            txt = "%s %s" % (axis, do.bl_rna.properties[prop].name)
            row.prop(do, prop, text=txt, index=driver.array_index, slider=True)
        elif isinstance(mo, Euler):
            #row = layout.row()
            axis = mo.order[driver.array_index]
            txt = "%s %s" % (axis, do.bl_rna.properties[prop].name)
            row.prop(do, prop, text=txt, index=driver.array_index, slider=True)
        elif isinstance(mo, Quaternion):
            #row = layout.row()
            axis = "WXYZ"[driver.array_index]
            txt = "%s %s" % (axis, do.bl_rna.properties[prop].name)
            row.prop(do, prop, text=txt, index=driver.array_index, slider=True)
        elif type(mo).__name__ == "bpy_prop_array":
            if prop == "color":
                row.prop(do, prop, text="")
                row = layout.row()
                axis = "RGBA"[driver.array_index]
                txt = "%s %s" % (axis, do.bl_rna.properties[prop].name)
                row.prop(do, prop, text=txt,
                         index=driver.array_index,
                         slider=True)
        else:
            row.prop(do, prop, index=driver.array_index)

        #layout.prop(driver, "expression")
        layout.prop(self, "amplify")
        layout.prop(self, "threshold")
        #layout.prop(self, "slider")
        action = getAction(speaker)

        if action:
            driver = driver.driver
            row = layout.row()
            row.label(action["channel_name"])

            i = 0
            minf = -1
            maxf = -1
            name = "Channel"
            if "Channels" in action:
                channels = action["Channels"]
                name = action["channel_name"]
                minf = action["minf"]
                maxf = action["maxf"]
            else:
                channels = len(action.fcurves)

            COLS = int(sqrt(channels))
            #box.split(percentage=0.50)
            while i < channels:
                channel = '%s%d' % (name, i)
                rna = speaker["_RNA_UI"][channel]
                if not i % COLS:
                    row = layout.row()
                col = row.column()
                propname = "glip%d" % ((i / 32))
                enabled = not (float(rna["b"] - rna["a"]) < 0.0001)
                col.enabled = enabled

                rowb = col.row()
                #rowb.scale_y  = rowb.scale_x = 1.3 / float(COLS-1)
                rowb.scale_y = rowb.scale_x = 0.5
                if enabled:
                    rowb.prop(speaker, '["%s"]' % channel, slider=True)
                else:
                    rowb.label("blah")

                rowa = col.row()
                rowa.prop(self, propname, toggle=True,
                         text="%d" % i, index=i % 32)

                #rowa.scale_y  = rowa.scale_x = 1.0 - rowb.scale_y
                i += 1
        #layout.menu("sounds.channelmenu")
        scene = context.scene
        screen = context.screen
        #layout.operator("screen.animation_play")
        row = layout.row(align=True)
        row.prop(self, "sync_play", toggle=True, text="PLAY", icon="PLAY")
        row.prop(self, "filter_sound", toggle=True, icon="SPEAKER")
        row = layout.row(align=True)
        row.prop(scene, "use_preview_range", text="", toggle=True)

        row.prop(scene, "frame_preview_start", text="Start")
        row.prop(scene, "frame_preview_end", text="End")

    def execute(self, context):
        #self.mode = 1
        return {'FINISHED'}
        dprint("execute %s" % self.channel)
        if self.channel != 'Menu':
            main(self, context)
        return {'FINISHED'}


class SimpleOperator(bpy.types.Operator):
    '''Add Custom Sound Drivers'''
    bl_idname = "wm.doc_view"
    bl_label = "Add Custom Sound Driver"
    doc_id = StringProperty(default="")
    _prefix = ""

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def invoke(self, context, event):
        print("INVOKE....................")

    def execute(self, context):
        if self.doc_id != "":
            dprint("Overwriting view docs for %s" % self.doc_id)
            #return { 'CANCELLED' }
        bpy.ops.ui.copy_data_path_button()
        x = bpy.ops.anim.copy_driver_button()
        bpy.ops.anim.driver_button_remove(all=False)
        context.scene.update()
        xlist = create_drivers_list()
        global GLOBALdriverlist
        GLOBALdriverlist = set([driver for xx in xlist
                                for driver in xlist[xx]])
        driverlist = GLOBALdriverlist

        if x == {'FINISHED'}:  # driver copied.
            try:
                bpy.ops.anim.paste_driver_button()
                xlist = create_drivers_list()
                bpy.ops.anim.paste_driver_button()
                driverlist_after = [driver for xx in xlist
                                    for driver in xlist[xx]]
                after = set(driverlist_after)
                changed = after - driverlist
                index = driverlist_after.index(list(changed)[0])
                return(bpy.ops.speaker.add_driver_channel('INVOKE_DEFAULT',
                                                          driver_index=index))
            except:
                print("EXEPTION")
                pass
        bpy.ops.anim.driver_button_add(all=False)
        xlist = create_drivers_list()
        context.scene.update()
        driverlist_after = [driver for xx in xlist for driver in xlist[xx]]
        after = set(driverlist_after)
        changed = after - driverlist
        index = driverlist_after.index(list(changed)[0])
        return(bpy.ops.speaker.add_driver_channel('INVOKE_DEFAULT',
                                                  driver_index=index))


class ContextSpeakerSelectMenu(bpy.types.Menu):
    bl_idname = "speaker.select_contextspeaker"
    bl_label = "Choose speaker to drive"
    driver = None

    def draw(self, context):
        speakers = [speaker for speaker in bpy.data.speakers
                    if "vismode" in speaker]
        for speaker in speakers:
            text = "%s (%s)" % (speaker.name, speaker.sound.name)
            self.layout.operator("speaker.add_driver_channel",
                                 text=text).contextspeakername = speaker.name


class ContextSpeakerMenu(bpy.types.Menu):
    bl_idname = "speaker.contextspeaker"
    bl_label = "Choose speaker to drive"
    driver = None

    def draw(self, context):
        speakers = [speaker for speaker in bpy.data.speakers
                    if "Channel0" in speaker]
        for speaker in speakers:
            text = "%s (%s)" % (speaker.name, speaker.sound.name)
            self.layout.operator("speaker.add_driver_channel",
                                 text=text).contextspeakername = speaker.name


def setcontextspeaker(name):
    xlist = create_drivers_list()
    #global GLOBALdriverlist
    #GLOBALdriverlist = set([driver for xx in xlist for driver in xlist[xx]])
    speaker = bpy.data.speakers.get(name)
    bpy.types.Scene.context_speaker = speaker


def overwriteviewdoc(enable):
    try:
        if enable:
            bpy.utils.unregister_class(bpy.types.WM_OT_doc_view)
            bpy.utils.register_class(SimpleOperator)
        else:
            bpy.utils.unregister_class(bpy.types.WM_OT_doc_view)
            bpy.utils.register_class(WM_OT_doc_view)
    except:
        print("HUMFFF this is driving me nuts")


def rightclickfudge(self, context):
    on = self.rightclick == 'ON'
    overwriteviewdoc(on)

bpy.types.Scene.speaker_settings = BoolProperty(name="Speaker Tools Settings",
                                               default=False)
bpy.types.Scene.rightclick = EnumProperty(items=(
            ("OFF", "OFF", "Prop toolbox right click off"),
            ("ON", "ON", "Overwrite view docs operator"),
            ),
            name="Right Click Fudge",
            default="OFF",
            description="Add speaker drivers from right click toolbox",
            #update=overwriteviewdoc,
            options={'HIDDEN'},
            update=rightclickfudge
            )


class SoundToolPanel(bpy.types.Panel):
    bl_label = "Sound Tools"
    bl_space_type = "VIEW_3D"
    #bl_region_type = "UI"
    bl_region_type = "TOOLS"

    @classmethod
    def poll(cls, context):
        speakers = [speaker for speaker in bpy.data.speakers
                    if "vismode" in speaker]
        return len(speakers) > 0

    def draw_header(self, context):
        scene = context.scene
        #rd = scene.render

        self.layout.prop(scene, "speaker_settings", text="")

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        if scene.speaker_settings:
            row = layout.row()
            box = row.box()
            row = box.row()
            row.label(text="Right Click Override", icon="INFO")
            row = box.row()
            row.prop(scene, "rightclick", expand=True)
            if scene.rightclick == 'ON':
                box.label("Overriden Op")
                box.label("View Online Python Reference")
            row = layout.row()
            props = scene.speaker_tool_settings
            row.prop(props, "material_driver_fix", text="Material Driver Fix",
                    toggle=True, icon='MATERIAL_DATA')
        row = layout.row()
        context_speaker = bpy.types.Scene.context_speaker
        if context_speaker is not None:
            text = "%s (%s)" % (context_speaker.name,
                                context_speaker.sound.name)
            row.menu("speaker.select_contextspeaker", text=text)
            #row = layout.row()
            #row.operator("wm.modal_timer_operator")
            box = layout.box()
            row = box.row(align=True)
            action = getAction(context_speaker)
            if action:
                SoundActionMenuRow(row, context_speaker, action, True)
                showEqualiser(box, context_speaker, action, info=False)
            row = layout.row()
            box = row.box()
            AllDriversPanel(box, context)
        else:
            row.menu("speaker.select_contextspeaker")


def register():

    #bpy.utils.register_class(SimpleOperator)
    bpy.types.Speaker.filter_sound = BoolProperty(default=False,
                                                  update=speaker_filter_sound)
    bpy.utils.register_class(ContextSpeakerSelectMenu)
    bpy.utils.register_class(AddCustomSoundDriverToChannel)
    bpy.utils.register_class(ContextSpeakerMenu)
    bpy.utils.register_class(SoundToolPanel)


def unregister():
    #bpy.utils.unregister_class(SimpleOperator)
    bpy.utils.unregister_class(AddCustomSoundDriverToChannel)
    bpy.utils.unregister_class(ContextSpeakerMenu)
    bpy.utils.unregister_class(ContextSpeakerSelectMenu)
    bpy.utils.unregister_class(SoundToolPanel)
