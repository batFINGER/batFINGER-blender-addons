# <pep8-80 compliant>
import bpy
from bpy.app.handlers import persistent
from bpy.props import *
from bpy.utils import preset_find, preset_paths
from bpy.types import PropertyGroup

from math import log, sqrt
from mathutils import Vector, Color
from speaker_tools.NLALipsync import SoundTools_LipSync_PT
from speaker_tools.presets import AddPresetSoundToolOperator
from bl_ui.properties_data_speaker  import DATA_PT_context_speaker, \
                DATA_PT_speaker, DATA_PT_cone, DATA_PT_distance, \
                DATA_PT_custom_props_speaker

from speaker_tools.utils import get_driver_settings, create_drivers_list,\
                icon_from_bpy_datapath, getSpeaker, getAction, AllDriversPanel

from speaker_tools.filter_playback import setup_buffer, play_buffer,\
                mix_buffer
# add drivers to the namespace


@persistent
def InitSoundTools(dummy):
    bpy.app.driver_namespace["context_speaker"] = None
    if "SoundDrive" not in bpy.app.driver_namespace:
        print("SoundDrive Added to drivers namespace")
        bpy.app.driver_namespace["SoundDrive"] = SoundDrive
    reset_drivers()
    bpy.app.handlers.frame_change_pre.append(live_speaker_view)
# method to reinvigorate disabled drivers in file.


def reset_drivers():
    driver_dict = create_drivers_list()
    return


def live_speaker_view(scene):
    #scene = bpy.context.scene
    #print("Frame Change", scene.frame_current)
    frame = scene.frame_current
    scene.play = True
    #bpy.data.speakers[0].vismode = bpy.data.speakers[0].vismode
    return None
    '''
    speakers = [speaker for speaker in bpy.data.speakers
                if "Channel0" in speaker]
    '''
    for speaker in bpy.data.speakers:
        # setting the enum to the enum will make the panel live
        if speaker.get("vismode") is None:
            continue
        speaker.vismode = speaker.vismode
        # turn off lipsync cos it's slow

        if True and speaker.animation_data:
            action = speaker.animation_data.action
            if action:
                timemarkers = [marker.name for marker in action.pose_markers
                               if marker.frame == frame]
                if len(timemarkers):
                    speaker.papagayo_phonemes = timemarkers[0]

# DRIVER methods ######################################


def SoundDrive(channels, amplify=1.0, norm=1.0, threshold=0.0):
    if isinstance(channels, float):
        channel = channels
    elif isinstance(channels, list):
        if len(channels) > 0:
            channel = sum(channels) / len(channels)
        else:
            channel = 0.0
    else:
        return 0.0  # somethings gone wrong
    #print("SoundDrive %s"%channel)
    value = amplify * norm * channel
    if value > threshold:
        return(value)
    else:
        return(0.0)


def getrange(fcurve, tolerance):
    #get the minimum and maximum points from an fcurve

    REJECT = tolerance  # reject frequencty
    #print(len(fcurve.sampled_points))
    points = [0.0]
    for point in fcurve.sampled_points:
        # bake sound to fcurve returns some rubbish when the frequency
        # is out of range
        # often the only usable point is in the first
        if point.co[1] > -REJECT and point.co[1] < REJECT:
            points.append(point.co[1])
    #print(points)
    #print("GETRANGE",min(points),max(points))
    hasrange = abs(max(points) - min(points)) > 0.01
    if hasrange:
        return True, min(points), max(points)
    else:
        return False, 0.0, 0.0


def f(freq):
    #output a format in Hz or kHz
    if freq < 1000:
        return("%dHz" % freq)
    elif freq < 1000000:
        khz = freq / 1000
        return("%.2fkHz" % khz)
    return(" ")


class DataButtonsPanel():
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"

    @classmethod
    def poll(cls, context):
        return context.speaker is not None


