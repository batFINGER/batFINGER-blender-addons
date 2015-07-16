import bpy
import time
from bpy.types import PropertyGroup, Panel, Operator
from bpy.props import *
from math import log, sqrt
from mathutils import Vector

from speaker_tools.Equalizer import showFilterBox, action_normalise_set

from speaker_tools.utils import get_driver_settings,\
                icon_from_bpy_datapath, getSpeaker, getAction,\
                set_channel_idprop_rna, f, propfromtype,\
                get_channel_index, copy_sound_action, nla_drop,\
                validate_channel_name, unique_name, splittime,\
                get_context_area

from speaker_tools.presets import notes_enum, note_from_freq,\
                freq_ranges, shownote


class Sound():
    def __init__(self, sound):
        pass


class BakeSoundGUIPanel():
    action = None
    baking = False
    status = []  # status of each fcurve
    bakeoptions = None
    current = 0
    report = ""
    wait = 0

    def draw_fcurve_slider(self, context):
        layout = self.layout
        action = self.action
        channels = action["Channels"]
        row = layout.row()
        #row.scale_y = 0.5
        if action:
            cf = row.column_flow(columns=channels, align=True)
            cf.scale_y = 0.5
            for i in range(channels):
                fc = action.fcurves[i]
                if not fc.mute:
                    cf.prop(fc, "color", text="")

    def draw_current_fcurve_slider(self, context, i=0):
        channels = len(self.status)
        layout = self.layout
        action = self.action
        row = layout.row()
        if action:
            baked_channels = len([i for i in range(channels)
                                  if self.status[i]])
            pc = (baked_channels / channels)
            fc = action.fcurves[i]
            split = row.split(percentage=pc)
            split.prop(fc, "color", text="")
            split.scale_y = 0.5
            if self.wait:
                row = layout.row()
                tick = self.wait // 4
                if tick < 2:
                    row.label(str(pc), icon='INFO')
                else:
                    row.label(str(pc), icon='ERROR')


