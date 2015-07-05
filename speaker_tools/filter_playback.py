# <pep8-80 compliant>
import bpy
import aud

from bpy.props import BoolProperty
from speaker_tools.utils import getAction

bpy.types.Speaker.play_speaker = BoolProperty(default=False)

DBG = False


def dprint(str):
    global DBG
    if DBG:
        print(str)


def playspeaker(name, volume=1.0, limit=[], highpass=None, lowpass=None):
    speaker_obj = bpy.data.objects.get(name)
    if not speaker_obj:
        dprint("No speaker object named %s" % name)
        return 0.0
    speaker = speaker_obj.data
    on = speaker.filter_sound
    if on:
        device = aud.device()
        #load the factory
        dprint("-" * 80)
        dprint("playing %s" % speaker.sound.filepath)
        dprint("-" * 80)
        dprint("limit %s" % str(limit))
        dprint("lowpass %s" % str(lowpass))
        dprint("highpass %s" % str(highpass))
        f = speaker.sound.factory
        #f = aud.Factory(speaker.sound.filepath)
        if len(limit):
            f = f.limit(limit[0], limit[1])
        if lowpass is not None:
            f = f.highpass(highpass)
        if highpass is not None:
            f = f.highpass(highpass)
        #apply the
        device.play(f)
    else:
        dprint('speaker.on = False')

#use console for test call
'''
Set the speaker to on to test..
in console
>>> C.object.data.on
False

>>> C.object.data.on = True

>>> ps = bpy.app.driver_namespace['ST_play_speaker']
>>> ps("Speaker")
------------------------------------------------------------------------------
playing C:\blender_test\audio\batman.wav
------------------------------------------------------------------------------
limit []
lowpass None
highpass None
'''
bpy.app.driver_namespace["ST_play_speaker"] = playspeaker
soundeffects = {}
soundeffects["Speaker"] = {1: {"limit": [], "low": 135, "high": 208},
                           200: {"limit": [], "low": None, "high": None}
                           }
ps = bpy.app.driver_namespace['ST_play_speaker']


def ST__filter_playback(scene):

    context = bpy.context
    device = aud.device()
    if not context:
        return None
    screen = context.screen
    if not screen.is_animation_playing:
        device.stopAll()
        return None

    cf = scene.frame_current
    fps = scene.render.fps / scene.render.fps_base
    if scene.use_preview_range:
        frame_start = scene.frame_preview_start
        frame_end = scene.frame_preview_end
    else:
        frame_start = scene.frame_start
        frame_end = scene.frame_end
    # get
    g = None
    for name, value in scene.sound_channels.items():
        speaker_name, action_name = name.split("__@__")
        speaker = bpy.data.speakers.get(speaker_name)
        action = getAction(speaker)
        if not speaker.filter_sound \
               or action_name != action.name:  # using the mute as a flag
            continue

        channel_name = action["channel_name"]
        fs = int(max(frame_start, action.frame_range.x))
        fe = min(frame_end, action.frame_range.y)
        if cf == fs:
            device.stopAll()

            for i in range(action["start"], action["end"]):
                if value.get("channel%02d" % i):
                    low = speaker['_RNA_UI']['CH%d' % i]['low']
                    high = speaker['_RNA_UI']['CH%d' % i]['high']
                    f = speaker.sound.factory
                    #f = aud.Factory(speaker.sound.filepath)
                    f = f.lowpass(low).highpass(high)
                    if g:
                        #f = f.join(g) # join
                        f = f.mix(g)
                    g = f

    if g:
        '''
        factory_buffered = aud.Factory.buffer
        (g.limit((fs-1) / fps, (fe-1) / fps))

        handle_buffered = device.play(factory_buffered)
        handle.position = 1.44
        '''

        print("playing")
        g = g.limit((fs - 1) / fps, (fe - 1) / fps)
        device.play(g)

# remove if there
fs = [f for f in bpy.app.handlers.frame_change_pre
      if f.__name__.startswith("ST__")]
for f in fs:
    bpy.app.handlers.frame_change_pre.remove(f)


def ST__scrubber(scene):
    frame = scene.frame_current
    fps = scene.render.fps
    if not frame % fps:

        start_time = frame // fps
        end_time = (start_time + 1 - 1 / fps)
        device.stopAll()
        ps("Speaker", limit=[start_time, end_time])


bpy.app.handlers.frame_change_pre.append(ST__filter_playback)