class SoundVisualiserPanel(DataButtonsPanel, bpy.types.Panel):
    bl_label = " "
    bl_options = {'HIDE_HEADER'}
    #bl_space_type = "GRAPH_EDITOR"
    #bl_region_type = "UI"
    driver_index = 0

    def draw_header(self, context):
        layout = self.layout
        row = layout.row()
        layout.menu("soundtest.menu", text="Select Sound Action", icon='SOUND')

    def drawvisenum(self, context):
        speaker = getSpeaker(context)
        layout = self.layout
        row = layout.row()
        row.prop(speaker, 'vismode', expand=True)

    def drawcontextspeaker(self, context, layout):
        ob = context.object
        speaker = getSpeaker(context)
        space = context.space_data

        split = layout.split(percentage=0.65)

        if ob:
            split.template_ID(ob, "data")
        elif speaker:
            split.template_ID(space, "pin_id")

    def draw(self, context):
        layout = self.layout
        sce = context.scene
        space = context.space_data
        speaker = getSpeaker(context)
        '''
        # Call menu executes the operator...
        row = layout.row()
        row.operator("wm.call_menu").name="speaker.preset_menu"
        '''
        row = layout.row()
        row.menu("speaker.preset_menu")

        nla = False
        action = None
        frame = sce.frame_current
        self.drawvisenum(context)
        row = layout.row()
        self.drawcontextspeaker(context, row)

        box = layout.box()
        has_sound = (speaker.sound is not None)
        if not has_sound:
            row = box.row()
            row.template_ID(speaker, "sound", open="sound.open_mono")
            return

        action = getAction(speaker, search=True)

        '''
        if "Channels" not in action:

            row = box.row()
            row.template_ID(speaker.animation_data,"action")
        '''
        row = box.row(align=True)
        #row.alignment = "E"

        SoundActionMenuRow(row, speaker, action, has_sound)
        if not has_sound:
            return

        if speaker.vismode == 'SOUND':
            box.label("Sound", icon='FILE_SOUND')
            soundbox = box.box()
            row = soundbox.row()
            row.prop(speaker.sound, "type")
            row = soundbox.row()
            split = row.split(percentage=0.75)
            split.template_ID(speaker, "sound", open="sound.open_mono")
            split.prop(speaker, "muted")
            row = soundbox.row()
            row.prop(speaker, "volume")
            row.prop(speaker, "pitch")

            box.label("Distance", icon='ARROW_LEFTRIGHT')
            distancebox = box.box()
            split = distancebox.split()

            col = split.column()
            col.label("Volume:")
            col.prop(speaker, "volume_min", text="Minimum")
            col.prop(speaker, "volume_max", text="Maximum")
            col.prop(speaker, "attenuation")

            col = split.column()
            col.label("Distance:")
            col.prop(speaker, "distance_max", text="Maximum")
            col.prop(speaker, "distance_reference", text="Reference")

            box.label("Cone", icon='MESH_CONE')
            conebox = box.box()
            split = conebox.split()
            col = split.column()

            col.label("Angle:")
            col.prop(speaker, "cone_angle_outer", text="Outer")
            col.prop(speaker, "cone_angle_inner", text="Inner")

            col = split.column()

            col.label("Volume:")
            col.prop(speaker, "cone_volume_outer", text="Outer")

        if action:
            minf = -1
            maxf = -1
            scale = action["row_height"]
            name = "Channel"
            if "Channels" in action:
                channels = action["Channels"]
                name = channel_name = action["channel_name"]
                minf = action["minf"]
                maxf = action["maxf"]
                start = action["start"]
                end = action["end"]
            else:
                channels = len(action.fcurves)
                minf = 0.0
                maxf = 0.0
                start = 0
                end = channels

            if start >= end:
                end = start + 1
            i = start

            if speaker.vismode == 'VISUAL':
                showEqualiser(box, speaker, action)
            elif speaker.vismode == 'OUT':
                showFilterBox(box, context, speaker, action)

            elif speaker.vismode == 'DRIVERS':
                if context.space_data.use_pin_id:
                    box = layout.box()
                    AllDriversPanel(box, context)
                box = layout.box()

                driver_index = SoundVisualiserPanel.driver_index
                box.scale_y = 0.8

                driver = speaker.animation_data.drivers[driver_index]
                '''
                text = "%s %s" % (driver.data_path, driver.driver.expression)
                row.menu("soundtest.menu",
                         text=text,
                         icon='DRIVER')
                '''
                for i, driver in enumerate(speaker.animation_data.drivers):
                    if i != driver_index:
                        continue
                    box = layout.box()
                    box.alert = driver.is_valid
                    row = box.row()
                    row.prop(speaker, driver.data_path, slider=True)
                    row = box.row()
                    row.prop(driver.driver, "expression")
                    for var in driver.driver.variables:
                        row = box.row()
                        row.prop(var, "name")
                        row = box.row()
                        row.prop(var.targets[0], "data_path")
                    box.operator("speaker.add_driver_channel",
                                 text="Rechoose target freq").driver_index = i
            elif speaker.vismode == 'LIPSYNC':
                bpy.types.SoundTools_LipSync_PT.draw(self, context)
            #print("ACTION",action)
            #timemarkers = ['rest']
            timemarkers = [marker
                           for marker in action.pose_markers
                           if marker.frame == frame]
            row = layout.row()
            if True:
                row.prop(speaker, "papagayo_phonemes", expand=True)
            row = layout.row()
            if len(timemarkers) and True:
                row.label(text="%s" % timemarkers[0].name, icon='MOD_MASK')
                row.prop(timemarkers[0], "frame", text="")
            else:
                timemarkers = [marker
                               for marker in action.pose_markers
                               if marker.frame > frame]
                if len(timemarkers):
                    row.label(text="NEXT %s" % timemarkers[0].name)
                else:
                    row.label("-")
        layout.prop(sce, "frame_current", emboss=True)


def test(self, context):
    if self.save_preset:
        if len(self.preset) == 0:
            self.save_preset = False
    return None