class SoundActionMethods:
    #icons = ['BLANK1', 'CHECKBOX_DEHLT', 'MESH_PLANE', 'ERROR']
    icons = ['BLANK1', 'CHECKBOX_DEHLT', 'MESH_PLANE', 'OUTLINER_OB_LATTICE']
    icontable = []

    def drawnormalise(self, context):
        layout = self.layout
        action = getAction(getSpeaker(context))
        row = layout.row(align=True)
        row.prop(action, "normalise", expand=True)
        sub = layout.row()
        sub.enabled = action.normalise != 'NONE'
        sub.prop(action, "normalise_range", text="", expand=True)
        return

    def nla_tracks(self, context):
        layout = self.layout
        speaker = getSpeaker(context)

        row = layout.row()
        if not getattr(speaker, "animation_data", None):
            row.label("NO ANITION DATA", icon='ERROR')
            return None
        row.prop(speaker.animation_data, "use_nla", toggle=True)
        if not speaker.animation_data.use_nla:
            return None
        for nla_track in speaker.animation_data.nla_tracks:
            # need to fix for only strips with soundactions.. for R'ON
            row = layout.row(align=True)
            for strip in nla_track.strips:
                action = strip.action
                sub = row.row()
                sub.alignment = 'LEFT'
                ch = strip.action["channel_name"]
                op = sub.operator("soundaction.change", text=ch)
                op.action = strip.action.name
                sub.enabled = action != speaker.animation_data.action

                #sub.label(strip.action["channel_name"])
                if not nla_track.mute:
                    icon = "MUTE_IPO_OFF"
                else:
                    icon = "MUTE_IPO_ON"
                row.prop(action, "normalise_range", text="", expand=True)
                row.prop(nla_track, "mute",  icon=icon,
                         text="", icon_only=True)

    def copy_action(self, context):
        speaker = getSpeaker(context)
        sound = speaker.sound
        bakeoptions = sound.bakeoptions
        scene = context.scene
        layout = self.layout
        row = layout.row(align=True)
        sub = row.row()
        sub.scale_x = 2
        op = sub.operator("soundaction.copy", text="Copy to Channel")

        row.prop(bakeoptions, "channel_name", text="")

        op.new_channel_name = bakeoptions.channel_name
        '''
        row = layout.row()
        op = row.operator("sound.bake_animation")
        row = layout.column()
        row.prop(scene, "sync_mode", expand=True)
        '''
        return

    def FCurveSliders(self, context):
        layout = self.layout
        speaker = getSpeaker(context)
        action = getAction(speaker)
        if not (action and speaker):
            return None

        channel_name = action["channel_name"]

        start = action["start"]
        end = action["end"]
        box = layout.box()
        #row  = box.row()
        #box.scale_y = 0.4
        cf = box.column_flow(columns=1)
        #cf.scale_y = action["row_height"]
        fcurves = action.fcurves
        for i in range(start, end + 1):
            channel = "%s%d" % (channel_name, i)
            v = speaker[channel]
            MIN = speaker["_RNA_UI"][channel]['min']
            MAX = speaker["_RNA_UI"][channel]['max']
            diff = MAX - MIN
            pc = 0.0
            if diff > 0.0000001:
                pc = (v - MIN) / diff
            #row = cf.row()
            #row.scale_y = action["row_height"]
            if pc < 0.00001:
                split = cf.split(percentage=0.0001)
                split.scale_y = action["row_height"]
                split.label("")
                continue
            split = cf.split(percentage=pc)
            split.scale_y = action["row_height"]
            split.prop(fcurves[i], "color", text="")
        row = box.row()
        row.scale_y = 0.2
        row.label(icon='BLANK1')

    def ColSliders(self, context):
        layout = self.layout
        speaker = getSpeaker(context)
        action = getAction(speaker)
        if not (action and speaker):
            return None

        channel_name = action["channel_name"]
        start = action["start"]
        end = action["end"]
        box = layout.box()
        #row  = box.row()
        #box.scale_y = 0.4
        cf = box.column()
        cf.scale_y = action["row_height"]
        for i in range(start, end + 1):
            channel = "%s%d" % (channel_name, i)
            cf.prop(speaker, '["%s"]' % channel, slider=True,
                       emboss=True, text="")

    def Sliders(self, context):
        layout = self.layout
        speaker = getSpeaker(context)
        action = getAction(speaker)
        if not (action and speaker):
            return None

        channel_name = action["channel_name"]
        start = action["start"]
        end = action["end"]
        box = layout.box()
        #row  = box.row()
        #box.scale_y = 0.4
        cf = box.column_flow(columns=1)
        cf.scale_y = action["row_height"]
        for i in range(start, end + 1):
            channel = "%s%d" % (channel_name, i)
            cf.prop(speaker, '["%s"]' % channel, slider=True,
                       emboss=True, text="")

    def EBT(self, context):
        layout = self.layout
        speaker = getSpeaker(context)
        action = getAction(speaker)
        # max and min of whole action

        def icon(ch, pc):
            cn = action["channel_name"]
            chi = "%s%d" % (cn, ch)
            mn = speaker['_RNA_UI'][chi]["min"]
            mx = speaker['_RNA_UI'][chi]["max"]
            vol_range = Vector((mx, mn)).magnitude
            mx = max(mn, mx)
            b = speaker['_RNA_UI'][chi]["b"]
            a = speaker['_RNA_UI'][chi]["a"]
            map_range = Vector((a, b)).magnitude
            v = map_range * abs(speaker[chi]) / vol_range

            o = 0  # no output
            if v >= vol_range * pc:
                o = 3
            elif  pc * vol_range < (abs(map_range)):
                o = 1
                #return 'CHECKBOX_DEHLT'
            return o

        # create a list channels x 10
        channels = action["Channels"]
        #row = layout.row()

        self.icontable = [[icon(j, (i + 1) / 20.0)
                           for i in range(20)]
                          for j in range(channels)]
        for l in self.icontable:
            i = l.count(3)
            if i:
                l[i - 1] = 2
        '''
        # horizontal
        cf = self.column_flow(columns=10, align=True)
        cf.scale_y = 0.4
        for i in range(10):
            for j in range(channels):
                cf.label(text='', icon=icontable[j][i])
        '''
        row = layout.box()
        row.scale_x = 0.5

        #row = row.row()
        cf = row.column_flow(columns=channels + 1)
        cf.scale_y = action["row_height"]
        cf.scale_x = action["row_height"]

        for j in range(channels + 1):
            if j == channels:
                for i in range(19, -1, -1):
                    cf.label("")
                continue
            for i in range(19, -1, -1):
                #col.label(text='', icon=self.icons[self.icontable[j][i]])
                cf.label(text='', icon=self.icons[self.icontable[j][i]])


class SoundPanel(Panel):
    bl_label = "Sound"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"
    #Open this one to see the big OPEN SOUND button
    #bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        speaker = getSpeaker(context)

        return (speaker and 'SOUND' in speaker.vismode)

    def draw_header(self, context):
        layout = self.layout
        layout.label("", icon='SOUND')

    def draw(self, context):
        layout = self.layout
        layout.enabled = not BakeSoundPanel.baking
        # get speaker returns the PROPERTIES PANEL speaker
        speaker = getSpeaker(context)
        # refactored code
        box = layout
        has_sound = (speaker.sound is not None)
        if not has_sound:
            row = box.row()
            row.template_ID(speaker, "sound", open="sound.open_mono")
            return

        row = box.row(align=True)

        if 'SOUND' in speaker.vismode:
            soundbox = box.box()
            row = soundbox.row(align=True)
            row.template_ID(speaker, "sound", open="sound.open_mono")
            sub = row.row()
            sub.alignment = 'RIGHT'
            sub.prop(speaker, "muted", text="")
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


