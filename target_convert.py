bl_info = {
    "name" : "Target Conversion",
    "description" : "Converts Target To Mesh", # To Allow Updating Of Mesh
    "author" : "Steffenvy", #Jacob Morris
    "blender" : (2, 80, 0),
    "location" : "Properties > Modifiers > Target Conversion",
    "version" : (1, 0),
    "category" : "Object"
    }

import bpy
import math
import bmesh
from bpy.props import StringProperty, BoolProperty, FloatProperty, FloatVectorProperty, PointerProperty, EnumProperty
import mathutils


compatibleTargetTypes = ['MESH', 'CURVE', 'SURFACE', 'META', 'FONT']


#bpy.types.Object.names = StringProperty(name = "Object Name", default = "")
#bpy.types.Object.rscale = BoolProperty(name = "Respect Scale?", default = False)

def object_poll(self, object):
    return (object.type in compatibleTargetTypes) or (object.instance_type != 'NONE') #== 'CURVE' or object.type == 'MESH' or object.instance_type != 'NONE'

bpy.types.Object.useCollection = BoolProperty(name = "Use Collection", default = False)
bpy.types.Object.objectTarget = bpy.props.PointerProperty(name = "Target", type=bpy.types.Object, poll=object_poll)
bpy.types.Object.collectionTarget = bpy.props.PointerProperty(name = "Target", type=bpy.types.Collection)

bpy.types.Object.respectScale = BoolProperty(name = "Respect Scale", default = False)

bpy.types.Object.removeDoubles = BoolProperty(name = "Remove Doubles?", default = False)
bpy.types.Object.doublesDistance = FloatProperty(name = "Doubles Distance", default = 0.0001)
bpy.types.Object.recalcNormals = BoolProperty(name = "Recalculate Normals?", default = False)
bpy.types.Object.targetRelative = BoolProperty(name = "Respect Local Positions", default = True) #Prefit
bpy.types.Object.keepMaterials = BoolProperty(name = "Keep Current Materials?", default = True)

bpy.types.Object.unifyUVs = BoolProperty(name = "Unify UV Maps?", default = True) #This is important for dupli-groups (curves have "Octo" uvs, and meshes "UVMap")
bpy.types.Object.cubeProjection = BoolProperty(name = "Do Cube Projection?", default = False)

bpy.types.Object.unwrapType = EnumProperty(name='Unwrap Type', items = {('NONE', 'none', 'No Projection'), ('CUBE', 'cube', 'Cube Projection'), ('SPHERE', 'sphere', 'Sphere Projection'), ('Cylinder', 'cylinder', 'Cylinder Projection')},
                    default='NONE')

bpy.types.Object.transformUVs = BoolProperty(name = "Transform UVs?", default = False)
bpy.types.Object.uvStartScale = FloatVectorProperty(name = "UV First Scale",subtype='XYZ',precision=2,size=2,default=(1.0,1.0))
bpy.types.Object.uvRotation = FloatProperty(name = "UV Rotation", default = 0)
bpy.types.Object.uvScale = FloatVectorProperty(name = "UV Second Scale",subtype='XYZ',precision=2,size=2,default=(1.0,1.0))
bpy.types.Object.uvOffset = FloatVectorProperty(name = "UV Offset",subtype='XYZ',precision=2,size=2,default=(0,0))


#TODO: maybe make sure to have at least one uv map????
#TODO: problem with mirror modifiers and all that? modifiers that depend on other positions?
#make target relative be possible but use world origin as default for offset.!

#hidden collections at least with instancing doesn't work
#instancing inside colleciton doesn't work when follection mode
#make it fail when the target is the same data as the o?

def rotate(origin, point, angle):
    angle *= 0.0174533

    ox, oy = origin
    px, py = point

    qx = ox + math.cos(angle) * (px - ox) - math.sin(angle) * (py - oy)
    qy = oy + math.sin(angle) * (px - ox) + math.cos(angle) * (py - oy)
    return qx, qy
    
    