class SPEAKER_OT_Visualise(bpy.types.Operator):
    '''Bake Multi Freqs to Action'''
    bl_idname = "speaker.visualise"
    bl_label = "Bake Sound to Multiple freq."
    # popups  so need to handle presets slightlty different
    #bl_options = {'PRESET'}  # Handle presets.
    # registered scripts and update functions = HAVOK
    #bl_options = { 'REGISTER', 'UNDO', 'PRESET' }
    preset = StringProperty(name="Preset",
                            default="",
                            update=test,
                            options={'SKIP_SAVE'},
                            description="Save Preset")
    channels = IntProperty(name="Channels",
                           default=16,
                           description="Number of frequencies to split",
                           min=1,
                           max=96)
    minf = FloatProperty(name="Min Freq",
                         default=4.0,
                         description="Minimum Freq",
                         min=0,
                         max=10000.0)
    maxf = FloatProperty(name="Max Freq",
                         default=10000.0,
                         description="Maximum Freq",
                         min=100.0,
                         max=1000000.0)
    attack = FloatProperty(name="Attack",
                           default=0.005,
                           description="Attack",
                           min=0.001, max=0.1)
    action_name = StringProperty(name="Action Name", default="SoundAction")
    channel_name = StringProperty(name="Channel Name", default="CH")

    release = FloatProperty(name="Release",
                            default=0.2,
                            description="Release")
    threshold = FloatProperty(name="Threshold",
                              default=0.005,
                              description="Threshold")
    sthreshold = FloatProperty(name="SquareThreshold",
                               default=0.005,
                               description="Square Threshold")

    square = BoolProperty(name="Square",
                          default=False,
                          description="Square")
    accumulate = BoolProperty(name="Accumulate",
                              default=False,
                              description="Accumulate")
    use_additive = BoolProperty(name="UseAdditive",
                                default=False,
                                description="Use Additive")
    use_log = BoolProperty(name="Log Scale",
                           default=True,
                           description="Use Log scale for channels")
    log_base = IntProperty(name="log_base",
                           default=16,
                           description="log base to use",
                           min=2,
                           soft_min=2,
                           soft_max=32,
                           max=64)

    xaction = StringProperty(name="xaction",
                             default="")

    crop = BoolProperty(default=False,
                        description="Crop to new limits")

    '''
    test = BoolProperty(default=True, update=test)
    '''

    save_preset = BoolProperty(default=False,
                               description="Save Preset",
                               options={'SKIP_SAVE'},
                               update=test,
                               )

    op = EnumProperty(items=(
                ("CROP", "CROP", "Display as Sliders"),
                ("REBAKE", "REBAKE", "Show sound visualiser"),
                ("NORMAL", "NORMAL", "Create Custom Driver(s)")
                ),
                name="Op",
                default="NORMAL",
                description="Visualisation Type",
                #update=setcontextspeakerENUM,
                options={'SKIP_SAVE'},
                )
    '''
    type = EnumProperty(items=(
                ("SFX", "SFX", "Sound Effects"),
                ("MUSIC", "MUSIC", "Music"),
                ("VOICE", "VOICE", "Voice")
                ),
                name="type",
                default="SFX",
                description="Input Type",
                #update=setcontextspeakerENUM,
                )
    '''

    type = StringProperty(default="SFX")

    TOL = FloatProperty(name="Max Val Limit",
                        description="Discard channel values greater",
                        default=100)

    #driver_index = IntProperty(default=-1)
    contextspeakername = StringProperty(default="None", options={'SKIP_SAVE'})
    bake_graph_op = None # used to pass the bake op to execute.

    @classmethod
    def poll(cls, context):
        return True

    def cancel(self, context):
        #bpy.types.Scene.soundtool_op = None
        print('cancelled')
        return {'CANCELLED'}

    def invoke(self, context, event):
        #create a Sounds action
        print("INVOKE")
        '''
        if bpy.types.Scene.soundtool_op is not None:
            bpy.types.Scene.soundtool_op.test = True
            bpy.types.Scene.soundtool_op.execute(context)
        '''
        bpy.types.Scene.soundtool_op = self
        use_preset = len(self.preset) > 0

        speaker = getSpeaker(context)
        if speaker is not None:
            self.type = speaker.sound.type
        if use_preset:
            pp = AddPresetSoundToolOperator.operator_path(None)
            path = preset_find(self.preset, pp)
            if path is not None:
                bpy.ops.script.python_file_run(filepath=path)
            self.use_preset = False
        if "SoundDrive" not in bpy.app.driver_namespace:
            InitSoundTools(context.scene)
        '''
        if self.driver_index > -1:
            bpy.types.SoundVisualiserPanel.driver_index = self.driver_index
            return {'RUNNING_MODAL'}
        '''

        if len(self.xaction):
            #print("ACTION %s" % self.xaction)
            soundaction = bpy.data.actions[self.xaction]
            if soundaction is not None:
                speaker.animation_data.action = soundaction
                rna = soundaction["rna"]
                #print(rna)
                speaker["_RNA_UI"] = eval(rna)

            return {'FINISHED'}
        wm = context.window_manager

        ad = speaker.animation_data
        if ad is not None and ad.action is not None and not use_preset:
            if "Channels" in speaker.animation_data.action:
                soundaction = ad.action
                self.channels = soundaction["Channels"]
                name = self.channel_name = soundaction["channel_name"]
                self.action_name = soundaction.name
                if self.op == 'REBAKE':
                    pass

                if self.op in ['CROP', 'REBAKE']:
                    #freqrange = eval(soundaction["needs_rebake"])
                    start = soundaction["start"]
                    end = soundaction["end"]
                    channel = "%s%d" % (name, start)
                    self.minf = speaker["_RNA_UI"][channel]["low"]
                    channel = "%s%d" % (name, end)
                    self.maxf = speaker["_RNA_UI"][channel]["high"]
                    self.op = 'NORMAL'
                else:
                    self.minf = soundaction["minf"]
                    self.maxf = soundaction["maxf"]
                self.use_log = soundaction["use_log"]
        print("INVOKE__________END")
        #print(context.space_data.type)
        #return {'FINISHED'}
        return wm.invoke_props_dialog(self)

    def draw_header(self, context):
        layout = self.layout()
        layout.label("HOOOOOHA")

    def draw(self, context):
        sce = context.scene
        speaker = getSpeaker(context)
        layout = self.layout

        #row.operator(self.bl_idname).preset = "FOOBAR"
        row = layout.row()
        preset_box = row.box()
        row = preset_box.row()
        if len(self.preset) == 0:
            txt = "Select Preset"
        else:
            txt = self.preset
        row.menu("speaker.preset_menu", text=txt)
        row = preset_box.row()
        row.prop(self, "save_preset")
        preset_row = preset_box.row()
        preset_row.prop(self, "preset")
        row.label(speaker.sound.name)
        row = layout.row()
        row.prop(self, "action_name")
        row = layout.row()
        # Specific to type MUSIC / VOICE / SFX
        if speaker.sound.type == "MUSIC":
            row = layout.row()
            row.label(icon='SOUND', text="")
            row.prop(sce, "note")
            row.prop(sce, "note")
            #row.menu("sound.music_notes", text="Notes")
            split = row.split(percentage=0.7)
            split.prop(self, "channel_name", text="Channel")

            #split.prop(self, "channels")
        else:
            split = row.split(percentage=0.7)
            split.prop(self, "channel_name", text="Channel")

            split.prop(self, "channels")
            row = layout.row()
            row.prop(self, "minf")
            row = layout.row()
            row.prop(self, "maxf")
            row = layout.row()
            split = row.split(percentage=0.40)
            split.prop(self, "use_log")

            split.prop(self, "log_base")
            #settings for other types

        # Settings for bake sound to fcurve Operator
        box = layout.box()
        box.label("Bake Sound to fcurve", icon='IPO')
        self.bake_graph_op = op = box.operator("graph.sound_bake", icon='IPO')
        #box.prop(self, "threshold")
        box.prop(self.bake_graph_op, "threshold")
        #box.prop(self, "release")
        box.prop(op, "release")
        op.attack = 0.333
        #box.prop(self, 'attack')
        box.prop(op, 'attack')
        #box.prop(self, "use_additive", icon="PLUS")
        box.prop(op, "use_additive", icon="PLUS")
        #box.prop(self, "accumulate", icon="PLUS")
        box.prop(op, "use_accumulate", icon="PLUS")
        row = box.row()
        split = row.split(percentage=0.20)
        #split.prop(self, "square")
        split.prop(op, "use_square")
        #split.prop(self, "sthreshold")
        split.prop(op, "sthreshold")
        layout.prop(self, "TOL")

    def execute(self, context):
        # set to frame 1
        rna = dict()
        action_rna = dict()
        save_frame = context.scene.frame_current
        '''
        Always bake from frame 1
        '''
        context.scene.frame_set(1)
        space = context.space_data
        area = context.area
        area_type = area.type

        #if space.type = "VIEW
        if area.type == 'VIEW_3D':
            speaker = bpy.app.driver_namespace["context_speaker"]
            speakerobjs = [speakerobj
                           for speakerobj in context.scene.objects
                           if speakerobj.data == speaker]
            context.scene.objects.active = speakerobjs[0]
        elif context.space_data.use_pin_id:
            #context.space_data.context = "OBJECT"
            speaker = context.space_data.pin_id
            #find the speaker object
            speakerobjs = [speakerobj
                           for speakerobj in context.scene.objects
                           if speakerobj.data == speaker]

            context.scene.objects.active = speakerobjs[0]
        else:
            speaker = context.object.data

        if self.op == 'REBAKE':
            print("REBAKE REMOVING ACTION")
            action = speaker.animation_data.action
            action["wavfile"] = ""  # take it out of sound actions
            action.name = "XXXXXX"

        context.area.type = 'GRAPH_EDITOR'
        soundaction = bpy.data.actions.new("%s" % (self.action_name))
        soundaction["Channels"] = self.channels
        soundaction["channel_name"] = self.channel_name
        soundaction["minf"] = self.minf
        soundaction["maxf"] = self.maxf
        soundaction["use_log"] = self.use_log
        soundaction["wavfile"] = speaker.sound.name

        #keep some UI stuff here too like the row height of each channel

        soundaction["row_height"] = 0.6

        if not speaker.animation_data:
            speaker.animation_data_create()
        speaker.animation_data.action = soundaction
        if not soundaction:
            return{'CANCELLED'}
        #CHANGE CAPS TO OP PROPS
        use_log = self.use_log
        MIN = 100
        MAX = -100
        if use_log:
            if self.minf == 0:
                self.minf = 1
            LOW = log(self.minf, self.log_base)
            HIGH = log(self.maxf, self.log_base)
            RANGE = HIGH - LOW
        else:
            LOW = self.minf
            HIGH = self.maxf
            RANGE = HIGH - LOW

        filepath = speaker.sound.filepath
        n = self.channels
        good = []
        for i in range(0, n):
            channel = '%s%d' % (self.channel_name, i)
            low = LOW + (i) * RANGE / n
            high = LOW + (i + 1) * RANGE / n
            speaker[channel] = 0.0
            #speaker.keyframe_insert('["%s"]' % channel)
            fcurve = soundaction.fcurves.new("DUMMY")
            fcurve.data_path ='["%s"]' % channel
            #fcurve = soundaction.fcurves[i]
            if use_log:
                low = self.log_base ** low
                high = self.log_base ** high
            fcurve.select = True
            try:
                op = self.bake_graph_op
                bpy.ops.graph.sound_bake(filepath=filepath,
                                     low=low,
                                     high=high,
                                     attack=op.attack,
                                     release=op.release,
                                     threshold=op.threshold,
                                     use_accumulate=op.use_accumulate,
                                     use_additive=op.use_additive,
                                     use_square=op.use_square,
                                     sthreshold=op.sthreshold)
            except:
                context.area.type = area_type
                # remove soundaction
                #bpy.data.actions.remove(soundaction)
                print("ERROR ENCOUNTERED IN SOUND BAKING")
                self.report({'ERROR'}, "Error Encountered in sound baking")
                soundaction["bake_error"] = "BZZ"
                return {'CANCELLED'}

            has_range, min_, max_ = getrange(fcurve, self.TOL)
            if min_ < MIN:
                MIN = min_
            elif max_ > MAX:
                MAX = max_

            if has_range:
                #flag it as dirty
                good.append(i)

            desc = "Frequency %s to %s (min:%.2f, max:%.2f)" %\
                        (f(low),  f(high), min_, max_)
            rna[channel] = {"name": "HARRY",
                            "min": 0.0,
                            "max": 0.5,
                            "description": desc,
                            "soft_min": min_,
                            "soft_max": max_,
                            "low": low,
                            "high": high,
                            "a": min_,
                            "b": max_}

            fcurve.select = False

        for i in range(0, n):
            #channel = 'Channel%d'%i
            channel = '%s%d' % (self.channel_name, i)
            rna[channel]["min"] = MIN
            rna[channel]["max"] = MAX
            if True:  # USE SOFT MIN SLIDERS relative_scale
                rna[channel]["soft_min"] = MIN
                rna[channel]["soft_max"] = MAX

        soundaction["max"] = MAX
        soundaction["min"] = MIN
        soundaction["rna"] = str(rna)
        if len(good) == 0:
            good_min = 0
            good_max = 0
        else:
            good_min = min(good)
            good_max = max(good)
        soundaction["start"] = good_min
        clip = self.channels - 1
        soundaction["end"] = good_max
        if len(good) == 0:
            soundaction["error"] = "NO CHANNELS BAKED"

        elif len(good) < self.channels:
            soundaction["error"] = "NEEDS REBAKE"

        #soundaction["show_freq"] = False
        #action_rna["show_freq"] =  {"default":True}
        action_rna["row_height"] = {"min": 0.001,
                                    "max": 1.0,
                                    "description": "Alter the row height",
                                    "soft_min": 0.0,
                                    "soft_max": 1.0}
        action_rna["start"] = {"min": 0,
                               "max": 1.0,
                               "description": "Clip Start",
                               "soft_min": 0,
                               "soft_max": clip}
        action_rna["end"] = {"min": 1,
                             "max": clip,
                             "description": "Clip End",
                             "soft_min": 1,
                             "soft_max": clip}
        speaker["_RNA_UI"] = rna
        soundaction["_RNA_UI"] = action_rna
        #speaker["Channels"] = n
        #speaker.keyframe_insert('["Channels"]')
        context.area.type = area_type
        context.scene.frame_set(save_frame)
        speaker.vismode = 'VISUAL'

        soundaction.vismode = 'SLIDER'

        if self.preset > "":
            bpy.ops.wm.soundtool_operator_preset_add(name=self.preset,
                                                     operator=self.bl_idname)
        '''
        Move the Sound to Frame 1
        '''
        scene = context.scene
        name = "%s__@__%s" % (speaker.name, soundaction.name)
        sound_channels = scene.sound_channels.get(name)
        if not sound_channels:
            sound_channels = scene.sound_channels.add()
            sound_channels.name = name

        scene.objects.active.animation_data.nla_tracks["SoundTrack"]\
                .strips["NLA Strip"].frame_start = 1.0

        return{'FINISHED'}


