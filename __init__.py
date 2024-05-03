
bl_info = {
    "name": "AutoMDL",
    "author": "NvC_DmN_CH",
    "version": (1, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > AutoMDL",
    "description": "Compiles models for Source where the blend project file is",
    "warning": "",
    "wiki_url": "",
    "category": "3D View"
}

import bpy
import os
import subprocess
import shutil
from pathlib import Path
import mathutils
import winreg
from bl_ui.generic_ui_list import draw_ui_list
import threading

temp_path = bpy.app.tempdir
games_paths_list = []
game_path = None
steam_path = None
studiomdl_path = None
gameManualTextInputIsInvalid = False
massTextInputIsInvalid = False
visMeshInputIsInvalid = False
phyMeshInputIsInvalid = False

def defineGameSelectDropdown(self, context):
    # game_select
    game_select_items_enum = []
    for i in range(len(games_paths_list)):
        game_name = str(os.path.basename(os.path.dirname(games_paths_list[i])))
        game_path = str(games_paths_list[i])
        item = (game_path, game_name, "")
        game_select_items_enum.append(item)
    
    
    bpy.types.Scene.game_select = bpy.props.EnumProperty(
        name = "Selected Option",
        items = game_select_items_enum,
        update = onGameDropdownChanged
    )
    
    # set default value to prefer certain branches instead of literally just the first item in the list
    #bpy.context.scene.game_select = # do we actually need to do this?
    
    # we need to update the dropdown once to let the default value affect the rest of the program, as if we selected it manually
    onGameDropdownChanged(None, context)

def onGameDropdownChanged(self, context):
    setGamePath(self, context, context.scene.game_select)

def onMassTextInputChanged(self, context):
    global massTextInputIsInvalid
    massTextInputIsInvalid = not is_float(context.scene.mass_text_input)

def onGameManualTextInputChanged(self, context):
    global gameManualTextInputIsInvalid
    gameManualTextInputIsInvalid = False
    
    in_folder = str(Path(os.path.join(context.scene.studiomdl_manual_input, ''))) # make sure to have a trailing slash, and its a string
    subdir_studiomdl = os.path.join(in_folder, "studiomdl.exe")
    has_studiomdl = os.path.exists( subdir_studiomdl )
    if not has_studiomdl:
        gameManualTextInputIsInvalid = True
        print("ERROR: Couldn't find studiomdl.exe in specified folder")
        return
    
    base_path = Path(os.path.dirname(in_folder))
    gameinfo_path = None
    # oh no, code copy pasted from getGamesList()
    # anyway
    # 
    # although we need the path to the folder which contains the gameinfo
    # so we need to iterate now again
    _subdirectories = [x for x in base_path.iterdir() if x.is_dir()]
    for k in range(len(_subdirectories)):
        _subdir = _subdirectories[k]
        has_gameinfo = os.path.exists( os.path.join(_subdir, "gameinfo.txt") )
        
        # currently we're returning the first folder which has a gameinfo.txt, in alot of games there are multiple folders which match this criteria. todo: is this an issue?
        if( has_gameinfo ):
            gameinfo_path = str(_subdir)
            break
    
    if gameinfo_path == None:
        gameManualTextInputIsInvalid = True
        print("ERROR: Couldn't find gameinfo.txt in game")
        return
    
    setGamePath(self, context, gameinfo_path)


def setGamePath(self, context, new_game_path_value):
    global game_path
    global studiomdl_path
    game_path = new_game_path_value
    studiomdl_path = os.path.join(os.path.dirname(game_path), "bin", "studiomdl.exe")

# returns list of source games which have a studiomdl.exe in the bin folder
def getGamesList():
    global steam_path
    common = Path(os.path.join(steam_path, r"steamapps/common"))
    
    # get all subdirectories in common
    subdirectories = [x for x in common.iterdir() if x.is_dir()]
    
    # okay let's filter games
    list = []
    
    for i in range(len(subdirectories)):
        subdir = subdirectories[i]
        subdir_bin = os.path.join(subdir, "bin")
        has_bin_folder = os.path.exists( subdir_bin )
        if( not has_bin_folder ):
            continue
        
        subdir_studiomdl = os.path.join(subdir_bin, "studiomdl.exe")
        has_studiomdl = os.path.exists( subdir_studiomdl )
        
        if( not has_studiomdl ):
            continue
        
        # okay!
        # although we need the path to the folder which contains the gameinfo
        # so we need to iterate now again
        _subdirectories = [x for x in subdir.iterdir() if x.is_dir()]
        for k in range(len(_subdirectories)):
            _subdir = _subdirectories[k]
            has_gameinfo = os.path.exists( os.path.join(_subdir, "gameinfo.txt") )
            
            # currently we're returning the first folder which has a gameinfo.txt, in alot of games there are multiple folders which match this criteria. todo: is this an issue?
            if( has_gameinfo ):
                list.append(_subdir)
                break
    
    return list

# attempt to figure out where steam is installed
def getSteamInstallationPath():
    
    # windows specific attempts
    if(os.name == 'nt'):
        # check in registry (x86)
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Valve\Steam") as key:
                return winreg.QueryValueEx(key, "SteamPath")[0]
        except Exception as e:
            print(e)
        
        # check in registry (x64)
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam") as key:
                return winreg.QueryValueEx(key, "InstallPath")[0]
        except Exception as e:
            print(e)
    
    # todo: linux specific attempts?
    
    return None


def refreshGameSelectDropdown(self, context):
    del bpy.types.Scene.game_select
    defineGameSelectDropdown(None, context)



class AutoMDLOperator(bpy.types.Operator):
    bl_idname = "wm.automdl"
    bl_label = "Update MDL"
    bl_description = "Compile model"
    
    
    def execute(self, context):
        
        # check if we have saved a blend file in the first place
        if (len(bpy.data.filepath) == 0):
            self.report({'ERROR'}, "Please save the project inside a models folder")
            return {'CANCELLED'}
        
        has_collision = False
        phy_mesh_obj = context.scene.phy_mesh
        if phy_mesh_obj and phy_mesh_obj.name in bpy.data.objects:
            has_collision = True
        
        vis_mesh_valid = checkVisMeshHasMesh(context)
        phy_mesh_valid = checkPhyMeshHasMesh(context)
        
        # check if meshes aren't even meshes
        if (not vis_mesh_valid):
            self.report({'ERROR'}, "Please select a mesh for Visual mesh")
            return {'CANCELLED'}
        
        if (not phy_mesh_valid) and has_collision == True:
            self.report({'ERROR'}, "Please select a mesh for Collision mesh")
            return {'CANCELLED'}
        
        # check if visual mesh and collision mesh point to valid objects in the scene
        if (context.scene.vis_mesh != None) and context.scene.vis_mesh.name not in bpy.context.scene.objects:
            self.report({'ERROR'}, "Visual mesh points to a deleted object!")
            visMeshInputIsInvalid = True
            vis_mesh_valid = False
            return {'CANCELLED'}
        
        if (context.scene.phy_mesh != None) and context.scene.phy_mesh.name not in bpy.context.scene.objects:
            self.report({'ERROR'}, "Collision mesh points to a deleted object!")
            phyMeshInputIsInvalid = True
            phy_mesh_valid = False
            return {'CANCELLED'}
        
        mesh_ext = "smd"
        blend_path = bpy.data.filepath
        qc_path = os.path.join(temp_path, "qc.qc")
        qc_modelpath = to_models_relative_path(blend_path)
        
        if(qc_modelpath is None):
            self.report({'ERROR'}, "Please save the project inside a models folder")
            return {'CANCELLED'}
            
        
        qc_vismesh = os.path.basename(qc_modelpath) + "_ref"
        qc_phymesh = os.path.basename(qc_modelpath) + "_phy"
            
        qc_staticprop = context.scene.staticprop
        qc_mass = context.scene.mass_text_input if not qc_staticprop else 1
        
        if not is_float(qc_mass):
            self.report({'ERROR'}, "Mass is invalid")
            return {'CANCELLED'}
        
        if(qc_modelpath == -1):
            self.report({'ERROR'}, "blend file must be inside a models folder")
            return {'CANCELLED'}
        

        
        # export smd
        self.exportObjectToSmd(context.scene.vis_mesh, os.path.join(temp_path, qc_vismesh), False)
        
        if(has_collision):
            self.exportObjectToSmd(context.scene.phy_mesh, os.path.join(temp_path, qc_phymesh), True)
        
        
        # set up qc
        convex_pieces = 0
        if has_collision:
            convex_pieces = CountIslands(phy_mesh_obj)
        
        qc_surfaceprop = context.scene.surfaceprop
        
        qc_cdmaterials_list = []
        for i in range(len(context.scene.cdmaterials_list)):
            str = context.scene.cdmaterials_list[i].name
            str = os.path.join(str, '', '').replace("\\", "/")
            qc_cdmaterials_list.append(str)
        
        qc_concave = convex_pieces > 1
        qc_maxconvexpieces = convex_pieces
        qc_mostlyopaque = context.scene.mostlyopaque
        qc_inertia = 1
        qc_damping = 0
        qc_rotdamping = 0
        
        #self.report({'ERROR'}, f"qc_maxconvexpieces: {qc_maxconvexpieces}") # debug
        
        # write qc
        with open(qc_path, "w") as file:
            file.write(f"$modelname \"{qc_modelpath}.mdl\"\n")
            file.write("\n")
            file.write(f"$bodygroup \"Body\"\n{{\n\tstudio \"{qc_vismesh}.{mesh_ext}\"\n}}\n")
            
            if(qc_staticprop):
                file.write("\n")
                file.write(f"$staticprop")
                file.write("\n")
                
            if(qc_mostlyopaque):
                file.write("\n")
                file.write(f"$mostlyopaque")
                file.write("\n")
            
            
            file.write("\n")
            file.write(f"$surfaceprop \"{qc_surfaceprop}\"\n")
            file.write("\n")
            file.write("$contents \"solid\"\n")
            file.write("\n")
            for i in range(len(qc_cdmaterials_list)):
                str = qc_cdmaterials_list[i]
                file.write(f"$cdmaterials \"{str}\"\n")
            file.write("\n")
            file.write(f"$sequence \"idle\" {{\n\t\"{qc_vismesh}.{mesh_ext}\"\n\tfps 30\n\tfadein 0.2\n\tfadeout 0.2\n\tloop\n}}\n")
            file.write("\n")
            
            if(has_collision == True):
                str = f"$collisionmodel \"{qc_phymesh}.{mesh_ext}\" {{"
                str += f"\n\t$concave\n\t$maxconvexpieces {qc_maxconvexpieces}" if qc_concave else ""
                str += f"\n\t$mass {qc_mass}\n\t$inertia {qc_inertia}\n\t$damping {qc_damping}\n\t$rotdamping {qc_rotdamping}"
                str += f"\n\t$rootbone \" \""
                str += f"\n}}"
                file.write(str)
        # end of writing qc
        
        # compile qc!
        studiomdl_quiet = True
        studiomdl_fastbuild = False # doesn't seem to have an effect
        studiomdl_nowarnings = True
        studiomdl_nox360 = True
        studiomdl_args = [studiomdl_path, "-game", game_path, "-nop4"]
        
        if(studiomdl_quiet):
            studiomdl_args.append("-quiet")
        
        if(studiomdl_fastbuild):
            studiomdl_args.append("-fastbuild")
        
        if(studiomdl_nowarnings):
            studiomdl_args.append("-nowarnings")
        
        if(studiomdl_nox360):
            studiomdl_args.append("-nox360")
        
        studiomdl_args.append(qc_path) # qc needs to be the last argument
        #print(studiomdl_args)
        subprocess.run(studiomdl_args)
        
        
        # move compiled stuff
        compile_path = os.path.join(game_path, "models", os.path.dirname(qc_modelpath))
        move_path = os.path.dirname(blend_path)
        
        compiled_model_name = Path(os.path.basename(qc_modelpath)).stem
        
        compiled_exts = [".dx80.vtx", ".dx90.vtx", ".mdl", ".phy", ".sw.vtx", ".vvd"]
        for i in range(len(compiled_exts)):
            path_old = os.path.join(compile_path, compiled_model_name + compiled_exts[i])
            path_new = os.path.join(move_path, compiled_model_name + compiled_exts[i])
            if(os.path.isfile(path_old)):
                shutil.move(path_old, path_new)
        
        # delete folder in game if empty
        if os.path.isdir(compile_path):
            if(len(os.listdir(temp_path)) == 0):
                os.rmdir(compile_path)
        
        
        # delete temp folder contents
        for filename in os.listdir(temp_path): 
            file_path = os.path.join(temp_path, filename)  
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)  
                elif os.path.isdir(file_path):
                    os.rmdir(file_path)
            except Exception as e:  
                print(f"Error deleting {file_path}: {e}")
        
        self.report({'INFO'}, f"If compile was successful, output should be in \"{os.path.join(move_path, '')}\"")
        return {'FINISHED'}
    
    
    def exportObjectToSmd(self, obj, path, is_collision_smd):
        
        # switch to object mode
        context_mode_snapshot = "null"
        if bpy.context.mode != 'OBJECT':
            context_mode_snapshot = bpy.context.active_object.mode
            bpy.ops.object.mode_set(mode='OBJECT')
            
        # todo: check if object obj exists?
        
        # get mesh, apply modifiers
        depsgraph = bpy.context.evaluated_depsgraph_get()
        object_eval = obj.evaluated_get(depsgraph)
        mesh = object_eval.to_mesh()
        mesh.calc_loop_triangles()
        
        # Apply object transform to the mesh vertices
        mesh.transform(obj.matrix_world)
        
        # write!
        with open(path + ".smd", "w") as file:
            
            # hardcoded but yea
            file.write("version 1\nnodes\n0 \"root\" -1\nend\nskeleton\ntime 0\n0 0 0 0 0 0 0\nend\ntriangles\n")
            
            has_materials = len(obj.material_slots) > 0
            material_name = "None"
            
            for tri in mesh.loop_triangles:
                
                if(has_materials):
                    material_name = obj.material_slots[tri.material_index].name
                
                # tri vertices
                vert_a = mesh.vertices[tri.vertices[0]]
                vert_b = mesh.vertices[tri.vertices[1]]
                vert_c = mesh.vertices[tri.vertices[2]]
                
                # tri positions
                pos_a = vert_a.co
                pos_b = vert_b.co
                pos_c = vert_c.co
                    
                 # tri normals
                normal_a = vert_a.normal
                normal_b = vert_b.normal
                normal_c = vert_c.normal
                
                if(tri.use_smooth == False or is_collision_smd):
                    normal = (pos_b - pos_a).cross(pos_c - pos_a).normalized()
                    normal_a = normal
                    normal_b = normal
                    normal_c = normal
                
                # tri uv coords
                uv_a = mesh.uv_layers.active.data[tri.loops[0]].uv
                uv_b = mesh.uv_layers.active.data[tri.loops[1]].uv
                uv_c = mesh.uv_layers.active.data[tri.loops[2]].uv
                
                file.write(f"{material_name}\n0  {pos_a.x:.6f} {pos_a.y:.6f} {pos_a.z:.6f}  {normal_a.x:.6f} {normal_a.y:.6f} {normal_a.z:.6f}  {uv_a.x:.6f} {uv_a.y:.6f} 0\n0  {pos_b.x:.6f} {pos_b.y:.6f} {pos_b.z:.6f}  {normal_b.x:.6f} {normal_b.y:.6f} {normal_b.z:.6f}  {uv_b.x:.6f} {uv_b.y:.6f} 0\n0  {pos_c.x:.6f} {pos_c.y:.6f} {pos_c.z:.6f}  {normal_c.x:.6f} {normal_c.y:.6f} {normal_c.z:.6f}  {uv_c.x:.6f} {uv_c.y:.6f} 0\n")
            file.write("end\n")
        
        # switch mode back
        if(context_mode_snapshot != "null"):
            bpy.ops.object.mode_set(mode=context_mode_snapshot)
        


