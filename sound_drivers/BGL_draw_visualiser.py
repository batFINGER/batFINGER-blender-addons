import bpy
import blf
import bgl
from mathutils import Vector
from bpy.props import (BoolProperty,
                       IntProperty,
                       FloatProperty,
                       IntVectorProperty,
                       StringProperty,
                       FloatVectorProperty,
                       PointerProperty)
from sound_drivers.utils import getAction, getSpeaker
from bpy.types import Panel, Operator, PropertyGroup
from bpy.utils import register_class, unregister_class

def draw_sound_widgets(context, wlist):
    speaker = context.scene.speaker
    action = getAction(speaker)
    
    for w in wlist:
        w.draw_action_header_text(speaker, action)

class bgl_SoundActionWidget():
    '''
    Create a SoundActionWidget
    '''
    handle = None
    def create_handle(self, context):
        
        handle = self.areatype.draw_handler_add(
            self.visualise,
            (context,),
           'WINDOW', 'POST_PIXEL')  
        #print("C_H", handle) 
        return handle     
        
    def remove_handle(self):
        #print("R_H", self.handle)
        if self.handle:
            self.areatype.draw_handler_remove(self.handle, 'WINDOW') 
            self.handle = None       
    
    def __init__(self, op, context, areatype):
        self.op = op
        self.areatype = areatype
        speaker = context.scene.speaker
        a = getAction(speaker)
        self.handle = self.create_handle(context)
        theme = context.user_preferences.themes[0]
        self.gridcol = [getattr(theme.view_3d.grid, c) for c in 'rgb']
        self.gridcol.append(1.0)

    def map_to_action(self, action, val, amplitude):
        if action.normalise in {'CHANNEL', 'ACTION'}:
            min, max = action.normalise_range
        else:
            min, max = action['min'], action['max']
        
        range = abs(max - min)
        #print("MINMAX", val, min, max, range, amplitude)
        if range < 0.0001:
            return 0
        return  (abs(val - min) / range) * amplitude      
    def draw_midi_keyboard(self, mx, my, w, h):
        '''
        Intented to create a keyboard where key widths are
        accurately in position. 
         
        See http://www.mathpages.com/home/kmath043.htm
        for the math.
         
        This keyboard has following properties (x=octave width).
        1. All white keys have equal width in front (W=x/7).
        2. All black keys have equal width (B=x/12).
        3. The narrow part of white keys C, D and E is W - B*2/3
        4. The narrow part of white keys F, G, A, and B is W - B*3/4
        '''
        bgl.glEnable(bgl.GL_BLEND)
        octaves = 7
        octave_width = (w - 20) / octaves
        wkw = octave_width / 7
        bkw = octave_width / 12
        cde = wkw - 2 * bkw / 3
        fgab = wkw - 3 * bkw / 4
        wkh = h
        bkh = 0.60 * h

        by = my + wkh - bkh
        x = mx
        y = my
        white = (1.0, 1.0, 1.0, 1.0)
        # draw the white keys
        for octave in range(octaves):
            for i in range(7):
                self.draw_box(x, y, wkw, wkh, col=white)
                x += (wkw + 1)
            # draw the black keys
            x = octave * 7 * (wkw + 1) + cde + mx + 1
            
            for i in range(2):
                self.draw_box(x, by, bkw, bkh)
                x += cde + bkw + 1
            x += fgab
            for i in range(3):
                self.draw_box(x, by, bkw, bkh)
                x += fgab + bkw + 1
            x += 1     
        
    def visualise(self, context):
        area = context.area
        
        speaker = context.scene.speaker
        action = getAction(speaker)
        if not context.window_manager.bgl_draw_speaker:
            self.remove_handle()                        
            return None

        if not getattr(action.bgl_action_draw, "use_%s" % area.type, False):
            return None
        '''
        lock to channel testcode
        
        space = context.area.spaces.active
        v = action.fcurves[8].evaluate(context.scene.frame_current)
        space.cursor_position_y = v
        '''
        #bgl.glPushAttrib(bgl.GL_ENABLE_BIT)
        
        
        (x, y) = getattr(action.bgl_action_draw, context.area.type).loc
        fw = (context.area.regions[-1].width - (x + 20))
        fh = context.area.regions[-1].height - 50

        AMP = getattr(action.bgl_action_draw,
                          context.area.type).height * fh / 100
        if action.get("MIDI"):
            
            bgl.glEnable(bgl.GL_BLEND)
            self.draw_box(x, y + AMP , 3 * fw , 20, col=self.gridcol)
            bgl.glDisable(bgl.GL_BLEND)
            self.draw_action_header_text(x, y+AMP, speaker, action)
            self.draw_midi_keyboard(x, y, fw, AMP)
        else:
            self.draw_spectrum(context, x, y, speaker, action)
            
                  
    def draw_spectrum(self, context, x, y, speaker, action):

        channels = action["Channels"]
        channel_name = action.get("channel_name")
        
                
        #bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA)
                     
        w = 100
        fw = (context.area.regions[-1].width - (x + 20))
        fh = context.area.regions[-1].height - 50
        lw = max(1, fw / channels)
        AMP = getattr(action.bgl_action_draw,
                          context.area.type).height * fh / 100

        #fw = channels * (lw)
        #self.draw_bar(x + (fw/2), y, AMP, lw=fw)
        #bgl.glEnable(bgl.GL_DEPTH_TEST)
        #bgl.glDepthFunc(bgl.GL_ALWAYS)
        #bgl.glDepthRange (0, 1)
        bgl.glEnable(bgl.GL_BLEND)
        self.draw_box(x, y + AMP , channels * (lw + 1) , 20, col=self.gridcol)
        bgl.glDisable(bgl.GL_BLEND)
        self.draw_action_header_text(x, y+AMP, speaker, action)
        #bgl.glDepthFunc(bgl.GL_LEQUAL) 
        
        bgl.glEnable(bgl.GL_BLEND)
        
        #self.bgl_defaults() 
        #return
        #lw = 4

        action_fcurve_color = [1, 1, 0, 1.0]
        a_col = baked_fcurve_color = [0.230, 0.40, 0.165, 1.0]
        
        if len(action.fcurves[0].keyframe_points):
           a_col = action_fcurve_color 
        elif len(action.fcurves[0].sampled_points):        
           a_col = baked_fcurve_color
        a_col[3] = 0.2

        for i in range(channels):
            col = a_col
            ch = "%s%d" % (channel_name, i)
            amp = self.map_to_action(action, speaker[ch], AMP)
            alpha = 0.2
            col[3] = alpha
            self.draw_box(x, y, lw, AMP, col=col)
            if action.fcurves[i].select:
                col = [c for c in action.fcurves[i].color]
                col.append(1.0)
            else:   
                col[3] = 0.8 # change to var
            self.draw_box(x, y, lw, amp, col=col)
            x = x + lw + 1
        (x, y) = getattr(action.bgl_action_draw, context.area.type).loc   

        self.bgl_defaults()

        
    def draw_action_header_text(self, x, y, speaker, action, margin=4):
        bgl.glPushAttrib(bgl.GL_COLOR_BUFFER_BIT | bgl.GL_ENABLE_BIT)
        font_id = 0
        #(x, y) = getattr(action.bgl_action_draw, 'VIEW_3D').loc
        x = x + margin
        y = y + margin
        #bgl.glEnable(bgl.GL_BLEND)
        bgl.glColor4f(1.0, 1.0, 1.0, 1.0)
        blf.size(font_id, 16, 64)
        blf.position(font_id, x, y, 0.0)
        baking = ""
        if bpy.types.BakeSoundPanel.baking:
            baking = "(BAKING....)"
        
        s = "[%s] %s %s" % (action["channel_name"], action.name, baking)
        blf.draw(font_id, s)
        blf.size(font_id, 20, 36)
        blf.position(font_id, x + 10 * len(s), y, 0.0)
        blf.draw(font_id, action["wavfile"])
        bgl.glPopAttrib()
        #self.bgl_defaults()
        
    def draw_bar(self, x, y, amplitude, lw=2, col=(0.0, 0.0, 0.0, 0.5)):
        bgl.glColor4f(*col)

        bgl.glLineWidth(lw)
        bgl.glBegin(bgl.GL_LINE_STRIP)
        bgl.glVertex2f(x, y)
        bgl.glVertex2f(x, y + amplitude)

        bgl.glEnd()
        
    def draw_box(self, x, y, w, h, col=(0.0, 0.0, 0.0, 1.0)):
        #bgl.glDepthRange (0.1, 1.0)
        bgl.glColor4f(*col)
        bgl.glBegin(bgl.GL_QUADS)
    
        bgl.glVertex2f(x+w, y+h)
        bgl.glVertex2f(x, y+h) 
        bgl.glVertex2f(x, y) 
        bgl.glVertex2f(x+w, y)      
        bgl.glEnd()
      
    def bgl_defaults(self):
        bgl.glLineWidth(1)
        bgl.glDisable(bgl.GL_DEPTH_TEST)
        bgl.glDisable(bgl.GL_BLEND)
        bgl.glColor4f(0.0, 0.0, 0.0, 1.0)