class SoundVisMenu(bpy.types.Menu):
    bl_idname = "soundtest.menu"
    bl_label = "Select a Sound"
    vismode = 'VISUAL'

    def draw(self, context):
        speaker = getSpeaker(context)
        #if SoundVisMenu.vismode in ["VISUAL", "SOUND", "DRIVERS"]:
        if True:
            actions = [action for action in bpy.data.actions
                       if "wavfile" in action
                       and action["wavfile"] == speaker.sound.name]

            for action in actions:
                self.layout.operator("speaker.visualise",
                                     text=action.name).xaction = action.name


class DriverMenu(bpy.types.Menu):
    bl_idname = "speaker_tools.driver_menu"
    bl_label = "Select a Driver"

    def draw(self, context):
        print("draw")


def showFilterBox(layout, context, speaker, action):
    if action:
        scene = context.scene
        minf = -1
        maxf = -1
        scale = action["row_height"]
        name = "Channel"
        if "Channels" in action:
            channels = action["Channels"]
            name = channel_name = action["channel_name"]
            minf = action["minf"]
            maxf = action["maxf"]
            MIN = action["min"]
            MAX = action["max"]
            start = action["start"]
            end = action["end"]
        else:
            channels = len(action.fcurves)
            minf = 0.0
            MIN = 0.0
            maxf = 0.0
            MAX = 0.0
            start = 0
            end = channels

        if start >= end:
            end = start + 1
        i = start
        box = layout
        row = box.row()
        row.prop(speaker, "filter_sound", toggle=True)
        b = bpy.app.driver_namespace.get("ST_buffer")
        h = bpy.app.driver_namespace.get("ST_handle")
        if b and not h:
            row = layout.row()
            row.label("BUFFERING %s" % b, icon='INFO')
        if b:
            row = layout.row()
            row.label("BUFFERED %s" % b, icon='INFO')
        if h:
            row = layout.row()
            if not h.status:
                row.label("Handle %s" % h.status, icon='INFO')
            else:
                row.label("Handle.position %d %0.2fs" % (h.status, h.position), icon='INFO')
        row = box.row()
        COLS = int(sqrt(channels))

        sound_channel_id = "%s__@__%s" % (speaker.name, action.name)
        sound_item = None
        from speaker_tools.filter_playback import  sound_buffer
        if sound_buffer:
            sound_item = sound_buffer.get(sound_channel_id)
        filter_item = scene.sound_channels.get(sound_channel_id)
        if filter_item is not None:
            row = box.row()
            row.prop(filter_item, "buffered")
            row = box.row()
            row.prop(filter_item, "valid_handle")
            for i in range(start, end + 1):
                cn = "channel%02d" % i
                #box.split(percentage=0.50)
                if not i % COLS:
                    row = box.row()
                col = row.column()
                #BUGGY on speaker object
                icon = 'OUTLINER_DATA_SPEAKER'
                if sound_item and sound_item.get(cn):
                    icon = 'OUTLINER_OB_SPEAKER'
                col.prop(filter_item,
                         cn,
                         text="%s" % i,
                         icon=icon,
                         toggle=True)