def TargetConvert(self, context):

    o = context.object
    
    if o.useCollection:
        target = o.collectionTarget
    else:
        target = o.objectTarget
        if o.data == target.data:
            return
        
    if target != None:

        prevData = o.data.copy()

        
        #Setup (prevents errors)
        if bpy.context.active_object.mode == 'EDIT':
            bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        o_hide = o.hide_viewport
        o.hide_viewport = False
        o_hide2 = o.hide_get()
        o.hide_set(False)
        
        
        
        #Single Object
        if o.useCollection == False and ((target.instance_type == 'NONE') or (len(target.children) == 0 and target.instance_type != 'COLLECTION')): #seems that if it's a deleted but still existing child, it will still think there is one. meh.
        #{
            if o.targetRelative:
                
                bpy.ops.object.select_all(action='DESELECT')
                target.select_set(True)
                context.view_layer.objects.active = target
                depsgraph = bpy.context.evaluated_depsgraph_get()
                print(depsgraph)
                target_eval = target.evaluated_get(depsgraph)
                print(target_eval)
                tempData = target_eval.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
                print(tempData)
                
                #tempData = target.to_mesh(preserve_all_data_layers=True) #context.scene, True, 'PREVIEW', calc_tessface=True, calc_undeformed=False) #ob.data

                bm = bmesh.new(use_operators=True) #o.data = bpy.data.meshes.new("Converted Mesh")
                bm.from_mesh(tempData) # nonetype
                bm.to_mesh(o.data)
                bm.free()
                
                #target.to_mesh_clear()
                target_eval.to_mesh_clear()

                target.select_set(False)
                context.view_layer.objects.active = o
                o.select_set(True)
                
                
                #This process doesn't copy materials, unlike the other methods
                if not o.keepMaterials:
                    o.data.materials.clear()
                    td = target.data
                    if len(td.materials) > 0: #To prevent a crash bug it seems. TODO: bug report?
                        for i in td.materials:
                            o.data.materials.append(i)
                    else:
                        o.data.materials.append(None)
                        
            else:
            
                bpy.ops.object.select_all(action='DESELECT')
                
                dupe = target.copy()
                context.scene.collection.objects.link(dupe)
                dupe.data = dupe.data.copy()
                dupe.hide_viewport = False
                dupe.select_set(True)
                context.view_layer.objects.active = dupe

                bpy.ops.object.convert(target='MESH')
                
                o.select_set(True)
                context.view_layer.objects.active = o
                   
                bm = bmesh.new() #use_operators=True) #o.data = bpy.data.meshes.new("Converted Mesh")
                bm.to_mesh(o.data)
                bm.free()
                
                bpy.ops.object.join()
                
                bpy.ops.object.select_all(action='DESELECT')
                o.select_set(True)
                context.view_layer.objects.active = o
        
            if o.unifyUVs:
                for uvmap in o.data.uv_layers :
                    uvmap.name = 'UVMap'
        
        #}
        else:
        #{
            #Remembers which collections were visible
            c_hiddens = []
            collections = bpy.data.collections
            for c in collections:
                c_hiddens.append(c.hide_render)
                c.hide_render = False
                   

            bpy.ops.object.select_all(action='DESELECT')

            
            #Gets duplicates, and selects them
            if o.useCollection:
                for t in target.all_objects:
                    if t.type in compatibleTargetTypes: #== "CURVE" or t.type == "MESH" or t.type == "TEXT":
                        if t != o:
                            tt = t.copy()
                            context.scene.collection.objects.link(tt)
                            tt.select_set(True)
            else:
                #Remembers some settings
                instanceType = target.instance_type
                instanceC = target.instance_collection
                visib = target.hide_viewport
                target.hide_viewport = False
                hidd = target.hide_get()
                target.hide_set(False)
                
                #Makes real
                target.select_set(True)
                context.view_layer.objects.active = target
                
                donts = target.children
                bpy.ops.object.duplicates_make_real(use_base_parent=True, use_hierarchy=False) #dupli_type = target.dupli_type
                target.select_set(False)             #target.dupli_type = dupli_type
                maybes = target.children
                yesses = [x for x in maybes if x not in donts]
                for x in yesses:
                    x.select_set(True) 
                    
                
                #Reverts
                target.instance_type = instanceType
                target.instance_collection = instanceC
                target.hide_viewport = visib
                target.hide_set(hidd)
        
    
            #Makes all be Meshes (not curves), at same time instantiating them
            sels = context.selected_objects
            bpy.ops.object.select_all(action='DESELECT')
            for sel in sels:
                sel.data = sel.data.copy()
                
                sel.select_set(True)
                context.view_layer.objects.active = sel
                bpy.ops.object.convert(target='MESH')
                
                if o.unifyUVs and sel.data.uv_layers:
                    for uvmap in sel.data.uv_layers :
                        uvmap.name = 'UVMap'
                
                sel.select_set(False) # I could maybe do this without de then re selecting?
            
            for sel in sels: #Reselects
                sel.select_set(True)
            
            
            #Clones
            targ = o
            useTempTarg = o.useCollection == False and o.targetRelative
            if useTempTarg:
                tempTarg = bpy.data.objects.new("temp", o.data)
                context.scene.collection.objects.link(tempTarg)
                tempTarg.matrix_world = target.matrix_world 
                tempTarg.hide_viewport = False
                targ = tempTarg
                
            #Clears mesh data
            mesh = targ.data
            bm = bmesh.new(use_operators=True) 
            bm.to_mesh(mesh)
            bm.free()
            
            #Joins the duplicates into the clone, then o, to preserve transformation differences
            targ.select_set(True)
            context.view_layer.objects.active = targ
            bpy.ops.object.join()
            o.data = targ.data #?
            
            #Deletes Clone
            bpy.ops.object.select_all(action='DESELECT')
            if useTempTarg:
                tempTarg.select_set(True)
                bpy.ops.object.delete()
            
            
            #Now select the result
            o.select_set(True)
            context.view_layer.objects.active = o

            
            #Reverts Collection Visibility
            i = 0
            for c in collections:
                c.hide_render = c_hiddens[i]
                i += 1
        #}
        
        
            
        #Resets to previous materials
        if o.keepMaterials:
            o.data.materials.clear()
            if len(prevData.materials) > 0: #To prevent a crash bug it seems. TODO: bug report?
                for i in prevData.materials:
                    o.data.materials.append(i)
            else:
                o.data.materials.append(None)
                
                    
        #Scales object
        if o.useCollection == False and o.respectScale == True: #and target.instance_type == 'NONE': #????
            o.scale = target.scale
            
        #Cube Projection preparation
        if o.cubeProjection == True:
            bpy.context.view_layer.objects.active = o
            maxcount = 1000
            while(len(o.data.uv_layers) and maxcount > 0): #is this paranoia?
                bpy.ops.mesh.uv_texture_remove()
                maxcount -= 1
            
        #Remove Doubles
        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.ops.mesh.select_all(action='SELECT')
        if o.removeDoubles == True:
            bpy.ops.mesh.remove_doubles(threshold=o.doublesDistance) #0.0001)
            bpy.ops.mesh.faces_shade_smooth()
            
        #Recalculate Normals
        if o.recalcNormals == True:
            bpy.ops.mesh.normals_make_consistent()
            
        #Cube Projection
        if o.cubeProjection == True and len(o.data.vertices) > 2:
            bpy.ops.uv.cube_project(cube_size=1.0)
               
        #Cube Projection
        bpy.ops.object.mode_set()
        
        bm = bmesh.new(use_operators=True) #o.data = bpy.data.meshes.new("Converted Mesh")
        bm.from_mesh(o.data)
        uv_layer = bm.loops.layers.uv.active
        if o.transformUVs:
            for face in bm.faces:
                for vert, loop in zip(face.verts, face.loops):
                    tuv = loop[uv_layer].uv #= #get_uvs(vert.index, face.index,...) #
                    tuv -= mathutils.Vector((.5,.5))
                    tuv.x *= o.uvStartScale.x
                    tuv.y *= o.uvStartScale.y
                    tuv = mathutils.Vector(rotate((0, 0), tuv, o.uvRotation))
                    tuv.x *= o.uvScale.x
                    tuv.y *= o.uvScale.y
                    tuv += mathutils.Vector((.5,.5))
                    tuv += o.uvOffset
                    loop[uv_layer].uv = tuv
            
        bm.to_mesh(o.data)
        bm.free()
        
        #Rehides
        o.hide_viewport = o_hide
        o.hide_set(o_hide2)
         
    else:
        self.report({"ERROR"}, "Object Not Found")
    
        
