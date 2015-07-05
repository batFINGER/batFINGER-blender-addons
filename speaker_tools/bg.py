import bpy
from bpy.props import StringProperty
from io_import_images_as_planes import IMPORT_OT_image_to_plane as ImportImageToPlane
from math import degrees, radians

class ModalTimerOperator(bpy.types.Operator):
    """Operator which runs its self from a timer"""
    bl_idname = "wm.modal_timer_operator"
    bl_label = "Modal Timer Operator"

    _timer = None
    object = None

    plane = None
    cam = None
    pivot = None

    @classmethod
    def poll(cls, context):
        return(context.mode == 'OBJECT')

    def modal(self, context, event):

        scene = context.scene

        if event.type == 'ESC':
            return self.cancel(context)

        if event.type == 'TIMER':
            if self.cam != context.scene.objects.active:
                print("GOT IT")

                self.plane = context.scene.objects.active
                # clean up code needed.


                self.plane.parent = self.cam
                self.cam.parent = self.pivot
                self.plane.location[2] = -10
                self.plane.scale = (5,5,5)
                self.cam.rotation_euler[0] = radians(90)
                self.cam.location[1] = -5
                self.pivot["CamPivot"] = True
                self.pivot.empty_draw_type = 'CONE'
                self.pivot.location = context.space_data.cursor_location
                scene.camera = self.cam
                bpy.ops.view3d.viewnumpad(type='CAMERA')
                context.scene.objects.active = self.pivot
                return self.cancel(context)
            else:
                print("WAITING")


        return {'PASS_THROUGH'}

    def execute(self, context):
        scene = context.scene
        bpy.ops.object.add(type='EMPTY',
                            view_align=False,
                            enter_editmode=False,
                            location=(0, 0, 0),
                            rotation=(0, 0, 0))
        self.pivot = context.scene.objects.active
        bpy.ops.object.add(type='CAMERA',
                            view_align=False,
                            enter_editmode=False,
                            location=(0, 0, 0),
                            rotation=(0, 0, 0))
        self.cam = context.scene.objects.active
        #bpy.ops.import_image.to_plane('INVOKE_DEFAULT',)
        bpy.ops.import_image.to_plane('INVOKE_DEFAULT',
                                      directory='F:\\blender\\car\\chevy\\',
                                      view_align=False,
                                      location=(0, 0, 0),
                                      rotation=(0, 0, 0),
                                      filter_image=True,
                                      filter_movie=True,
                                      filter_folder=True,
                                      filter_glob="",
                                      align=True,
                                      align_offset=0.1,
                                      extension='*',
                                      use_dimension=False,
                                      factor=500,
                                      use_shadeless=False,
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

        context.window_manager.modal_handler_add(self)
        self._timer = context.window_manager.event_timer_add(0.1, context.window)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        context.window_manager.event_timer_remove(self._timer)
        return {'CANCELLED'}

def main(context):
    #bpy.ops.import_image.to_plane('INVOKE_DEFAULT')
    for ob in context.scene.objects:
        print(ob)


class RefPicChoose(bpy.types.Operator):
    """Choose Reference Image"""
    bl_idname = "view_3d.choose_ref_image"
    bl_label = "Choose Ref Image"

    pic = StringProperty("Image", default="")
    @classmethod
    def poll(cls, context):
        return True


    def execute(self, context):
        scene = context.scene
        pivots = [object for object in context.scene.objects if "CamPivot" in object]

        for pivot in pivots:
            pivot.hide = True
            cam = pivot.children[0]
            cam.hide = True
            image = cam.children[0]
            image.hide = True

        image = scene.objects.get(self.pic)
        if image is not None:
            image.hide = False
            camera = image.parent
            camera.hide = False
            pivot = camera.parent
            pivot.hide = False
            scene.camera = camera

        print(self.pic)
        main(context)
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        layout.label("TEST")


class RefImageView(bpy.types.Menu):
    bl_label = "Select Ref Image"
    bl_idname = "ref_image.select"

    def draw(self, context):
        pivots = [object for object in context.scene.objects if "CamPivot" in object]
        layout = self.layout

        for pivot in pivots:
            camobj = pivot.children[0]
            cam = camobj.data
            image = camobj.children[0]
            tex = image.material_slots[0].material.texture_slots[0].texture
            layout.operator("view_3d.choose_ref_image", text=image.name, icon='IMAGE_DATA').pic = image.name
            ''' If only it where True
            layout.template_preview(tex)
            '''

def dotshow(row):
    return None
    model_ref1 = bpy.data.objects.get("RP1").location
    model_ref2 = bpy.data.objects.get("RP2").location
    ref1 = bpy.data.objects.get("RefPoint1").matrix_world.to_translation()
    ref2 = bpy.data.objects.get("RefPoint2").matrix_world.to_translation()

    v1 = model_ref2 - model_ref1
    v2 = ref2 - ref1

    print(v1, v2)
    print(degrees(v1.angle(v2)))
    print(v1.dot(v2))

    axis = v1.cross(v2)
    print(axis)

    row.label("Angle %f.2 dot %f.2" % ( degrees(v1.angle(v2)), v1.dot(v2)))


class AlignToRefPicPanel(bpy.types.Panel):
    """Set up camera ref pic"""
    bl_label = "Perspective Ref Images"
    #bl_idname = "OBJECT_PT_hello"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    #bl_context = "object"

    @classmethod
    def poll(self, context):
        scene = context.scene
        cam = scene.camera
        pivot = cam.parent
        return (pivot is not None and "CamPivot" in pivot)

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        camobj = scene.camera
        cam = camobj.data

        obj = camobj.parent

        if obj is None:
            layout.operator("wm.modal_timer_operator")
            return None

        image = camobj.children[0]
        tex = image.material_slots[0].material.texture_slots[0].texture

        row = layout.row()
        box = row.box()

        row = box.row()
        row.menu("ref_image.select")

        row = box.row()
        row.operator("wm.modal_timer_operator")

        row = box.row()
        row.template_preview(tex)
        row.scale_x = 2

        row = box.row()
        row.prop(camobj,"location", index=1, icon='CAMERA_DATA')

        row = box.row()
        row.prop(image,"location", index=2, icon='IMAGE_DATA')

        row = layout.row()
        box = row.box()
        box.label("Pivot",icon='EMPTY_DATA')

        row = box.row()

        row.column().prop(obj, "location")
        if obj.rotation_mode == 'QUATERNION':
            row.column().prop(obj, "rotation_quaternion", text="Rotation")
        elif obj.rotation_mode == 'AXIS_ANGLE':
            #row.column().label(text="Rotation")
            #row.column().prop(pchan, "rotation_angle", text="Angle")
            #row.column().prop(pchan, "rotation_axis", text="Axis")
            row.column().prop(obj, "rotation_axis_angle", text="Rotation")
        else:
            row.column().prop(obj, "rotation_euler", text="Rotation")

        row = layout.row()
        box = row.box()

        row = box.row()
        row.label("Camera", icon='CAMERA_DATA')

        row = box.row()
        row.prop(cam, "type", expand=True)

        row = box.row()
        split = row.split()

        col = split.column()
        if cam.type == 'PERSP':
            row = col.row()
            if cam.lens_unit == 'MILLIMETERS':
                row.prop(cam, "lens")
            elif cam.lens_unit == 'DEGREES':
                row.prop(cam, "angle")
            row.prop(cam, "lens_unit", text="")

        elif cam.type == 'ORTHO':
            col.prop(cam, "ortho_scale")

        row = layout.row()
        dotshow(row)

def register():
    bpy.utils.register_class(RefPicChoose)
    ImportImageToPlane.bl_idname = "import_image.to_plane"
    bpy.utils.register_class(ImportImageToPlane)
    bpy.utils.register_class(ModalTimerOperator)
    bpy.utils.register_class(RefImageView)
    bpy.utils.register_class(AlignToRefPicPanel)


def unregister():
    bpy.utils.unregister_class(ModalTimerOperator)
    bpy.utils.unregister_class(RefPicChoose)
    bpy.utils.unregister_class(bpy.types.IMPORT_IMAGE_OT_to_plane)
    bpy.utils.unregister_class(RefImageView)
    bpy.utils.unregister_class(AlignToRefPicPanel)

register()
