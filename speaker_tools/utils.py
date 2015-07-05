import bpy
import re
from mathutils import Vector, Color, Euler, Quaternion

# <pep8-80 compliant>

bpy_collections = ["scenes", "objects", "meshes", "materials", "textures",
        "speakers", "worlds", "curves", "armatures", "particles", "lattices",
        "shape_keys", "lamps", "cameras"]


def format_data_path(row, path, icon_only=False, padding=0):
    # look for material / texture in data path

    def rep_spaces(txt, to_spaces=False):
        if to_spaces:
            return txt.replace("+", " ")
        else:
            return txt.replace(" ", "+")

    rexps = [('MATERIAL', r'material_slots\[(\S+)\]\.material\.(\S+)'),
             ('TEXTURE', r'texture_slots\[(\S+)\]\.texture\.(\S+)'),
             ('TEXTURE', r'texture_slots\[(\S+)\]\.(\S+)'),
             ('MODIFIER', r'modifiers\[\"(\S+)\"\]\.(\S+)'),
             ('MODIFIER', r'modifiers\[(\S+)\]\.canvas_settings\.(\S+)'),
             ('CONSTRAINT', r'constraints\[(\S+)\]\.(\S+)'),
             ('SHAPEKEY_DATA', r'key_blocks\[(\S+)\]\.(\S+)'),
             ('COLOR', r'color'),
              ]
    path = rep_spaces(path)
    for icon, regexp in rexps:
        name = ""
        m = re.match(regexp, path)
        # Material match
        if m is not None:
            padding -= 1
            col = row.column()
            col.alignment = 'LEFT'
            if not icon_only:
                if len(m.groups()):
                    name = "[%s]" % rep_spaces(m.groups()[0], True)
                else:
                    name = "[%s]" % path
            col.label(icon=icon, text=name)
            if len(m.groups()):
                path = m.groups()[1]

    if not icon_only:
        col = row.column()
        col.alignment = 'RIGHT'
        col.label(rep_spaces(path, True))
    if padding > 0:
        for i in range(padding):
            bcol = row.column()
            bcol.alignment = 'LEFT'
            bcol.label(icon='BLANK1')


def icon_from_bpy_datapath(path):
    icons = ['SCENE', 'OBJECT_DATA', 'MESH', 'MATERIAL', 'TEXTURE', 'SPEAKER',
            'WORLD', 'CURVE', 'ARMATURE', 'PARTICLES', 'LATTICE_DATA',
            'SHAPEKEY_DATA', 'LAMP', 'CAMERA_DATA']

    sp = path.split(".")
    col = sp[2].split('[')[0]
    #collection name will be index
    return  icons[bpy_collections.index(col)]


def create_drivers_list(drivers_list={}, filter="", output_to_file=False):

    def driver_key(driver):
        context = bpy.context  # don't like doing this ...pass context
        return "%s%s" % (driver.data_path, driver.array_index)

    for col in bpy_collections:
        collection = eval("bpy.data.%s" % col)
        for ob in collection:
            if ob.animation_data is not None:
                drivers = [driver for driver in ob.animation_data.drivers]
                if len(drivers) > 0:
                    drivers.sort(key=driver_key)
                    drivers_list[repr(ob)] = drivers
    return drivers_list


def getAction(speaker, search=False):
    action = None
    if speaker.animation_data:
        action = speaker.animation_data.action
        if action is not None:
            if "bake_error" in action.keys():
                return None
            return action
        if speaker.animation_data.use_nla:
            return None
    return action

#FRAME change method to make the equalizer update live to panel


def getSpeaker(context):
    space = context.space_data
    if space.type == 'PROPERTIES':
        if space.use_pin_id:
            return space.pin_id
        else:
            if context.object is not None and context.object.type == 'SPEAKER':
                return context.object.data
    # otherwise return the context speaker.
    return bpy.types.Scene.context_speaker


