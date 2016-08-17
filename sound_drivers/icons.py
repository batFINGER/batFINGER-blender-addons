import bpy

from os import path
from bpy.types import UILayout
icon_value = UILayout.icon
enum_item_icon = UILayout.enum_item_icon
icon_dir = path.join(path.dirname(__file__), "icons")
preview_collections = {}

def register():
    # Note that preview collections returned by bpy.utils.previews
    # are regular py objects - you can use them to store custom data.
    import bpy.utils.previews
    pcoll = bpy.utils.previews.new()

    # path to the folder where the icon is
    # the path is calculated relative to this py file inside the addon folder
    # load a preview thumbnail of a file and store in the previews collection
    icons = {"midi" : "midi.png",
            }
    for key, f in icons.items():
        pcoll.load(key, path.join(icon_dir, f), 'IMAGE')

    preview_collections["main"] = pcoll

def unregister():
    for pcoll in preview_collections.values():
        bpy.utils.previews.remove(pcoll)
    preview_collections.clear()
