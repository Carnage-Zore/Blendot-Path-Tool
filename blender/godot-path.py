import bpy, os, json, mathutils
from bpy.props import EnumProperty, BoolProperty, StringProperty
from bpy.types import Panel, Operator

bl_info = {
    "name": "Godot Path Exporter",
    "author": "Lewis Cianci",
    "version": (1, 0),
    "blender": (2, 80, 0),
    "location": "View3D > Add Mesh",
    "description": "Exports paths for godot",
    "category": "3D View",
}

"""
CarnageZore - Made modifications:
* Added UI
* Removed Save hook
* Allowed for exporting only the selected curves as well as all (two seperate buttons)

This change includes 2 operators that both call the search_for_curves function wich
I have modified to incorporate the filename and filepath properties. 

I have including a new function to fix invalid filenames.

I have replaced the collection looping with a more efficient way of finding the objects using 
bpy.context.selected_objects or bpy.data.objects for all
instead of looping through each collection to get the objects.

With the UI the persistancy is pointless so its gone.

I removed the references to csv as it didnt seem to be used.

"""

def write_curve_data_to_array(curve, curvesArray):
    axis_correct = mathutils.Matrix((
    (1, 0, 0),  # X in blender is  X in Godot
    (0, 0, -1),  # Y in blender is -Z in Godot
    (0, 1, 0),  # Z in blender is  Y in Godot
    )).normalized()
    
    print('exporting ' + curve.name)
    for spline in curve.data.splines:
        #points = []
        pointLocations = []
        print(spline.type)
        if spline.type == 'BEZIER':
            pointIndex = 0
            src_points = spline.bezier_points
            if spline.use_cyclic_u:
                # Godot fakes a closed path by adding the start point at the end
                # https://github.com/godotengine/godot-proposals/issues/527
                src_points = [*src_points, src_points[0]]
            for point in src_points:
                # blender handles are absolute
                # godot handles are relative to the control point
                #points.extend((point.handle_left - point.co) @ axis_correct)
                #points.extend((point.handle_right - point.co) @ axis_correct)
                #points.extend(point.co @ axis_correct)
                #tilts.append(point.tilt)
                 pointLocation = {
                    'leftHandle': list((point.handle_left - point.co) @ axis_correct),
                    'rightHandle': list((point.handle_right - point.co) @ axis_correct),
                    'position': list(point.co @ axis_correct),
                    'tilt': point.tilt
                 }
                 pointLocations.append(pointLocation)
                 print(pointLocation)
            #print(points)
            # data = {}
            curveData = {}

            curveData["name"] = curve.name
            curveData["points"] = pointLocations
            translatedPosition = curve.matrix_world.to_translation()
            curveData["location"]= {"x": translatedPosition.x, "y": translatedPosition.y, "z": translatedPosition.z}
            curveData["scale"] = {"x": curve.scale.x, "y": curve.scale.y, "z": curve.scale.z}
            curveData["rotation"] = {"x": curve.rotation_euler.x, "y": curve.rotation_euler.z, "z": curve.rotation_euler.y}
            curvesArray.append(curveData)
             
def recursively_search_curves(obj, curvesArray):
    print(obj.name)
    print(obj.type)
    if obj.data is not None and obj.type is not None:
        if obj.type == 'CURVE':
            write_curve_data_to_array(obj, curvesArray)
        for child in obj.children:
            recursively_search_curves(child, curvesArray)

def validate_filename(filename):
    for c in ["*", "?", "<", ">", "|", "\"", "\\", "/", ":"]:
        filename = filename.replace(c, "")
    return filename.replace(".json","")

def search_for_curves(export_all=False):
    output_file = bpy.context.scene.curve_export_filepath
    filename = validate_filename(bpy.context.scene.curve_export_filename.strip())
    #blend_base_name = os.path.splitext(os.path.basename(blend_file_path))[0]
    #output_dir = os.path.join(os.path.dirname(blend_file_path), blend_base_name)
    #output_file = os.path.join(output_dir, blend_base_name + 'curves.json')
    if not os.path.exists(output_file):
        print('Folder does not exist.')
        return False
    if filename == "":
        print('File name must be at least 1 charcter long.')
        return False
    print('File is being saved!!')
    
    curves = []
    if export_all:
        #for collection in bpy.data.collections:
        #    print(collection.name)
        #    for obj in collection.all_objects:
        for ob in bpy.data.objects:
            recursively_search_curves(ob, curves)
    else:
        for ob in bpy.context.selected_objects:
            recursively_search_curves(ob, curves)
    # print(bpy.context.scene.objects)
    # recursively_search_curves(bpy.context.scene.objects, curves)
    #os.makedirs(os.path.dirname(), exist_ok=True)
    with open(f"{output_file}/{filename}.json", 'w+', encoding='utf-8') as f:
        json.dump(curves, f, ensure_ascii=False, indent=4)

    return True

class ExportCurvesUI(Panel):
    bl_label = "Export Bézier Curves for Godot"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Export Curves'

    def draw(self, context):
        ui = self.layout
        ui.prop(context.scene, "curve_export_filepath")
        ui.prop(context.scene, "curve_export_filename")
        box = ui.box()
        box.label(text="Export All Bézier Curves")
        box.operator(ExportAllCurves.bl_idname, text=ExportAllCurves.bl_label)
        box = ui.box()
        box.label(text="Export Selected Bézier Curves")
        box.operator(ExportSelectedCurves.bl_idname, text=ExportSelectedCurves.bl_label)

class ExportAllCurves(Operator):
    bl_label = "Export"
    bl_idname = "export.all_curves"
    bl_options = {"REGISTER"}

    def execute(self, context):
        search_for_curves(True)
        return {"FINISHED"}

class ExportSelectedCurves(Operator):
    bl_label = "Export"
    bl_idname = "export.selected_curves"
    bl_options = {"REGISTER"}

    def execute(self, context):
        search_for_curves()
        return {"FINISHED"}

classes = (
    ExportCurvesUI, 
    ExportAllCurves, 
    ExportSelectedCurves
)

def register():
    print('[Export Bézier Curves] registering')
    bpy.types.Scene.curve_export_filepath = StringProperty(
        name="Output Folder", description="The folder the file will be saved to",
        default="", subtype="DIR_PATH"
    )
    bpy.types.Scene.curve_export_filename = StringProperty(
        name="File name", description="The name of the output file",
        default=""
    )
    for clss in classes:
        bpy.utils.register_class(clss)
    
def unregister():
    print('[Export Bézier Curves] un-registering')
    for clss in reversed(classes):
        bpy.utils.unregister_class(clss)

    del bpy.types.Scene.curve_export_filename
    del bpy.types.Scene.curve_export_filepath

if __name__ == "__main__":
    register()
