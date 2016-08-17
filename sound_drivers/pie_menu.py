import bpy
from bpy.types import Menu
from bpy.utils import register_class, unregister_class

from sound_drivers.sounddriver import DriverManager_DriverOp

class PieMenuDriverPopup(bpy.types.Operator, DriverManager_DriverOp):
    """Edit Driver Details"""
    bl_idname = "driver.popup_driver"
    bl_label = "Driver Manager"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None
    
    def check(self, context):
        return True
    
    def invoke(self, context, event):
        wm = context.window_manager
        '''
        if wm is None:

            # try and start the b***
            bpy.ops.wm.drivermanager_update('INVOKE_DEFAULT')
            wm = context.window_manager
        '''
        wm.update_dm = not wm.update_dm
        d = self.get_driver()
        print(d, dir(d))
        if d:         
            bpy.ops.driver.edit('INVOKE_DEFAULT', dindex=d.index, toggle=True)
        return(wm.invoke_props_dialog(self))
        
    def draw(self, context):
        d = self.get_driver()
        if d:        
            scene = context.scene    
            gui = d.driver_gui(scene)
            if gui is not None:
                self.layout.prop(gui, "gui_types",
                             text="",
                             expand=True,
                             icon_only=True)
            d.draw_slider(self.layout)
            d.edit(self.layout, context)
            self.check(context)
        
    def execute(self, context):
        print("DRIVER PIE EXEC")
        return {'FINISHED'}


class VIEW3D_PIE_drivers(Menu):
    # label is displayed at the center of the pie menu.
    bl_label = "Select Mode"

    @classmethod
    def poll(self, context):
        dm = context.driver_manager
        print("PM POLL", dm is not None, hasattr(context, "driver_manager"))
        return True
        return dm is not None

    def draw(self, context):
        layout = self.layout
        layout.label("WHERE")
        obj = context.object
        dm = context.driver_manager
        if dm is None:
            layout.operator("drivermanager.update")
            return None
        
        pie = layout.menu_pie()
        dm.draw_pie_menu(obj, pie)
        return None

addon_keymaps = []
def register():
    #addon_keymaps.clear()
    register_class(VIEW3D_PIE_drivers)
    register_class(PieMenuDriverPopup)
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = wm.keyconfigs.addon.keymaps.new(name='Drivers Pie Menu', space_type='VIEW_3D')
        kmi = km.keymap_items.new("wm.call_menu_pie", type='D', value='PRESS', ctrl=True)
        kmi.properties.name = "VIEW3D_PIE_drivers"
        addon_keymaps.append((km, kmi))

def unregister():
    unregister_class(VIEW3D_PIE_drivers)
    bpy.utils.unregister_class(PieMenuDriverPopup)
    # handle the keymap
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

if __name__ == "__main__":
    register()

    bpy.ops.wm.call_menu_pie(name="VIEW3D_PIE_drivers")
