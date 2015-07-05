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
    "name": "Speaker Tools",
    "author": "batFINGER",
    "location": "Properties > Speaker > Toolshelf",
    "description": "Add Equaliser / Driver / Lipsync to speaker data",
    "warning": "Still in Testing",
    "wiki_url": "",
    "version": (0, 1),
    "blender": (2, 6, 4),
    "tracker_url": "",
    "support": 'TESTING',
    "category": "Animation"}


mods = ("Equalizer", "EqMenu", "NLALipsync",
        "filter_playback", "utils", "presets")
if "bpy" in locals():
    import imp
    for mod in mods:
        exec("imp.reload(%s)" % mod)


else:
    for mod in mods:
        exec("from . import %s" % mod)


import bpy


def register():
    Equalizer.register()
    EqMenu.register()
    NLALipsync.register()
    presets.register()


def unregister():
    Equalizer.unregister()
    EqMenu.unregister()
    NLALipsync.unregister()
    presets.unregister()