class SoundVisualiserPanel(SoundActionMethods, Panel):
    bl_label = "Visualiser"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"
    #bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):

        speaker = getSpeaker(context)

        return (speaker and 'VISUAL'
                in speaker.vismode)

    def draw_header(self, context):
        layout = self.layout
        speaker = getSpeaker(context)
        action = getAction(speaker)
        if not action:
            layout.label("", icon='SEQ_HISTOGRAM')
            return

        op = layout.operator("action.visualiser", icon='SEQ_HISTOGRAM',
                             emboss=False, text="")
        op.action_name = action.name

    def draw(self, context):
        layout = self.layout
        layout.enabled = not BakeSoundPanel.baking
        speaker = getSpeaker(context)
        action = getAction(speaker)

        #checks
        if speaker.sound is None:
            layout.label("Speaker has No Sound", icon='INFO')
            return
        if action is None:
            layout.label("No Action Baked", icon='INFO')
            return
        elif action is None:
            layout.label("No Action Baked", icon='INFO')
            return
        elif action['wavfile'] != speaker.sound.name:
            layout.label("No Action Baked", icon='INFO')
            layout.label("for %s" % speaker.sound.name)
            return
        '''
        layout.label(repr(action))
        if action:
            layout.label(action['wavfile'])

        '''
        if not BakeSoundPanel.baking:
            if action.vismode == 'SLIDER':
                self.Sliders(context)
            elif action.vismode == 'FCURVE':
                self.FCurveSliders(context)
            elif action.vismode == 'VERTICAL':
                self.EBT(context)

            #self.ColSliders(context)


class SoundActionPanel(SoundActionMethods, Panel):
    bl_label = "Sound Action"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"
    #bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        speaker = getSpeaker(context)
        action = getAction(speaker)

        return (speaker and action\
                and 'ACTION' in speaker.vismode)

    def SoundActionMenu(self, context, speaker=None,
                        action=None, has_sound=True):
        speaker = getSpeaker(context)
        action = getAction(speaker)
        if action is None:
            layout.label("NO ACTION", icon='INFO')
            return
        layout = self.layout
        channel_name = action["channel_name"]
        row = layout.row(align=True)
        if has_sound:
            sub = row.row()
            sub.alignment = 'LEFT'
            #col.alignment = 'LEFT'
            sub.menu("soundtest.menu", text=channel_name)
            #sub = row.row()
            row.prop(action, "name", text="")
            sub = row.row()
            sub.alignment = 'RIGHT'
            sub.prop(action, "use_fake_user",
                       toggle=True, text="F")

    def draw_header(self, context):
        layout = self.layout
        layout.label("", icon='ACTION')

    def draw(self, context):
        layout = self.layout
        layout.enabled = not BakeSoundPanel.baking
        speaker = getSpeaker(context)
        action = getAction(speaker)
        self.SoundActionMenu(context)

        row = layout.row(align=True)
        self.drawnormalise(context)
        self.copy_action(context)
        row = layout.row()
        row.operator("soundaction.unbake")


class SoundNLAPanel(SoundActionMethods, Panel):
    bl_label = "NLA Mixer Panel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"
    #bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        speaker = getSpeaker(context)

        return (speaker
                and hasattr(speaker, "animation_data")
                and 'NLA' in speaker.vismode)

    def draw_header(self, context):
        layout = self.layout
        layout.label("", icon='NLA')

    def draw(self, context):
        layout = self.layout
        layout.enabled = not BakeSoundPanel.baking
        self.nla_tracks(context)


class FilterSoundPanel(Panel):
    bl_label = "Filter Sound"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        speaker = getSpeaker(context)

        return (speaker and 'OUT' in speaker.vismode)

    def draw_header(self, context):
        layout = self.layout
        layout.label("", icon='FILTER')

    def draw(self, context):
        layout = self.layout
        layout.enabled = not BakeSoundPanel.baking
        speaker = getSpeaker(context)
        action = getAction(speaker)
        showFilterBox(layout, context, speaker, action)