def showEqualiser(layout, speaker, action, info=True):
    if action:
        minf = -1
        maxf = -1
        scale = action["row_height"]
        name = "Channel"
        if "Channels" in action:
            channels = action["Channels"]
            name = channel_name = action["channel_name"]
            minf = action["minf"]
            maxf = action["maxf"]
            MIN = action["min"]
            MAX = action["max"]
            start = action["start"]
            end = action["end"]
        else:
            channels = len(action.fcurves)
            minf = 0.0
            MIN = 0.0
            maxf = 0.0
            MAX = 0.0
            start = 0
            end = channels

        if start >= end:
            end = start + 1
        i = start

    box = layout
    if info:
        #box.scale_y = scale
        desc = "%d channels (%s to %s)" % (channels, f(minf), f(maxf))
        desc2 = "MIN %.2f MAX %.2f" % (action["min"], action["max"])
        '''
        row = box.row()
        if nla:
            row.label(icon="NLA")
        else:
            row.label(icon="ACTION")
            if not action.use_fake_user:
                row.prop(action,"use_fake_user",toggle=True,
                emboss=True,text="SAVE THIS?")
        row.enabled = not nla
        '''
        box.label(text=desc, icon='INFO')
        box.label(desc2)
        row = box.row()
        row.prop(speaker.animation_data, "use_nla")
        '''
        row = box.row()
        row.prop(speaker, "play")
        '''
        row = box.row()
        row.prop(action, "vismode", expand=True)
        row = box.row()
        split = row.split(percentage=0.2)
        split.prop(action, "show_freq",
                   emboss=True, text="",
                   icon_only=True,
                   icon='ARROW_LEFTRIGHT')
        split.prop(action, '["row_height"]', slider=True)
        split.prop(action, '["start"]', slider=True)
        split.prop(action, '["end"]', slider=True)
        if (end + 1 - start) < channels:
            split.operator("speaker.visualise",
                           text="CROP").op = 'CROP'
        #box.enabled = False
        #box.split(percentage=0.50)
        row = box.row()
        if "error" in action:
            error = action["error"]
            if error == "NEEDS REBAKE":
                row.operator("speaker.visualise",
                         text="REBAKE?",
                         icon='ERROR').op = 'REBAKE'
                row = box.row()
                row.label(text="Not all frequencies baked")
            else:
                row.label(text=error, icon='ERROR')

    eqbox = box.column()
    eqbox.scale_x = scale
    eqbox.scale_y = scale
    sp = 0.2
    if action.show_freq:
        sp = 0.01

    if action.vismode == 'VERTICAL':
        EqualiserBoxVert(eqbox, speaker, channel_name,
                         start, end, sp, MIN, MAX)
    else:
        EqualiserBox(eqbox, speaker, channel_name, start, end, sp,
                     TEXT=(action.vismode == 'HORIZONTAL'))