def get_driver_settings(fcurve, speaker):
    reg_exps = [r'SoundDrive\(\[(\S+) \]\,(\S+)\)', r'SoundDrive\(\[(\S+)\]\)',
                r'SoundDrive\((\S+)\)']
    expression = fcurve.driver.expression.replace(" ", "")  # replace the

    match = False
    for i, regex in enumerate(reg_exps):
        m = re.match(regex, expression)
        if m is not None:
            match = True
            break

    channels = []  # Channels from expression
    var_channels = []  # channels from vars
    args = []

    if not match:
        pass

    elif i == 0:  # list only match
        channels.extend(m.groups()[0].split(","))
        args.extend(m.groups()[1].split(","))
    elif i == 1:  # list with vars
        channels.extend(m.groups()[0].split(","))
    elif i == 2:  # single var
        channels.append(m.groups()[0].split(",")[0])
        args = m.groups()[0].split(",")[1:]

    driver = fcurve.driver
    speakers = [speaker.id_data
                for speaker in bpy.data.speakers
                if speaker.get("vismode") is not None]

    var_channels = [var.name
                    for var in driver.variables
                    if expression.startswith("SoundDrive")
                    and var.targets[0] is not None
                    and var.targets[0].id in speakers]

    #TODO check lists fix expression remove dead vars
    return var_channels, args


def driver_filter_draw(layout, context):
    scene = context.scene
    settings = scene.speaker_tool_settings
    row = layout.row(align=True)
    row.label("FILTER", icon='FILTER')
    row.prop(settings, "filter_object", icon='OBJECT_DATA', toggle=True,
            text="")
    if settings.filter_object:
        row.prop(settings, "filter_context", toggle=True,
                text="CONTEXT")
    row.prop(settings, "filter_world", icon='WORLD', toggle=True,
            text="")
    row.prop(settings, "filter_material", icon='MATERIAL', toggle=True,
            text="")
    row.prop(settings, "filter_texture", icon='TEXTURE', toggle=True,
            text="")
    row.prop(settings, "filter_monkey", icon='MONKEY', toggle=True,
            text="")
    row.prop(settings, "filter_speaker", icon='SPEAKER', toggle=True,
            text="")