'''
def draw_text_callback(context, data):
    area = context.area
    if getSpeaker(context) is None:
        return None
    
    font_id = 0
    #...
    region = context.region
    #region3d = context.space_data.region_3d

    region_mid_width = region.width / 2.0
    region_mid_height = region.height / 2.0

    # vars for projection
    #perspective_matrix = region3d.perspective_matrix.copy()
    def draw_bar(x, y, amplitude, lw=2, col=(0.0, 0.0, 0.0, 0.5)):
        #bgl.glPushAttrib(bgl.GL_ENABLE_BIT)


        # 50% alpha, 2 pixel width line
        #bgl.glEnable(bgl.GL_BLEND)
        bgl.glColor4f(*col)
        bgl.glLineWidth(lw)

        bgl.glBegin(bgl.GL_LINE_STRIP)

        bgl.glVertex2i(x, y)
        bgl.glVertex2i(x, y + amplitude)

        bgl.glEnd()
        #bgl.glPopAttrib()

    def draw_action_header_text(speaker, action, x, y):
        
        bgl.glColor4f(0.0, 0.0, 0.0, 1.0)
        blf.size(font_id, 20, 72)
        blf.position(font_id, x - 3.0, y - 4.0, 0.0)
        blf.draw(font_id, a["channel_name"])
        blf.size(font_id, 20, 36)
        blf.position(font_id, x - 3.0, y - 20.0, 0.0)
        blf.draw(font_id, a["wavfile"])
    spk = getSpeaker(context)
    a = getAction(spk) 
    
    loc = context.object.location
    (x, y) = getattr(a.bgl_action_draw, area.type).loc
    action_fcurve_color = [1, 1, 0, 1.0]
    baked_fcurve_color = [0.230, 0.40, 0.165, 1.0]
    
    if len(a.fcurves[0].keyframe_points):
       a_col = action_fcurve_color 
    elif len(a.fcurves[0].sampled_points):        
       a_col = baked_fcurve_color
    a_col[3] = 0.2

    # use for on speaker ui
    #x = Vector((1,0,0))
    #z = Vector((0,0,1))

    channel_name = a["channel_name"]
    channels = a["Channels"]

    draw_action_header_text(spk, a, x-20, y+10)

    w = 10
    w = (context.area.width - 20) / channels
    lw = min(10, int(w))
    AMP = getattr(a.bgl_action_draw, area.type).height
    
    def map_to_action(a, val, amplitude):
        if a.normalise in {'CHANNEL', 'ACTION'}:
            min, max = a.normalise_range
        else:
            min, max = a['min'], a['max']
        
        range = abs(max - min)
        #print("MINMAX", val, min, max, range, amplitude)
        if range < 0.0001:
            return 0
        return int( (abs(val - min) / range) * amplitude)
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glEnable(bgl.GL_DEPTH_TEST)
    #bgl.glDepthMask(bgl.GL_TRUE)
    bgl.glDepthRange (0.0, 0.9);
    #bgl.glDepthFunc(bgl.GL_ALWAYS)    
    for i in range(channels):
        col = a_col
        ch = "%s%d" % (channel_name, i)
        amp = map_to_action(a, spk[ch], AMP)

        x = x + lw + 1

        col[3] = 0.2
        draw_bar(x, y, AMP, lw=lw, col=col)
        if False:
            col = [c for c in a.fcurves[i].color]
            col.append(1.0)

        col[3] = 0.6
        draw_bar(x, y, amp, lw=lw, col=col)
        
    (x, y) = getattr(a.bgl_action_draw, area.type).loc
    bgl.glDepthRange (0.1, 1.0);
    #bgl.glDepthFunc(bgl.GL_LEQUAL)
    #bgl.glClearDepth(0.9)
    draw_bar(x, y, AMP, lw=channels * (lw + 1) , col=(0.0, 0.0, 0.0, 1))
    
    # restore opengl defaults
    bgl.glLineWidth(1)
    bgl.glDisable(bgl.GL_DEPTH_TEST)
    bgl.glDisable(bgl.GL_BLEND)
    bgl.glColor4f(0.0, 0.0, 0.0, 1.0)
'''
           