class TargetConversionAdd(bpy.types.Operator):
    bl_label = "Add Mesh Object"
    bl_idname = "mesh.target_convert_add"
    bl_options = {"UNDO"}
    
    def execute(self, context):
        target = context.object
        na = target.name
        clone = target.copy()
        clone.data = target.data.copy()
        
        #Collections
        #context.scene.collection.objects.link(clone)
        for c in target.users_collection:
            c.objects.link(clone)
        
        if ' Maker' in na:
            clone.name = na.replace(' Maker', '')
        else:
            clone.name = na + ' Result' #' Mesh'
          
        bpy.ops.object.select_all(action='DESELECT')
        clone.select_set(True)
        context.view_layer.objects.active = clone
        bpy.ops.object.convert(target='MESH')
          
        clone["objectTarget"] = target
        
        clone.instance_type = 'NONE'

        
        #Parents
        target.select_set(True)
        clone.select_set(True)
        context.view_layer.objects.active = clone
        target.parent = clone #bpy.ops.object.parent_no_inverse_set() #bpy.ops.object.parent_set(type='OBJECT', keep_transform=False) #True
        target.matrix_local.identity() # = mathutils.Matrix.identity()
        target.select_set(False)

        
        #bpy.ops.target_converter.upgrade(clone) #?
        
        return {"FINISHED"}
         
        