def SoundActionMenuRow(row, speaker, action, has_sound):
    if has_sound:
        col = row.column()
        col.alignment = 'LEFT'
        col.menu("soundtest.menu", text="", icon='SOUND')
    #col.alignment="LEFT"
    if action:
        col = row.column()
        col.prop(action, "name", emboss=True, text="")
    else:
        col = row.column()
        #col.label("NO SOUND BAKED")
        col.operator("speaker.visualise",
                     text="Bake %s" % speaker.sound.name)
    col = row.column()
    col.alignment = 'RIGHT'
    split = col.split()
    split.alignment = 'RIGHT'
    if not has_sound:
        return
    if action:
        split.prop(action, "use_fake_user",
                   toggle=True, text="F", emboss=True)
    split.operator("speaker.visualise", text="", icon='ZOOMIN')


def EqualiserBox(eqbox, speaker, channel_name, start, end, sp, TEXT=False):
    TEXTWIDTH = 50

    for i in range(start, end + 1):
        channel = "%s%d" % (channel_name, i)
        row = eqbox.row()
        #row.scale_y = scale
        #row.scale_x =  scale
        split = row.split(percentage=sp)
        split.label(f(speaker["_RNA_UI"][channel]["low"]))
        #col2.label(f(speaker["_RNA_UI"][channel]["low"]))
        rna = speaker["_RNA_UI"][channel]

        #print("%d smin %s"%(i,rna["soft_min"]))
        #print("smax %s"%rna["soft_max"])
        if float(rna["b"] - rna["a"]) < 0.0001:
            wbox = split.box()
            wbox.scale_y = 0.5
            wbox.scale_x = 0.5
            wbox.label("NO DATA IN THIS FREQUENCY")
        elif TEXT:
            value = speaker[channel] * TEXTWIDTH
            #split.prop(speaker, '["%s"]' % channel, slider=True)
            #row.alignment = 'LEFT'
            value = speaker.get(channel)
            split.alignment = 'LEFT'
            MIN = speaker["_RNA_UI"][channel]['min']
            MAX = speaker["_RNA_UI"][channel]['max']
            maxf = speaker['_RNA_UI'][channel]['b']
            minf = speaker['_RNA_UI'][channel]['a']
            diff = MAX - MIN
            pc = (maxf - MIN) / diff
            if pc < 0.0001:
                pc = 0.0001
            split = split.split(percentage=pc)
            frow = split.column()
            pc = 0.5
            if maxf > 0:
                pc = value / maxf
            else:
                pc = 0.001
            if pc > 0.001:
                fbox = frow.split(percentage=pc)
                fbox.box()

            split.box()
        else:
            split.prop(speaker, '["%s"]' % channel, slider=True, emboss=True)
            #fbox.label(icon='LAYER_USED')  # wierd 3d effect
            '''
            for i in range(1, 10):
                pc = float(i) / 10.0
                top = pc * diff
                col = split.row()
                col.alignment = 'LEFT'
                if speaker.get(channel) > top:
                    col.label("", icon='MESH_PLANE')
                elif MAX > top:
                    col.label("", icon='CHECKBOX_DEHLT')
            '''
        i += 1


