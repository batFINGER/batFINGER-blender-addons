import bpy

#from . import debug
from bpy.types import FCurve, Operator
from bpy.utils import register_class, unregister_class
from mathutils import Vector, Color, Euler, Quaternion
from math import sqrt
import re
from operator import attrgetter
from bpy.app.handlers import persistent
from bpy.props import StringProperty, PointerProperty, BoolProperty,\
    IntProperty, CollectionProperty, FloatProperty,\
    EnumProperty
from bpy.types import PropertyGroup
from sound_drivers.utils import format_data_path, driver_filter_draw,\
    getSpeaker, getAction, get_icon,\
    remove_handlers_by_prefix,\
    get_driver_settings,\
    driver_expr

from sound_drivers.EqMenu import main
from sound_drivers import debug
#dm = None

'''
Update methods
'''


def update_dm(self, context):
    dns = bpy.app.driver_namespace
    dm = dns.get("DriverManager")

    if dm is not None:
        dm.get_all_drivers_list()

bpy.types.WindowManager.update_dm =\
    BoolProperty(description="Refresh Driver List",
                             update=update_dm)


def toggle_driver_fix(self, context):
    handler = bpy.app.handlers.frame_change_post

    handlers = [f for f in handler if f.__name__ == "mat_driver_fix"]
    for f in handlers:
        handler.remove(f)
    if self.material_driver_fix:
        bpy.app.handlers.frame_change_post.append(mat_driver_fix)

bpy_collections = []


def wonk(self, context):
    dm = bpy.app.driver_namespace['DriverManager']
    sp = context.scene.speaker
    a = getAction(sp)
    if dm is None or dm._setting_channels or sp is None or a is None:
        return None
    ed = dm._edit_driver_gui
    cn = a['channel_name']
    if self.rna_type.identifier.startswith('SoundDriverChannel'):
        if not self.value:
            bpy.ops.dm.remove_driver_var(varname=self.name)
        else:
            channel_list = [ch.name for ch in ed.channels if
                            ch.value and ch.name.startswith(cn)]
            main(ed, context, sp, a, channel_list)
    elif self.rna_type.identifier.startswith('EditDriver'):
        channel_list = [ch.name for ch in ed.channels if
                        ch.value and ch.name.startswith(cn)]
        main(self, context, sp, a, channel_list)
        # do amplify things etc
        pass
    #main(self, context, speaker, action, channel_list)

'''
Handlers
'''


def set_var_index(self, context):
    dm = bpy.app.driver_namespace['DriverManager']
    if dm is None:
        return None
    d = dm._edit_driver
    gui = dm._edit_driver_gui
    if gui is None or d is None:
        return None

    if self.varname == "":
        self.var_index = -1
        return

    if self.varname not in d.fcurve.driver.variables.keys():
        self.varname = d.fcurve.driver.variables[self.var_index]
        return None

    self.var_index = d.fcurve.driver.variables.find(self.varname)


@persistent
def SOUND_DRIVERS_load(dummy):
    debug.print("SOUND_DRIVERS_load")
    BPY_COLLECTION_TYPE = type(bpy.data.objects)
    prop_dict = {}

    bpy_collections.clear()
    for name in dir(bpy.data):
        o = getattr(bpy.data, name)
        if isinstance(o, BPY_COLLECTION_TYPE):
            prop_dict[name] = BoolProperty(default=False)
            bpy_collections.append(name)

    filters = type('Filters', (PropertyGroup,), prop_dict)
    expanders = type('Expand', (PropertyGroup,), prop_dict)

    ch_dic = {}
    ch_dic["name"] = StringProperty()
    ch_dic["value"] = FloatProperty(default=0.0)
    #ch_dic["rna_type"] = StringProperty()

    DriverVar = type('DriverVar', (PropertyGroup,), ch_dic)
    register_class(DriverVar)

    ch_dic = {}
    ch_dic["name"] = StringProperty()
    ch_dic["value"] = BoolProperty(default=False, update=wonk)

    SoundDriverChannel = type('SoundDriverChannel', (PropertyGroup,), ch_dic)
    register_class(SoundDriverChannel)

    prop_dic = {}
    prop_dic["collection"] = StringProperty(default="",
                                            description="Driven Object Collection")
    prop_dic["object"] = StringProperty(default="",
                                        description="Driven Object")
    prop_dic["data_path"] = StringProperty(default="")
    prop_dic["array_index"] = IntProperty(default=0)
    prop_dic["channels"] = CollectionProperty(type=SoundDriverChannel)
    prop_dic["vars"] = CollectionProperty(type=DriverVar)
    amplify = FloatProperty(name="Amplify",
                            default=1.0,
                            min=-1000,
                            max=1000,
                            description="Amplify the output",
                            update=wonk,
                            soft_min=-10.0,
                            soft_max=10.0)

    prop_dic["amplify"] = amplify
    prop_dic["use_threshold"] = BoolProperty(default=False)
    threshold = FloatProperty(name="Threshold",
                              default=0.0,
                              min=0.0,
                              max=1000,
                              description="Only calculate when input is greater\
                              than threshold",
                              update=wonk,
                              soft_max=10.0)
    prop_dic["threshold"] = threshold
    prop_dic["varname"] = StringProperty(default="",
                                         name="Driver Variable Name",
                                         update=set_var_index)
    prop_dic["var_index"] = IntProperty(default=-1,
                                        name="Driver Variable Name")
    op = EnumProperty(items=(
        ("sum", "SUM", "Sum Values"),
        ("avg", "AVERAGE", "Average Value"),
        ("min", "MIN", "Minimum Value"),
        ("max", "MAX", "Maximum Value")
    ),
        name="Function",
        default="avg",
        description="Method for Channel List",
        update=wonk,
    )

    gui_type = EnumProperty(items=(
        ("STD", "Standard", "Standard Interface", 'DRIVER', 0),
        ("SPK", "SoundDriver", "Sound Driver", 'SOUND', 1)
    ),
        name="Choose Interface",
        default="STD",
        description="Driver GUI Type",
        update=wonk,
    )

    prop_dic["gui_type"] = gui_type
    prop_dic["op"] = op
    prop_dic["value"] = FloatProperty(default=0.0, options={'ANIMATABLE'})
    prop_dic["array_index"] = IntProperty(default=0)

    EditDriver = type('EditDriver', (PropertyGroup,), prop_dic)

    register_class(filters)
    register_class(expanders)
    register_class(EditDriver)

    prop_dict = {"filters": PointerProperty(type=filters),
                 "expanders": PointerProperty(type=expanders),
                 "edit_drivers": CollectionProperty(type=EditDriver),
                 "use_filters": BoolProperty(default=False),
                 "material_driver_fix": BoolProperty(default=False,
                                                     name="Material Driver Fix",
                                                     update=toggle_driver_fix,
                                                     description="Live material drivers")
                 }

    driver_gui = type('Driver_Gui', (PropertyGroup,), prop_dict)
    register_class(driver_gui)
    bpy.types.Scene.driver_gui = PointerProperty(type=driver_gui)

    # remove it for reload same file.
    # unload should be called from pre load handler
    # SOUND_DRIVERS_unload(dummy)
    print("Setting Up Driver Manager")

    dm = bpy.app.driver_namespace.get("DriverManager")
    if not dm:
        dm = DriverManager()
        bpy.app.driver_namespace["DriverManager"] = dm
    else:
        dm.edit_driver = None


@persistent
def SOUND_DRIVERS_unload(dummy):
    debug.print("SPEAER_TOOLS_unload")

    try:
        #global dm
        dm = bpy.app.driver_namespace.get("DriverManager")
        if dm:
            dm.clear()
            print("Clearing Driver Manager")
    except:
        print("PROBLEM UNLOADING DM")
        pass

# this is ugly and needs fixing


def mat_driver_fix(scene):
    frame = scene.frame_current
    fcurves = [fcurve for mat in bpy.data.materials
               if hasattr(mat, "animation_data")
               and mat.animation_data is not None
               for fcurve in mat.animation_data.drivers]
    for fcurve in fcurves:
        mat = fcurve.id_data
        attr = fcurve.data_path
        sp = attr.split(".")
        if len(sp) > 1:
            attr = sp.pop()
            mat = mat.path_resolve(".".join(sp))
        index = fcurve.array_index
        value = fcurve.evaluate(frame)
        ob = mat.path_resolve(attr)
        if type(ob).__name__ in ["Vector", "Color", "bpy_props_array"]:
            ob[index] = value
        else:
            setattr(mat, attr, value)


