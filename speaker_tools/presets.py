# <pep8-80 compliant>
import bpy
from bpy.utils import preset_find, preset_paths
from bpy.types import Menu, Operator
from bpy.props import FloatProperty
from bl_operators.presets import AddPresetBase
from math import log
import os

notes = ['A', 'A#', 'B', 'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#']


def note_from_freq(freq):
    steps = round(12 * log(freq / 27.5, 2)) % 12
    octave = (steps - 3) / 12
    note = notes[steps]
    return "%s%d" % (note, octave)


def start(self, context):
    print("START", self.start)
    op = bpy.types.Scene.soundtool_op
    is_valid = op is not None
    if is_valid:
        op.minf = self.start


class SPEAKER_OT_GUI(Operator):
    bl_idname = "speaker.gui"
    bl_label = "Music GUI"
    start = FloatProperty(default=88.0)
    end = FloatProperty(default=5500.0)

    def execute(self, context):
        op = bpy.types.Scene.soundtool_op
        is_valid = op is not None
        if is_valid:
            note = note_from_freq(self.start)
            print(note)
            op.minf = self.start
        return {'FINISHED'}


class SOUND_MT_Music_Notes(Menu):
    bl_idname = "sound.music_notes"
    bl_label = "Choose a note"

    def draw(self, context):
        layout = self.layout
        octave = 0
        for note in range(0, 88):
            name = notes[note % 12]
            if name == "C":
                octave += 1  # Go up an octave
            freq = 27.5 * 2 ** (note / 12.0)
            name = "%s%d (%.2f)" % (name, octave, freq)
            layout.operator("speaker.gui", text=name).start = freq


class SPEAKER_MT_Presets(Menu):
    bl_idname = "speaker.preset_menu"
    bl_label = "Choose a preset"

    def draw(self, context):
        def icon(type):
            if type == 'SFX':
                return 'SOUND'
            else:
                return 'SPEAKER'
        sound = getattr(context.object.data, 'sound', None)
        count = 0
        layout = self.layout
        path = os.path.join('operator', 'speaker.visualise')
        paths = preset_paths(path)
        # draw a menu
        for directory in paths:
            directory = os.path.join(directory, sound.type)
            if not os.path.isdir(directory):
                continue
            psts = os.listdir(directory)
            for f in psts:
                count += 1
                if count == 1:
                    layout.label(text=sound.type, icon=icon(sound.type))
                    layout.separator()
                pres = os.path.splitext(f)[0]
                layout.operator('speaker.visualise', text=pres).preset = pres
        if count == 0:
            layout.label("None")


class AddPresetSoundToolOperator(AddPresetBase, Operator):
    '''Add an Application Interaction Preset'''
    bl_idname = "wm.soundtool_operator_preset_add"
    bl_label = "Operator Preset"
    preset_menu = "WM_MT_operator_presets"

    operator = bpy.props.StringProperty(
            name="Operator",
            maxlen=64,
            options={'HIDDEN'},
            default="SPEAKER_OT_visualise"
            )

    name = bpy.props.StringProperty(
        name="Name",
        description="Name of the preset, used to make the path name",
        maxlen=64,
        options={'SKIP_SAVE'},
        )

    preset_defines = [
        "op = bpy.types.Scene.soundtool_op",
    ]

    @property
    def preset_subdir(self):
        import os
        op = bpy.types.Scene.soundtool_op
        type = op.type
        return os.path.join('operator', 'speaker.visualise', type)

    @property
    def preset_values(self):
        properties_blacklist = Operator.bl_rna.properties.keys()

        prefix, suffix = self.operator.split("_OT_", 1)
        op = getattr(getattr(bpy.ops, prefix.lower()), suffix)
        operator_rna = op.get_rna().bl_rna
        del op

        ret = []
        for prop_id, prop in operator_rna.properties.items():
            if not (prop.is_hidden or prop.is_skip_save):
                if prop_id not in properties_blacklist:
                    ret.append("op.%s" % prop_id)

        return ret

    @staticmethod
    def operator_path(operator):
        import os
        op = bpy.types.Scene.soundtool_op
        type = op.type
        return os.path.join('operator', 'speaker.visualise', type)


def register():
    bpy.utils.register_class(SOUND_MT_Music_Notes)
    bpy.utils.register_class(SPEAKER_MT_Presets)
    bpy.utils.register_class(SPEAKER_OT_GUI)
    bpy.utils.register_class(AddPresetSoundToolOperator)


def unregister():
    bpy.utils.unregister_class(SOUND_MT_Music_Notes)
    bpy.utils.unregister_class(SPEAKER_MT_Presets)
    bpy.utils.unregister_class(SPEAKER_OT_GUI)
    bpy.utils.unregister_class(AddPresetSoundToolOperator)