def EqualiserBoxVert(eqbox, speaker, channel_name, start, end, sp, MIN, MAX):
    eqbox.alignment = 'EXPAND'
    #eqbox = eqbox.column()
    diff = MAX - MIN
    for i in range(1, 11):
        pc = float(10.2 - i) / 10.0
        top = pc * diff
        row = eqbox.row()
        #row.alignment = 'LEFT'
        for j in range(start, end + 1):
            channel = "%s%d" % (channel_name, j)
            maxf = speaker['_RNA_UI'][channel]['b']
            minf = speaker['_RNA_UI'][channel]['a']
            fdiff = maxf - minf
            col = row.column()
            col.alignment = 'CENTER'
            if speaker.get(channel) > top:
                col.label("", icon='MESH_PLANE')
            elif maxf > top:
                col.label("", icon='CHECKBOX_DEHLT')

            else:
                col.label("", icon='BLANK1')


def setcontextspeakerENUM(self, context):
    return None
    #print("Change mode to %s"%self.vismode)
    #print(context.object)
    SoundVisMenu.vismode = self.vismode
    if context.object is None or context.object.type != "SPEAKER":
        #print("Not a speaker")
        return(None)
    speaker = context.object.data

    #print(len(drivers))
    if self.vismode == "DRIVERS":
        if speaker.animation_data is None:
            speaker.animation_data_create()

        drivers = speaker.animation_data.drivers
        if len(drivers) == 0:
            speaker["Driver0"] = 0.0
            driver = speaker.driver_add('["Driver0"]').driver
            bpy.types.SoundVisualiserPanel.driver_index = 0
            channel = "Channel0"
            var = driver.variables.new()
            var.type = "SINGLE_PROP"
            var.name = channel
            target = var.targets[0]
            target.id_type = "SPEAKER"
            target.id = speaker.id_data
            target.data_path = '["%s"]' % channel
            driver.expression = 'SoundDrive(%s)' % channel


def defaultPanels(regflag):
    if regflag:
        bpy.utils.register_class(DATA_PT_speaker)
        bpy.utils.register_class(DATA_PT_context_speaker)
        bpy.utils.register_class(DATA_PT_cone)
        bpy.utils.register_class(DATA_PT_distance)
        bpy.utils.register_class(DATA_PT_custom_props_speaker)
    else:
        bpy.utils.unregister_class(DATA_PT_speaker)
        bpy.utils.unregister_class(DATA_PT_context_speaker)
        bpy.utils.unregister_class(DATA_PT_cone)
        bpy.utils.unregister_class(DATA_PT_distance)
        bpy.utils.unregister_class(DATA_PT_custom_props_speaker)


def play_live(self, context):
    print("PLAY LIVE")
    print(self, dir(self))
    speakers = ModalTimerOperator.speakers
    print(speakers)
    if self.play:
        if self not in speakers:
            speakers.append(self)
    '''
    else:
        if self in speakers:
            #speakers.remove(self)
    '''
    return None


class ModalTimerOperator(bpy.types.Operator):
    '''Operator which runs its self from a timer.'''
    bl_idname = "wm.modal_timer_operator"
    bl_label = "Modal Timer Operator"

    _timer = None
    speakers = []

    def modal(self, context, event):
        if event.type == 'ESC':
            return self.cancel(context)

        if event.type == 'TIMER':
            #print(len(ModalTimerOperator.speakers))
            for speaker in ModalTimerOperator.speakers:
                speaker.vismode = speaker.vismode
        return {'PASS_THROUGH'}

    def execute(self, context):
        wm = context.window_manager
        wm.modal_handler_add(self)
        ModalTimerOperator.speakers = [speaker
                                       for speaker in bpy.data.speakers
                                       if speaker.play == True]

        self._timer = wm.event_timer_add(0.1, context.window)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        context.window_manager.event_timer_remove(self._timer)
        return {'CANCELLED'}


def mat_driver_fix(scene):
    frame = scene.frame_current
    fcurves = [fcurve for mat in bpy.data.materials
               if mat.animation_data
               for fcurve in mat.animation_data.drivers]
    for fcurve in fcurves:
        mat = fcurve.id_data
        attr = fcurve.data_path
        sp = attr.split(".")
        if len(sp) > 1:
            attr = sp.pop()
            mat = mat.path_resolve(".".join(sp))
        index = fcurve.array_index
        value = fcurve.evaluate(frame)
        ob = mat.path_resolve(attr)
        if type(ob).__name__ in ["Vector", "Color", "bpy_props_array"]:
            ob[index] = value
        else:
            setattr(mat, attr, value)