class SoundDriver():
    _index = 0
    _min = 0

    is_color = False

    def check_driver(self):
        ''' check driver against gui driver '''
        # could flag the bad var here.
        dic = {}
        from_driver = self
        td = self.fcurve.driver
        fd = self.gui_driver.driver

        if fd is None:
            return False

        if td.type != fd.type:
            return False
        #td.expression = fd.expression
        for var in fd.variables:
            v = td.variables.get(var.name)
            if v is None:
                dic[var.name] = False
                return False
            if v.name != var.name:
                return False
            if v.type != var.type:
                return False
            for i, target in var.targets.items():
                if var.type == 'SINGLE_PROP':
                    if v.targets[i].data_path != target.data_path:
                        return False
                if v.targets[i].id != target.id:
                    return False
                if v.targets[i].transform_type != target.transform_type:
                    return False
                if v.targets[i].transform_space != target.transform_space:
                    return False
                if v.targets[i].bone_target != target.bone_target:
                    return False
        return True

    def _get_is_monkey(self):
        if self.fcurve is None:
            return False
        driver = self.fcurve.driver
        if len(driver.variables) == 1 \
                and driver.variables[0].name == "var" \
                and driver.variables[0].targets[0].id is None:
            return True
        return False
    is_monkey = property(_get_is_monkey)

    def demonkify(self):
        var = self.fcurve.driver.variables.get("var")
        if var:
            self.fcurve.driver.variables.remove(var)

    is_rgba_color = False
    _driven_object = "None"

    def _set_driven_object(self, obj):
        ''' set the driven object of driver '''
        if (self.is_node
                and (self.collection_name == "scenes"
                     or self.collection_name == "lamps"
                     or self.collection_name == "materials"
                     or self.collection_name == "textures")
                and obj is not None):
            self._driven_object = "%s.node_tree" % repr(obj)
            return

        if obj is not None:
            txt = repr(obj)
            if txt.find("...") > 0:
                if self.fcurve is not None:
                    txt = "%s.%s" % (self.fcurve.id_data, self.data_path)
                elif self.is_node:
                    txt = 'bpy.data.node_groups["%s"]' %\
                        (self.object_name)
                    self.text = "NODEEEE"

            self._driven_object = txt

    def _get_driven_object(self):
        try:
            return(eval(self._driven_object))
        except:
            return None

    driven_object = property(_get_driven_object, _set_driven_object)

    def validate(self):
        '''
        Check if the Driver is Valid
        '''
        try:
            if self.is_node:
                if self.collection_name == "scenes":
                    self.driven_object.path_resolve(self.data_path)
                else:
                    self.driven_object.path_resolve(self.data_path)
            else:
                self.fcurve.id_data.path_resolve(self.fcurve.data_path)
        except:
            return False
        return True

    _vd = {}

    def get_driver_fcurve(self):
        # fix for nodes
        if self.is_node:
            if self.collection_name == "scenes":
                obj = self.driven_object
            else:
                obj = self.driven_object
        else:
            obj = getattr(bpy.data, self.collection_name).get(self.object_name)
        if obj is None:
            return None
        ad = getattr(obj, "animation_data")
        if ad is None:
            return None
        drivers = [d for d in ad.drivers
                   if d.data_path == self.data_path and
                   d.array_index == self.array_index]
        if not len(drivers):
            return None

        if self.is_node:
            pass

        return drivers[0]

    fcurve = property(get_driver_fcurve)

    def _get_is_modifier(self):
        return self.data_path.startswith("modifiers")

    is_modifier = property(_get_is_modifier)

    def _get_is_constraint(self):
        return self.data_path.startswith("constraints")

    is_constraint = property(_get_is_constraint)

    def _getvariabledict(self):
        vars = self.fcurve.driver.variables
        vd = self._vd = {}
        for v in vars:
            t = v.targets[0].id
            if t:
                tn = vd.get(t.name)
                if not tn:
                    tn = vd[t.name] = []
                tn.append(v)
            else:
                nn = vd.get("None")
                if not nn:
                    nn = vd["None"] = []
                nn.append(v)

        return vd

    vd = property(_getvariabledict)

    def _getmin(self):
        do = self.driven_object
        mo = eval(self.default_value)
        x = self.fcurve.evaluate(0)
        if x < self._min:
            self._min = x
        return self._min

    def _getmax(self):
        x = self.fcurve.evaluate(0)
        if x >= self._max:
            self._max = x
        return self._max

    max = property(_getmax)
    min = property(_getmin)

    prop = ""
    is_vector = False
    text = ""

    def draw_error(self, layout):
        layout.label(text="BAD PATH", icon="ERROR")

    def draw_default(self, layout):
        fcurve = self.fcurve
        do = self.driven_object
        if not do:
            return(self.draw_error(layout))
        layout.prop(do, self.prop, index=fcurve.array_index, slider=True)

    def draw_node_slider(self, layout, context):
        l = self.data_path.split(".")
        length = len(l)
        if length > 2:
            value = l[-1]
            input_ = l[-2]
            x = ""
            for s in l[:length - 2]:
                x = "%s.%s" % (x, s)
            node = x.strip(".")

        elif length == 2:
            value = ""
            input_ = l[1]
            node = l[0]

        #debug.print("NIV", node, input_, value, self.data_path)
        node = self.driven_object.path_resolve(node)
        #row.label(node.rna_type.identifier + str(l))
        if length == 2:
            layout.prop(node, l[1])
            return None
        # check for connector

        node_input = node.path_resolve(input_)
        layout.enabled = not node_input.is_linked
        # row.label(str(node_input.is_linked))
        val = node_input.path_resolve(value)
        #node_input.draw(context, layout, node, node_input.name)
        fmt_str = "%s:%s"
        if node_input.name.lower().startswith("color"):
            fmt_str = "%%s: %c %%s" % "RGBA"[self.array_index]
        name = fmt_str % (node.name, node_input.name)
        layout.prop(node_input, "default_value", index=self.array_index,
                    text=name)
        #node_input.draw(context, row, node, "")
        #node_input.draw(context, layout, node, self.text)
        #layout.template_node_socket(color=(0.0, 0.0, 1.0, 1.0))

    def draw_slider(self, layout):
        fcurve = self.fcurve
        do = self.driven_object
        if not do:
            return(self.draw_error(layout))

        if self.is_idprop and self.prop.strip('["]') not in do.keys():
            return(self.draw_error(layout))

        layout.prop(do, self.prop,
                    text=self.text,
                    index=self.fcurve.array_index,
                    slider=True)

    def baking_draw(self, layout, scale_y=1.0):
        d = self
        dm = bpy.app.driver_namespace.get("DriverManager")
        if dm is None:
            layout.label("BAKING")
        # BAKE DRIVE DRAW METHOD NEEDED FOR DRIVER CLASS
        row = layout.row(align=True)
        pc = getattr(d, "bake_pc", 0.0)
        split = row.split(pc, align=True)
        split.scale_y = scale_y
        #split.prop(d.fcurve, "color", text="")
        if d.is_vector:
            split.prop(d.fcurve.id_data,
                       d.data_path,
                       index=d.array_index,
                       slider=True,
                       text="")
        else:
            if d.is_modifier:
                split.prop(d.driven_object, d.prop, slider=True, text="")
            else:
                split.prop(d.fcurve.id_data, d.data_path, slider=True, text="")

        split.prop(bpy.context.scene.driver_gui.edit_drivers[0], 'value', slider=True, text="")


    def __init__(self, driver, collection_name,
                 object_name, data_path, array_index):
        scene_name = None
        self.collection_name = collection_name
        sp = object_name.split("__#__")
        if len(sp) == 2:
            scene_name = sp[0]
            object_name = sp[0]

        self.object_name = object_name
        self.data_path = data_path
        self.array_index = array_index

        self.is_seq = data_path.startswith("sequence_editor.sequences_all")

        self.is_node = (data_path.startswith("node")
                        or self.collection_name == "node_groups")

        rna_type = driver.id_data.rna_type
        self.is_material = data_path.startswith("materials")\
            or rna_type.identifier.startswith("Material")
        self.is_texture = data_path.startswith("textures")
        #driver_fcurve = self.fcurve
        driver_fcurve = driver
        is_vector = False
        text = ""
        if scene_name is not None:
            #do = eval(scene_name)
            do = getattr(bpy.data, collection_name).get(scene_name)
            #do = bpy.data.scenes.get(scene_name)
        else:
            do = driver_fcurve.id_data
        mo = None
        sp = driver_fcurve.data_path.split("][")

        if len(sp) == 2:
            prop = "[%s" % sp[1]

        else:
            sp = driver_fcurve.data_path.split(".")
            prop = sp[-1]

        path = driver_fcurve.data_path.replace("%s" % prop, "")
        array_index = driver_fcurve.array_index
        xx = repr(do)
        if scene_name is not None:
            # quick node fix hack
            bpy_data_path = "bpy.data.%s['%s']" % (collection_name, scene_name)
        else:
            bpy_data_path = "%s.%s" % (xx, path)
        # quick fix for nodes
        # check for custom properties hack
        is_idprop = False
        if bpy_data_path[-1] == '.':
            bpy_data_path = bpy_data_path[:-1]

        try:
            do = eval(bpy_data_path)
        except:
            pass
            # check for nodes
        finally:
            do = None
        # bone custom props of form bone["xx"]["prop"]

        # find the "]["

        if prop.startswith("["):
            do = driver.id_data
            is_idprop = True
        else:
            try:
                do = eval(bpy_data_path)
            except:
                do = None
            try:
                mo = do.path_resolve(prop)
            except:
                mo = None

        if do is None:
            is_vector = False
            text = "BAD_PATH"
            can_edit = False

        elif is_idprop:
            text = prop.strip('["]')

        elif isinstance(mo, Vector):
            is_vector = True
            axis = "XYZ"[array_index]
            text = "%s %s" % (axis, do.bl_rna.properties[prop].name)
            mo = mo[array_index]

        elif isinstance(mo, Euler):
            is_vector = True
            axis = mo.order[array_index]
            text = "%s %s" % (axis, do.bl_rna.properties[prop].name)
            mo = mo[array_index]

        elif isinstance(mo, Quaternion):
            is_vector = True
            axis = "WXYZ"[array_index]
            text = "%s %s" % (axis, do.bl_rna.properties[prop].name)
            mo = mo[array_index]

        elif isinstance(mo, Color):
            is_vector = True
            '''
            driver.color = (0,0,0)
            driver.color[array_index] = 1
            '''
            self.is_color = True
            rgb = "RGB"[array_index]
            text = "%s %s" % (rgb, do.bl_rna.properties[prop].name)
            mo = mo[array_index]

        elif type(mo).__name__ == "bpy_prop_array":
            is_vector = True
            if prop == "color":
                self.is_rgba_color = True
                axis = "RGBA"[array_index]
                text = "%s %s" % (axis, do.bl_rna.properties[prop].name)
            else:
                text = "%s[%d]" % (do.bl_rna.properties[prop].name,
                                   array_index)
            mo = mo[array_index]

        elif not self.is_node:
            is_vector = False
            if prop in do.bl_rna.properties.keys():
                text = do.bl_rna.properties[prop].name
            else:
                text = "PROBLEM"

        self.driven_object = do
        self.default_value = repr(mo)
        self.is_vector = is_vector
        self.is_idprop = is_idprop
        self.prop = prop
        self.text = text

    def edit(self, layout):
        gui = self.gui
        if gui is None:
            return None
        if self.fcurve is None:
            layout.label(text="Driver Problems")
            return None
        driver = self.fcurve.driver
        box = layout
        row = box.row(align=True)
        row.enabled = False
        row.prop(self.fcurve, "data_path", text="", icon="RNA")
        if self.is_vector:
            sub = row.row()
            sub.alignment = 'RIGHT'
            sub.prop(self.fcurve, "array_index", text="")
        row = box.row()
        row.prop(driver, "type")
        if driver.type == 'SCRIPTED':
            row = box.row()
            row.prop(driver, "expression", text="Expr")
            row.operator("drivermanager.input_text", text="", icon="SCRIPT")
        '''
        row = box.row()
        row.label("min:%.2f max:%.2f" % (self.min,self.max))
        '''

        varbox = box.box()

        for tn, varlist in self.vd.items():
            if tn == "None":
                continue

            target = varlist[0].targets[0]
            row = varbox.row()
            row.alignment = 'LEFT'
            row.label("", icon_value=row.icon(target.id))
            #row.prop(target.id, "name", text="")
            row.label(target.id.name)
            if target.data_path.startswith("node_tree"):
                row.label("(node_tree)", icon='NODETREE')

            for var in varlist:
                target = var.targets[0]
                row = varbox.row(align=True)
                row.scale_y = 0.5
                col2 = row
                # FIX THIS
                sub = col2.row()
                sub.scale_y = 0.5
                sub.alignment = 'LEFT'
                sub.label(var.name)

                if var.type == 'SINGLE_PROP':
                    dp = target.data_path
                    if len(dp) == 0:
                        col2.label("No data_path")
                        continue

                    p = dp
                    suffixes = ["rgba", "xyz", "wxyz"]
                    found = False
                    for suffix in suffixes:
                        if found:
                            break
                        for i, ch in enumerate(suffix):
                            if p.endswith(".%c" % ch):
                                dp = "%s[%d]" % (p[:-2], i)
                                found = True
                                break

                    p = dp.strip(']')
                    i = -1

                    idx = -1
                    while p[-1].isnumeric():
                        i += 1
                        idx += 10 ** i + int(p[-1])
                        p = p[:-1]
                        p = p.strip('[')

                    try:
                        if i > -1:
                            path = p
                            col2.prop(target.id, path, index=idx, slider=True)
                        elif target.data_path.startswith("node_tree"):
                            ntree = target.id.node_tree
                            p = target.data_path.replace("node_tree.", "")
                            p = p.replace(".default_value", "")
                            i = p.find(".inputs")
                            sp = p[:i]
                            i = i + 1
                            ps = p[i:]

                            node = ntree.path_resolve(sp)
                            input = node.path_resolve(ps)
                            name = "%s:%s" % (node.name, input.name)
                            col2.prop(input, "default_value", text=name,
                                      icon='NODE')

                            #col2.template_node_view(ntree, node, input)
                        else:
                            try:
                                mo = target.id.path_resolve(target.data_path)

                                col2.prop(target.id,
                                          target.data_path,
                                          slider=True)
                            except:
                                col2.label("%s = %.2f" % (dp, mo))
                    except:
                        col2.label("ERROR")
                elif var.type == 'TRANSFORMS':
                    target = var.targets[0]
                    x = self.locs.get(var.name, None)
                    if target is None:
                        continue
                    tt = target.transform_type.replace("LOC_",
                                                       "Location ")
                    tt = tt.replace("ROT_", "Rotation ")
                    tt = tt.replace("SCALE_", "Scale ")
                    ts = target.transform_space.replace("_SPACE", "")
                    if x is not None:
                        desc = "%s (%s) %f" % (tt, ts, x)
                        col2.label(desc)
                    else:
                        op = row.operator("driver.edit",
                                          text="Update Dependencies",
                                          icon='FILE_REFRESH')
                        op.dindex = self.index
                        op.update = True
                else:
                    col2.label("%s TYPE" % var.type)
                op = row.operator("dm.remove_driver_var", text="", icon="X")
                op.varname = var.name

        invalid_targets = self.vd.get("None")
        if invalid_targets:
            row = box.row()
            row.label("Variables")
            ivarbox = box.box()
            for v in invalid_targets:
                row = ivarbox.row()
                row.alert = True
                row.label("%s has no valid target" % v.name, icon='ERROR')
                op = row.operator("dm.remove_driver_var", text="", icon="X")
                op.varname = v.name

        row = layout.row()
        if not self.check_driver():
            row.scale_y = 0.5
            op = row.operator("driver.edit",
                              text="Update Dependencies",
                              icon='FILE_REFRESH')
            op.update = True
            row = layout.row()

        d = self.fcurve
        layout = row
        layout = layout.box()
        row = layout.row(align=True)
        row.prop_search(gui,
                        "varname",
                        d.driver,
                        "variables",
                        icon='VIEWZOOM',
                        text="EDIT")
        row.operator("driver.new_var", icon="ZOOMIN", text="")
        if gui.var_index < 0 or gui.var_index >= len(d.driver.variables):
            return
        var = d.driver.variables[gui.var_index]

        #layout.label("%3f" % d.evaluate(0))
        row = layout.row(align=True)
        row.prop(var, "name", text="")
        op = row.operator("dm.remove_driver_var", text="", icon='X')
        op.varname = var.name
        row = layout.row()
        row.prop(var, 'type', text="")

        for i, target in enumerate(var.targets):
            row = layout.row(align=True)
            row.label("Target %d" % i)
            #row.template_ID(target, "id_type")
            row.prop(target, "id_type", text="")
            row.prop(target, "id", text="")
            if var.type in ['TRANSFORMS', 'LOC_DIFF', 'ROTATION_DIFF']:
                if target.id and target.id.type == 'ARMATURE':
                    layout.prop_search(target,
                                       "bone_target",
                                       target.id.data,
                                       "bones",
                                       text="Bone")

            if var.type in ['TRANSFORMS']:
                layout.prop(target, "transform_type")
                layout.prop(target, "transform_space")
            if var.type in ['LOC_DIFF']:
                layout.prop(target, "transform_space")
            if var.type == 'SINGLE_PROP':
                layout.prop(var.targets[0], "data_path", icon='RNA')

    def inputs(self, layout):
        box = layout.box()
        # inputs
        for var in self.fcurve.driver.variables:
            row = box.row()
            # row.label(var.name)
            target = var.targets[0]
            if target.id:
                row.label(var.name)
                row.prop(target.id, target.data_path, slider=True)


