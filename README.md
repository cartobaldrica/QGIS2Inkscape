# QGIS2Inkscape
An Inkscape extension for formatting SVG exports from QGIS. Typicaly, SVG exports are filled with empty layers and ungrouped styles. This extension is therefore designed to increase ease of use for QGIS > Inkscape cartographic workflows.

### Installing
    1. Download the QGIS2Inkscape library ZIP file, and unzip the QGIS2Inkscape folder.
    2. Open Inkscape.
    3. In Settings > System > User extensions, you can access the where Inkscape extensions are housed. Open the folder.
    4. Copy the QGIS2Inkscape folder into the extensions folder.
    5. Restart Inkscape.
    6. The QGIS2Inkscape extension can be found in Extensions > QGIS2Inkscape.

### How to Use
    1. Create a map in QGIS! 
    2. Create a layout using your QGIS map.
    3. Once your layout has been created, select "Export Map as SVG"
    4. In the "SVG Export Optiosn" window, select the following settings. 
        * [✔️] Export map layers as SVG Groups
        * [✔️] Always export as vectors (select this even if you raster layers)
        * [✔️] Export RDF Medata
        * [ ] Simplify geometries to reduce file output size
        * Text Export: Always Export Text as Text Objects
    5. Open the resulting SVG in Inkscape.
    6. Select and run the QGIS2Inkscape extension!