class TargetConversionUpdate(bpy.types.Operator):
    bl_label = "Update Mesh"
    bl_idname = "mesh.target_convert_update"
    bl_options = {"UNDO"}
    
    def execute(self, context):
        TargetConvert(self, context)
        return {"FINISHED"}
        
            
#Upgrading from curve_converter
class TCUpdate(bpy.types.Operator):
    bl_label = "Upgrade From Curve-Converter"
    bl_idname = "target_converter.upgrade"
    bl_options = {"UNDO"}
    
    def execute(self, context):
        for o in context.blend_data.objects:
            if "names" in o.keys():
                if o["names"] != "":
                    try:
                        o["objectTarget"] = bpy.data.objects[o["names"]]
                    except:
                        pass
                del o["names"]
            
            if "rscale" in o.keys():
                o["respectScale"] = o["rscale"]
                del o["rscale"]
            
        return {"FINISHED"}
         
      


            
class SelectTarget(bpy.types.Operator):
    bl_label = "Select Target"
    bl_idname = "target_converter.select_target"
    bl_options = {"UNDO"}
    
    def execute(self, context):

        try:
            o = bpy.context.active_object
            target = o["objectTarget"]
            target.hide_viewport = False
            target.select_set(True)
            context.view_layer.objects.active = target
            o.select_set(False)
        except:
            pass
            
        return {"FINISHED"}
         
        
        
class TargetConversionPanel(bpy.types.Panel):
    bl_label = "Target Conversion"
    bl_idname = "OBJECT_PT_convert"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "modifier"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout; o = context.object
            
        if o.type == "MESH":
        
            layout.prop(o, "useCollection", icon = "NONE"); 
            if o.useCollection:
                layout.prop(o, "collectionTarget", icon = "NONE") #layout.prop_search(o, "names",  context.scene, "objects"); 
            else:
                layout.prop(o, "objectTarget", icon = "NONE")
                layout.prop(o, "targetRelative", icon = "OUTLINER_OB_EMPTY")
                layout.prop(o, "respectScale", icon="CON_SIZELIKE") #I can't find "MAN_SCALE" (scaling icon)
                
            layout.prop(o, "keepMaterials", icon = "MATERIAL")
            layout.prop(o, "recalcNormals", icon = "MOD_NORMALEDIT")

            layout.separator_spacer()
            layout.prop(o, "removeDoubles", icon = "NONE")
            if o.removeDoubles:
                layout.prop(o, "doublesDistance", icon = "NONE")

            layout.separator_spacer()
            layout.label(text="UVs:", icon = "GROUP_UVS")
            layout.prop(o, "unifyUVs", icon = "NONE")
            layout.prop(o, "cubeProjection", icon = "NONE")
            
            layout.prop(o, "transformUVs", icon = "NONE")
            if o.transformUVs:
                layout.prop(o, "uvStartScale", icon = "NONE")
                layout.prop(o, "uvRotation", icon = "NONE")
                layout.prop(o, "uvScale", icon = "NONE")
                layout.prop(o, "uvOffset", icon = "NONE")
            
            layout.separator_spacer()

            layout.operator(TargetConversionUpdate.bl_idname, text=TargetConversionUpdate.bl_label)
            
            layout.separator(factor=5)

            
        if o.type in compatibleTargetTypes: # == "CURVE" or o.type == "MESH":
            layout.operator(TargetConversionAdd.bl_idname, text=TargetConversionAdd.bl_label)

            
        if o.useCollection == False and o.objectTarget != None:
            layout.separator(factor=5)
            layout.operator(SelectTarget.bl_idname, text=SelectTarget.bl_label)

            

        
classes = (
    TargetConversionAdd,
    TargetConversionUpdate,
    TargetConversionPanel,
    TCUpdate,
    SelectTarget
)

register, unregister = bpy.utils.register_classes_factory(classes)

if __name__ == "__main__":
    register()
    