class BGLDrawSpeaker(Operator):
    """Draw the Context Speaker Action"""
    bl_idname = "wm.draw_speaker_vis"
    bl_label = "Modal Timer Operator"
    '''
    Refactor to allow for running modal for widget functionality
    '''

    timer = None
    handle = None
    callbacks = []

    def modal(self, context, event):


        if event.type == 'TIMER':
            if not context.scene.bgl_draw_speaker:
                
                return self.cancel(context)

            # change theme color, silly!
            pass


        return {'PASS_THROUGH'}

    def execute(self, context):
        #wm = context.window_manager
        #self.timer = wm.event_timer_add(0.1, context.window)
        #wm.modal_handler_add(self)
        self.callbacks.append(bgl_SoundActionWidget(self, context, bpy.types.SpaceView3D))
        self.callbacks.append(bgl_SoundActionWidget(self, context, bpy.types.SpaceGraphEditor))
        self.callbacks.append(bgl_SoundActionWidget(self, context, bpy.types.SpaceNLA))
        '''
        self.handle = bpy.types.SpaceView3D.draw_handler_add(
            draw_sound_widgets,
            (context, [data]),
           'WINDOW', 'POST_PIXEL') 
        '''       
        #for h in bpy.types.SpaceView3D.
        '''
        self.handle = bpy.types.SpaceView3D.draw_handler_add(
           draw_text_callback, 
           (context, data,),
           'WINDOW', 'POST_PIXEL')
        self.graph_handle = bpy.types.SpaceGraphEditor.draw_handler_add(
           draw_text_callback, 
           (context, data,),
           'WINDOW', 'POST_PIXEL')        
        self.NLA_handle = bpy.types.SpaceNLA.draw_handler_add(
           draw_text_callback, 
           (context, data,),
           'WINDOW', 'POST_PIXEL')
        '''
        #return {'RUNNING_MODAL'}
        return {'FINISHED'}


    def cancel(self, context):
        wm = context.window_manager
        
        for cb in self.callbacks:
            cb.remove_handle()
            del(cb)
            
        wm.event_timer_remove(self.timer)
        self.callbacks.clear()
        '''
        bpy.types.SpaceView3D.draw_handler_remove(self.handle, 'WINDOW')
        bpy.types.SpaceGraphEditor.draw_handler_remove(self.graph_handle, 'WINDOW')
        bpy.types.SpaceNLA.draw_handler_remove(self.NLA_handle, 'WINDOW')
        '''
        
        for area in context.screen.areas:
            area.tag_redraw()
        return {'CANCELLED'}