class AutoMDLPanel(bpy.types.Panel):
    bl_label = "AutoMDL"
    bl_idname = "PT_AutoMDLPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'AutoMDL'
    
    def draw(self, context):
        layout = self.layout
        
        vis_mesh_valid = checkVisMeshHasMesh(context)
        phy_mesh_valid = checkPhyMeshHasMesh(context)
        
        row = layout.row()
        global steam_path
        if(steam_path is not None):
            row.label(text= "Choose compiler:")
            row = layout.row()
            row.prop(context.scene, "game_select", text="")
        else:
            row.label(text= "Directory containing studiomdl.exe:")
            row = layout.row()
            row.alert = gameManualTextInputIsInvalid
            row.prop(context.scene, "studiomdl_manual_input")
            
        row = layout.row()
        
        row = layout.row()
        row.enabled = vis_mesh_valid
        row.operator("wm.automdl")
        row = layout.row()
        
        row = layout.row()
        row.label(text= "Visual mesh:")
        row.prop_search(context.scene, "vis_mesh", bpy.context.scene, "objects", text="")
        
        row = layout.row()
        row.label(text= "Collision mesh:")
        row.prop_search(context.scene, "phy_mesh", bpy.context.scene, "objects", text="")
        
        row = layout.row()
        
        if vis_mesh_valid:
            if phy_mesh_valid:
                row = layout.row()
                row.enabled = phy_mesh_valid
                row.label(text= "Surface type:")
                row.prop(context.scene, "surfaceprop", text="")
                
                row = layout.row()
                if( not context.scene.staticprop):
                    row.label(text= "Mass:")
                    row.alert = massTextInputIsInvalid
                    row.prop(context.scene, "mass_text_input")
                else:
                    row.label(text= "No mass")
        
                #row = layout.row()
                #row.enabled = phy_mesh_valid
                #row.prop(context.scene, "concave", text="Concave");
        
        
        
        row = layout.row()
        row.label(text= " ")
        row = layout.row()
        

        if vis_mesh_valid:
            if context.scene.vis_mesh.material_slots:
                row.label(text= "Path to VMT files will be:")
                row = layout.row()
                row.prop(context.scene, 'cdmaterials_type', expand=True)
                row = layout.row()
                
                if context.scene.cdmaterials_type == '0':
                    if len(bpy.data.filepath) != 0:
                        if vis_mesh_valid:
                            modelpath = to_models_relative_path(bpy.data.filepath)
                            for slot in context.scene.vis_mesh.material_slots:
                                row = layout.row()
                                row.label(text=os.path.join("materials/models/", modelpath, slot.name).replace("\\", "/") + ".vmt", icon='MATERIAL')
                    else:
                        row.label(text="Blend file is not inside a models folder", icon='ERROR')
                else:
                    draw_ui_list(
                        layout,
                        context,
                        list_path="scene.cdmaterials_list",
                        active_index_path="scene.cdmaterials_list_active_index",
                        unique_id="cdmaterials_list_id",
                    )
            else:
                row.label(text="Visual mesh has no materials", icon='INFO')
                
        row = layout.row()
        row.label(text="")
        row = layout.row()
        row.label(text="General options:")
        row = layout.row()
        row.prop(context.scene, "mostlyopaque", text="Has Transparent Materials")
        
        row = layout.row()
        row.prop(context.scene, "staticprop", text="Static Prop")