def AllDriversPanel(box, context):

    def driver_icon(fcurve):
        driver = fcurve.driver
        if len(driver.variables) == 1 \
                and driver.variables[0].name == "var" \
                and driver.variables[0].targets[0].id is None:
            return 'MONKEY'
        return 'DRIVER'

    #row.template_ID(context.scene.objects,'active')
    scene = context.scene
    settings = scene.speaker_tool_settings
    box.scale_y = box.scale_x = 0.8
    driver_filter_draw(box, context)
    xlist = {}
    olist = {}
    xlist = create_drivers_list(xlist)
    i = 0
    print("*" * 30)
    for xx in xlist:
        row = box.row()
        if xx.startswith("bpy.data.objects") and not settings.filter_object:
            i += len(xlist[xx])
            continue
        elif xx.startswith("bpy.data.materials") and not settings.filter_material:
            i += len(xlist[xx])
            continue

        obj = eval(xx)
         
        print(obj.name, obj, xx)

        if  context.scene.objects.active == obj:
            row.template_ID(context.scene.objects, 'active')
        else:
            if settings.filter_context and xx.startswith("bpy.data.objects"):
                i += len(xlist[xx])
                continue
            row.label(text="", icon=icon_from_bpy_datapath(xx))
            row.prop(obj, "name", text="")
        for driver in xlist[xx]:
            icon = driver_icon(driver)
            if not icon.startswith("MONKEY") and settings.filter_monkey:
                i += 1
                continue

            can_edit = True
            row = box.row(align=True)
            #row.scale_y = row.scale_x = 0.8
            #row = box.row()
            infocol = row.column()
            infocol = infocol.row()
            infocol.alignment = 'LEFT'
            infocol.prop(driver.driver, "is_valid", text="",
                         icon=icon)
            propcol = row.row()
            propcol = propcol.row(align=True)
            format_data_path(propcol, driver.data_path, True, padding=2)
            buttoncol = row.column(align=False)
            buttoncol.alignment = 'RIGHT'
            row.alert = driver.driver.is_valid

            sp = driver.data_path.split(".")
            prop = sp[-1]
            path = driver.data_path.replace("%s" % prop, "")
            bpy_data_path = "%s.%s" % (xx, path)
            if bpy_data_path[-1] == '.':
                bpy_data_path = bpy_data_path[:-1]
            try:
                do = eval(bpy_data_path)
                mo = do.path_resolve(prop)
            except:
                do = None
                mo = None

            if do is None:
                propcol.label(text="BAD PATH", icon="ERROR")
                can_edit = False

            elif isinstance(mo, Vector):
                axis = "XYZ"[driver.array_index]
                text = "%s %s" % (axis, do.bl_rna.properties[prop].name)
                propcol.prop(do, prop, text=text,
                             index=driver.array_index, slider=True)

            elif isinstance(mo, Euler):
                axis = mo.order[driver.array_index]
                text = "%s %s" % (axis, do.bl_rna.properties[prop].name)
                propcol.prop(do, prop,
                             text=text,
                             index=driver.array_index,
                             slider=True)

            elif isinstance(mo, Quaternion):
                axis = "WXYZ"[driver.array_index]
                text = "%s %s" % (axis, do.bl_rna.properties[prop].name)
                propcol.prop(do, prop,
                             text=text,
                             index=driver.array_index,
                             slider=True)

            elif isinstance(mo, Color):
                rgb = "RGB"[driver.array_index]
                text = "%s %s" % (rgb, do.bl_rna.properties[prop].name)
                propcol.prop(do, prop,
                             text=text,
                             index=driver.array_index,
                             slider=True)

            elif type(mo).__name__ == "bpy_prop_array":
                if prop == "color":
                    axis = "RGBA"[driver.array_index]
                    txt = "%s %s" % (axis, do.bl_rna.properties[prop].name)
                    propcol.prop(do, prop,
                                 text=txt,
                                 index=driver.array_index,
                                 slider=True)
            else:
                propcol.prop(do, prop, index=driver.array_index, slider=True)

            split = buttoncol.split(align=True)

            split.alignment = 'RIGHT'
            split.operator("speaker.add_driver_channel",
                               icon="ZOOMOUT", text="").delete_index = i
            split.operator("speaker.add_driver_channel",
                               icon="FCURVE", text="").fcurve_index = i
            row = split.row(align=True)
            row.enabled = can_edit
            row.alignment = 'RIGHT'
            row.operator("speaker.add_driver_channel",
                               text="EDIT").driver_index = i
            i += 1
            '''

            if xx.find("shape_keys") > 0:
                if ".value" in driver.data_path:
                    do = obj.path_resolve(driver.data_path.split('.value')[0])
                    propcol.prop(do, 'value', slider=True,
                                 index=driver.array_index)
                else:
                    sp = driver.data_path.split(".")
                    prop = sp[-1]
                    path = driver.data_path.replace(".%s" % prop, "")
                    #print(prop)
                    do = obj.path_resolve(path)
                    propcol.prop(do, prop, index=driver.array_index)
            elif driver.data_path.find("material_slots") == 0:
                #print("material")
                sp = driver.data_path.split(".")
                prop = sp[-1]
                path = driver.data_path.replace(".%s" % prop, "")
                #print(prop)
                do = obj.path_resolve(path)
                l_col = propcol.column()
                l_col.alignment = 'LEFT'
                l_col = l_col.row()
                l_col.label(text="",
                        icon=icon_from_bpy_datapath("bpy.data.materials"))

                if prop.find("color") != -1 \
                        and driver.data_path.find('texture_slots') == -1:
                    rgb = "RGB"
                    l_col.label(text=rgb[driver.array_index])
                    c_col = propcol.column()
                    c_col = c_col.row()
                    c_col.prop(do, prop, index=driver.array_index)
                    r_col = propcol.column()
                    r_col = r_col.row()
                    r_col.alignment = 'RIGHT'
                    r_col.prop(do, prop, text="")
                else:
                    propcol.prop(do, prop)
            else:
                propcol.prop(obj,
                             driver.data_path,
                             slider=True,
                             index=driver.array_index)
            buttoncol.operator("speaker.add_driver_channel",
                               text="EDIT").driver_index = i
            #row.label("%s %d %d" % (xx,driver.array_index,i))
            row = box.row(align=True)
            '''
    row = box.row()
    driver_index = bpy.types.SoundVisualiserPanel.driver_index
    #row.enabled = False  # SINGLE
    # SINGLE will support multiple copyable drivers one for now.