class DriverManager():
    _edit_driver = None
    _filterdic = {}
    ticker = 0
    _all_drivers_list = []

    def index(self, driver):
        try:
            index = self._all_drivers_list.index(driver)
        except:
            index = -1
        return index

    def find(self, index):
        ''' return a driver from the index '''
        if index not in range(len(self._all_drivers_list)):
            return None
        return self._all_drivers_list[index]

    def copy_driver(self, from_driver, target_fcurve):
        ''' copy driver '''
        td = target_fcurve.driver
        fd = from_driver.fcurve.driver
        td.type = fd.type
        td.expression = fd.expression
        for var in fd.variables:
            v = td.variables.new()
            v.name = var.name
            v.type = var.type
            if from_driver.is_monkey:
                continue
            for i, target in var.targets.items():
                if var.type == 'SINGLE_PROP':
                    v.targets[i].id_type = target.id_type
                    v.targets[i].data_path = target.data_path
                v.targets[i].id = target.id
                v.targets[i].transform_type = target.transform_type
                v.targets[i].transform_space = target.transform_space
                v.targets[i].bone_target = target.bone_target

    def check_deleted_drivers(self):
        fcurves = [d.fcurve for d in self.all_drivers_list]
        if None in fcurves:
            self.get_all_drivers_list()

    def check_added_drivers(self, obj):
        if obj is None:
            return False
        fcurves = [d.fcurve for d in self.all_drivers_list]
        obj_fcurves = []
        if hasattr(obj, "animation_data") and obj.animation_data is not None:
            obj_fcurves = [d for d in obj.animation_data.drivers]
            # check the object fcurves are in the fcurves coll
            for fc in obj_fcurves:
                if fc not in fcurves:
                    self.get_all_drivers_list()
        return False

    def _get_adl(self):
        for i, d in enumerate(self._all_drivers_list):
            d.index = i
        return self._all_drivers_list

    all_drivers_list = property(_get_adl)
    _dels = []
    updates = 0

    def get_all_drivers_list(self):
        '''
        Searches for all drivers in a blend
        '''
        for sd in self._all_drivers_list:
            if (not sd.validate()
                    or (sd.driven_object is None)
                    or sd.fcurve
                    is None):
                self.updates += 1
                self._all_drivers_list.remove(sd)

        self._dels = [n.fcurve for n in self._all_drivers_list]
        for collname in bpy_collections:
            # hack for nodes
            if collname in ["lamps", "materials", "textures"]:
                coll = getattr(bpy.data, collname)
                collection = [l for l in coll]
                collection.extend([(l, l.node_tree)
                                   for l in coll
                                   if l.use_nodes])
            elif collname == "scenes":
                collection = [s for s in bpy.data.scenes]
                collection.extend([(s, s.node_tree)
                                   for s in bpy.data.scenes
                                   if s.use_nodes])
                collection.extend([(s, s.sequence_editor.sequences_all)
                                   for s in bpy.data.scenes
                                   if s.sequence_editor is not None])
            else:
                collection = getattr(bpy.data, collname, None)
            if collection is None:
                continue

            # make a new entry for collection

            if not len(collection):
                continue

            scene = None
            for ob in collection:
                if isinstance(ob, tuple):
                    # it's a freaken node.. why not in bpy.data... grumble.
                    colln = "%s.%s" % (repr(ob[0]), repr(ob[1]))
                    scene = ob[0]
                    ob = ob[1]
                if (hasattr(ob, 'animation_data')
                        and ob.animation_data is not None):
                    drivers = [d for d in ob.animation_data.drivers]
                    if not len(drivers):
                        continue

                    for d in drivers:
                        if d not in self._dels\
                                and not d.data_path.startswith("driver_gui"):
                            self.updates += 1
                            dp = d.data_path
                            ix = d.array_index
                            print("Driver",
                                  collname,
                                  ob.name,
                                  dp, ix,
                                  )
                            if scene is not None:
                                obname = "%s__#__%s" % (scene.name, ob.name)
                            else:
                                obname = ob.name
                            self._all_drivers_list.append(
                                SoundDriver(d,
                                            collname,
                                            obname,
                                            dp,
                                            ix))

        return self._all_drivers_list
        '''
        return sorted(self._all_drivers_list,
                      key=attrgetter("collection_name",
                                     "object_name",
                                     "data_path",
                                     "array_index"))
        '''

    #xxxx = property(get_all_drivers_list)

    def get_filter_dic(self):
        self._filterdic.clear()
        # for d in self._all_drivers_list:
        for d in self._all_drivers_list:
            coll = self._filterdic.setdefault(d.collection_name, {})
            obj = coll.setdefault(d.object_name, {})
            dp = obj.setdefault(d.data_path, {})
            ai = dp.setdefault(d.array_index, self._all_drivers_list.index(d))
        return self._filterdic

    filter_dic = property(get_filter_dic)

    def clear(self):
        self._PanelInvader(remove_only=True)
        # mute all drivers
        for d in self._all_drivers_list:
            if (d.fcurve.driver.expression.startswith("SoundDrive")
                    or d.fcurve.driver.expression.startswith("GetLocals")):
                d.fcurve.driver.is_valid = False
        # clear the drivers list
        self._all_drivers_list = []
        # del(bpy.app.driver_namespace['DriverManager'])
        #self = None

        return

    def __init__(self):
        self.get_all_drivers_list()
        self.updates = 0
        self.updated = False
        self.updating = False
        self._edit_driver = None
        self._PanelInvader()
        # quick fix
        for d in self._all_drivers_list:
            if d.fcurve is None:
                continue
            if (d.fcurve.driver.expression.startswith("SoundDrive")
                    or d.fcurve.driver.expression.startswith("GetLocals")):
                d.fcurve.driver.is_valid = True

    def is_sound_driver(self, driver):
        if driver.driver.expression.startswith("SoundDrive"):
            return True
        return False

    def query_driver_list(self, collname, id_path, data_path, array_index):
        try:
            return(self.all_drivers[collname][id_path][data_path][array_index])
        except:
            return(None)

    # gui settings

    def draw_menus(self, layout, context):
        layout = layout.layout
        layout.alignment = 'LEFT'

        # layout.template_header(menus=True)
        layout.menu("drivermanager.tools_menu", text="", icon="MENU_PANEL")
        #layout.operator("driver_manager.settings", emboss=False)
        #row.menu("OBJECT_MT_custom_menu", text="Tools")

    _edit_driver_gui = None

    _setting_channels = False

    def set_edit_driver_gui(self, context, create=False):
        self._setting_channels = True
        '''Return the edit_driver_gui'''
        '''
        if self._edit_driver_gui is not None:
            return self._edit_driver_gui
        '''
        scene = context.scene
        if (hasattr(scene, "animation_data")
                and scene.animation_data is not None):
            for d in scene.animation_data.drivers:
                if d.data_path.startswith("driver_gui"):
                    scene.driver_remove(d.data_path)

        eds = scene.driver_gui.edit_drivers
        ed = None
        d = self._edit_driver
        if d is not None:
            for e in eds:
                if e.collection != d.collection_name:
                    continue
                if e.object != d.object_name:
                    continue
                if e.data_path != d.data_path:
                    continue
                if e.array_index != d.array_index:
                    continue
                # if we are here we have it
                ed = e
                break

            # create a gui
            if ed is None:
                ed = eds.add()
                ed.collection = d.collection_name
                ed.object = d.object_name
                ed.data_path = d.data_path
                ed.array_index = d.array_index
            # set up channels
            dummy, args = get_driver_settings(d.fcurve)
            # add a driver to the value
            ed.driver_remove('value')
            test_driver = ed.driver_add('value')
            self.copy_driver(d, test_driver)
            test_driver.driver.type = 'SCRIPTED'
            test_driver.driver.expression = 'GetLocals(locals())'
            cs = context.scene.speaker
            a = getAction(cs)

            for arg in args:
                k, v = arg.split("=")
                if k in ed.bl_rna.properties.keys():
                    # get the prop type
                    p = ed.bl_rna.properties.get(k)
                    if p.rna_type.identifier.startswith("FloatP"):
                        setattr(ed, k, float(v))
                    elif p.rna_type.identifier.startswith("IntP"):
                        setattr(ed, k, int(v))
                    elif p.rna_type.identifier.startswith("Enum"):
                        setattr(ed, k, v.strip("'"))
                    else:
                        setattr(ed, k, v)

            if a is not None and cs is not None:
                cn = a["channel_name"]
                channels = a["Channels"]
                chs = [ch for ch in ed.channels if ch.name.startswith(cn)]
                exist = len(chs) == channels
                if not exist:
                    for ch in chs:
                        print("removing channel:", ch.name)
                        ed.channels.remove(ed.channels.find(ch.name))
                driver = d.fcurve.driver
                if True:  # len(chs) != channels:
                    for i in range(0, channels):
                        channel = chs[i] if exist else ed.channels.add()
                        channel.name = "%s%d" % (cn, i)
                        if channel.name in driver.variables.keys():
                            dvar = driver.variables[channel.name]
                            if dvar.targets[0].id == cs:
                                channel.value = True
                            else:
                                # variable there but with other speaker alert
                                pass
                        else:
                            channel.value = False

        self._edit_driver_gui = ed
        if d is not None:
            setattr(d, "gui", ed)
            setattr(d, "gui_driver", test_driver)
        self._setting_channels = False
        return ed

    def set_edit_driver(self, driver):
        ed = self._edit_driver
        if ed is not None:
            if hasattr(ed, "is_open"):
                delattr(ed, "is_open")
        self._edit_driver = driver
        self._edit_driver_gui = None
        return driver

    def get_edit_driver(self):
        return self._edit_driver

    edit_driver = property(get_edit_driver, set_edit_driver)

    def edit_draw(self, layout, context):
        scene = context.scene
        sp = scene.speaker
        action = getAction(sp)
        if sp is None or action is None:
            return None

        dm = bpy.app.driver_namespace['DriverManager']
        if dm is None:
            return
        edr = dm.edit_driver
        if edr is None:
            row = layout.row()
            row.label("NO EDIT DRIVER")

        area = context.area
        space = context.space_data

        # make a new gui for edit driver
        eds = scene.driver_gui.edit_drivers
        eds = [dm._edit_driver_gui]
        for ed in eds:
            row = layout.row()
            if ed is None:

                row.label("NO GUI")
                return
            sub = row.row()
            sub.alignment = 'LEFT'
            #col.alignment = 'LEFT'
            channel_name = action["channel_name"]
            sub.menu("soundtest.menu", text=channel_name)
            #sub = row.row()
            row.prop(action, "name", text="")

            row = layout.row(align=True)
            row.prop(action, "normalise", expand=True)
            sub = layout.row()
            sub.enabled = action.normalise != 'NONE'
            sub.prop(action, "normalise_range", text="", expand=True)
            '''

            # Debug stuff
            row.enabled = False
            row.prop(edr.fcurve, "data_path", text="", icon="RNA")
            if edr.is_vector:
                sub = row.row()
                sub.alignment = 'RIGHT'
                sub.prop(edr.fcurve, "array_index", text="")
            row.prop(ed, "collection")
            row = layout.row()
            row.prop(ed, "object")
            row = layout.row()
            row.prop(ed, "data_path")
            row.prop(ed, "array_index")
            '''
            box = layout.box()
            row = box.row()
            row.prop(ed, "op")
            row = box.row()
            row.prop(ed, "amplify")
            row = box.row()
            row.prop(ed, "threshold")
            #row = row.row(align=True)
            #row.scale_y = 0.5
            a = sp.animation_data.action
            if a is None or "channel_name" not in a.keys():
                row = box.row()
                row.label("ERROR WITH ACTION", icon='ERROR')
                return None
            cn = a['channel_name']
            channels = a['Channels']
            cols = min(int(sqrt(channels)), 16)
            #cf = row.column_flow(columns=cols, align=True)

            chs = [ch for ch in ed.channels if ch.name.startswith(cn)]
            for i, ch in enumerate(chs):
                if not i % cols:
                    row = box.row()
                #col = cf.row()
                col = row.column()
                #col.scale_y = 0.5
                # col.label(ch.name)
                col.prop(ch, 'value', text=str(i), toggle=True)
                r = col.row()
                r.scale_y = 0.4

                r.prop(sp, '["%s"]' % ch.name, slider=True, text="")
        row = layout.row()
        row.scale_y = 0.5
        '''
        row.label("INPUTS")
        row = layout.row(align=True)
        action = sp.animation_data.action
        row.prop(action, "normalise", text="", expand=False)
        row.prop(action, "normalise_range", text="", expand=True)
        '''
        row = layout.row()
        row.label("OUTPUTS")
        row = layout.row(align=True)
        # NEEDS REFACTOR
        d = edr.fcurve
        mods = getattr(d, "modifiers", None)
        gm = None
        if mods is not None:
            for mi, m in enumerate(mods):
                if m.type == 'GENERATOR':
                    gm = m
                    break
        if gm is not None:
            row.prop(gm, "coefficients", text="offset", index=0)
            row.prop(gm, "coefficients", text="amplify", index=1)
            sub = row.row()
            sub.alignment = 'RIGHT'
            op = sub.operator("editdriver.remove_modifier", icon='X', text="")
            op.idx = mi
        else:
            op = row.operator("editdriver.add_modifier")
            # op.type = 'GENERATOR' #  it's the default

    def draw_spitter(self, context):
        self.check_deleted_drivers()
        collection = 'None'
        object = 'None'
        # return collection panel
        area = context.area
        space = context.space_data

        obj = None
        ctxt = 'NONE'
        if hasattr(space, "context"):
            ctxt = space.context
        '''
        string = "%s %s" % (area.type, ctxt)
        print(string)
        '''
        if area.type.startswith('PROPERTIES'):
            if space.pin_id:
                obj = space.pin_id
            else:
                obj = context.object

            '''
            if obj is None and ctxt not in ["SCENE", "WORLD", :
                return None, None, None
            '''
            self.check_added_drivers(obj)
            if space.context.startswith('DATA'):
                obj = obj.data
                self.check_added_drivers(obj)
                object = obj.name
                if hasattr(context, 'mesh'):
                    collection = 'meshes'

                elif hasattr(context, 'metaball'):
                    collection = "metaballs"

                elif hasattr(context, 'lattice'):
                    collection = 'lattices'

            elif space.context.startswith('OBJECT'):
                panel = "OBJECT_PT_context_object"
                object = obj.name
                collection = "objects"

            elif space.context.startswith('MATERIAL'):
                collection = "materials"
                if hasattr(
                        obj, "active_material") and obj.active_material is not None:
                    object = obj.active_material.name
                    obj = obj.active_material
                    self.check_added_drivers(obj)
                else:
                    # has no active material or no materials
                    obj = None

            elif space.context.startswith('WORLD'):
                collection = "worlds"
                if hasattr(context, "world"):
                    object = context.world.name
                    obj = [context.world, context.world.light_settings]
                    self.check_added_drivers(context.world)

            elif space.context.startswith('SCENE'):
                collection = "scenes"
                obj = context.scene
                self.check_added_drivers(obj)
                object = obj.name

            elif space.context.startswith('MODIFIER'):
                collection = "objects"
                object = obj.name
                obj = [m for m in obj.modifiers]

            elif space.context.startswith('CONSTRAINT'):
                collection = "objects"
                object = obj.name
                obj = [c for c in obj.constraints]

            elif space.context.startswith('TEXTURE'):
                collection = "textures"
                mat = obj.active_material
                obj = None
                if mat is not None:
                    tex = mat.active_texture
                    if tex is not None:
                        self.check_added_drivers(mat)
                        object = tex.name
                        slot = mat.texture_slots[mat.active_texture_index]
                        obj = [slot, tex]

        elif area.type.startswith("NODE_EDITOR"):
            collection = "node_groups"
            obj = context.active_node

        return collection, object, obj

    # The menu can also be called from scripts
    def get_object_dic(self, collection, object):
        dm = self
        if dm is None:
            return
        dic = dm.filter_dic
        if collection not in dic.keys():
            return {}
        dic = dic[collection]
        if object not in dic.keys():
            return {}
        dic = dic[object]

        return dic

    def draw_layout(self, layout, context, drivers):
        box = layout.column()

        for d in drivers:
            row = box.row(align=True)
            if d.fcurve is None:
                wm = context.window_manager
                sub = row.row()
                sub.alignment = 'LEFT'
                sub.prop(wm, "update_dm", text="", icon='FILE_REFRESH')
                row.label("NO FCurve Info", icon='INFO')
                continue
                # buggered
            buttoncol = row.column(align=True)
            buttoncol.alignment = 'LEFT'
            col = row.column()
            edop = buttoncol.operator("driver.edit",
                                      emboss=False,
                                      icon='TRIA_RIGHT',
                                      text="")

            edop.toggle = True
            try:
                edop.dindex = self._all_drivers_list.index(d)
            except:
                buttoncol.alert = True
                #row.disabled = True
                edop.dindex = -1
            #dm.driver_draw(d, row)
            self.driver_draw(d, col)
            if getattr(d, "is_open", False):
                ed = True
                row = box.row(align=True)
                leftcol = row.column()
                leftcol.alignment = 'LEFT'

                if getattr(d, "gui", None) is not None:
                    leftcol.prop(d.gui, "gui_type",
                                 text="",
                                 expand=True,
                                 icon_only=True)

                if d.is_monkey:
                    op = leftcol.operator("drivermanager.demonkify", text="",
                                          icon='MONKEY')
                    op.driver_index = d.index
                leftcol.operator("editdriver.bake2fcurves",
                                 text="", icon='FCURVE')

                rightcol = row.column()

                ebox = rightcol.box()
                '''
                if getattr(d, "edit_driver_baking", False):
                    d.baking_draw(ebox)

                '''
                ebox.enabled = not getattr(d, "edit_driver_baking", False)
                if getattr(self, "_edit_driver_gui", None) is None:

                    ebox.label("UH OH", icon='ERROR')
                    delattr(d, "is_open")
                elif self._edit_driver_gui.gui_type == "STD":
                    d.edit(ebox)
                elif self._edit_driver_gui.gui_type == "SPK":
                    UserPrefs = context.user_preferences
                    if not UserPrefs.system.use_scripts_auto_execute:
                        ebox.label("AUTO SCRIPTS NOT ENABLED", icon='ERROR')
                        row = ebox.row()
                        row.prop(UserPrefs.system, "use_scripts_auto_execute")
                    elif not len(context.scene.soundspeakers):
                        ebox.label("NO DRIVER SPEAKERS")
                        speakers = [s for s in context.scene.objects
                                    if s.type == 'SPEAKER']
                        if len(speakers):
                            row = ebox.row()
                            row.label("Please set up the speaker")
                        else:
                            ebox.operator("object.speaker_add")
                    elif context.scene.speaker is None:
                        ebox.label("NO CONTEXT SPEAKER")
                        ebox.menu("speaker.select_contextspeaker")
                    else:
                        self.edit_draw(ebox, context)

    def panel_draw_menu(self, panel, context):
        layout = panel.layout
        row = layout.row()
        sub = row.row()
        sub.alignment = 'LEFT'
        wm = context.window_manager
        sub.prop(wm, "update_dm", text="", icon='FILE_REFRESH')

        row.menu('drivermanager.menu', icon='DRIVER')

    def panel_draw(self, panel, context):
        def node_name(str):
            name = str.replace('nodes["', '')
            name = name[:name.find(']') - 1]
            return name

        dm = self
        layout = panel.layout
        collection, ob, obj = self.draw_spitter(context)
        '''
        dic = self.get_object_dic(collection, ob)
        for key in dic.keys():
            row = layout.row()
            row.label(key)
        '''
        if obj is None:
            return None
        if isinstance(obj, list):
            drivers = [d for d in self._all_drivers_list
                       if d.driven_object in obj]

        elif obj.rna_type.identifier.find('Node') > 0:
            drivers = [d for d in self._all_drivers_list
                       if d.is_node
                       and node_name(d.fcurve.data_path)
                       == context.active_node.name]
        else:
            '''
            drivers = [d for d in self._all_drivers_list
                       if d.driven_object == obj]
            '''
            drivers = [d for d in self._all_drivers_list
                       if (d.collection_name == collection
                           and d.object_name == obj.name)
                       or d.driven_object == obj]

        #print(len(drivers),  ob, obj)
        self.draw_layout(layout, context, drivers)

    def _PanelInvader(self, remove_only=False):
        panels = ["SCENE_PT_scene",
                  "OBJECT_PT_context_object",
                  "DATA_PT_context_mesh",
                  "MATERIAL_PT_context_material",
                  "TEXTURE_PT_context_texture",
                  "OBJECT_PT_constraints",
                  "DATA_PT_modifiers",
                  "DATA_PT_context_metaball",
                  "WORLD_PT_context_world",
                  "DATA_PT_context_lattice",
                  "DATA_PT_context_lamp",
                  "NODE_PT_active_node_generic",
                  "Cycles_PT_context_material"]

        for p in panels:
            pt = getattr(bpy.types, p, None)
            if pt is None:
                continue
            draw_funcs = [f for f in pt._dyn_ui_initialize()
                          if f.__name__.startswith("panel_draw")]

            bpy.utils.unregister_class(pt)
            for f in draw_funcs:
                pt.remove(f)
            if not remove_only:
                pt.append(self.panel_draw_menu)
                pt.append(self.panel_draw)
            bpy.utils.register_class(pt)

    def panel_shutter(self):
        import bl_ui
        prop_mods = [mod for mod in dir(bl_ui) if mod.startswith('properties')]
        for k in prop_mods:
            prop_mod = getattr(bl_ui, k)
            panels = [p for p in dir(prop_mod) if p.find("_PT_") > 1]

        # panel_shutter()

    def draw_filters(self, layout, context):
        layout = layout.layout
        scene = context.scene
        gui = scene.driver_gui
        filters = gui.filters
        filterrow = layout.row(align=True)
        sub = filterrow.row()
        sub.alignment = 'LEFT'
        wm = context.window_manager
        sub.prop(wm, "update_dm", text="", icon='FILE_REFRESH')
        filterrow.prop(gui, "use_filters", text="", icon='FILTER', toggle=True)

        # for key in self.get_driver_dict().keys():
        row = filterrow.row(align=True)

        row.enabled = gui.use_filters
        for key in self.filter_dic:
            row.prop(filters, key, text="", icon=get_icon(key), toggle=True)

    def driver_draw(self, sounddriver, layout):
        # move to isMonkey
        def driver_icon(fcurve):
            driver = fcurve.driver
            if len(driver.variables) == 1 \
                    and driver.variables[0].name == "var" \
                    and driver.variables[0].targets[0].id is None:
                return 'MONKEY'
            return 'DRIVER'

        i = 0

        driver = sounddriver.fcurve
        if not driver:
            return None
        box = layout
        icon = driver_icon(driver)
        can_edit = True
        row = box.row(align=True)
        if self.updating:
            row.label("UPDATING")
            row.alert = True
            return
        row.enabled = can_edit
        #row.alignment = 'RIGHT'

        #row.prop(driver.driver, "is_valid", text="", icon=icon)
        row.prop(driver, "mute", text="", icon=icon)
        colrow = row.row()
        colrow.scale_x = 0.3
        colrow.alignment = 'LEFT'
        colrow.prop(driver, "color", text="", icon=icon)
        if sounddriver.is_node:
            # quick hack need to pass context or refactor
            sounddriver.draw_node_slider(row, bpy.context)
        else:
            # sounddriver.
            if getattr(sounddriver, "edit_driver_baking", False):
                sounddriver.baking_draw(row)
            else:
                sounddriver.draw_slider(row)

        row.prop(driver.driver, "is_valid", text="", icon=icon)
        #row = row.row(align=True)
        #row.alignment = 'RIGHT'
        format_data_path(row, driver.data_path, True, padding=1)
        #propcol = row.row()
        #propcol.alignment = 'RIGHT'
