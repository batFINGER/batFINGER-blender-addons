import bpy


def add_ref_images(context, directory, files, use_some_setting):
    print("running read_some_data...")
    scene = context.scene
    containerEmpty, spot, shrink_target, cone  = setup(context)
    for file in files:
        print(file)
    filelist = [{"name":file.name} for file in files]
    bpy.ops.import_image.to_plane(files=filelist,
                              directory=directory,
                              
                              location=(0, 0, 0),
                              rotation=(0, 0, 0),
                              factor=500,
                              use_shadeless=True,
                              use_transparency=False,
                              transparency_method='MASK',
                              use_transparent_shadows=False,
                              shader='BSDF_DIFFUSE',
                              overwrite_node_tree=True,
                              use_premultiply=False,
                              match_len=True,
                              use_fields=False,
                              use_auto_refresh=True,
                              relative=False)

    # ok images selected go into selected_objects
    image_planes = [plane for plane in context.selected_objects]
    for plane in image_planes:

        hide_all(context)
        bpy.ops.object.add(type='EMPTY',
                            view_align=False,
                            enter_editmode=False,
                            location=(0, 0, 0),
                            rotation=(0, 0, 0))
        pivot = context.scene.objects.active
        bpy.ops.object.add(type='CAMERA',
                            view_align=False,
                            enter_editmode=False,
                            location=(0, 0, 0),
                            rotation=(0, 0, 0))
        cam = context.scene.objects.active

        plane.parent = self.cam
        cam.parent = self.pivot
        plane.location[2] = -10
        plane.scale = (5,5,5)
        cam.rotation_euler[0] = radians(90)
        cam.location[1] = -5
        pivot["CamPivot"] = True
        pivot.empty_draw_type = 'CONE'
        pivot.location = context.space_data.cursor_location
        scene.camera = self.cam
        context.scene.objects.active = self.pivot
        containerEmpty, spot, shrink_target, cone = setup(context)
        pivot.parent = containerEmpty
        plane.hide_select = True
        plane.hide_render = True
        cam.hide_select = True
        bpy.ops.view3d.choose_ref_image(pic=self.plane.name)
    return {'FINISHED'}


# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty, CollectionProperty
from bpy.types import Operator

class RefImage(bpy.types.PropertyGroup):
    view = EnumProperty(
            name="Example Enum",
            description="Choose between two items",
            items=(('FRONT', "Front", ""),
                   ('RIGHT', "Right", ""),
                   ('LEFT', "Left", ""),
                   ('BACK', "Back", ""),
                   ('TOP', "Top", ""),
                   ('BOTTOM', "Bottom", "")),
            default='OPT_A',
    name = bpy.props.StringProperty(name="Test Prop", default="Unknown")
    value = bpy.props.IntProperty(name="Test Prop", default=22)

bpy.utils.register_class(RefImage)


class ImportSomeData(Operator, ImportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "import_test.some_data"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Import Some Data"

    # ImportHelper mixin class uses this


    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    settings = bpy.props.CollectionProperty(type=SceneSettingItem)
    use_setting = BoolProperty(
            name="Example Boolean",
            description="Example Tooltip",
            default=True,
            )

            )
    # -----------
    # File props.
    files = CollectionProperty(type=bpy.types.OperatorFileListElement,
                               options={'HIDDEN', 'SKIP_SAVE'})

    directory = StringProperty(maxlen=1024, subtype='DIR_PATH',
                               options={'HIDDEN', 'SKIP_SAVE'})

    # Show only images/videos, and directories!
    filter_image = BoolProperty(default=True, options={'HIDDEN', 'SKIP_SAVE'})
    filter_movie = BoolProperty(default=True, options={'HIDDEN', 'SKIP_SAVE'})
    filter_folder = BoolProperty(default=True, options={'HIDDEN', 'SKIP_SAVE'})
    filter_glob = StringProperty(default="", options={'HIDDEN', 'SKIP_SAVE'})


    def draw(self, context):
        layout = self.layout


    def execute(self, context):
        print(self.files)
        print(dir(self.files))
        print(self.files.__doc__)
        return read_some_data(context, self.directory, self.files, self.use_setting)


# Only needed if you want to add into a dynamic menu
def menu_func_import(self, context):
    self.layout.operator(ImportSomeData.bl_idname, text="Text Import Operator")


def register():
    bpy.utils.register_class(ImportSomeData)
    #bpy.types.INFO_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(ImportSomeData)
    #bpy.types.INFO_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register()

    # test call
    bpy.ops.import_test.some_data('INVOKE_DEFAULT')