class BakeSoundPanel(BakeSoundGUIPanel, Panel):
    bl_label = "Bake Panel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"
    #bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        speaker = getSpeaker(context)
        if speaker is not None and 'BAKE' in speaker.vismode:
            return True

        return False

    def draw_freqs(self, layout, bakeoptions):
        if bakeoptions.sound_type == 'MUSIC':
            layout.label('Note Range (From-To)', icon='SOUND')
            box = layout.box()
            row = box.row()
            row.prop(bakeoptions, "music_start_note", text="")
            row.prop(bakeoptions, "music_end_note", text="")
        else:
            layout.label("Frequencies")
            row = layout.row()
            cbox = row.box()
            crow = cbox.row(align=True)
            sub = crow.row()
            sub.alignment = 'LEFT'
            sub.prop(bakeoptions, "auto_adjust", text="", icon='AUTO')
            crow.prop(bakeoptions, "minf", text="")
            crow.prop(bakeoptions, "maxf", text="")
            sub = crow.row()
            sub.alignment = 'RIGHT'
            sub.scale_x = 0.5
            sub.prop(bakeoptions, "use_log", toggle=True, text="LOG")

    def draw_header(self, context):
        layout = self.layout
        layout.label("", icon='FCURVE')

    def draw(self, context):
        space = context.space_data
        layout = self.layout

        if space.use_pin_id:
            speaker = space.pin_id
            # check not pinned in speaker context.
            if hasattr(speaker, "type"):
                speaker = speaker.data
        else:
            speaker = context.object.data
        sound = speaker.sound
        if sound is None:
            row = layout.row()
            row.label("No Sound to Bake", icon='INFO')
            return None

        scene = context.scene

        bakeoptions = sound.bakeoptions
        bake_operator = bakeoptions.bake_operator

        # Settings for bake sound to fcurve Operator
        op = layout.operator("wm.bake_sound_to_action", text="BAKE",
                             icon='FCURVE')
        op.sound_name = sound.name
        op.speaker_name = speaker.name

        ### TEST FOR SQUIZ
        action = None
        channels = 0
        if speaker.animation_data:
            action = speaker.animation_data.action
            if action is not None:
                channels = action["Channels"]

        if self.baking:
            if channels > 24:
                i = getattr(self, "channel", 0)
                self.draw_current_fcurve_slider(context, i=i)
            else:
                self.draw_fcurve_slider(context)
            row = layout.row(align=False)
            row.label(BakeSoundPanel.report)
            row = layout.row(align=False)
            #row.column_flow(columns=10, align=True)
            if action:
                box = layout.box()
                #box.scale_y = 0.5
                for i in range(bakeoptions.channels):
                    c = i % 10
                    r = i // 10
                    if not c:
                        #row = layout.row(align=True)
                        row = box.row()
                        row.scale_y = 0.5

                        cf = row.column_flow(columns=11, align=False)
                        cf.scale_y = 0.5
                        #cf.alignment = 'RIGHT'
                        #cols = [row.column() for i in range(9)]

                    '''
                    if not c:
                        row = layout.row()
                        row.column_flow(columns=10, align=True)
                    '''

                    lb = cf.column()
                    status = self.status[i]
                    if not status:
                        lb.label(text="", icon='CHECKBOX_DEHLT')
                    elif status == 1:
                        lb.label(text="", icon='MESH_PLANE')
                    elif status == 99:
                        lb.label(text="", icon='ERROR')

            row = box.row()
            row.scale_y = 2
            row = layout.row(align=True)
            row.prop(bakeoptions, "minf")
            row.prop(bakeoptions, "maxf")

            return

        #row.operator(self.bl_idname).preset = "FOOBAR"
        row = layout.row()
        row.prop(bakeoptions, "show_graph_editor", toggle=True, emboss=True)
        '''
        preset_box = row.box()
        row = preset_box.row()
        if len(bakeoptions.preset) == 0:
            txt = "Select Preset"
        else:
            txt = bakeoptions.preset
        row.menu("speaker.preset_menu", text=txt)
        row = preset_box.row()
        #row.prop(bakeoptions, "save_preset")
        preset_row = preset_box.row()
        preset_row.prop(bakeoptions, "preset")
        row = layout.row()
        row.menu("sound.music_notes")
        '''
        row = layout.row()
        row.label("Action (%s)" % sound.name, icon='ACTION')
        abox = layout.box()
        arow = abox.row(align=True)
        arow.prop(bakeoptions, "sound_type", text="")
        arow.prop(bakeoptions, "action_name", text="")
        '''
        #type will be moved from sound to bake type.
        row = layout.row()
        row.prop(sound, "type", text=sound.type)
        '''

        row = layout.row()
        if not validate_channel_name(context):
            row.label("Channel in USE or INVALID", icon='ERROR')
            row.alert = True
            row = layout.row()

        #col.scale_x = row.scale_y = 2

        row.label("Channel")
        row = layout.row()
        box = row.box()
        #col.scale_x = row.scale_y = 2
        brow = box.row(align=True)
        brow.prop(bakeoptions, "channel_name", text="Name")
        sub = brow.row()
        sub.prop(bakeoptions, "channels", text="")
        sub.enabled = bakeoptions.sound_type != 'MUSIC'
        row = layout.row()

        self.draw_freqs(layout, bakeoptions)
        row = layout.row()

        row.label("Bake Sound to F-Curves", icon='IPO')
        box = layout.box()
        #box.operator("graph.sound_bake", icon='IPO')
        box.prop(bake_operator, "threshold")
        box.prop(bake_operator, "release")
        box.prop(bake_operator, 'attack')
        box.prop(bake_operator, "use_additive", icon="PLUS")
        box.prop(bake_operator, "use_accumulate", icon="PLUS")

        row = box.row()

        split = row.split(percentage=0.20)
        split.prop(bake_operator, "use_square")
        split.prop(bake_operator, "sthreshold")
        #layout.prop(self, "TOL")


class SoundVisMenu(bpy.types.Menu):
    bl_idname = "soundtest.menu"
    bl_label = "Select a Sound"
    vismode = 'VISUAL'

    def draw(self, context):
        speaker = context.scene.speaker
        #if SoundVisMenu.vismode in ["VISUAL", "SOUND", "DRIVERS"]:
        if True:
            actions = [action for action in bpy.data.actions
                       if "wavfile" in action
                       and action["wavfile"] == speaker.sound.name]

            for action in actions:
                op = self.layout.operator("soundaction.change",
                          text="%s %s"\
                          % (action["channel_name"], action.name))
                op.action = action.name


