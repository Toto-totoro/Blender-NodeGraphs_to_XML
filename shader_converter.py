# Blender NodeGraphs_to_XML
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
import hashlib
import traceback
from lxml import etree as ET
from .geometry_converter import convert_nodegroup_to_xml


def convert_materials_to_xml(materials: list) -> str:
    # root element
    root = ET.Element("ShaderGraphs")

    for material in materials:
        convert_material_to_xml(material, root)

    return ET.tostring(root, pretty_print=True).decode()


def convert_material_to_xml(material, root):
    material_element = ET.SubElement(root, "Material", name=material.name)

    # TODO: check if output format is optimal for info retrieval

    # Iterate through the nodes in the node group
    for node in material.node_tree.nodes:
        
        # check for node groups and convert them recursively
        if node.bl_idname == "ShaderNodeGroup" or node.bl_idname == "GeometryNodeGroup":
            if node.node_tree is not None:
                convert_nodegroup_to_xml(node.node_tree, material_element)
            else:
                print(f"Node group {node.name} has no node tree assigned.")
            continue  # Skip the rest for node groups
            


        node_element = ET.SubElement(material_element, "Node", name=node.name, type=node.bl_idname)

        # mostly properties regarding graphical representation in blender
        # TODO: validate wether all needed node properties are exported
        filter_unnecessary = {
        'type',
        'name',
        'label',
        
        'width',
        'height',
        'use_custom_color',
        'color_tag',
        'select',
        'show_options',
        'show_preview',
        'hide',
        'show_texture',
        'internal_links',
        'warning_propagation',

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
        'parent', # TODO: might be useful, don't know, investigate
        'color',

        # TODO: verify if these are needed
        'texture_mapping',
        'color_mapping'
        }



        for prop_name in node.bl_rna.properties.keys():
            if prop_name in filter_unnecessary:  # filter out unnecessary properties
                continue
            prop = getattr(node, prop_name)

            # collection properties (inputs, outputs)
            if isinstance(prop, bpy.types.bpy_prop_collection):
                convert_bpy_collection_to_xml(prop, prop_name, node_element)

            # standard type properties
            elif isinstance(prop, (str, int, float, bool)):
                ET.SubElement(node_element, "Constant", name=prop_name, value=str(prop))

            # mapping properties (TexMapping, ColorMapping)
            #! Not Sure if these are even needed lol
            # elif isinstance(prop, bpy.types.TexMapping) or isinstance(prop, bpy.types.ColorMapping):
            #    convert_bpy_mapping_to_xml(prop, prop_name, node_element)

            # vector properties (Vector)
            elif isinstance(prop, mathutils.Vector):
                convert_mathutils_vector_to_xml(prop, prop_name, node_element)

            else:
                print(f"Unsupported property type for {prop_name} in node {node.name}: {type(prop)}")

    # TODO: sort links in graph order
    # Store node links
    # Format: <Link from_node="NodeA" from_socket="Output" to_node="NodeB" to_socket="Input"/>
    # Socket is the connection point (variable) from the graph
    
    for link in nodegroup.links:
        from_id = port_id_hash(link.from_node.name, link.from_socket.as_pointer())
        to_id = port_id_hash(link.to_node.name, link.to_socket.as_pointer())
        connection_element = ET.SubElement(
            nodegroup_element,
            "Connection"
        )
        connection_element.set("from", from_id)
        connection_element.set("to", to_id)



###################################################
# Conversion Helpers for different property types #
###################################################

def convert_mathutils_vector_to_xml(prop, prop_name, parent_element):
    try:
        vector_element = ET.SubElement(parent_element, "Property", name=prop_name, type=type(prop).__name__)
        for i, v in enumerate(prop):
            ET.SubElement(vector_element, "Value", data=str(v))
    except Exception as e:
        print(f"{prop_name}: {type(prop)} | is not a mathutils.Vector")
        traceback.print_exc()

def convert_mathutils_euler_to_xml(prop, prop_name, parent_element):
    try:
        euler_element = ET.SubElement(parent_element, "Property", name=prop_name, type=type(prop).__name__)
        for i, v in enumerate(prop):
            ET.SubElement(euler_element, "Value", data=str(v))
        ET.SubElement(euler_element, "Value", data=str(prop.order))
    except Exception as e:
        print(f"{prop_name}: {type(prop)} | is not a mathutils.Euler")
        traceback.print_exc()

def convert_bpy_collection_to_xml(prop, prop_name, parent_element):
    try:
        for item in prop:
            if item is None:
                continue

            if item.is_linked:
                item_element = ET.SubElement(parent_element, "Port", name=item.name, direction="out" if item.is_output else "in", id=port_id_hash(parent_element.get("name"), item.as_pointer()))
            else:
                if item.is_output:
                    continue  # Skip unlinked output items
                
                if hasattr(item, 'default_value'):
                    if isinstance(item.default_value, bpy.types.bpy_prop_array):
                        item_element = ET.SubElement(parent_element, "Port", name="vectorIn", direction="in", id=port_id_hash(parent_element.get("name"), item.as_pointer()))
                        extracted_vec_element = ET.SubElement(parent_element.getparent(), "Node", name=item.name, type=str(getattr(item, 'type', None)))
                        vec_coordinate_names = ['x', 'y', 'z']
                        for i in range(3):
                            ET.SubElement(extracted_vec_element, "Constant", name=vec_coordinate_names[i], value=str(item.default_value[i]))
                        extracted_vec_element_outsocket = ET.SubElement(extracted_vec_element, "Port", name="vectorOut", direction="out", id=port_id_hash(parent_element.get("name"), f"{item.as_pointer()}vectorOut"))

                        ET.SubElement(parent_element.getparent(), "Connection", from_=extracted_vec_element_outsocket.get("id"), to=item_element.get("id"))
                    else:
                        item_element = ET.SubElement(parent_element, "Constant", name=item.name, value=str(item.default_value))

    except Exception as e:
        print(f"{prop_name}: {type(prop)} | is not a bpy.types.bpy_prop_collection")
        traceback.print_exc()

# TODO: ColorMapping has item ColorRamp, which is a collection (of ColorRampElements); needs special handling, not imlemented yet
def convert_bpy_mapping_to_xml(prop, prop_name, parent_element):
    texture_mapping_element = ET.SubElement(parent_element, "Constant", name=prop_name)
    for item, item_value in prop.bl_rna.properties.items():
        if item == 'rna_type':
            continue
        item_value = getattr(prop, item, None)
        item_element = ET.SubElement(texture_mapping_element, "Item", name=str(item), type=type(item_value).__name__)
        if isinstance(item_value, mathutils.Vector) or isinstance(item_value, mathutils.Euler) or isinstance(item_value, mathutils.Color):
            for v in item_value:
                ET.SubElement(item_element, "Value", data=str(v))
            if isinstance(item_value, mathutils.Euler):
                ET.SubElement(item_element, "Value", data=str(item_value.order))
                
        else:
            item_element.set("value", str(item_value))


########################
# Other Helper Methods #
########################

def port_id_hash(parent_name, item_pointer):
    return hashlib.sha1(f'{parent_name}{item_pointer}'.encode()).hexdigest()
