# Blender ShaderGraph_to_XML
# Contributor(s): Tom Schäfer (tschaefer.acc@gmail.com) and Laurin von Bergmann
#
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import bpy
import mathutils
from lxml import etree as ET

def convert_materials_to_xml(materials: list) -> str:
    # root element
    root = ET.Element("ShaderGraphs")

    for material in materials:
        convert_shader_graph_to_xml(material, root)

    return ET.tostring(root, pretty_print=True).decode()

def convert_shader_graph_to_xml(material, root):
    material_element = ET.SubElement(root, "Material", name=material.name)

    # TODO: node groups should get replaced by their contents. They can be identified by their bl_idname "ShaderNodeGroup" and accessed via bpy.data.node_groups.
    # TODO: check if output format is optimal for info retrieval

    # Iterate through the nodes in the material's node tree
    for node in material.node_tree.nodes:
        node_element = ET.SubElement(material_element, "Node", type=node.bl_idname, name=node.name)

        # Add properties of the node as sub-elements

        """
        Replaced property selection by filtering out, since many nodes have special properties
        and unneccesary ones are shared by most (if not all)
        """
        # property_selection = {
        #     'type', 'inputs', 'outputs', 'internal_links', 'node_tree'
        # }
        


        filter_unnecessary = {
        'width',
        'height',
        'use_custom_color',
        'color_tag',
        'select',
        'show_options',
        'show_preview',
        'hide',
        'show_texture',

        'bl_idname',
        'bl_label',
        'bl_description',
        'bl_icon',
        'bl_static_type',
        'bl_width_default',
        'bl_width_min',
        'bl_width_max',
        'bl_height_default',
        'bl_height_min',
        'bl_height_max',

        # these are currently filtered out by isinstance checking anyway lol
        'rna_type',
        'location',
        'location_absolute',
        'dimensions',
        'parent', #TODO might be useful, don't know, investigate
        'color'
        }


        # TODO: validate wether all needed node properties are exported
        # TODO: list of currently unsupported properties (details at end of file):
        """
        color_mapping, image, image_user, sun_direction, object, mapping
        """

        for prop_name in node.bl_rna.properties.keys():
            if prop_name in filter_unnecessary:  # filter out unnecessary properties
                continue
            prop = getattr(node, prop_name)

            # collection properties (inputs, outputs, internal_links)
            if isinstance(prop, bpy.types.bpy_prop_collection):
                collection_element = ET.SubElement(node_element, "Property", name=prop_name, type=type(prop).__name__)
                for item in prop.keys():
                    if prop.get(item) is None:
                        continue
                    item = prop.get(item)
                    item_element = ET.SubElement(collection_element, "Item", name=item.name, type=str(getattr(item, 'type', None)))
                    if hasattr(item, 'default_value'):
                        if isinstance(item.default_value, bpy.types.bpy_prop_array):
                            for v in item.default_value:
                                ET.SubElement(item_element, "Value", data=str(v))
                        else:
                            item_element.set("value", str(item.default_value))

            # standard type properties
            elif isinstance(prop, (str, int, float, bool)):
                ET.SubElement(node_element, "Property", name=prop_name, type=type(prop).__name__, value=str(prop))

            # texture mapping property
            elif isinstance(prop, bpy.types.TexMapping):
                texture_mapping_element = ET.SubElement(node_element, "Property", name=prop_name, type=type(prop).__name__)
                for item, item_value in prop.bl_rna.properties.items():
                    if item == 'rna_type':
                        continue
                    item_element = ET.SubElement(texture_mapping_element, "Item", name=str(item), type=type(item_value).__name__)
                    
                    if isinstance(item_value, bpy.types.FloatProperty):
                        for v in getattr(prop, item, None):
                            ET.SubElement(item_element, "Value", data=str(v))
                    else:
                        item_element.set("value", str(getattr(prop, item, None)))

            # vector properties (Vector)
            elif isinstance(prop, mathutils.Vector):
                vector_element = ET.SubElement(node_element, "Property", name=prop_name, type=type(prop).__name__)
                for i, v in enumerate(prop):
                    ET.SubElement(vector_element, "Value", data=str(v))

            else:
                print(f"Unsupported property type for {prop_name} in node {node.name}: {type(prop)}")

    # TODO: sort links in graph order
    # Store node links
    # Format: <Link from_node="NodeA" from_socket="Output" to_node="NodeB" to_socket="Input"/>
    # Socket is the connection point (variable) from the graph
    links_element = ET.SubElement(material_element, "Links")
    for link in material.node_tree.links:
        ET.SubElement(
            links_element,
            "Link",
            from_node=link.from_node.name,
            from_socket=link.from_socket.name,
            to_node=link.to_node.name,
            to_socket=link.to_socket.name,
        )

"""
Unsupported property type for color_mapping in node Brick Texture: <class 'bpy.types.ColorMapping'>
Unsupported property type for color_mapping in node Checker Texture: <class 'bpy.types.ColorMapping'>
Unsupported property type for color_mapping in node Gradient Texture: <class 'bpy.types.ColorMapping'>
Unsupported property type for color_mapping in node Gabor Texture: <class 'bpy.types.ColorMapping'>
Unsupported property type for image in node Image Texture: <class 'NoneType'>
Unsupported property type for color_mapping in node Image Texture: <class 'bpy.types.ColorMapping'>
Unsupported property type for image_user in node Image Texture: <class 'bpy.types.ImageUser'>
Unsupported property type for color_mapping in node Magic Texture: <class 'bpy.types.ColorMapping'>
Unsupported property type for color_mapping in node Noise Texture: <class 'bpy.types.ColorMapping'>
Unsupported property type for color_mapping in node Noise Texture.001: <class 'bpy.types.ColorMapping'>
Unsupported property type for color_mapping in node Sky Texture: <class 'bpy.types.ColorMapping'>
Unsupported property type for color_mapping in node Voronoi Texture: <class 'bpy.types.ColorMapping'>
Unsupported property type for color_mapping in node Wave Texture: <class 'bpy.types.ColorMapping'>
Unsupported property type for object in node Texture Coordinate: <class 'NoneType'>
Unsupported property type for mapping in node RGB Curves: <class 'bpy.types.CurveMapping'>
Unsupported property type for mapping in node Float Curve: <class 'bpy.types.CurveMapping'>
"""