class VisualiserOptions(bpy.types.Operator):
    """Visualiser Options"""
    bl_idname = "action.visualiser"
    bl_label = "Visualiser Options"
    action_name = StringProperty(default="", options={'SKIP_SAVE'})

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_popup(self, width=200)

    def execute(self, context):
        return {'FINISHED'}
        pass

    def draw(self, context):
        action = bpy.data.actions.get(self.action_name)
        layout = self.layout
        layout.label("Visualiser Settings", icon='SEQ_HISTOGRAM')
        col = layout.column()
        col.prop(action, "vismode", expand=True)
        row = layout.row(align=True)
        sub = row.row()
        sub.alignment = 'LEFT'
        sub.label("", icon='NLA')
        col = row.row()
        col.prop(action, '["row_height"]', text="h", slider=True)
        col = layout.row()
        col.prop(action, '["start"]', text="Start", slider=True)
        col.prop(action, '["end"]', text="  End", slider=True)


class ChangeSoundAction(Operator):
    """Load Action"""
    bl_idname = "soundaction.change"
    bl_label = "Load Action"
    action = StringProperty(default="")

    def execute(self, context):
        speaker = context.scene.speaker
        if not speaker:
            return {'CANCELLED'}
        soundaction = bpy.data.actions.get(self.action)
        if soundaction is not None:
            SoundVisMenu.bl_label = soundaction["channel_name"]
            speaker.animation_data.action = soundaction
            action_normalise_set(soundaction, context)

        dm = bpy.app.driver_namespace['DriverManager']
        if dm is not None:
            dm.set_edit_driver_gui(context)
        return {'FINISHED'}


class CopySoundAction(bpy.types.Operator):
    """Copy Action with new channel name"""
    bl_idname = "soundaction.copy"
    bl_label = "Action Copy"
    new_channel_name = StringProperty(default="AA")
    nla_drop = BoolProperty(default=True)

    @classmethod
    def poll(cls, context):
        return (context.active_object is not None
                and validate_channel_name(context))

    def execute(self, context):
        speaker = getSpeaker(context)
        original_action = speaker.animation_data.action
        newaction = copy_sound_action(speaker, self.new_channel_name)

        if newaction is not None:
            speaker.animation_data.action = newaction
            speaker.sound.bakeoptions.channel_name =\
                    unique_name(speaker.channels, self.new_channel_name)

            if self.nla_drop:
                # need to override context to use.. cbf'd
                nla_drop(speaker, newaction, 1, self.new_channel_name)
            return {'FINISHED'}

        return {'CANCELLED'}


class UnbakeSoundAction(Operator):
    bl_idname = 'soundaction.unbake'
    bl_label = 'unBake to Action'
    bl_description = 'Resample baked f-curve to a new Action / f-curve'
    bl_options = {'UNDO'}


    @classmethod
    def poll(cls, context):
        return getSpeaker(context) is not None


    def execute(self, context):
        obj = context.object.data
        old_action = obj.animation_data.action
        name = old_action.name

        pts = [(c.sampled_points, c.data_path, c.array_index) for c in obj.animation_data.action.fcurves if c.sampled_points]
        if pts:
            keys = old_action.copy()
            for f in keys.fcurves:
                keys.fcurves.remove(f)
            for sam, dat, ind in pts:
                fcu = keys.fcurves.new(data_path=dat, index=ind)
                
                fcu.keyframe_points.add(len(sam))
                for i in range(len(sam)):
                    w = fcu.keyframe_points[i]
                    w.co = w.handle_left = w.handle_right = sam[i].co
            obj.animation_data.action = keys
            # replace in nla
            strips = [s for t in obj.animation_data.nla_tracks for s in t.strips if s.action == old_action]
            for s in strips:
                s.action = keys
            bpy.data.actions.remove(old_action)
            keys.name = name
        return{'FINISHED'}