'''
Operators
'''


class AddDriverVar(Operator):
    """Add Driver Variable"""
    bl_idname = "driver.new_var"
    bl_label = "Add Driver Variable"

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        dm = bpy.app.driver_namespace.get("DriverManager")
        # check if var is in variables
        name = "var"
        i = 1
        while name in dm.edit_driver.fcurve.driver.variables.keys():
            name = "var%d" % i
            i += 1
        v = dm.edit_driver.fcurve.driver.variables.new()
        v.name = name
        dm._edit_driver_gui.varname = v.name
        return {'FINISHED'}


class EditTextFieldOperator(Operator):
    """Edit Text Field in Popup"""
    bl_idname = "drivermanager.input_text"
    bl_label = "Text Input"

    @classmethod
    def poll(cls, context):
        dm = bpy.app.driver_namespace.get("DriverManager")
        return dm is not None and dm.edit_driver is not None

    def draw(self, context):
        dm = bpy.app.driver_namespace.get("DriverManager")
        driver = dm.edit_driver.fcurve.driver
        layout = self.layout
        row = layout.row()

        row.label("Driver Scripted Expression", icon='DRIVER')
        row = layout.row()
        row.prop(driver, "expression", text="")

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_popup(self, width=800)

    def execute(self, context):
        return {'FINISHED'}


