# coding=utf-8
#
# Copyright (C) 2025 Gareth Baldrica-Franklin, gbaldrica@pm.me
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# This program includes source code from the Remove Empty Groups Extension (https://inkscape.org/~MarioVoigt/%E2%98%85remove-empty-groups)
# created by Mario Voight in 2020, which is also licensed under a GNU General Public License, and
# the Deep Ungroup extension, created by Github user jv-rebatov (https://github.com/rebatov/deep-ungroup-inkscape).
#
"""
This extension formats SVG files exported from QGIS into layers based on common styles. 
"""

import inkex
from inkex import Transform, Style, Group
import sys

class QGIS2Inkscape(inkex.EffectExtension):
    startdepth = 1
    maxdepth = 65535
    keepdepth = 0
    #DEEP UNGROUP
    def _merge_transform(self, node, transform):
        """Propagate transform to remove inheritance"""
        try:
            # Handle SVG viewBox transformation
            if node.tag.endswith('}svg') and node.get("viewBox"):
                try:
                    vx, vy, vw, vh = [float(x) for x in node.get("viewBox").split()]
                    dw = float(node.get("width", vw))
                    dh = float(node.get("height", vh))
                    viewbox_transform = Transform(
                        f"translate({-vx}, {-vy}) scale({dw / vw}, {dh / vh})")
                    this_transform = viewbox_transform @ Transform(transform)
                    this_transform = this_transform @ Transform(node.get("transform"))
                    del node.attrib["viewBox"]
                except (ValueError, TypeError, ZeroDivisionError):
                    this_transform = Transform(transform) @ Transform(node.get("transform"))
            else:
                this_transform = Transform(transform) @ Transform(node.get("transform"))

            # Set the node's transform - only set if it's not empty or identity
            transform_str = str(this_transform)
            if transform_str and transform_str != "translate(0,0)" and transform_str != "matrix(1,0,0,1,0,0)":
                node.set("transform", transform_str)
            else:
                node.pop("transform", None)
        except Exception as e:
            # Fallback: apply transform directly without modification
            # Only log in headless mode or when debugging
            if transform and str(transform) != "translate(0,0)" and str(transform) != "matrix(1,0,0,1,0,0)":
                existing_transform = node.get("transform", "")
                if existing_transform:
                    node.set("transform", f"{transform} {existing_transform}")
                else:
                    node.set("transform", str(transform))

    def _merge_style(self, node, parent_style):
        """Propagate style to remove inheritance"""
        try:
            # Parse current node's style
            current_style = Style(node.get("style", ""))
            
            # Convert node's XML style attributes to style properties and remove them
            inheritable_xml_attrs = ["fill", "stroke", "opacity", "stroke-width", "stroke-dasharray", 
                                   "stroke-linecap", "stroke-linejoin", "fill-opacity", "stroke-opacity",
                                   "font-family", "font-size", "font-weight", "font-style"]
            
            for attr in inheritable_xml_attrs:
                if node.get(attr):
                    # Node's own XML attribute takes precedence over everything
                    current_style[attr] = node.get(attr)
                    node.pop(attr, None)
            
            # Attributes that should not be propagated to children (remain local)
            non_propagated = ["filter", "mask", "clip-path"]
            local_style = Style()
            
            # Separate non-propagated attributes
            for key in non_propagated:
                if key in current_style:
                    local_style[key] = current_style[key]
                    del current_style[key]

            # Create merged style: parent styles + node's own styles (node takes precedence)
            merged_style = Style(parent_style) if parent_style else Style()
            merged_style.update(current_style)
            
            # Add back the non-propagated local styles
            merged_style.update(local_style)

            # Apply the final style to the node
            if merged_style:
                node.style = merged_style
            else:
                node.pop("style", None)
                    
        except Exception as e:
            # Fallback: preserve existing styles
            # Keep existing style as-is to avoid breaking the element
            pass

    def _merge_clippath(self, node, parent_clippath_url):
        """Handle clip-path inheritance"""
        if not parent_clippath_url:
            return

        try:
            node_transform = Transform(node.get("transform"))
            
            # Check if transform is not identity (check for meaningful transforms)
            transform_str = str(node_transform)
            if transform_str and transform_str != "translate(0,0)" and transform_str != "matrix(1,0,0,1,0,0)":
                # Create new clipPath with inverse transform
                inverse_transform = -node_transform
                
                # Ensure defs element exists
                if self.svg.defs is None:
                    self.svg.defs = inkex.etree.SubElement(self.svg, 'defs')
                
                # Create clipPath element manually
                new_clippath = inkex.etree.SubElement(
                    self.svg.defs, 'clipPath',
                    {'clipPathUnits': 'userSpaceOnUse',
                     'id': self.svg.get_unique_id("clipPath")})
                
                # Find original clippath
                original_clippath_id = parent_clippath_url[5:-1]  # Remove "url(#" and ")"
                original_clippath = self.svg.getElementById(original_clippath_id)
                
                if original_clippath is not None:
                    # Reference original clippath elements with inverse transform
                    for child in original_clippath:
                        if child.get('id'):  # Only process children with IDs
                            use_elem = inkex.etree.SubElement(
                                new_clippath, 'use',
                            {'href': f"#{child.get('id')}", 
                             'transform': str(inverse_transform),
                             'id': self.svg.get_unique_id("use")})
                    
                    parent_clippath_url = f"url(#{new_clippath.get('id')})"

            # Apply clip-path to node or chain it if node already has one
            current_clippath = node.get("clip-path")
            if current_clippath:
                # Find the end of the clip-path chain
                clippath_element = self.svg.getElementById(current_clippath[5:-1])
                while clippath_element is not None and clippath_element.get("clip-path"):
                    next_clippath_url = clippath_element.get("clip-path")
                    clippath_element = self.svg.getElementById(next_clippath_url[5:-1])
                
                if clippath_element is not None:
                    clippath_element.set("clip-path", parent_clippath_url)
            else:
                node.set("clip-path", parent_clippath_url)
        except Exception as e:
            # Fallback: apply clip-path directly
            if not node.get("clip-path"):
                node.set("clip-path", parent_clippath_url)

    def _ungroup(self, group_node):
        """Flatten a group into the same z-order as its parent"""
        try:
            parent = group_node.getparent()
            if parent is None:
                return

            parent_index = list(parent).index(group_node)
            
            # Collect group style including XML attributes that should be inherited
            group_style = Style(group_node.get("style", ""))
            
            # Add inheritable XML attributes to the style
            inheritable_attrs = ["fill", "stroke", "opacity", "stroke-width", "stroke-dasharray", 
                               "stroke-linecap", "stroke-linejoin", "fill-opacity", "stroke-opacity",
                               "font-family", "font-size", "font-weight", "font-style"]
            
            for attr in inheritable_attrs:
                attr_value = group_node.get(attr)
                if attr_value and attr not in group_style:
                    group_style[attr] = attr_value
            
            group_transform = Transform(group_node.get("transform"))
            group_clippath = group_node.get("clip-path")

            # Process children in reverse order to maintain z-order
            children = list(group_node)
            for child in reversed(children):
                try:
                    self._merge_transform(child, group_transform)
                    self._merge_style(child, group_style)
                    self._merge_clippath(child, group_clippath)
                    parent.insert(parent_index, child)
                except Exception as e:
                    # Still try to move the child to preserve structure
                    try:
                        parent.insert(parent_index, child)
                    except:
                        pass

            # Remove the now-empty group
            parent.remove(group_node)
        except Exception as e:
            # Log only critical ungroup failures
            inkex.errormsg(f"Failed to ungroup {group_node.get('id', 'unknown')}: {e}")

    def _should_ungroup(self, node, depth, height):
        """Determine if a node should be ungrouped based on criteria"""
        return (node.tag.endswith('}g') and  # SVG group element
                node.getparent() is not None and
                height >= self.keepdepth and
                depth >= self.startdepth and
                depth <= self.maxdepth)

    def _deep_ungroup(self, node):
        """Recursively ungroup using iteration to avoid stack limits"""
        # Use a stack-based approach instead of recursion
        stack = [{'node': node, 'depth': 0, 'prev': {'height': None}, 'height': None}]

        while stack:
            current = stack[-1]
            current_node = current['node']
            depth = current['depth']
            height = current['height']

            # Forward pass: calculate height
            if height is None:
                # Skip non-graphical elements using tag checking
                tag = current_node.tag
                if (tag.endswith('}namedview') or tag.endswith('}defs') or 
                    tag.endswith('}metadata') or tag.endswith('}foreignObject')):
                    stack.pop()
                    continue

                # Base case: not a group or empty group
                if not tag.endswith('}g') or len(current_node) == 0:
                    current['height'] = 0
                else:
                    # Recursive case: process children
                    depth += 1
                    for child in current_node:
                        stack.append({
                            'node': child, 
                            'prev': current,
                            'depth': depth, 
                            'height': None
                        })
            else:
                # Backward pass: process ungrouping
                if self._should_ungroup(current_node, depth, height):
                    self._ungroup(current_node)

                # Propagate height up
                height += 1
                previous = current['prev']
                prev_height = previous['height']
                if prev_height is None or prev_height < height:
                    previous['height'] = height

                stack.pop()

    def run_ungroup(self):
        """Main effect method"""
        try:
            root_children = list(self.svg)
            for element in root_children:
                try:
                    self._deep_ungroup(element)
                except Exception as e:
                    inkex.errormsg(f"Error processing document element {element.get('id', 'unknown')}: {e}")
            
        except Exception as e:
            inkex.errormsg(f"Deep Ungroup: Critical error in main effect: {e}")
            # Re-raise to ensure Inkscape knows the extension failed
            raise
    
    def effect(self):
        #REMOVE EMPTY GROUPS
        # gets all group elements in document, at any/all nested levels
        groups = self.document.xpath('//svg:g',namespaces=inkex.NSS)
        # end if there are no groups
        if len(groups) == 0:
            return
        # loop through groups
        for group in groups:
            # checks if item is empty leaf, and if so prune up branch
            while len(group.getchildren()) == 0:
                # this group is empty, delete it
                parent = group.getparent()
                parent.remove(group)
                # see if we should delete the parent too, recursively
                group = parent
        #UNGROUP REMAINING ELEMENTS
        self.run_ungroup()
        #DELETE RECTANGLES
        rects = self.document.xpath('//svg:rect',namespaces=inkex.NSS)
        for rect in rects:
            rect.delete()
        #SORT BY STYLE
        for group in groups:
            styles = []
            colorGroup = []
            #create list of styles
            for child in group.getchildren():
                style = child.style
                if style not in styles:
                    styles.append(style)
                    groupNum = len(styles)
                    groupName = "Group" + str(groupNum)
                    newGroup = group.add(Group.new(groupName))
                    colorGroup.append(newGroup)
            #move children to styles
            for child in group.getchildren():
                if child.tag_name != 'g':
                    style = child.style
                    if style in styles:
                        f = styles.index(style)
                        colorGroup[f].add(child)
        
if __name__ == '__main__':
    QGIS2Inkscape().run()
