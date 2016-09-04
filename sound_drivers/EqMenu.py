'''
Slowly being taken out.... 

'''
import bpy
import re
from math import sqrt
from mathutils import Vector, Color, Euler, Quaternion
from random import random
from bpy.props import \
        StringProperty, IntProperty, EnumProperty, FloatProperty, \
        BoolVectorProperty, BoolProperty


from sound_drivers.sound_action import  SoundActionMenuRow

from sound_drivers.utils import \
        get_driver_settings, \
        icon_from_bpy_datapath, format_data_path, getAction, getSpeaker

from sound_drivers.filter_playback import setup_buffer, play_buffer,\
     mix_buffer, sound_buffer, remove_filter_handlers, setup_filter_handlers
# <pep8-80 compliant>


def dprint(str):
    DEBUG = False
    if bpy.app.debug or DEBUG:
        print(str)


def speaker_filter_sound(self, context):
    if not self.filter_sound:
        remove_filter_handlers()
        return
    # stop playback and go to frame 1
    screen = context.screen
    scene = context.scene
    filter_sound(self, self.animation_data.action, context)
    playing = screen.is_animation_playing
    if playing:
        #this will stop it
        bpy.ops.screen.animation_play()
    scene.frame_set(1)

    self.muted = self.filter_sound
    h = bpy.app.driver_namespace.get("ST_handle")
    if not self.filter_sound:
        if h and h.status:
            h.stop()
        return None

    b = bpy.app.driver_namespace.get("ST_buffer")
    if not b:
        if setup_buffer(context):
            b = bpy.app.driver_namespace["ST_buffer"] = mix_buffer(context)

    if not h:
        bpy.app.driver_namespace["ST_handle"] = play_buffer(b)
    if playing:
        #this will restart it
        bpy.ops.screen.animation_play()
    setup_filter_handlers()
    return None


def get_sound_channel(scene, name):
    sound_channel = scene.sound_channels.get(name)
    if not sound_channel:
        sound_channel = scene.sound_channels.add()
        sound_channel.name = name
    return sound_channel


def filter_sound(speaker, action, context):
    #print("FILTER SOUND", self.filter_sound)
    scene = context.scene

    name = "%s__@__%s" % (speaker.name, action.name)
    #speaker_filter_sound(speaker, context)
    if True:

        sound_channel = get_sound_channel(scene, name)
        if scene.use_preview_range:
            frame_start = scene.frame_preview_start
            frame_end = scene.frame_preview_end
        else:
            frame_start = scene.frame_start
            frame_end = scene.frame_end
        fs = max(action.frame_range.x, frame_start)
        # have to go back to start to enable effect
        #scene.frame_set(fs)

        '''
        for i in action["Channels"]
            ch = "channel%02d" % i
            if getattr(sound_channel, ch) != sw:
                setattr(sound_channel, ch, sw)
        '''


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




class ContextSpeakerMenu(bpy.types.Menu):
    bl_idname = "speaker.contextspeaker"
    bl_label = "Choose speaker to drive"
    driver = None

    def draw(self, context):
        layout = self.layout
        layout = layout.column(align=True)

        actions = [a for a in bpy.data.actions if 'wavfile' in a.keys()]
        speaker_dict = {}
        wf = [a["wavfile"] for a in actions]
        speakers = [s for s in bpy.data.speakers if "vismode" in s.keys()]

        for speaker in speakers:
            row = layout.row()
            row.label(speaker.name, icon='SPEAKER')
            row = layout.row()
            #row.separator()
            sp = speaker_dict.setdefault(speaker.name, {})
            sounds = [s for s in bpy.data.sounds if s.name in wf]
            for sound in sounds:
                row = layout.row()
                row.label(sound.name)
                sp[sound.name] = [a for a in actions
                                  if a["wavfile"] == sound.name]
                for a in sp[sound.name]:
                    '''
                    row = layout.row()
                    row.label(text=" ")
                    '''
                    text = "[%s] %s" % (a["channel_name"], a.name)
                    op = row.operator("soundaction.change", text=text)
                    op.action = a.name


def register():

    #bpy.utils.register_class(SimpleOperator)
    bpy.types.Speaker.filter_sound = BoolProperty(default=False,
                                                  update=speaker_filter_sound)
    #bpy.types.Scene.sync_play =  BoolProperty(default=False, update=sync_play)
    bpy.utils.register_class(ContextSpeakerSelectMenu)
    #bpy.utils.register_class(AddCustomSoundDriverToChannel)
    bpy.utils.register_class(ContextSpeakerMenu)
    ###bpy.utils.register_class(SoundToolPanel)


def unregister():
    #bpy.utils.unregister_class(SimpleOperator)
    #bpy.utils.unregister_class(AddCustomSoundDriverToChannel)
    bpy.utils.unregister_class(ContextSpeakerMenu)
    bpy.utils.unregister_class(ContextSpeakerSelectMenu)
    ###bpy.utils.unregister_class(SoundToolPanel)