class BakeSoundAction(Operator):
    """Bake Multiple Sound Frequencies to Action"""
    bl_idname = "wm.bake_sound_to_action"
    bl_label = "Bake Sound"
    bl_options = {'INTERNAL'}

    _timer = None
    speaker_name = StringProperty(name="Speaker", default="Speaker")
    sound_name = StringProperty(name="Speaker", default="Sound")
    count = 0
    channels = 0
    fp = None
    c = {}
    context_override = False
    baking = False
    baked = False
    sound = None
    speaker = None
    graph = None
    view3d = None
    change_last = False
    bakeorder = []
    bake_times = []
    retries = []  # add channel here if it has no range.

    @classmethod
    def poll(cls, context):
        
        if context.space_data.pin_id is not None and context.space_data.pin_id != context.scene.objects.active.data:
            return False
        return validate_channel_name(context)

    def channel_range(self):
        bakeoptions = self.sound.bakeoptions

        # get the channel
        channel = self.bakeorder[self.count]
        channels = bakeoptions.channels
        if bakeoptions.sound_type == 'MUSIC':
            return freq_ranges(bakeoptions.music_start_note,\
                               bakeoptions.music_end_note)[channel]

        if bakeoptions.use_log:
            # 0Hz is silence? shouldn't get thru trap anyway
            if bakeoptions.minf == 0:
                bakeoptions.minf = 1
            LOW = log(bakeoptions.minf, bakeoptions.log_base)
            HIGH = log(bakeoptions.maxf, bakeoptions.log_base)
            RANGE = HIGH - LOW
            low = LOW + (channel) * RANGE / channels
            high = LOW + (channel + 1) * RANGE / channels
            low = bakeoptions.log_base ** low
            high = bakeoptions.log_base ** high

        else:
            LOW = bakeoptions.minf
            HIGH = bakeoptions.maxf
            RANGE = HIGH - LOW
            low = LOW + (channel) * RANGE / channels
            high = LOW + (channel + 1) * RANGE / channels

        return (low, high)

    def modal(self, context, event):
        BakeSoundPanel.baking = True

        bakeoptions = self.sound.bakeoptions
        channels = bakeoptions.channels
        bake_operator = bakeoptions.bake_operator
        sound = self.sound
        speaker = self.speaker
        action = speaker.animation_data.action

        if event.type == 'ESC' or not BakeSoundPanel.baking:
            self.clean()
            return self.cancel(context)

        if BakeSoundPanel.wait > 0:
            BakeSoundPanel.wait -= 1
            return {'PASS_THROUGH'}

        if  self.count >= bakeoptions.channels:
            # Success do PostPro
            # return {'PASS_THROUGH'}
            return self.finished(context)

        if self.baking:
            return {'PASS_THROUGH'}

        if event.type == 'TIMER':
            if self.baking:
                return
            #context.scene.frame_set(1)
            self.baking = True
            fc = action.fcurves[self.bakeorder[self.count]]

            channel = self.bakeorder[self.count]
            setattr(BakeSoundPanel, "channel", channel)
            BakeSoundPanel.report = "[%s%d]" % (bakeoptions.channel_name,
                                                      channel)

            fc.select = True
            #FIXME FIXME FIXME
            fp = bpy.path.abspath(sound.filepath)
            low, high = self.channel_range()
            if not self.context_override or not self.graph:
                context.area.type = 'GRAPH_EDITOR'
                context.area.spaces.active.mode = 'FCURVES'
                self.c = context.copy()

            context.scene.frame_set(1)
            #context.area.type = 'GRAPH_EDITOR'

            t0 = time.clock()
            try:
                #x = bpy.ops.graph.sound_bake(

                x = bpy.ops.graph.sound_bake(self.c,
                             filepath=fp,
                             low=low,
                             high=high,
                             attack=bake_operator.attack,
                             release=bake_operator.release,
                             threshold=bake_operator.threshold,
                             use_accumulate=bake_operator.use_accumulate,
                             use_additive=bake_operator.use_additive,
                             use_square=bake_operator.use_square,
                             sthreshold=bake_operator.sthreshold)
            except:
                print("ERROR IN BAKE OP")
                '''
                for k in self.c.keys():
                    print(k, ":", self.c[k])

                '''
                return self.cancel(context)

            if self.graph:
                bpy.ops.graph.view_all(self.c)

            context.area.type = 'PROPERTIES'
            t1 = time.clock()
            self.bake_times.append(t1 - t0)

            fc_range, points = fc.minmax
            vol_range = abs(fc_range[1] - fc_range[0])
            # FIXME make retry count an addon var.
            if self.retries.count(channel) > channels // 5:
                print("TOO MANY RETRIES")
                self.clean()
                return self.cancel(context)
            if bakeoptions.auto_adjust\
                and (vol_range < 0.0001 or vol_range > 1e10):
                print("NO RANGE", vol_range)
                self.retries.append(channel)
                BakeSoundPanel.status[channel] = 99
                if channel == 0:
                    BakeSoundPanel.report = "[%s%d] NO Lo RANGE.. adjusting" \
                    % (bakeoptions.channel_name, channel)
                    bakeoptions.minf = high
                elif channel == (bakeoptions.channels - 1):
                    BakeSoundPanel.report = "[%s%d] NO Hi RANGE .. adjusting" \
                                       % (bakeoptions.channel_name, channel)
                    self.change_last == True
                    bakeoptions.maxf = low
                else:
                    BakeSoundPanel.wait = 20  # wait 2 seconds to continue
                    BakeSoundPanel.report = "[%s%d] NO Mid RANGE\
                            .. continuing" % (bakeoptions.channel_name,\
                                                      channel)
                    self.count += 1
                #need to set count down one
            else:
                BakeSoundPanel.status[channel] = 1
                # set up the rna
                rna = speaker["_RNA_UI"]
                channel_name = "%s%d" % (bakeoptions.channel_name, channel)

                is_music = bakeoptions.sound_type == 'MUSIC'
                set_channel_idprop_rna(channel_name,
                                       rna,
                                       low,
                                       high,
                                       fc_range,
                                       fc_range,
                                       is_music=is_music)

                print("%4s %8s %8s %10.4f %10.4f" %\
                          (channel_name,\
                           f(low),\
                           f(high),\
                           fc_range[0],\
                           fc_range[1]),\
                           end="")
                print(" %02d:%02d:%02d" % (splittime(t1 - t0)))
                BakeSoundPanel.report = rna[channel_name]["description"]\
                        .replace("Frequency", "")
                if channel == (bakeoptions.channels - 1)\
                        and self.change_last:
                    self.change_last = False
                    action.fcurves[0].mute = True
                    bakeorder[0], bakeorder[channels - 1] =\
                            bakeorder[channels - 1], bakeorder[0]
                    # need to swap n clear first fcurve
                    # mute the first fcurve
                _min, _max = fc_range
                if _min < action["min"]:
                    action["min"] = _min
                if _max > action["max"]:
                    action["max"] = _max
                self.count += 1

            fc.mute = not bool(BakeSoundPanel.status[channel])
            fc.select = False
            self.baking = False
            self.baked = True

        return {'PASS_THROUGH'}

    def execute(self, context):
        self.speaker = bpy.data.speakers.get(self.speaker_name)
        self.c = context.copy()
        self.first_baked = False
        self.last_baked = False
        self.sound = bpy.data.sounds.get(self.sound_name)
        if not (self.sound and self.speaker):
            return {'CANCELLED'}
        bakeoptions = self.sound.bakeoptions
        self.retries = []

        if bakeoptions.show_graph_editor:
            self.view3d = get_context_area(context, {}, 'VIEW_3D',
                                  context_screen=True)
            if self.view3d is not None:
                self.view3d.type = 'GRAPH_EDITOR'

        self.graph = get_context_area(context,
                              self.c,
                              'GRAPH_EDITOR',
                              context_screen=bakeoptions.show_graph_editor)

        self.context_override = self.graph is not None\
                and self.graph.spaces.active.mode != 'DRIVERS'

        if "_RNA_UI" not in self.speaker.keys():
            self.speaker["_RNA_UI"] = dict()

        context.scene.frame_set(1)
        channels = bakeoptions.channels

        # Create the action # might move this to see if one channel baked
        current_action = None
        if not self.speaker.animation_data:
            self.speaker.animation_data_create()
        elif self.speaker.animation_data.action:
            current_action = self.speaker.animation_data.action

        action = bpy.data.actions.new(bakeoptions.action_name)
        if current_action:
            #take some settings from last baked
            action.vismode = current_action.vismode

        action["Channels"] = channels
        action["channel_name"] = bakeoptions.channel_name
        action["minf"] = bakeoptions.minf
        action["maxf"] = bakeoptions.maxf
        action["use_log"] = bakeoptions.use_log
        action["wavfile"] = self.sound.name
        action["min"] = 1000000
        action["max"] = -1000000
        action["start"] = 0
        action["end"] = channels - 1

        #keep some UI stuff here too like the row height of each channel

        # use 0.4 as a default value
        action["row_height"] = 0.4
        action_rna = {}
        action_rna["row_height"] = {"min": 0.001,
                                    "max": 1.0,
                                    "description": "Alter the row height",
                                    "soft_min": 0.0,
                                    "soft_max": 1.0}
        action_rna["start"] = {"min": 0,
                               "max": 1.0,
                               "description": "Clip Start",
                               "soft_min": 0,
                               "soft_max": channels - 1}
        action_rna["end"] = {"min": 1,
                             "max": channels - 1,
                             "description": "Clip End",
                             "soft_min": 1,
                             "soft_max": channels - 1}

        action["_RNA_UI"] = action_rna
        #action["rna"] = str(action_rna)
        # set up the fcurves
        BakeSoundPanel.action = action
        BakeSoundPanel.wait = 0
        BakeSoundPanel.status = [0 for i in range(channels)]
        for i in range(channels):
            p = "%s%d" % (bakeoptions.channel_name, i)
            self.speaker[p] = 0.0
            fc = action.fcurves.new('["%s"]' % p)
            fc.select = False
            fc.mute = True

        bakeorder = [i for i in range(channels)]
        if channels > 1:
            bakeorder[1], bakeorder[channels - 1] = bakeorder[channels - 1],\
                                                    bakeorder[1]
        self.bakeorder = bakeorder

        self.speaker.animation_data.action = action
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, context.window)
        context.window_manager.modal_handler_add(self)
        self.wait = 30
        #print("RUNNING MODALO")
        print("-" * 80)
        print("BAKING %s to action %s" % (self.sound.name, action.name))
        print("-" * 80)
        return {'RUNNING_MODAL'}

    def finished(self, context):
        # return to view3d
        if self.view3d is not None:
            self.view3d.type = 'VIEW_3D'
        print("TOTAL BAKE TIME: %02d:%02d:%02d" %
                  splittime(sum(self.bake_times)))
        BakeSoundPanel.report = "Finished Baking"
        context.area.header_text_set()
        # set up the rnas
        sp = self.speaker
        sound = self.sound
        action = sp.animation_data.action
        bakeoptions = sound.bakeoptions
        boo = bakeoptions.bake_operator
        # save non defaults to an ID prop.

        action['boo'] = bakeoptions.sound_type

        action['_RNA_UI']['boo'] = dict(boo.items())

        channel_name = action['channel_name']
        vcns = ["%s%d" % (channel_name, i) for i in
                range(bakeoptions.channels)]

        sp_rna = {k: sp['_RNA_UI'][k].to_dict()
                  for k in sp['_RNA_UI'].keys()
                  if k in vcns}

        action['rna'] = str(sp_rna)

        context.window_manager.event_timer_remove(self._timer)
        BakeSoundPanel.baking = False
        # drop the action into the NLA
        nla_drop(sp, action, 1, channel_name)
        # normalise to action. This will set the
        action.normalise = 'ACTION'
        bakeoptions.channel_name = unique_name(sp.channels, channel_name)
        if context.scene.speaker is None:
            sp.is_context_speaker = True
        return {'FINISHED'}

    def clean(self):
        speaker = self.speaker
        action = speaker.animation_data.action
        if action:
            speaker.animation_data.action = None
            bpy.data.actions.remove(action)

    def cancel(self, context):
        if self.view3d is not None:
            self.view3d.type = 'VIEW_3D'

        BakeSoundPanel.report = "User Cancelled Cleaning..."
        BakeSoundPanel.baking = False
        context.area.header_text_set()
        context.window_manager.event_timer_remove(self._timer)
        return {'CANCELLED'}