class BGL_Draw_VisualiserPanel(Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'data'
    bl_label = "BGL Visualiser"
    screen_areas = ['VIEW_3D', 'NLA_EDITOR', 'GRAPH_EDITOR']

    @classmethod
    def poll(cls, context):
        #print("EDP", context.driver_manager.edit_driver is not None)
        screen_areas = [a.type for a in context.screen.areas if a.type in cls.screen_areas]
        return context.scene.speaker is not None and len(screen_areas)
    
    def draw_header(self, context):
        layout = self.layout
        dm = context.driver_manager
        scene = context.scene
        wm = context.window_manager
        layout.prop(wm, "bgl_draw_speaker", text="")

              
    def draw(self, context):
        layout = self.layout
        dm = context.driver_manager
        speaker = getSpeaker(context)
        action = getAction(speaker)
        screen_areas = [a.type for a in context.screen.areas]
        for t in self.screen_areas:
            if t not in screen_areas:
                continue
            action_bgl = getattr(action.bgl_action_draw, t, None)
            if action_bgl is None:
                continue
            row = layout.row()
            text = bpy.types.Space.bl_rna.properties['type'].enum_items[t].name
            row.prop(action.bgl_action_draw, "use_%s" % t, text=text)
            box = layout.box()
            box.prop(action_bgl, "loc")
            box.prop(action_bgl, "color")
            box.prop(action_bgl, "height")
        
  

def start(self, context):
    if self.bgl_draw_speaker:
        bpy.ops.wm.draw_speaker_vis()
    else:
        scene = context.scene
        for area in context.screen.areas:
            area.tag_redraw()
            for region in area.regions:
                region.tag_redraw()
               
        
def update_graph(self, context):
    if context.area.type == 'PROPERTIES':
        bpy.ops.graph.view_all_with_bgl_graph()
    return None

def reg_action_bgl():
    prop_dic = {"loc": IntVectorProperty(size=2, default=(24, 24), min=0),
                "color": FloatVectorProperty(subtype='COLOR_GAMMA', size=4),
                "height": IntProperty(min=20, max=100, step=1, subtype='PERCENTAGE', description="Height (Percent of View)", update=update_graph),
                "use_fcurve_colors": BoolProperty(default=True)
                }
           
    action_bgl_props = type("ActionBGL", (PropertyGroup,), prop_dic)
    register_class(action_bgl_props)
    
    prop_dic = {
                "use_VIEW_3D": BoolProperty(default=False) ,
                "VIEW_3D": PointerProperty(type=action_bgl_props),
                "use_GRAPH_EDITOR": BoolProperty(default=True, update=update_graph) ,
                "GRAPH_EDITOR": PointerProperty(type=action_bgl_props),
                "use_NLA_EDITOR": BoolProperty(default=False) ,
                "NLA_EDITOR": PointerProperty(type=action_bgl_props),
                }
    action_bgl_view = type("ActionViewBGL", (PropertyGroup,), prop_dic)
    register_class(action_bgl_view)
    bpy.types.Action.bgl_action_draw = PointerProperty(type=action_bgl_view)
    
    

def register():
    bpy.types.WindowManager.bgl_draw_speaker = BoolProperty(update=start,
                                                    name="Draw Details",                                                    
                                                    default=False,
                                                    description="Show BGL Visualiser")
    #register_module(__name__)
    register_class(BGLDrawSpeaker)
    register_class(BGL_Draw_VisualiserPanel)
    reg_action_bgl()

def unregister():
    #unregister_module(__name__)
    unregister_class(BGLDrawSpeaker)
    unregister_class(BGL_Draw_VisualiserPanel)


    