def toggle_driver_fix(self, context):
    print("HANDLER")
    handler = bpy.app.handlers.frame_change_post

    handlers = [f for f in handler if f.__name__ == "mat_driver_fix"]
    for f in handlers:
        handler.remove(f)
    if self.material_driver_fix:
        bpy.app.handlers.frame_change_post.append(mat_driver_fix)


class SoundToolSettings(PropertyGroup):
    material_driver_fix = BoolProperty(default=False, update=toggle_driver_fix,
                                      description="Make material drivers live")
    show_vis = BoolProperty(default=True, description="Show Visualiser")
    filter_object = BoolProperty(default=True,
                                 description="Filter Drivers by Objects")
    filter_context = BoolProperty(default=True,
                                  description="Filter Drivers by Context")
    filter_material = BoolProperty(default=True,
                                   description="Filter Drivers by Material")
    filter_monkey = BoolProperty(default=True,
                                 description="Filter Drivers by New (Monkeys)")
    filter_texture = BoolProperty(default=True,
                                  description="Filter Drivers by Texture")
    filter_world = BoolProperty(default=True,
                                description="Filter Drivers by World")
    filter_speaker = BoolProperty(default=True,
                                description="Filter Drivers by Speaker")
    context_speaker = StringProperty(default="None")


def speaker_channel_buffer(self, context):

    #b = bpy.app.driver_namespace.get("ST_buffer")
    h = bpy.app.driver_namespace.get("ST_handle")
    b = bpy.app.driver_namespace["ST_buffer"] = mix_buffer(context)
    if h:
        h.stop()
    print("BUFFFFFFFFER")
    return None

class SoundChannels(PropertyGroup):

    name = StringProperty(default="SoundChannels")
    buffered = BoolProperty(default=False, description="Buffered")
    valid_handle = BoolProperty(default=False, description="Has Valid Handle")
    action_name = StringProperty(default="SoundChannels")
    pass

for i in range(96):
    setattr(SoundChannels, "channel%02d" % i,
            BoolProperty(default=i==0, description="Channel %02d" % i, update=speaker_channel_buffer))


def dummy(self, context):
    return None


def register():
    defaultPanels(False)
    bpy.types.Scene.SoundToolsGUISettings =\
                BoolVectorProperty(name="GUI_Booleans",
                                   size=32,
                                   default=(False for i in range(0, 32)))

    bpy.types.Speaker.vismode = EnumProperty(items=(
                ("SOUND", "SOUND", "Edit sound properties"),
                ("OUT", "OUT", "Filter Output"),
                ("VISUAL", "VISUAL", "Show sound visualiser")
                ),
                name="SoundDriver",
                default="SOUND",
                description="Vis to display, driver to build a driver",
                options={'HIDDEN'},
                )

    '''
                ("DRIVERS", "DRIVERS", "Create Custom Driver(s)"),
                ("NLA", "NLA", "Lay Down Tracks in the NLA"),
                ("LIPSYNC", "LIPSYNC", "Add Lip sync to this wav")
    '''

    bpy.types.Action.vismode = EnumProperty(items=(
                ("SLIDER", "SLIDER", "Display as Sliders"),
                ("VERTICAL", "VERTICAL", "Show sound visualiser"),
                ("HORIZONTAL", "HORIZONTAL", "Create Custom Driver(s)")
                ),
                name="Visual Type",
                default="SLIDER",
                description="Visualisation Type",
                #update=setcontextspeakerENUM,
                options={'HIDDEN'},
                )

    bpy.types.Sound.type = EnumProperty(items=(
                ("SFX", "SFX", "Sound Effects"),
                ("MUSIC", "MUSIC", "Music"),
                ("VOICE", "VOICE", "Voice")
                ),
                name="type",
                default="SFX",
                description="Input Type",
                #update=setcontextspeakerENUM,
                )

    bpy.utils.register_class(SoundChannels)
    #BUGGY on SPEAKER object
    bpy.types.Scene.sound_channels = CollectionProperty(type=SoundChannels)

    bpy.types.Scene.play = BoolProperty("Play",
                default=True,
                description="Play Live",
                update=dummy)

    bpy.utils.register_class(SoundToolSettings)
    bpy.types.Scene.speaker_tool_settings = \
            PointerProperty(type=SoundToolSettings)

    bpy.types.Action.show_freq = BoolProperty(default=True)
    bpy.types.Scene.soundtool_op = None  # context.active_operator
    bpy.utils.register_class(ModalTimerOperator)
    bpy.utils.register_class(SPEAKER_OT_Visualise)
    bpy.utils.register_class(SoundVisualiserPanel)
    bpy.utils.register_class(SoundVisMenu)
    bpy.app.handlers.load_post.append(InitSoundTools)
    #InitSoundTools(bpy.context.scene)


def unregister():
    defaultPanels(True)
    bpy.utils.unregister_class(SoundChannels)
    bpy.utils.unregister_class(SPEAKER_OT_Visualise)
    bpy.utils.unregister_class(SoundVisualiserPanel)
    bpy.utils.unregister_class(SoundVisMenu)
    bpy.utils.unregister_class(ModalTimerOperator)
    bpy.utils.unregister_class(SoundToolSettings)

    bpy.app.handlers.load_post.remove(InitSoundTools)