def get_dm():
    dns = bpy.app.driver_namespace
    dm = dns.get("DriverManager")
    return dm



def register():
    bakeop = bpy.types.GRAPH_OT_sound_bake
    propdic = {}
    propfromtype(propdic, bakeop)
    bakeprops = type("BakeFCProperties", (PropertyGroup,), propdic)

    bpy.utils.register_class(bakeprops)
    propdic = {}
    sound_type = EnumProperty(items=(
                ("SOUND", "SOUND", "Basic Sound"),
                ("SFX", "SFX", "Sound Effects"),
                ("MUSIC", "MUSIC", "Music"),
                ("VOICE", "VOICE", "Voice")
                ),
                name="type",
                default="SOUND",
                description="Input Type",
                update=shownote
                )
    propdic["sound_type"] = sound_type

    propdic["preset"] = StringProperty(name="Preset",
                            default="",
                            #update=test,
                            options={'SKIP_SAVE'},
                            description="Save Preset")

    propdic["action_name"] = StringProperty(name="Action Name",
                                            default="SoundAction")

    propdic["channel_name"] = StringProperty(name="Channel Name",
                                             default="AA",
                              description="Limit Name to two Uppercase chars")

    propdic["channels"] = IntProperty(name="Channels",
                           default=16,
                           description="Number of frequencies to split",
                           min=1,
                           max=1000)
    propdic["minf"] = FloatProperty(name="Min Freq",
                         default=4.0,
                         description="Minimum Freq",
                         min=0,
                         max=10000.0)
    propdic["maxf"] = FloatProperty(name="Max Freq",
                         default=10000.0,
                         description="Maximum Freq",
                         min=100.0,
                         max=1000000.0)

    propdic["use_log"] = BoolProperty(name="Log Scale",
                           default=True,
                           description="Use Log scale for channels")

    propdic["show_graph_editor"] = BoolProperty(name="3DView to Graph",
           description="Change 3D view to Graph Editor to visualise bake",\
           default=True)
    propdic["music_start_note"] = notes_enum
    propdic["music_end_note"] = notes_enum

    # doh.. this is useless.
    propdic["log_base"] = IntProperty(name="log_base",
                           default=2,
                           description="log base to use",
                           min=2,
                           soft_min=2,
                           soft_max=32,
                           max=64)
    txt = "Automatically adjust end ranges for nill bake data"
    propdic["auto_adjust"] = BoolProperty(default=True, description=txt)

    propdic["bake_operator"] = PointerProperty(type=bakeprops)

    bakeoptions = type("BakeOptions", (PropertyGroup,), propdic)
    #Menus
    bpy.utils.register_class(SoundVisMenu)

    # Operators
    bpy.utils.register_class(bakeoptions)
    bpy.utils.register_class(ChangeSoundAction)
    bpy.utils.register_class(CopySoundAction)
    bpy.utils.register_class(BakeSoundAction)
    bpy.utils.register_class(UnbakeSoundAction)
    bpy.utils.register_class(VisualiserOptions)

    bpy.types.Sound.bakeoptions = PointerProperty(type=bakeoptions)
    # Panels
    bpy.utils.register_class(SoundPanel)
    bpy.utils.register_class(SoundVisualiserPanel)
    bpy.utils.register_class(SoundActionPanel)
    bpy.utils.register_class(SoundNLAPanel)
    bpy.utils.register_class(FilterSoundPanel)
    bpy.utils.register_class(BakeSoundPanel)


def unregister():
    bpy.utils.unregister_class(SoundVisMenu)
    bpy.utils.unregister_class(ChangeSoundAction)
    bpy.utils.unregister_class(BakeSoundAction)
    bpy.utils.unregister_class(UnbakeSoundAction)
    bpy.utils.unregister_class(SoundPanel)
    bpy.utils.unregister_class(SoundVisualiserPanel)
    bpy.utils.unregister_class(VisualiserOptions)
    bpy.utils.unregister_class(SoundActionPanel)
    bpy.utils.unregister_class(SoundNLAPanel)
    bpy.utils.unregister_class(FilterSoundPanel)
    bpy.utils.unregister_class(BakeSoundPanel)
    bpy.utils.unregister_class(CopySoundAction)