# for cdmaterials list

class CdMaterialsPropGroup(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty()


classes = [
    CdMaterialsPropGroup
]

class_register, class_unregister = bpy.utils.register_classes_factory(classes)

def register():
    bpy.types.Scene.surfaceprop_text_input = bpy.props.StringProperty(name="", default="")
    
    bpy.types.Scene.mass_text_input = bpy.props.StringProperty(name="", default="35", description="Mass in kilograms (KG)\nBy default, the Player can +USE pick up 35KG max.\nThe gravgun can pick up 250KG max.\nThe portal gun can pick up 85KG max", update=onMassTextInputChanged)
    
    # vis mesh
    bpy.types.Scene.vis_mesh = bpy.props.PointerProperty(
        type=bpy.types.Object,
        name="Selected Object",
        description="Select an object from the scene"
    )
    
    # col mesh
    bpy.types.Scene.phy_mesh = bpy.props.PointerProperty(
        type=bpy.types.Object,
        name="Selected Object",
        description="Select an object from the scene"
    )
    
    # surfaceprop
    bpy.types.Scene.surfaceprop = bpy.props.EnumProperty(
        name="Selected Option",
        items = [
            ("Concrete", "Concrete", ""),
            ("Chainlink", "Chainlink", ""),
            ("Canister", "Canister", ""),
            ("Crowbar", "Crowbar", ""),
            ("Metal", "Metal", ""),
            ("Metalvent", "Metalvent", ""),
            ("Popcan", "Popcan", ""),
            ("Wood", "Wood", ""),
            ("Plaster", "Plaster", ""),
            ("Dirt", "Dirt", ""),
            ("Grass", "Grass", ""),
            ("Sand", "Sand", ""),
            ("Snow", "Snow", ""),
            ("Ice", "Ice", ""),
            ("Flesh", "Flesh", ""),
            ("Glass", "Glass", ""),
            ("Tile", "Tile", ""),
            ("Paper", "Paper", ""),
            ("Cardboard", "Cardboard", ""),
            ("Plastic_Box", "Plastic_Box", ""),
            ("Plastic_barrel", "Plastic_barrel", ""),
            ("Plastic", "Plastic", ""),
            ("Rubber", "Rubber", ""),
            ("Clay", "Clay", ""),
            ("Porcelain", "Porcelain", ""),
            ("Computer", "Computer", "")
        ]
    )
    
    bpy.types.Scene.staticprop = bpy.props.BoolProperty(
        name="Static Prop",
        description="Enable if used as prop_static\n($staticprop in QC)",
        default=False
    )
    
    bpy.types.Scene.mostlyopaque = bpy.props.BoolProperty(
        name="Has Transparency",
        description="Enabling this may fix sorting issues that come with using transparent materials. \nRenders model in 2 passes, one for opaque materials, and one for materials with transparency\n($mostlyopaque in QC)",
        default=False
    )
    
    
    bpy.types.Scene.cdmaterials_type = bpy.props.EnumProperty(items =
        (
            ('0','Same as MDL',''),
            ('1','Other','')
        )
    )
    
    # cdmaterials list
    class_register()
    bpy.types.Scene.cdmaterials_list = bpy.props.CollectionProperty(type=CdMaterialsPropGroup)
    bpy.types.Scene.cdmaterials_list_active_index = bpy.props.IntProperty()
    
    # set default
    bpy.context.scene.cdmaterials_list.clear()
    bpy.ops.uilist.entry_add(list_path="scene.cdmaterials_list", active_index_path="scene.cdmaterials_list_active_index")
    bpy.context.scene.cdmaterials_list[0].name = "models/"
    
    global steam_path
    global games_paths_list
    steam_path = getSteamInstallationPath()
    if(steam_path != None):
        steam_path = os.path.join(steam_path, "").replace("\\", "/")
        games_paths_list = getGamesList()
        defineGameSelectDropdown(None, bpy.context)
    else:
        steam_path = None
        bpy.types.Scene.studiomdl_manual_input = bpy.props.StringProperty(name="", default="", description="Path to the studiomdl.exe file", update=onGameManualTextInputChanged)
        onGameManualTextInputChanged(None, bpy.context) # need to update once to let the program know of the default value
    
    bpy.utils.register_class(AutoMDLOperator)
    bpy.utils.register_class(AutoMDLPanel)
    
def unregister():
    bpy.utils.unregister_class(AutoMDLOperator)
    bpy.utils.unregister_class(AutoMDLPanel)
    del bpy.types.Scene.surfaceprop_text_input
    del bpy.types.Scene.vis_mesh
    del bpy.types.Scene.phy_mesh
    del bpy.types.Scene.surfaceprop
    del bpy.types.Scene.staticprop
    del bpy.types.Scene.mostlyopaque
    del bpy.types.Scene.mass_text_input
    del bpy.types.Scene.game_select
    del bpy.types.Scene.cdmaterials_type
    del bpy.types.Scene.studiomdl_manual_input
    
    # cdmaterials list
    class_unregister()
    del bpy.types.Scene.cdmaterials_list
    del bpy.types.Scene.cdmaterials_list_active_index


def checkVisMeshHasMesh(context):
    vis_mesh_obj = context.scene.vis_mesh
    return (vis_mesh_obj and vis_mesh_obj.type == 'MESH' and vis_mesh_obj.name in bpy.data.objects) == True


def checkPhyMeshHasMesh(context):
    phy_mesh_obj = context.scene.phy_mesh
    return (phy_mesh_obj and phy_mesh_obj.type == 'MESH' and phy_mesh_obj.name in bpy.data.objects) == True


def to_models_relative_path(file_path):
    MODELS_FOLDER_NAME = "models"

    
    # See if we can find a models folder up the chain
    index = file_path.rfind(MODELS_FOLDER_NAME)

    if index != -1:
        root = file_path[:index + len(MODELS_FOLDER_NAME)]
    else:
        # Alert
        return None

    return os.path.splitext(os.path.relpath(file_path, root))[0].replace("\\", "/")




# lemon's answer in https://blender.stackexchange.com/questions/75332/how-to-find-the-number-of-loose-parts-with-blenders-python-api

# i would implement it myself but i haven't done much graph stuff, and speed is really needed right now, and first implementation would be slow. This here is an efficient alogrithm to count the number of loose parts inside a mesh

from collections import defaultdict

def MakeVertPaths( verts, edges ):
    #Initialize the path with all vertices indexes
    result = {v.index: set() for v in verts}
    #Add the possible paths via edges
    for e in edges:
        result[e.vertices[0]].add(e.vertices[1])
        result[e.vertices[1]].add(e.vertices[0])
    return result

def FollowEdges( startingIndex, paths ):
    current = [startingIndex]

    follow = True
    while follow:
        #Get indexes that are still in the paths
        eligible = set( [ind for ind in current if ind in paths] )
        if len( eligible ) == 0:
            follow = False #Stops if no more
        else:
            #Get the corresponding links
            next = [paths[i] for i in eligible]
            #Remove the previous from the paths
            for key in eligible: paths.pop( key )
            #Get the new links as new inputs
            current = set( [ind for sub in next for ind in sub] )

def CountIslands( obj ):
    #Prepare the paths/links from each vertex to others
    paths = MakeVertPaths( obj.data.vertices, obj.data.edges )
    found = True
    n = 0
    while found:
        try:
            #Get one input as long there is one
            startingIndex = next( iter( paths.keys() ) )
            n = n + 1
            #Deplete the paths dictionary following this starting index
            FollowEdges( startingIndex, paths )               
        except:
            found = False
    return n


def CountIslands2(obj):
    mesh = obj.data
    paths={v.index:set() for v in mesh.vertices}
    for e in mesh.edges:
        paths[e.vertices[0]].add(e.vertices[1])
        paths[e.vertices[1]].add(e.vertices[0])
    lparts=[]
    while True:
        try:
            i=next(iter(paths.keys()))
        except StopIteration:
            break
        lpart={i}
        cur={i}
        while True:
            eligible={sc for sc in cur if sc in paths}
            if not eligible:
                break
            cur={ve for sc in eligible for ve in paths[sc]}
            lpart.update(cur)
            for key in eligible: paths.pop(key)
        lparts.append(lpart)
    
    return len(lparts)


def is_float(value):
  if value is None:
      return False
  try:
      float(value)
      return True
  except:
      return False