class UpdateDriverlistOperator(Operator):
    """Driver Manager Update"""
    bl_idname = "drivermanager.update"
    bl_label = "Driver Manager Update"
    name = StringProperty(default="")

    @classmethod
    def poll(cls, context):
        #global dm
        return True
        return(dm is not None)

    def execute(self, context):
        dm = bpy.app.driver_namespace.get("DriverManager")
        if not dm:
            SOUND_DRIVERS_load(context.scene)
        '''
        else:
            # update the driver list.
            dm.driver_dict = dm.get_driver_dict()
        #global dm
        '''
        return {'FINISHED'}


class DriverSelectorOperator(Operator):
    """Select Driver"""
    bl_idname = "driver.edit"
    bl_label = "Select Driver"
    dindex = IntProperty(default=0, options={'SKIP_SAVE'})
    array_index = IntProperty(default=0)
    data_path = StringProperty(default="")
    col = StringProperty(default="")
    name = StringProperty(default="")
    toggle = BoolProperty(default=False, options={'SKIP_SAVE'})
    update = BoolProperty(default=False, options={'SKIP_SAVE'})

    driver = None

    @classmethod
    def poll(cls, context):
        #global dm
        dm = bpy.app.driver_namespace.get("DriverManager")
        return(dm is not None)

    def invoke(self, context, event):
        dm = bpy.app.driver_namespace.get("DriverManager")
        if dm is None:
            return {'CANCELLED'}
        scene = context.scene
        eds = scene.driver_gui.edit_drivers
        # dm.check_updates(context)

        driver = dm.all_drivers_list[self.dindex]
        is_open = getattr(driver, "is_open", False)

        if self.update:
            #dm.edit_driver = driver
            dm.set_edit_driver_gui(context, create=True)
            return {'FINISHED'}
        elif self.toggle:
            setattr(driver, 'is_open', not is_open)
            if driver.is_open:
                dm.edit_driver = driver
                dm.set_edit_driver_gui(context, create=True)
                return {'FINISHED'}
        if driver == dm.edit_driver:
            dm.edit_driver = None
            return {'CANCELLED'}
        return {'FINISHED'}

        self.driver = driver
        return self.execute(context)

    def execute(self, context):

        return {'FINISHED'}


