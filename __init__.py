
bl_info = {
    "name": "AutoMDL",
    "author": "NvC_DmN_CH",
    "version": (1, 0),
    "blender": (2, 8, 0),
    "location": "View3D > Sidebar > AutoMDL",
    "description": "Compiles models for Source where the blend project file is",
    "warning": "",
    "wiki_url": "",
    "category": "3D View"
}

from . import addon

def register():
    addon.register()
    
def unregister():
    addon.unregister()