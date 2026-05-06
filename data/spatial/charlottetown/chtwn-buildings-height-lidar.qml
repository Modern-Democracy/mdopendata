<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="3.34" styleCategories="Symbology|Labeling|Fields|Forms|Rendering">
  <renderer-v2 type="graduatedSymbol" attr="height_lidar_m" graduatedMethod="GraduatedColor" symbollevels="0" forceraster="0" enableorderby="0">
    <ranges>
      <range symbol="0" lower="0.000000000000000" upper="4.000000000000000" label="0 - 4 m"/>
      <range symbol="1" lower="4.000000000000000" upper="7.000000000000000" label="4 - 7 m"/>
      <range symbol="2" lower="7.000000000000000" upper="10.000000000000000" label="7 - 10 m"/>
      <range symbol="3" lower="10.000000000000000" upper="14.000000000000000" label="10 - 14 m"/>
      <range symbol="4" lower="14.000000000000000" upper="20.000000000000000" label="14 - 20 m"/>
      <range symbol="5" lower="20.000000000000000" upper="40.000000000000000" label="20 - 40 m"/>
    </ranges>
    <symbols>
      <symbol type="fill" name="0" alpha="0.88" clip_to_extent="1" force_rhr="0">
        <layer class="SimpleFill" enabled="1" pass="0" locked="0">
          <prop k="color" v="241,248,233,225"/>
          <prop k="outline_color" v="92,112,82,130"/>
          <prop k="outline_width" v="0.12"/>
          <prop k="outline_width_unit" v="MM"/>
          <prop k="style" v="solid"/>
        </layer>
      </symbol>
      <symbol type="fill" name="1" alpha="0.88" clip_to_extent="1" force_rhr="0">
        <layer class="SimpleFill" enabled="1" pass="0" locked="0">
          <prop k="color" v="198,232,190,225"/>
          <prop k="outline_color" v="80,105,76,130"/>
          <prop k="outline_width" v="0.12"/>
          <prop k="outline_width_unit" v="MM"/>
          <prop k="style" v="solid"/>
        </layer>
      </symbol>
      <symbol type="fill" name="2" alpha="0.88" clip_to_extent="1" force_rhr="0">
        <layer class="SimpleFill" enabled="1" pass="0" locked="0">
          <prop k="color" v="123,199,160,225"/>
          <prop k="outline_color" v="47,92,77,135"/>
          <prop k="outline_width" v="0.12"/>
          <prop k="outline_width_unit" v="MM"/>
          <prop k="style" v="solid"/>
        </layer>
      </symbol>
      <symbol type="fill" name="3" alpha="0.88" clip_to_extent="1" force_rhr="0">
        <layer class="SimpleFill" enabled="1" pass="0" locked="0">
          <prop k="color" v="56,154,163,225"/>
          <prop k="outline_color" v="32,78,86,145"/>
          <prop k="outline_width" v="0.12"/>
          <prop k="outline_width_unit" v="MM"/>
          <prop k="style" v="solid"/>
        </layer>
      </symbol>
      <symbol type="fill" name="4" alpha="0.88" clip_to_extent="1" force_rhr="0">
        <layer class="SimpleFill" enabled="1" pass="0" locked="0">
          <prop k="color" v="55,98,160,225"/>
          <prop k="outline_color" v="34,56,97,155"/>
          <prop k="outline_width" v="0.12"/>
          <prop k="outline_width_unit" v="MM"/>
          <prop k="style" v="solid"/>
        </layer>
      </symbol>
      <symbol type="fill" name="5" alpha="0.88" clip_to_extent="1" force_rhr="0">
        <layer class="SimpleFill" enabled="1" pass="0" locked="0">
          <prop k="color" v="73,45,121,225"/>
          <prop k="outline_color" v="43,31,75,160"/>
          <prop k="outline_width" v="0.12"/>
          <prop k="outline_width_unit" v="MM"/>
          <prop k="style" v="solid"/>
        </layer>
      </symbol>
    </symbols>
    <source-symbol>
      <symbol type="fill" name="0" alpha="0.88" clip_to_extent="1" force_rhr="0">
        <layer class="SimpleFill" enabled="1" pass="0" locked="0">
          <prop k="color" v="123,199,160,225"/>
          <prop k="outline_color" v="47,92,77,135"/>
          <prop k="outline_width" v="0.12"/>
          <prop k="outline_width_unit" v="MM"/>
          <prop k="style" v="solid"/>
        </layer>
      </symbol>
    </source-symbol>
    <classificationMethod id="EqualInterval">
      <symmetricMode enabled="0" astride="0" symmetrypoint="0"/>
    </classificationMethod>
  </renderer-v2>
  <labeling type="simple">
    <settings>
      <text-style fieldName="" fontFamily="Arial" fontSize="8" fontSizeUnit="Point" namedStyle="Regular" previewBkgrdColor="#ffffff" textColor="35,35,35,255" isExpression="0"/>
      <text-format blendMode="0" multilineHeight="1" multilineHeightUnit="Percentage"/>
      <placement placement="0" centroidWhole="0" fitInPolygonOnly="0" dist="0"/>
      <rendering drawLabels="0"/>
    </settings>
  </labeling>
  <fieldConfiguration>
    <field name="source_osm_building_id"/>
    <field name="osm_type"/>
    <field name="osm_id"/>
    <field name="building"/>
    <field name="name"/>
    <field name="levels"/>
    <field name="source_tags"/>
    <field name="extracted_at"/>
    <field name="source_note"/>
    <field name="height_lidar_m"/>
    <field name="height_lidar_method"/>
    <field name="height_lidar_confidence"/>
    <field name="height_lidar_status"/>
    <field name="height_lidar_source_tiles"/>
    <field name="height_lidar_point_count"/>
    <field name="height_lidar_ground_m"/>
    <field name="height_lidar_roof_m"/>
    <field name="height_lidar_updated_at"/>
    <field name="height_lidar_provenance"/>
  </fieldConfiguration>
  <blendMode>0</blendMode>
  <featureBlendMode>0</featureBlendMode>
  <layerOpacity>1</layerOpacity>
</qgis>