class Bake2FCurveOperator(bpy.types.Operator):
    """(un)Bake Driver to Action"""
    bl_idname = "editdriver.bake2fcurves"
    bl_label = "Bake to FCurve"
    selection = BoolProperty(default=False, options={'SKIP_SAVE'})

    def get_drivers(self):
        dns = bpy.app.driver_namespace
        dm = dns.get("DriverManager")
        if dm is None:
            return None

        if self.selection:
            return [d for d in dm.all_drivers_list]
        return [dm.edit_driver]

    chunks = 50
    wait = 0
    driver = None
    drivers = None
    _timer = None
    pc = 0
    _pc = 0  # where we're up to
    f = 0  # start frame
    bakeframes = []

    def is_baking(self):
        return self.pc < self.chunks
    baking = property(is_baking)

    def modal(self, context, event):
        if event.type in {'RIGHTMOUSE', 'ESC'}:
            return self.cancel(context)

        if self.wait > 0:
            self.wait -= 1
            return {'PASS_THROUGH'}

        if self.pc >= self.chunks:
            return self.finished(context)

        if event.type == 'TIMER':
            for d in self.drivers:
                self.driver = d
                self.bake(context)
            self.f += self.bakeframes[self.pc]
            self.pc += 1
            self.wait = 5

        return {'PASS_THROUGH'}

    def remove(self, context):
        # remove the fcurve if there is one and return finished.
        driver = self.driver.fcurve
        obj = driver.id_data
        if obj.animation_data.action is not None:
            raction = obj.animation_data.action
            fcurves = [fcurve for fcurve in raction.fcurves
                       if fcurve.data_path == driver.data_path
                       and fcurve.array_index == driver.array_index]
            if len(fcurves):
                # remove the fcurve and return
                raction.fcurves.remove(fcurves[0])
                # remove the action if empty
                if not len(raction.fcurves):
                    obj.animation_data.action = None
                    if not raction.users:
                        bpy.data.actions.remove(raction)
                return True
        return False

    def bake(self, context):
        scene = context.scene
        frame = self.f
        frame_end = self.f + self.bakeframes[self.pc] - 1
        # bake to scene frame range
        self.driver.edit_driver_baking = True
        setattr(self.driver, "bake_pc", self.pc / self.chunks)
        driver = self.driver.fcurve
        obj = driver.id_data

        #action = speaker.animation_data.action

        # make an unbaked fcurve for the driver.
        # check whether there is already an fcurve

        while frame <= frame_end:
            scene.frame_set(frame)
            # quick fix try array, then without
            try:
                driver.id_data.keyframe_insert(driver.data_path,
                                               index=driver.array_index)
            except:
                driver.id_data.keyframe_insert(driver.data_path)
                #print("Error in baking")
            finally:
                frame = frame + 1
        return True

    def execute(self, context):
        scene = context.scene

        self.drivers = self.get_drivers()
        print(len(self.drivers))
        r = []
        for d in self.drivers:
            self.driver = d
            if self.remove(context):
                print("REMOVE", d)
                r.append(d)
        for d in r:
           self.drivers.remove(d)
        print(len(self.drivers))
        if not len(self.drivers):
            return {'FINISHED'}

        self.scene_frame = scene.frame_current
        self.f = scene.frame_start
        frames = scene.frame_end - scene.frame_start
        bakeframes = [frames // self.chunks for i in range(self.chunks)]
        bakeframes[-1] += frames % self.chunks
        self.bakeframes = bakeframes

        wm = context.window_manager
        self._timer = wm.event_timer_add(0.001, context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def finished(self, context):
        for d in self.drivers:
            delattr(d, "edit_driver_baking")
            delattr(d, "bake_pc")
        scene = context.scene
        scene.frame_set(self.scene_frame)
        wm = context.window_manager
        wm.event_timer_remove(self._timer)

        return {'FINISHED'}

    def cancel(self, context):
        # scene.frame_set(scene_frame)
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        print("Baking cancelled")
        return {'CANCELLED'}


class RemoveDriverVarOperator(Operator):
    """Remove Driver Variable"""
    bl_idname = "dm.remove_driver_var"
    bl_label = "Remove Driver Variable"
    varname = StringProperty(default="")

    @classmethod
    def poll(cls, context):
        #global dm
        dm = bpy.app.driver_namespace.get("DriverManager")
        return(dm is not None)

    def execute(self, context):
        dm = bpy.app.driver_namespace.get("DriverManager")
        if dm.edit_driver is not None:
            fcurve = dm.edit_driver.fcurve
            d = fcurve.driver
            var = d.variables.get(self.varname)
            d.variables.remove(var)

            channels, args = get_driver_settings(fcurve)
            if self.varname not in channels:
                return {'FINISHED'}
            channels.pop(channels.index(self.varname))
            '''
            ctxt = str(channels).replace("'", "").replace(" ", "")
            s = d.expression
            x = s.find("SoundDrive")
            if x > -1:
                m = s.find(")",x) + 1
                fmt = s.replace(s[x:m],"%s")
            else:
                fmt = "%s"
            new_expr = 'SoundDrive(%s' % (ctxt)
            for arg in args:
                new_expr = '%s,%s' % (new_expr, arg)
            new_expr = "%s)" % new_expr
            new_expr = new_expr.replace('[,','[')
            '''
            d.expression = driver_expr(d.expression, channels, args)
            dm.set_edit_driver_gui(context)

        return {'FINISHED'}


class RGBColorFCurves(Operator):
    """Add RGB Color FCurves"""
    bl_idname = "drivermanager.rgb_color_fcurves"
    bl_label = "RGB Color FCurves"

    @classmethod
    def poll(cls, context):
        dm = bpy.app.driver_namespace["DriverManager"]
        return dm is not None

    def execute(self, context):
        dm = bpy.app.driver_namespace["DriverManager"]
        color_drivers = [d for d in dm.all_drivers_list
                         if d.fcurve is not None
                         and (d.is_color or d.is_rgba_color)
                         and d.array_index < 3]
        for d in color_drivers:
            d.fcurve.color = (0, 0, 0)
            d.fcurve.color[d.array_index] = 1
        # main(context)
        return {'FINISHED'}


class DriverManagerDemonkify(Operator):
    """Fix (Remove) Monkeys"""
    bl_idname = "drivermanager.demonkify"
    bl_label = "Demonkify"
    driver_index = IntProperty(default=-1, options={'SKIP_SAVE'})

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        dm = bpy.app.driver_namespace.get('DriverManager')
        if dm is None:
            print("No Driver Manager")
            return {'CANCELLED'}
        if self.driver_index >= 0:
            monkeys = [dm.all_drivers_list[self.driver_index]]
        else:
            monkeys = [m for m in dm.all_drivers_list if m.is_monkey]
        for m in monkeys:
            var = m.fcurve.driver.variables.get("var")
            m.fcurve.driver.variables.remove(var)
        return {'FINISHED'}


class DriverManagerSettings(Operator):
    """Driver Manager Settings"""
    bl_idname = "driver_manager.settings"
    bl_label = "Tools"

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        return bpy.ops.wm.call_menu(name="drivermanager.tools_menu")
'''
Panels
'''


class DriversManagerPanel(bpy.types.Panel):
    """Driver Tool Panel"""
    bl_label = "Driver Manager"
    bl_idname = "VIEW3D_PT_DriversManager"
    #bl_space_type = 'PROPERTIES'
    bl_space_type = "VIEW_3D"
    #bl_region_type = 'WINDOW'
    bl_region_type = "TOOLS"
    #bl_context = "object"
    #bl_options = {'DEFAULT_CLOSED'}
    bl_category = 'SoundDrive'

    @classmethod
    def poll(self, context):
        dm = bpy.app.driver_namespace.get("DriverManager")
        if not dm:
            return True
        return bool(len(dm.all_drivers_list))

    @classmethod
    def idchange(cls, s):
        cls.bl_idname = s

    def draw_header(self, context):
        scene = context.scene
        layout = self.layout
        dm = bpy.app.driver_namespace.get("DriverManager")

        if dm is not None:
            dm.draw_menus(self, context)
            pass

    def draw(self, context):

        scene = context.scene
        layout = self.layout
        dns = bpy.app.driver_namespace

        box = layout
        dm = dns.get("DriverManager")
        UserPrefs = context.user_preferences

        if not UserPrefs.system.use_scripts_auto_execute:
            row = layout.row()
            row.prop(UserPrefs.system, "use_scripts_auto_execute")
            row = layout.row()
            row.label("Warning Will not work unless Auto Scripts Enabled",
                      icon='ERROR')
            return
        if dm is None:
            #dm = DriverManager()
            box.label("No Driver Mangager", icon='INFO')
            row = box.row()
            row.operator("drivermanager.update")
            row = box.row()
            row.label("Once enabled will poll on drivers")

            return

        # dm.check_updates(context)
        row = box.row(align=True)
        if not len(dm._all_drivers_list):
            box.label("NO DRIVERS FOUND", icon='INFO')
            return
        ###dm.draw_menus(row, context)
        dm.draw_filters(self, context)
        ed = False
        settings = scene.driver_gui
        drivers_dict = dm.filter_dic
        seq_header, node_header = False, False
        for collname, collection in drivers_dict.items():
            bpy_collection = getattr(bpy.data, collname)
            # need to reorder for sequencer and nodes.
            # check for filter FIXME
            if settings.use_filters:
                if hasattr(settings.filters, collname):
                    if getattr(settings.filters, collname):
                        continue
            row = box.row()
            icon = get_icon(collname)

            if not len(collection):
                continue
            for name, object_drivers in collection.items():
                iobj = obj = bpy_collection.get(name)
                if hasattr(obj, "data") and obj.data is not None:
                    iobj = obj.data

                if not obj:
                    # a missing ob should invoke a dm refresh
                    continue
                # XXX code for context ...............................
                _filter_context_object = True
                if (collname == 'objects'
                        and _filter_context_object
                        and (obj != context.object
                             and obj not in context.selected_objects)):
                    continue

                _filter_context_scene = True
                if (collname == 'scenes'
                        and _filter_context_scene
                        and (obj != context.scene)):
                    continue

                # context world not in all spaces
                _filter_context_world = True
                if (collname == 'worlds'
                        and _filter_context_world
                        and hasattr(context, "world")
                        and (obj != context.world)):
                    continue

                row = box.row(align=True)
                row.label(text="", icon='DISCLOSURE_TRI_RIGHT')
                icon = get_icon(obj.rna_type.name)
                if hasattr(obj, "type"):
                    icon = get_icon(obj.type)

                '''
                if  context.scene.objects.active == obj:
                    row.template_ID(context.scene.objects, 'active')
                else:
                    row.label(text="", icon=icon)
                    row.prop(obj, "name", text="")


                '''
                #  TO BE REFACTORED
                row.label(text=obj.name, icon=icon)

                drivers = [dm.find(sdi)
                           for dp, ds in object_drivers.items()
                           for i, sdi in ds.items()]

                dm.draw_layout(layout, context, drivers)

        row = box.row()
        row.label("UPDATES %d" % dm.updates)
        '''
        if dm.edit_driver and not ed:
            #take out the edit driver
            dm.edit_driver = None

            row.label("OOPS")

        '''


class DriverRemoveModifier(bpy.types.Operator):
    """Remove Modifer"""
    bl_idname = "editdriver.remove_modifier"
    bl_label = "Remove Modifier"
    idx = IntProperty(name="Modifier Index", default=0)

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        dns = bpy.app.driver_namespace
        dm = dns.get("DriverManager")
        if dm is None:
            return {'CANCELLED'}
        ed = dm.edit_driver
        if ed is None:
            return {'CANCELLED'}
        mod = ed.fcurve.modifiers[self.idx]
        ed.fcurve.modifiers.remove(mod)
        return {'FINISHED'}


class DriverAddModifier(bpy.types.Operator):
    """Add Generator Modifer"""
    bl_idname = "editdriver.add_modifier"
    bl_label = "Add GENERATOR"
    # change to enum property. get list from mod types.
    type = StringProperty(default='GENERATOR')

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        dns = bpy.app.driver_namespace
        dm = dns.get("DriverManager")
        if dm is None:
            return {'CANCELLED'}
        ed = dm.edit_driver
        if ed is None:
            return {'CANCELLED'}
        ed.fcurve.modifiers.new(type=self.type)
        return {'FINISHED'}


'''
Menus
'''


class DriverMangagerToolMenu(bpy.types.Menu):
    bl_label = "Driver Manager Tools"
    bl_idname = "drivermanager.tools_menu"

    def draw(self, context):
        scene = context.scene
        layout = self.layout

        layout.menu("speaker.select_contextspeaker", icon='SPEAKER')
        layout.menu("soundtest.menu", icon="ACTION")

        op = layout.operator("editdriver.bake2fcurves", icon='FCURVE', text="Bake All")
        op.selection = True
        layout.operator("drivermanager.rgb_color_fcurves", icon='COLOR')
        layout.operator("drivermanager.demonkify", icon='MONKEY')

        # use an operator enum property to populate a sub-menu
        layout.operator_menu_enum("object.select_by_type",
                                  property="type",
                                  text="Select All by Type...",
                                  )

        layout.prop(scene.driver_gui,
                    "material_driver_fix",
                    icon='MATERIAL_DATA')


class SimpleCustomMenu(bpy.types.Menu):
    bl_label = "Driver Manager"
    bl_idname = "drivermanager.menu"

    def draw(self, context):
        layout = self.layout
        dm = bpy.app.driver_namespace['DriverManager']
        if dm is None:
            return
        area = context.area
        space = context.space_data
        ctxt = 'NONE'
        if hasattr(space, "context"):
            ctxt = space.context

        dm.draw_spitter(context)
        if area.type.startswith('PROPERTIES'):
            layout.label(space.context)
            if space.context.startswith('DATA'):
                layout.label('DATA')
            if space.context.startswith('OBJECT'):
                layout.label('OBJECT')
            if space.context.startswith('MATERIAL'):
                layout.label('MATERIAL')
            if space.context.startswith('TEXTURE'):
                layout.label('TEXTURE')
            if space.context.startswith('MODIFIER'):
                layout.label('MODIFIERS')

###########################################################
'''
Property Methods
'''


def driver_minmax(driver_fcurve):
    scene = bpy.context.scene
    # get the minmax of the driver over playback range.
    '''
    THIS IS FAR TOO HEAVY TO RUN AS A PROPERTY
    o = driver.id_data
    i = driver.array_index
    dp =driver.data_path
    o.path_resolve(dp)
    '''
    v = []
    for f in range(scene.frame_start, scene.frame_end):
        scene.frame_set(f)
        v.append(driver_fcurve.evaluate(f))
    '''
    #v = [driver_fcurve.evaluate(f)
    for f in range(scene.frame_start, scene.frame_end)]
    '''
    _min = min(v)
    _max = max(v)
    return ((_min, _max), (v.index(_min), v.index(_max)))


def fcurve_minmax(self):
    # return ((min, max), (min_index, max_index))
    # it thru keyframe_points
    if len(self.keyframe_points):
        col = self.keyframe_points
    elif len(self.sampled_points):
        col = self.sampled_points
    else:
        return ((0, 0), (0, 0))
        return(driver_minmax(self))
    # check for modifiers
    mods = [mod for mod in self.modifiers if not mod.mute and mod.is_valid]
    if len(mods):
        v = [self.evaluate(p.co[0]) for p in col]
    else:
        v = [p.co[1] for p in col]
    _min = min(v)
    _max = max(v)
    return ((_min, _max), (v.index(_min), v.index(_max)))

'''
Property Groups
'''


def register():
    bpy.types.FCurve.minmax = property(fcurve_minmax)
    #bpy.types.Scene.dm = BoolProperty(default=False, update=toggle_dm)
    register_class(DriverSelectorOperator)
    register_class(Bake2FCurveOperator)
    register_class(DriversManagerPanel)
    register_class(EditTextFieldOperator)
    register_class(UpdateDriverlistOperator)
    register_class(RemoveDriverVarOperator)
    register_class(DriverManagerDemonkify)
    register_class(DriverManagerSettings)
    register_class(SimpleCustomMenu)
    register_class(DriverMangagerToolMenu)
    register_class(AddDriverVar)
    register_class(DriverAddModifier)
    register_class(DriverRemoveModifier)

    register_class(RGBColorFCurves)

    # get rid of any handlers floating around.
    remove_handlers_by_prefix('SOUND_DRIVERS_')
    bpy.app.handlers.load_post.append(SOUND_DRIVERS_load)
    bpy.app.handlers.load_pre.append(SOUND_DRIVERS_unload)

    # set up the driver manager
    #bpy.app.driver_namespace["DriverManager"] = None


def unregister():
    unregister_class(DriverSelectorOperator)
    unregister_class(Bake2FCurveOperator)
    unregister_class(DriversManagerPanel)
    unregister_class(EditTextFieldOperator)
    unregister_class(UpdateDriverlistOperator)
    unregister_class(RemoveDriverVarOperator)
    unregister_class(RGBColorFCurves)
    unregister_class(DriverManagerDemonkify)
    unregister_class(DriverManagerSettings)
    unregister_class(DriverMangagerToolMenu)
    unregister_class(SimpleCustomMenu)
    unregister_class(AddDriverVar)
    unregister_class(DriverAddModifier)
    unregister_class(DriverRemoveModifier)
    # We don't want these hanging around.
    remove_handlers_by_prefix('SOUND_DRIVERS_')

    #global dm
    dm = bpy.app.driver_namespace.get("DriverManager")
    if dm is not None:
        dm.clear()
        print("Driver Manager Cleared")
        # del(dm)
