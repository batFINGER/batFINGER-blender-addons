# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####
# <pep8-80 compliant>


bl_info = {
    "name": "Sound Drivers",
    "author": "batFINGER",
    "location": "Properties > Speaker > Toolshelf",
    "description": "Drive Animations with baked sound files",
    "warning": "Still in Testing",
    "wiki_url": "http://wiki.blender.org/index.php/\
                User:BatFINGER/Addons/Sound_Drivers",
    "version": (1, 1),
    "blender": (2, 7, 5),
    "tracker_url": "",
    "support": 'TESTING',
    "category": "Animation"}

mods = ("sounddriver",
        "speaker",
        "sound",
        "visualiser",
        "Equalizer",
        "EqMenu",
        "NLALipsync",
        "filter_playback",
        "utils",
        "presets")

if "bpy" in locals():
    import imp
    for mod in mods:
        exec("imp.reload(%s)" % mod)


else:
    for mod in mods:
        exec("from . import %s" % mod)


import bpy
from bpy.types import  AddonPreferences
from bpy.props import StringProperty
from bpy.utils import register_class, unregister_class


class SpeakerToolsAddonPreferences(AddonPreferences):
    ''' Speaker Tools User Prefs '''
    bl_idname = "sound_drivers"

    temp_folder = StringProperty(
            name="Example File Path",
            subtype='DIR_PATH',
            )

    def draw(self, context):
        def icon(test):
            if test:
                icon = 'FILE_TICK'
            else:
                icon = 'ERROR'
            return icon

        layout = self.layout
        # check that automatic scripts are enabled
        UserPrefs = context.user_preferences
        dns = bpy.app.driver_namespace
        row = layout.row()
        row.prop(UserPrefs.system, "use_scripts_auto_execute")

        if not UserPrefs.system.use_scripts_auto_execute:
            row = layout.row()
            row.label("Warning Will not work unless Auto Scripts Enabled",
                      icon='ERROR')
        row = layout.row()
        row.label("SoundDrive in Driver Namespace", icon=icon("SoundDrive" in
                                                              dns))
        row = layout.row()
        row.label("GetLocals in Driver Namespace", icon=icon("GetLocals" in
                                                              dns))
        test = "DriverManager" in dns
        row = layout.row()
        row.label("DriverManager Started", icon=icon(test))
        if not test:
            row = layout.row()
            row.operator("drivermanager.update")


def register():
    register_class(SpeakerToolsAddonPreferences)
    sounddriver.register()
    speaker.register()
    sound.register()
    visualiser.register()
    Equalizer.register()
    EqMenu.register()
    NLALipsync.register()
    presets.register()
    filter_playback.register()


def unregister():
    unregister_class(SpeakerToolsAddonPreferences)
    sounddriver.unregister()
    speaker.unregister()
    sound.unregister()
    visualiser.unregister()
    Equalizer.unregister()
    EqMenu.unregister()
    NLALipsync.unregister()
    presets.unregister()
    filter_playback.register()
