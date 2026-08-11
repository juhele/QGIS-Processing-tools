# -*- coding: utf-8 -*-
"""
Safecast Fixed Sensors Loader
QGIS Processing algorithm

Connects to https://simplemap.safecast.org/ogc
loads the "sensors" collection, adds coordinates + doserate_uSvh,
and applies one of the two provided styles (default = style 1).
"""

from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterBoolean,
    QgsFeature,
    QgsField,
    QgsFields,
    QgsGeometry,
    QgsPointXY,
    QgsWkbTypes,
    QgsCoordinateReferenceSystem,
    QgsFeatureSink,
    QgsVectorLayer,
    QgsMapLayerStyle,
    QgsProcessingLayerPostProcessorInterface,
    QgsNetworkAccessManager,
    QgsApplication,
)
from qgis.PyQt.QtNetwork import QNetworkRequest
from qgis.PyQt.QtCore import QUrl, QEventLoop
import json
import os


class SafecastFixedSensorsLoader(QgsProcessingAlgorithm):

    OUTPUT = "OUTPUT"
    STYLE = "STYLE"
    LOAD_ON_COMPLETION = "LOAD_ON_COMPLETION"

    # Full QML content of the two styles (embedded for portability)
    STYLE_1_QML = r'''<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis labelsEnabled="0" simplifyLocal="1" maxScale="0" minScale="0" hasScaleBasedVisibilityFlag="0" simplifyDrawingTol="1" styleCategories="AllStyleCategories" simplifyAlgorithm="0" symbologyReferenceScale="-1" readOnly="0" simplifyMaxScale="1" version="3.44.11-Solothurn" simplifyDrawingHints="0" autoRefreshMode="Disabled" autoRefreshTime="0">
  <flags>
    <Identifiable>1</Identifiable>
    <Removable>1</Removable>
    <Searchable>1</Searchable>
    <Private>0</Private>
  </flags>
  <temporal enabled="0" mode="0" durationUnit="min" endField="" startExpression="" startField="" fixedDuration="0" limitMode="0" endExpression="" durationField="fid" accumulate="0">
    <fixedRange>
      <start></start>
      <end></end>
    </fixedRange>
  </temporal>
  <elevation extrusionEnabled="0" zoffset="0" extrusion="0" symbology="Line" zscale="1" type="IndividualFeatures" showMarkerSymbolInSurfacePlots="0" customToleranceEnabled="0" clamping="Terrain" binding="Centroid" respectLayerSymbol="1">
    <data-defined-properties>
      <Option type="Map">
        <Option name="name" value="" type="QString"/>
        <Option name="properties"/>
        <Option name="type" value="collection" type="QString"/>
      </Option>
    </data-defined-properties>
    <profileLineSymbol>
      <symbol is_animated="0" frame_rate="10" name="" force_rhr="0" alpha="1" clip_to_extent="1" type="line">
        <data_defined_properties>
          <Option type="Map">
            <Option name="name" value="" type="QString"/>
            <Option name="properties"/>
            <Option name="type" value="collection" type="QString"/>
          </Option>
        </data_defined_properties>
        <layer enabled="1" class="SimpleLine" id="{0fa3661f-5914-47ee-92da-b9287ff153f1}" locked="0" pass="0">
          <Option type="Map">
            <Option name="align_dash_pattern" value="0" type="QString"/>
            <Option name="capstyle" value="square" type="QString"/>
            <Option name="customdash" value="5;2" type="QString"/>
            <Option name="customdash_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="customdash_unit" value="MM" type="QString"/>
            <Option name="dash_pattern_offset" value="0" type="QString"/>
            <Option name="dash_pattern_offset_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="dash_pattern_offset_unit" value="MM" type="QString"/>
            <Option name="draw_inside_polygon" value="0" type="QString"/>
            <Option name="joinstyle" value="bevel" type="QString"/>
            <Option name="line_color" value="255,158,23,255,rgb:1,0.6196078,0.0901961,1" type="QString"/>
            <Option name="line_style" value="solid" type="QString"/>
            <Option name="line_width" value="0.6" type="QString"/>
            <Option name="line_width_unit" value="MM" type="QString"/>
            <Option name="offset" value="0" type="QString"/>
            <Option name="offset_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="offset_unit" value="MM" type="QString"/>
            <Option name="ring_filter" value="0" type="QString"/>
            <Option name="trim_distance_end" value="0" type="QString"/>
            <Option name="trim_distance_end_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="trim_distance_end_unit" value="MM" type="QString"/>
            <Option name="trim_distance_start" value="0" type="QString"/>
            <Option name="trim_distance_start_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="trim_distance_start_unit" value="MM" type="QString"/>
            <Option name="tweak_dash_pattern_on_corners" value="0" type="QString"/>
            <Option name="use_custom_dash" value="0" type="QString"/>
            <Option name="width_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" value="" type="QString"/>
              <Option name="properties"/>
              <Option name="type" value="collection" type="QString"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
    </profileLineSymbol>
    <profileFillSymbol>
      <symbol is_animated="0" frame_rate="10" name="" force_rhr="0" alpha="1" clip_to_extent="1" type="fill">
        <data_defined_properties>
          <Option type="Map">
            <Option name="name" value="" type="QString"/>
            <Option name="properties"/>
            <Option name="type" value="collection" type="QString"/>
          </Option>
        </data_defined_properties>
        <layer enabled="1" class="SimpleFill" id="{b5d90d08-15bf-408b-9c99-c2a9b396910c}" locked="0" pass="0">
          <Option type="Map">
            <Option name="border_width_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="color" value="255,158,23,255,rgb:1,0.6196078,0.0901961,1" type="QString"/>
            <Option name="joinstyle" value="bevel" type="QString"/>
            <Option name="offset" value="0,0" type="QString"/>
            <Option name="offset_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="offset_unit" value="MM" type="QString"/>
            <Option name="outline_color" value="182,113,16,255,rgb:0.7142748,0.4425269,0.0644236,1" type="QString"/>
            <Option name="outline_style" value="solid" type="QString"/>
            <Option name="outline_width" value="0.2" type="QString"/>
            <Option name="outline_width_unit" value="MM" type="QString"/>
            <Option name="style" value="solid" type="QString"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" value="" type="QString"/>
              <Option name="properties"/>
              <Option name="type" value="collection" type="QString"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
    </profileFillSymbol>
    <profileMarkerSymbol>
      <symbol is_animated="0" frame_rate="10" name="" force_rhr="0" alpha="1" clip_to_extent="1" type="marker">
        <data_defined_properties>
          <Option type="Map">
            <Option name="name" value="" type="QString"/>
            <Option name="properties"/>
            <Option name="type" value="collection" type="QString"/>
          </Option>
        </data_defined_properties>
        <layer enabled="1" class="SimpleMarker" id="{a52ef2f1-d34f-431e-8a3f-23a054ff9d80}" locked="0" pass="0">
          <Option type="Map">
            <Option name="angle" value="0" type="QString"/>
            <Option name="cap_style" value="square" type="QString"/>
            <Option name="color" value="255,158,23,255,rgb:1,0.6196078,0.0901961,1" type="QString"/>
            <Option name="horizontal_anchor_point" value="1" type="QString"/>
            <Option name="joinstyle" value="bevel" type="QString"/>
            <Option name="name" value="diamond" type="QString"/>
            <Option name="offset" value="0,0" type="QString"/>
            <Option name="offset_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="offset_unit" value="MM" type="QString"/>
            <Option name="outline_color" value="182,113,16,255,rgb:0.7142748,0.4425269,0.0644236,1" type="QString"/>
            <Option name="outline_style" value="solid" type="QString"/>
            <Option name="outline_width" value="0.2" type="QString"/>
            <Option name="outline_width_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="outline_width_unit" value="MM" type="QString"/>
            <Option name="scale_method" value="diameter" type="QString"/>
            <Option name="size" value="3" type="QString"/>
            <Option name="size_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="size_unit" value="MM" type="QString"/>
            <Option name="vertical_anchor_point" value="1" type="QString"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" value="" type="QString"/>
              <Option name="properties"/>
              <Option name="type" value="collection" type="QString"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
    </profileMarkerSymbol>
  </elevation>
  <renderer-v2 symbollevels="0" type="RuleRenderer" referencescale="-1" forceraster="0" enableorderby="0">
    <rules key="{90de6fa9-c2f0-40ab-bc08-8b75c64f2b96}">
      <rule symbol="0" key="{2a61f9c6-75a8-43e5-88de-80abe01dbd27}" label="&lt; 0.05" filter="&quot;doserate_uSvh&quot; >= 0 AND &quot;doserate_uSvh&quot; &lt;= 0.05"/>
      <rule symbol="1" key="{4fd20a5e-af65-4b40-9266-44cd36d0cf96}" label="0.05 - 0.10" filter="&quot;doserate_uSvh&quot; > 0.05 AND &quot;doserate_uSvh&quot; &lt;= 0.10"/>
      <rule symbol="2" key="{7e82c68f-563c-4de5-bfb0-02eb0461947f}" label="0.10 - 0.20" filter="&quot;doserate_uSvh&quot; > 0.10 AND &quot;doserate_uSvh&quot; &lt;= 0.20"/>
      <rule symbol="3" key="{3d72dcb6-32ec-409b-87cb-0980c00b954d}" label="0.20 - 0.30" filter="&quot;doserate_uSvh&quot; > 0.20 AND &quot;doserate_uSvh&quot; &lt;= 0.30"/>
      <rule symbol="4" key="{1dd6f564-ce3a-4512-9455-9d40e102453b}" label="0.30 - 0.80" filter="&quot;doserate_uSvh&quot; > 0.30 AND &quot;doserate_uSvh&quot; &lt;= 0.80"/>
      <rule symbol="5" key="{ad181f59-3bad-46dd-8fb8-258a1597a1a5}" label="0.8 - 1" filter="&quot;doserate_uSvh&quot; > 0.80 AND &quot;doserate_uSvh&quot; &lt;= 1.00"/>
      <rule symbol="6" key="{fd53d998-42ad-4569-9fd2-340d0b16e350}" label="1 - 5" filter="&quot;doserate_uSvh&quot; > 1.00 AND &quot;doserate_uSvh&quot; &lt;= 5.00"/>
      <rule symbol="7" key="{7d615f20-de45-48eb-b149-70f06d59a805}" label="5 - 10" filter="&quot;doserate_uSvh&quot; > 5.00 AND &quot;doserate_uSvh&quot; &lt;= 10.0"/>
      <rule symbol="8" key="{ef32ef44-2ed7-48df-ad52-8ba0197ee386}" label="10 - 70" filter="&quot;doserate_uSvh&quot; > 10.0 AND &quot;doserate_uSvh&quot; &lt;= 70.0"/>
      <rule symbol="9" key="{9fb908d7-f47a-4128-8c75-59c5a0336603}" label="> 70" filter="ELSE"/>
    </rules>
    <symbols>
      <symbol is_animated="0" frame_rate="10" name="0" force_rhr="0" alpha="1" clip_to_extent="1" type="marker">
        <data_defined_properties>
          <Option type="Map">
            <Option name="name" value="" type="QString"/>
            <Option name="properties"/>
            <Option name="type" value="collection" type="QString"/>
          </Option>
        </data_defined_properties>
        <layer enabled="1" class="SimpleMarker" id="{73e3a1c4-0f2e-4a0b-b319-189a28b3dfd6}" locked="0" pass="0">
          <Option type="Map">
            <Option name="angle" value="0" type="QString"/>
            <Option name="cap_style" value="square" type="QString"/>
            <Option name="color" value="0,0,0,255,rgb:0,0,0,1" type="QString"/>
            <Option name="horizontal_anchor_point" value="1" type="QString"/>
            <Option name="joinstyle" value="bevel" type="QString"/>
            <Option name="name" value="triangle" type="QString"/>
            <Option name="offset" value="0,0" type="QString"/>
            <Option name="offset_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="offset_unit" value="MM" type="QString"/>
            <Option name="outline_color" value="0,0,0,0,rgb:0,0,0,0" type="QString"/>
            <Option name="outline_style" value="solid" type="QString"/>
            <Option name="outline_width" value="0" type="QString"/>
            <Option name="outline_width_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="outline_width_unit" value="MM" type="QString"/>
            <Option name="scale_method" value="diameter" type="QString"/>
            <Option name="size" value="3" type="QString"/>
            <Option name="size_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="size_unit" value="MM" type="QString"/>
            <Option name="vertical_anchor_point" value="1" type="QString"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" value="" type="QString"/>
              <Option name="properties"/>
              <Option name="type" value="collection" type="QString"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol is_animated="0" frame_rate="10" name="1" force_rhr="0" alpha="1" clip_to_extent="1" type="marker">
        <data_defined_properties>
          <Option type="Map">
            <Option name="name" value="" type="QString"/>
            <Option name="properties"/>
            <Option name="type" value="collection" type="QString"/>
          </Option>
        </data_defined_properties>
        <layer enabled="1" class="SimpleMarker" id="{916d5101-8c16-48bf-8825-c1e32bf7cc95}" locked="0" pass="0">
          <Option type="Map">
            <Option name="angle" value="0" type="QString"/>
            <Option name="cap_style" value="square" type="QString"/>
            <Option name="color" value="0,0,157,255,rgb:0,0,0.6156863,1" type="QString"/>
            <Option name="horizontal_anchor_point" value="1" type="QString"/>
            <Option name="joinstyle" value="bevel" type="QString"/>
            <Option name="name" value="triangle" type="QString"/>
            <Option name="offset" value="0,0" type="QString"/>
            <Option name="offset_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="offset_unit" value="MM" type="QString"/>
            <Option name="outline_color" value="0,0,0,255,rgb:0,0,0,1" type="QString"/>
            <Option name="outline_style" value="solid" type="QString"/>
            <Option name="outline_width" value="0" type="QString"/>
            <Option name="outline_width_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="outline_width_unit" value="MM" type="QString"/>
            <Option name="scale_method" value="diameter" type="QString"/>
            <Option name="size" value="3" type="QString"/>
            <Option name="size_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="size_unit" value="MM" type="QString"/>
            <Option name="vertical_anchor_point" value="1" type="QString"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" value="" type="QString"/>
              <Option name="properties"/>
              <Option name="type" value="collection" type="QString"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol is_animated="0" frame_rate="10" name="2" force_rhr="0" alpha="1" clip_to_extent="1" type="marker">
        <data_defined_properties>
          <Option type="Map">
            <Option name="name" value="" type="QString"/>
            <Option name="properties"/>
            <Option name="type" value="collection" type="QString"/>
          </Option>
        </data_defined_properties>
        <layer enabled="1" class="SimpleMarker" id="{7135fa58-83b0-45d0-996c-6e9dd94d7a69}" locked="0" pass="0">
          <Option type="Map">
            <Option name="angle" value="0" type="QString"/>
            <Option name="cap_style" value="square" type="QString"/>
            <Option name="color" value="0,59,255,255,rgb:0,0.2313725,1,1" type="QString"/>
            <Option name="horizontal_anchor_point" value="1" type="QString"/>
            <Option name="joinstyle" value="bevel" type="QString"/>
            <Option name="name" value="triangle" type="QString"/>
            <Option name="offset" value="0,0" type="QString"/>
            <Option name="offset_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="offset_unit" value="MM" type="QString"/>
            <Option name="outline_color" value="0,0,0,255,rgb:0,0,0,1" type="QString"/>
            <Option name="outline_style" value="solid" type="QString"/>
            <Option name="outline_width" value="0" type="QString"/>
            <Option name="outline_width_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="outline_width_unit" value="MM" type="QString"/>
            <Option name="scale_method" value="diameter" type="QString"/>
            <Option name="size" value="3" type="QString"/>
            <Option name="size_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="size_unit" value="MM" type="QString"/>
            <Option name="vertical_anchor_point" value="1" type="QString"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" value="" type="QString"/>
              <Option name="properties"/>
              <Option name="type" value="collection" type="QString"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol is_animated="0" frame_rate="10" name="3" force_rhr="0" alpha="1" clip_to_extent="1" type="marker">
        <data_defined_properties>
          <Option type="Map">
            <Option name="name" value="" type="QString"/>
            <Option name="properties"/>
            <Option name="type" value="collection" type="QString"/>
          </Option>
        </data_defined_properties>
        <layer enabled="1" class="SimpleMarker" id="{ef8b1444-130c-4f30-9542-2687f4669f00}" locked="0" pass="0">
          <Option type="Map">
            <Option name="angle" value="0" type="QString"/>
            <Option name="cap_style" value="square" type="QString"/>
            <Option name="color" value="0,217,255,255,rgb:0,0.8509804,1,1" type="QString"/>
            <Option name="horizontal_anchor_point" value="1" type="QString"/>
            <Option name="joinstyle" value="bevel" type="QString"/>
            <Option name="name" value="triangle" type="QString"/>
            <Option name="offset" value="0,0" type="QString"/>
            <Option name="offset_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="offset_unit" value="MM" type="QString"/>
            <Option name="outline_color" value="0,0,0,255,rgb:0,0,0,1" type="QString"/>
            <Option name="outline_style" value="solid" type="QString"/>
            <Option name="outline_width" value="0" type="QString"/>
            <Option name="outline_width_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="outline_width_unit" value="MM" type="QString"/>
            <Option name="scale_method" value="diameter" type="QString"/>
            <Option name="size" value="3" type="QString"/>
            <Option name="size_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="size_unit" value="MM" type="QString"/>
            <Option name="vertical_anchor_point" value="1" type="QString"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" value="" type="QString"/>
              <Option name="properties"/>
              <Option name="type" value="collection" type="QString"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol is_animated="0" frame_rate="10" name="4" force_rhr="0" alpha="1" clip_to_extent="1" type="marker">
        <data_defined_properties>
          <Option type="Map">
            <Option name="name" value="" type="QString"/>
            <Option name="properties"/>
            <Option name="type" value="collection" type="QString"/>
          </Option>
        </data_defined_properties>
        <layer enabled="1" class="SimpleMarker" id="{c89ec810-d620-4e36-afd1-d555d6209439}" locked="0" pass="0">
          <Option type="Map">
            <Option name="angle" value="0" type="QString"/>
            <Option name="cap_style" value="square" type="QString"/>
            <Option name="color" value="119,135,255,255,rgb:0.4666667,0.5294118,1,1" type="QString"/>
            <Option name="horizontal_anchor_point" value="1" type="QString"/>
            <Option name="joinstyle" value="bevel" type="QString"/>
            <Option name="name" value="triangle" type="QString"/>
            <Option name="offset" value="0,0" type="QString"/>
            <Option name="offset_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="offset_unit" value="MM" type="QString"/>
            <Option name="outline_color" value="0,0,0,255,rgb:0,0,0,1" type="QString"/>
            <Option name="outline_style" value="solid" type="QString"/>
            <Option name="outline_width" value="0" type="QString"/>
            <Option name="outline_width_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="outline_width_unit" value="MM" type="QString"/>
            <Option name="scale_method" value="diameter" type="QString"/>
            <Option name="size" value="3" type="QString"/>
            <Option name="size_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="size_unit" value="MM" type="QString"/>
            <Option name="vertical_anchor_point" value="1" type="QString"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" value="" type="QString"/>
              <Option name="properties"/>
              <Option name="type" value="collection" type="QString"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol is_animated="0" frame_rate="10" name="5" force_rhr="0" alpha="1" clip_to_extent="1" type="marker">
        <data_defined_properties>
          <Option type="Map">
            <Option name="name" value="" type="QString"/>
            <Option name="properties"/>
            <Option name="type" value="collection" type="QString"/>
          </Option>
        </data_defined_properties>
        <layer enabled="1" class="SimpleMarker" id="{2ec36012-9308-46a4-b1e4-2c21e11c0b6d}" locked="0" pass="0">
          <Option type="Map">
            <Option name="angle" value="0" type="QString"/>
            <Option name="cap_style" value="square" type="QString"/>
            <Option name="color" value="255,0,232,255,rgb:1,0,0.9098039,1" type="QString"/>
            <Option name="horizontal_anchor_point" value="1" type="QString"/>
            <Option name="joinstyle" value="bevel" type="QString"/>
            <Option name="name" value="triangle" type="QString"/>
            <Option name="offset" value="0,0" type="QString"/>
            <Option name="offset_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="offset_unit" value="MM" type="QString"/>
            <Option name="outline_color" value="0,0,0,255,rgb:0,0,0,1" type="QString"/>
            <Option name="outline_style" value="solid" type="QString"/>
            <Option name="outline_width" value="0" type="QString"/>
            <Option name="outline_width_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="outline_width_unit" value="MM" type="QString"/>
            <Option name="scale_method" value="diameter" type="QString"/>
            <Option name="size" value="3" type="QString"/>
            <Option name="size_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="size_unit" value="MM" type="QString"/>
            <Option name="vertical_anchor_point" value="1" type="QString"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" value="" type="QString"/>
              <Option name="properties"/>
              <Option name="type" value="collection" type="QString"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol is_animated="0" frame_rate="10" name="6" force_rhr="0" alpha="1" clip_to_extent="1" type="marker">
        <data_defined_properties>
          <Option type="Map">
            <Option name="name" value="" type="QString"/>
            <Option name="properties"/>
            <Option name="type" value="collection" type="QString"/>
          </Option>
        </data_defined_properties>
        <layer enabled="1" class="SimpleMarker" id="{039ad29e-a1c7-4ed7-8327-ba0f95d917bd}" locked="0" pass="0">
          <Option type="Map">
            <Option name="angle" value="0" type="QString"/>
            <Option name="cap_style" value="square" type="QString"/>
            <Option name="color" value="255,0,75,255,rgb:1,0,0.2941176,1" type="QString"/>
            <Option name="horizontal_anchor_point" value="1" type="QString"/>
            <Option name="joinstyle" value="bevel" type="QString"/>
            <Option name="name" value="triangle" type="QString"/>
            <Option name="offset" value="0,0" type="QString"/>
            <Option name="offset_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="offset_unit" value="MM" type="QString"/>
            <Option name="outline_color" value="0,0,0,255,rgb:0,0,0,1" type="QString"/>
            <Option name="outline_style" value="solid" type="QString"/>
            <Option name="outline_width" value="0" type="QString"/>
            <Option name="outline_width_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="outline_width_unit" value="MM" type="QString"/>
            <Option name="scale_method" value="diameter" type="QString"/>
            <Option name="size" value="3" type="QString"/>
            <Option name="size_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="size_unit" value="MM" type="QString"/>
            <Option name="vertical_anchor_point" value="1" type="QString"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" value="" type="QString"/>
              <Option name="properties"/>
              <Option name="type" value="collection" type="QString"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol is_animated="0" frame_rate="10" name="7" force_rhr="0" alpha="1" clip_to_extent="1" type="marker">
        <data_defined_properties>
          <Option type="Map">
            <Option name="name" value="" type="QString"/>
            <Option name="properties"/>
            <Option name="type" value="collection" type="QString"/>
          </Option>
        </data_defined_properties>
        <layer enabled="1" class="SimpleMarker" id="{94777d27-bce0-415b-8825-4dcf381e9d47}" locked="0" pass="0">
          <Option type="Map">
            <Option name="angle" value="0" type="QString"/>
            <Option name="cap_style" value="square" type="QString"/>
            <Option name="color" value="255,184,0,255,rgb:1,0.7215686,0,1" type="QString"/>
            <Option name="horizontal_anchor_point" value="1" type="QString"/>
            <Option name="joinstyle" value="bevel" type="QString"/>
            <Option name="name" value="triangle" type="QString"/>
            <Option name="offset" value="0,0" type="QString"/>
            <Option name="offset_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="offset_unit" value="MM" type="QString"/>
            <Option name="outline_color" value="0,0,0,255,rgb:0,0,0,1" type="QString"/>
            <Option name="outline_style" value="solid" type="QString"/>
            <Option name="outline_width" value="0" type="QString"/>
            <Option name="outline_width_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="outline_width_unit" value="MM" type="QString"/>
            <Option name="scale_method" value="diameter" type="QString"/>
            <Option name="size" value="3" type="QString"/>
            <Option name="size_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="size_unit" value="MM" type="QString"/>
            <Option name="vertical_anchor_point" value="1" type="QString"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" value="" type="QString"/>
              <Option name="properties"/>
              <Option name="type" value="collection" type="QString"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol is_animated="0" frame_rate="10" name="8" force_rhr="0" alpha="1" clip_to_extent="1" type="marker">
        <data_defined_properties>
          <Option type="Map">
            <Option name="name" value="" type="QString"/>
            <Option name="properties"/>
            <Option name="type" value="collection" type="QString"/>
          </Option>
        </data_defined_properties>
        <layer enabled="1" class="SimpleMarker" id="{166ae4c8-332b-4056-a1ce-d7e7b95c5150}" locked="0" pass="0">
          <Option type="Map">
            <Option name="angle" value="0" type="QString"/>
            <Option name="cap_style" value="square" type="QString"/>
            <Option name="color" value="255,255,113,255,rgb:1,1,0.4431373,1" type="QString"/>
            <Option name="horizontal_anchor_point" value="1" type="QString"/>
            <Option name="joinstyle" value="bevel" type="QString"/>
            <Option name="name" value="triangle" type="QString"/>
            <Option name="offset" value="0,0" type="QString"/>
            <Option name="offset_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="offset_unit" value="MM" type="QString"/>
            <Option name="outline_color" value="35,35,35,255,rgb:0.1372549,0.1372549,0.1372549,1" type="QString"/>
            <Option name="outline_style" value="solid" type="QString"/>
            <Option name="outline_width" value="0" type="QString"/>
            <Option name="outline_width_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="outline_width_unit" value="MM" type="QString"/>
            <Option name="scale_method" value="diameter" type="QString"/>
            <Option name="size" value="3" type="QString"/>
            <Option name="size_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="size_unit" value="MM" type="QString"/>
            <Option name="vertical_anchor_point" value="1" type="QString"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" value="" type="QString"/>
              <Option name="properties"/>
              <Option name="type" value="collection" type="QString"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol is_animated="0" frame_rate="10" name="9" force_rhr="0" alpha="1" clip_to_extent="1" type="marker">
        <data_defined_properties>
          <Option type="Map">
            <Option name="name" value="" type="QString"/>
            <Option name="properties"/>
            <Option name="type" value="collection" type="QString"/>
          </Option>
        </data_defined_properties>
        <layer enabled="1" class="SimpleMarker" id="{01587915-3a14-4dab-8eb2-925bbc9736e9}" locked="0" pass="0">
          <Option type="Map">
            <Option name="angle" value="0" type="QString"/>
            <Option name="cap_style" value="square" type="QString"/>
            <Option name="color" value="255,255,255,255,rgb:1,1,1,1" type="QString"/>
            <Option name="horizontal_anchor_point" value="1" type="QString"/>
            <Option name="joinstyle" value="bevel" type="QString"/>
            <Option name="name" value="triangle" type="QString"/>
            <Option name="offset" value="0,0" type="QString"/>
            <Option name="offset_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="offset_unit" value="MM" type="QString"/>
            <Option name="outline_color" value="35,35,35,255,rgb:0.1372549,0.1372549,0.1372549,1" type="QString"/>
            <Option name="outline_style" value="solid" type="QString"/>
            <Option name="outline_width" value="0" type="QString"/>
            <Option name="outline_width_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="outline_width_unit" value="MM" type="QString"/>
            <Option name="scale_method" value="diameter" type="QString"/>
            <Option name="size" value="3" type="QString"/>
            <Option name="size_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="size_unit" value="MM" type="QString"/>
            <Option name="vertical_anchor_point" value="1" type="QString"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" value="" type="QString"/>
              <Option name="properties"/>
              <Option name="type" value="collection" type="QString"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
    </symbols>
    <data-defined-properties>
      <Option type="Map">
        <Option name="name" value="" type="QString"/>
        <Option name="properties"/>
        <Option name="type" value="collection" type="QString"/>
      </Option>
    </data-defined-properties>
  </renderer-v2>
  <selection mode="Default">
    <selectionColor invalid="1"/>
    <selectionSymbol>
      <symbol is_animated="0" frame_rate="10" name="" force_rhr="0" alpha="1" clip_to_extent="1" type="marker">
        <data_defined_properties>
          <Option type="Map">
            <Option name="name" value="" type="QString"/>
            <Option name="properties"/>
            <Option name="type" value="collection" type="QString"/>
          </Option>
        </data_defined_properties>
        <layer enabled="1" class="SimpleMarker" id="{d5bafbcc-0c88-4f75-865d-c443af3f9d6d}" locked="0" pass="0">
          <Option type="Map">
            <Option name="angle" value="0" type="QString"/>
            <Option name="cap_style" value="square" type="QString"/>
            <Option name="color" value="255,0,0,255,rgb:1,0,0,1" type="QString"/>
            <Option name="horizontal_anchor_point" value="1" type="QString"/>
            <Option name="joinstyle" value="bevel" type="QString"/>
            <Option name="name" value="circle" type="QString"/>
            <Option name="offset" value="0,0" type="QString"/>
            <Option name="offset_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="offset_unit" value="MM" type="QString"/>
            <Option name="outline_color" value="35,35,35,255,rgb:0.1372549,0.1372549,0.1372549,1" type="QString"/>
            <Option name="outline_style" value="solid" type="QString"/>
            <Option name="outline_width" value="0" type="QString"/>
            <Option name="outline_width_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="outline_width_unit" value="MM" type="QString"/>
            <Option name="scale_method" value="diameter" type="QString"/>
            <Option name="size" value="2" type="QString"/>
            <Option name="size_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="size_unit" value="MM" type="QString"/>
            <Option name="vertical_anchor_point" value="1" type="QString"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" value="" type="QString"/>
              <Option name="properties"/>
              <Option name="type" value="collection" type="QString"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
    </selectionSymbol>
  </selection>
  <customproperties>
    <Option type="Map">
      <Option name="dualview/previewExpressions" type="List">
        <Option value="COALESCE( &quot;device_name&quot;, '&lt;NULL>' )" type="QString"/>
      </Option>
      <Option name="embeddedWidgets/count" value="0" type="int"/>
      <Option name="variableNames"/>
      <Option name="variableValues"/>
    </Option>
  </customproperties>
  <blendMode>0</blendMode>
  <featureBlendMode>0</featureBlendMode>
  <layerOpacity>1</layerOpacity>
  <geometryOptions removeDuplicateNodes="0" geometryPrecision="0">
    <activeChecks/>
    <checkConfiguration/>
  </geometryOptions>
  <legend type="default-vector" showLabelLegend="0"/>
  <referencedLayers/>
  <referencingLayers/>
  <fieldConfiguration>
    <field name="fid" configurationFlags="NoFlag">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="id" configurationFlags="NoFlag">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="device_id" configurationFlags="NoFlag">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="device_name" configurationFlags="NoFlag">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="last_reading_at" configurationFlags="NoFlag">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="type" configurationFlags="NoFlag">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="unit" configurationFlags="NoFlag">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="value" configurationFlags="NoFlag">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="unit_type" configurationFlags="NoFlag">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="CPM" configurationFlags="NoFlag">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="doserate_uSvh" configurationFlags="NoFlag">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="xcoord" configurationFlags="NoFlag">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="ycoord" configurationFlags="NoFlag">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
  </fieldConfiguration>
  <aliases>
    <alias name="" index="0" field="fid"/>
    <alias name="" index="1" field="id"/>
    <alias name="" index="2" field="device_id"/>
    <alias name="" index="3" field="device_name"/>
    <alias name="" index="4" field="last_reading_at"/>
    <alias name="" index="5" field="type"/>
    <alias name="" index="6" field="unit"/>
    <alias name="" index="7" field="value"/>
    <alias name="" index="8" field="unit_type"/>
    <alias name="" index="9" field="CPM"/>
    <alias name="" index="10" field="doserate_uSvh"/>
    <alias name="" index="11" field="xcoord"/>
    <alias name="" index="12" field="ycoord"/>
  </aliases>
  <defaults>
    <default applyOnUpdate="0" field="fid" expression=""/>
    <default applyOnUpdate="0" field="id" expression=""/>
    <default applyOnUpdate="0" field="device_id" expression=""/>
    <default applyOnUpdate="0" field="device_name" expression=""/>
    <default applyOnUpdate="0" field="last_reading_at" expression=""/>
    <default applyOnUpdate="0" field="type" expression=""/>
    <default applyOnUpdate="0" field="unit" expression=""/>
    <default applyOnUpdate="0" field="value" expression=""/>
    <default applyOnUpdate="0" field="unit_type" expression=""/>
    <default applyOnUpdate="0" field="CPM" expression=""/>
    <default applyOnUpdate="0" field="doserate_uSvh" expression=""/>
    <default applyOnUpdate="0" field="xcoord" expression=""/>
    <default applyOnUpdate="0" field="ycoord" expression=""/>
  </defaults>
  <constraints>
    <constraint unique_strength="1" constraints="3" exp_strength="0" field="fid" notnull_strength="1"/>
    <constraint unique_strength="0" constraints="0" exp_strength="0" field="id" notnull_strength="0"/>
    <constraint unique_strength="0" constraints="0" exp_strength="0" field="device_id" notnull_strength="0"/>
    <constraint unique_strength="0" constraints="0" exp_strength="0" field="device_name" notnull_strength="0"/>
    <constraint unique_strength="0" constraints="0" exp_strength="0" field="last_reading_at" notnull_strength="0"/>
    <constraint unique_strength="0" constraints="0" exp_strength="0" field="type" notnull_strength="0"/>
    <constraint unique_strength="0" constraints="0" exp_strength="0" field="unit" notnull_strength="0"/>
    <constraint unique_strength="0" constraints="0" exp_strength="0" field="value" notnull_strength="0"/>
    <constraint unique_strength="0" constraints="0" exp_strength="0" field="unit_type" notnull_strength="0"/>
    <constraint unique_strength="0" constraints="0" exp_strength="0" field="CPM" notnull_strength="0"/>
    <constraint unique_strength="0" constraints="0" exp_strength="0" field="doserate_uSvh" notnull_strength="0"/>
    <constraint unique_strength="0" constraints="0" exp_strength="0" field="xcoord" notnull_strength="0"/>
    <constraint unique_strength="0" constraints="0" exp_strength="0" field="ycoord" notnull_strength="0"/>
  </constraints>
  <constraintExpressions>
    <constraint field="fid" desc="" exp=""/>
    <constraint field="id" desc="" exp=""/>
    <constraint field="device_id" desc="" exp=""/>
    <constraint field="device_name" desc="" exp=""/>
    <constraint field="last_reading_at" desc="" exp=""/>
    <constraint field="type" desc="" exp=""/>
    <constraint field="unit" desc="" exp=""/>
    <constraint field="value" desc="" exp=""/>
    <constraint field="unit_type" desc="" exp=""/>
    <constraint field="CPM" desc="" exp=""/>
    <constraint field="doserate_uSvh" desc="" exp=""/>
    <constraint field="xcoord" desc="" exp=""/>
    <constraint field="ycoord" desc="" exp=""/>
  </constraintExpressions>
  <expressionfields/>
  <attributeactions>
    <defaultAction value="{00000000-0000-0000-0000-000000000000}" key="Canvas"/>
  </attributeactions>
  <attributetableconfig actionWidgetStyle="dropDown" sortOrder="0" sortExpression="">
    <columns>
      <column name="fid" width="-1" hidden="0" type="field"/>
      <column name="id" width="-1" hidden="0" type="field"/>
      <column name="device_id" width="-1" hidden="0" type="field"/>
      <column name="device_name" width="-1" hidden="0" type="field"/>
      <column name="last_reading_at" width="-1" hidden="0" type="field"/>
      <column name="type" width="-1" hidden="0" type="field"/>
      <column name="unit" width="-1" hidden="0" type="field"/>
      <column name="value" width="-1" hidden="0" type="field"/>
      <column name="unit_type" width="-1" hidden="0" type="field"/>
      <column name="CPM" width="-1" hidden="0" type="field"/>
      <column name="doserate_uSvh" width="-1" hidden="0" type="field"/>
      <column name="xcoord" width="-1" hidden="0" type="field"/>
      <column name="ycoord" width="-1" hidden="0" type="field"/>
      <column width="-1" hidden="1" type="actions"/>
    </columns>
  </attributetableconfig>
  <conditionalstyles>
    <rowstyles/>
    <fieldstyles/>
  </conditionalstyles>
  <storedexpressions/>
  <editform tolerant="1"></editform>
  <editforminit/>
  <editforminitcodesource>0</editforminitcodesource>
  <editforminitfilepath></editforminitfilepath>
  <editforminitcode><![CDATA[# -*- coding: utf-8 -*-
"""
QGIS forms can have a Python function that is called when the form is
opened.

Use this function to add extra logic to your forms.

Enter the name of the function in the "Python Init function"
field.
An example follows:
"""
from qgis.PyQt.QtWidgets import QWidget

def my_form_open(dialog, layer, feature):
    geom = feature.geometry()
    control = dialog.findChild(QWidget, "MyLineEdit")
]]></editforminitcode>
  <featformsuppress>0</featformsuppress>
  <editorlayout>generatedlayout</editorlayout>
  <editable>
    <field name="CPM" editable="1"/>
    <field name="device_id" editable="1"/>
    <field name="device_name" editable="1"/>
    <field name="doserate_uSvh" editable="1"/>
    <field name="fid" editable="1"/>
    <field name="id" editable="1"/>
    <field name="last_reading_at" editable="1"/>
    <field name="type" editable="1"/>
    <field name="unit" editable="1"/>
    <field name="unit_type" editable="1"/>
    <field name="value" editable="1"/>
    <field name="xcoord" editable="1"/>
    <field name="ycoord" editable="1"/>
  </editable>
  <labelOnTop>
    <field labelOnTop="0" name="CPM"/>
    <field labelOnTop="0" name="device_id"/>
    <field labelOnTop="0" name="device_name"/>
    <field labelOnTop="0" name="doserate_uSvh"/>
    <field labelOnTop="0" name="fid"/>
    <field labelOnTop="0" name="id"/>
    <field labelOnTop="0" name="last_reading_at"/>
    <field labelOnTop="0" name="type"/>
    <field labelOnTop="0" name="unit"/>
    <field labelOnTop="0" name="unit_type"/>
    <field labelOnTop="0" name="value"/>
    <field labelOnTop="0" name="xcoord"/>
    <field labelOnTop="0" name="ycoord"/>
  </labelOnTop>
  <reuseLastValue>
    <field name="CPM" reuseLastValue="0"/>
    <field name="device_id" reuseLastValue="0"/>
    <field name="device_name" reuseLastValue="0"/>
    <field name="doserate_uSvh" reuseLastValue="0"/>
    <field name="fid" reuseLastValue="0"/>
    <field name="id" reuseLastValue="0"/>
    <field name="last_reading_at" reuseLastValue="0"/>
    <field name="type" reuseLastValue="0"/>
    <field name="unit" reuseLastValue="0"/>
    <field name="unit_type" reuseLastValue="0"/>
    <field name="value" reuseLastValue="0"/>
    <field name="xcoord" reuseLastValue="0"/>
    <field name="ycoord" reuseLastValue="0"/>
  </reuseLastValue>
  <dataDefinedFieldProperties/>
  <widgets/>
  <previewExpression>COALESCE( "device_name", '&lt;NULL>' )</previewExpression>
  <mapTip enabled="1"></mapTip>
  <layerGeometryType>0</layerGeometryType>
</qgis>'''

    STYLE_2_QML = r'''<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis labelsEnabled="0" simplifyLocal="1" maxScale="0" minScale="0" hasScaleBasedVisibilityFlag="0" simplifyDrawingTol="1" styleCategories="AllStyleCategories" simplifyAlgorithm="0" symbologyReferenceScale="-1" readOnly="0" simplifyMaxScale="1" version="3.44.11-Solothurn" simplifyDrawingHints="0" autoRefreshMode="Disabled" autoRefreshTime="0">
  <flags>
    <Identifiable>1</Identifiable>
    <Removable>1</Removable>
    <Searchable>1</Searchable>
    <Private>0</Private>
  </flags>
  <temporal enabled="0" mode="0" durationUnit="min" endField="" startExpression="" startField="" fixedDuration="0" limitMode="0" endExpression="" durationField="fid" accumulate="0">
    <fixedRange>
      <start></start>
      <end></end>
    </fixedRange>
  </temporal>
  <elevation extrusionEnabled="0" zoffset="0" extrusion="0" symbology="Line" zscale="1" type="IndividualFeatures" showMarkerSymbolInSurfacePlots="0" customToleranceEnabled="0" clamping="Terrain" binding="Centroid" respectLayerSymbol="1">
    <data-defined-properties>
      <Option type="Map">
        <Option name="name" value="" type="QString"/>
        <Option name="properties"/>
        <Option name="type" value="collection" type="QString"/>
      </Option>
    </data-defined-properties>
    <profileLineSymbol>
      <symbol is_animated="0" frame_rate="10" name="" force_rhr="0" alpha="1" clip_to_extent="1" type="line">
        <data_defined_properties>
          <Option type="Map">
            <Option name="name" value="" type="QString"/>
            <Option name="properties"/>
            <Option name="type" value="collection" type="QString"/>
          </Option>
        </data_defined_properties>
        <layer enabled="1" class="SimpleLine" id="{0fa3661f-5914-47ee-92da-b9287ff153f1}" locked="0" pass="0">
          <Option type="Map">
            <Option name="align_dash_pattern" value="0" type="QString"/>
            <Option name="capstyle" value="square" type="QString"/>
            <Option name="customdash" value="5;2" type="QString"/>
            <Option name="customdash_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="customdash_unit" value="MM" type="QString"/>
            <Option name="dash_pattern_offset" value="0" type="QString"/>
            <Option name="dash_pattern_offset_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="dash_pattern_offset_unit" value="MM" type="QString"/>
            <Option name="draw_inside_polygon" value="0" type="QString"/>
            <Option name="joinstyle" value="bevel" type="QString"/>
            <Option name="line_color" value="255,158,23,255,rgb:1,0.6196078,0.0901961,1" type="QString"/>
            <Option name="line_style" value="solid" type="QString"/>
            <Option name="line_width" value="0.6" type="QString"/>
            <Option name="line_width_unit" value="MM" type="QString"/>
            <Option name="offset" value="0" type="QString"/>
            <Option name="offset_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="offset_unit" value="MM" type="QString"/>
            <Option name="ring_filter" value="0" type="QString"/>
            <Option name="trim_distance_end" value="0" type="QString"/>
            <Option name="trim_distance_end_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="trim_distance_end_unit" value="MM" type="QString"/>
            <Option name="trim_distance_start" value="0" type="QString"/>
            <Option name="trim_distance_start_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="trim_distance_start_unit" value="MM" type="QString"/>
            <Option name="tweak_dash_pattern_on_corners" value="0" type="QString"/>
            <Option name="use_custom_dash" value="0" type="QString"/>
            <Option name="width_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" value="" type="QString"/>
              <Option name="properties"/>
              <Option name="type" value="collection" type="QString"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
    </profileLineSymbol>
    <profileFillSymbol>
      <symbol is_animated="0" frame_rate="10" name="" force_rhr="0" alpha="1" clip_to_extent="1" type="fill">
        <data_defined_properties>
          <Option type="Map">
            <Option name="name" value="" type="QString"/>
            <Option name="properties"/>
            <Option name="type" value="collection" type="QString"/>
          </Option>
        </data_defined_properties>
        <layer enabled="1" class="SimpleFill" id="{b5d90d08-15bf-408b-9c99-c2a9b396910c}" locked="0" pass="0">
          <Option type="Map">
            <Option name="border_width_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="color" value="255,158,23,255,rgb:1,0.6196078,0.0901961,1" type="QString"/>
            <Option name="joinstyle" value="bevel" type="QString"/>
            <Option name="offset" value="0,0" type="QString"/>
            <Option name="offset_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="offset_unit" value="MM" type="QString"/>
            <Option name="outline_color" value="182,113,16,255,rgb:0.7142748,0.4425269,0.0644236,1" type="QString"/>
            <Option name="outline_style" value="solid" type="QString"/>
            <Option name="outline_width" value="0.2" type="QString"/>
            <Option name="outline_width_unit" value="MM" type="QString"/>
            <Option name="style" value="solid" type="QString"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" value="" type="QString"/>
              <Option name="properties"/>
              <Option name="type" value="collection" type="QString"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
    </profileFillSymbol>
    <profileMarkerSymbol>
      <symbol is_animated="0" frame_rate="10" name="" force_rhr="0" alpha="1" clip_to_extent="1" type="marker">
        <data_defined_properties>
          <Option type="Map">
            <Option name="name" value="" type="QString"/>
            <Option name="properties"/>
            <Option name="type" value="collection" type="QString"/>
          </Option>
        </data_defined_properties>
        <layer enabled="1" class="SimpleMarker" id="{a52ef2f1-d34f-431e-8a3f-23a054ff9d80}" locked="0" pass="0">
          <Option type="Map">
            <Option name="angle" value="0" type="QString"/>
            <Option name="cap_style" value="square" type="QString"/>
            <Option name="color" value="255,158,23,255,rgb:1,0.6196078,0.0901961,1" type="QString"/>
            <Option name="horizontal_anchor_point" value="1" type="QString"/>
            <Option name="joinstyle" value="bevel" type="QString"/>
            <Option name="name" value="diamond" type="QString"/>
            <Option name="offset" value="0,0" type="QString"/>
            <Option name="offset_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="offset_unit" value="MM" type="QString"/>
            <Option name="outline_color" value="182,113,16,255,rgb:0.7142748,0.4425269,0.0644236,1" type="QString"/>
            <Option name="outline_style" value="solid" type="QString"/>
            <Option name="outline_width" value="0.2" type="QString"/>
            <Option name="outline_width_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="outline_width_unit" value="MM" type="QString"/>
            <Option name="scale_method" value="diameter" type="QString"/>
            <Option name="size" value="3" type="QString"/>
            <Option name="size_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="size_unit" value="MM" type="QString"/>
            <Option name="vertical_anchor_point" value="1" type="QString"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" value="" type="QString"/>
              <Option name="properties"/>
              <Option name="type" value="collection" type="QString"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
    </profileMarkerSymbol>
  </elevation>
  <renderer-v2 symbollevels="0" type="RuleRenderer" referencescale="-1" forceraster="0" enableorderby="0">
    <rules key="{74cddd6d-7e4e-4e30-892e-2ec268fc1739}">
      <rule symbol="0" key="{4c3d2b10-dd04-42e7-a88e-828a4a36822e}" label="&lt; 0.08" filter="&quot;doserate_uSvh&quot; >= 0.000000 AND &quot;doserate_uSvh&quot; &lt;= 0.080000"/>
      <rule symbol="1" key="{2e759373-c1ba-4eb6-acb9-e4b0a41b1872}" label="0.08 - 0.10" filter="&quot;doserate_uSvh&quot; > 0.080000 AND &quot;doserate_uSvh&quot; &lt;= 0.100000"/>
      <rule symbol="2" key="{eb6c8de6-9c63-44bc-a048-2de690cd4c63}" label="0.10 - 0.15" filter="&quot;doserate_uSvh&quot; > 0.100000 AND &quot;doserate_uSvh&quot; &lt;= 0.150000"/>
      <rule symbol="3" key="{7c84140d-4c1e-4151-9ca7-e42625afc2f1}" label="0.15 - 0.20" filter="&quot;doserate_uSvh&quot; > 0.150000 AND &quot;doserate_uSvh&quot; &lt;= 0.200000"/>
      <rule symbol="4" key="{4249bf5e-4342-4466-8db5-269a2c11a2f8}" label="0.20 - 0.25" filter="&quot;doserate_uSvh&quot; > 0.200000 AND &quot;doserate_uSvh&quot; &lt;= 0.250000"/>
      <rule symbol="5" key="{cd45c2aa-5b10-4798-9199-7667ea440921}" label="0.25 - 0.30" filter="&quot;doserate_uSvh&quot; > 0.250000 AND &quot;doserate_uSvh&quot; &lt;= 0.300000"/>
      <rule symbol="6" key="{05013511-8eec-459d-8592-934de5264f7e}" label="0.30 - 0.50" filter="&quot;doserate_uSvh&quot; > 0.300000 AND &quot;doserate_uSvh&quot; &lt;= 0.500000"/>
      <rule symbol="7" key="{b2376229-6c89-4795-9694-e5806ebeb888}" label="0.50 - 1.00" filter="&quot;doserate_uSvh&quot; > 0.500000 AND &quot;doserate_uSvh&quot; &lt;= 1.000000"/>
      <rule symbol="8" key="{e467e2fa-4fa7-4ee1-9e61-1b8eb83f3f48}" label="1.00 - 10.00" filter="&quot;doserate_uSvh&quot; > 1.000000 AND &quot;doserate_uSvh&quot; &lt;= 10.000000"/>
      <rule symbol="9" key="{15fe2f3b-a071-4e0a-a4c6-737ad35360aa}" label=">10" filter="ELSE"/>
    </rules>
    <symbols>
      <symbol is_animated="0" frame_rate="10" name="0" force_rhr="0" alpha="1" clip_to_extent="1" type="marker">
        <data_defined_properties>
          <Option type="Map">
            <Option name="name" value="" type="QString"/>
            <Option name="properties"/>
            <Option name="type" value="collection" type="QString"/>
          </Option>
        </data_defined_properties>
        <layer enabled="1" class="SimpleMarker" id="{e2826dcc-73d7-47e2-ae77-527bb657bfa7}" locked="0" pass="0">
          <Option type="Map">
            <Option name="angle" value="0" type="QString"/>
            <Option name="cap_style" value="square" type="QString"/>
            <Option name="color" value="0,0,127,255,rgb:0,0,0.4980392,1" type="QString"/>
            <Option name="horizontal_anchor_point" value="1" type="QString"/>
            <Option name="joinstyle" value="bevel" type="QString"/>
            <Option name="name" value="triangle" type="QString"/>
            <Option name="offset" value="0,0" type="QString"/>
            <Option name="offset_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="offset_unit" value="MM" type="QString"/>
            <Option name="outline_color" value="0,0,0,255,rgb:0,0,0,1" type="QString"/>
            <Option name="outline_style" value="solid" type="QString"/>
            <Option name="outline_width" value="0" type="QString"/>
            <Option name="outline_width_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="outline_width_unit" value="MM" type="QString"/>
            <Option name="scale_method" value="area" type="QString"/>
            <Option name="size" value="3" type="QString"/>
            <Option name="size_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="size_unit" value="MM" type="QString"/>
            <Option name="vertical_anchor_point" value="1" type="QString"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" value="" type="QString"/>
              <Option name="properties"/>
              <Option name="type" value="collection" type="QString"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol is_animated="0" frame_rate="10" name="1" force_rhr="0" alpha="1" clip_to_extent="1" type="marker">
        <data_defined_properties>
          <Option type="Map">
            <Option name="name" value="" type="QString"/>
            <Option name="properties"/>
            <Option name="type" value="collection" type="QString"/>
          </Option>
        </data_defined_properties>
        <layer enabled="1" class="SimpleMarker" id="{ac24ecec-5d34-4741-917b-e654950a9123}" locked="0" pass="0">
          <Option type="Map">
            <Option name="angle" value="0" type="QString"/>
            <Option name="cap_style" value="square" type="QString"/>
            <Option name="color" value="0,85,191,255,rgb:0,0.3333333,0.7490196,1" type="QString"/>
            <Option name="horizontal_anchor_point" value="1" type="QString"/>
            <Option name="joinstyle" value="bevel" type="QString"/>
            <Option name="name" value="triangle" type="QString"/>
            <Option name="offset" value="0,0" type="QString"/>
            <Option name="offset_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="offset_unit" value="MM" type="QString"/>
            <Option name="outline_color" value="0,0,0,255,rgb:0,0,0,1" type="QString"/>
            <Option name="outline_style" value="solid" type="QString"/>
            <Option name="outline_width" value="0" type="QString"/>
            <Option name="outline_width_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="outline_width_unit" value="MM" type="QString"/>
            <Option name="scale_method" value="area" type="QString"/>
            <Option name="size" value="3" type="QString"/>
            <Option name="size_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="size_unit" value="MM" type="QString"/>
            <Option name="vertical_anchor_point" value="1" type="QString"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" value="" type="QString"/>
              <Option name="properties"/>
              <Option name="type" value="collection" type="QString"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol is_animated="0" frame_rate="10" name="2" force_rhr="0" alpha="1" clip_to_extent="1" type="marker">
        <data_defined_properties>
          <Option type="Map">
            <Option name="name" value="" type="QString"/>
            <Option name="properties"/>
            <Option name="type" value="collection" type="QString"/>
          </Option>
        </data_defined_properties>
        <layer enabled="1" class="SimpleMarker" id="{fd95cbf7-e15c-4703-aedd-f80e971896fb}" locked="0" pass="0">
          <Option type="Map">
            <Option name="angle" value="0" type="QString"/>
            <Option name="cap_style" value="square" type="QString"/>
            <Option name="color" value="0,170,255,255,rgb:0,0.6666667,1,1" type="QString"/>
            <Option name="horizontal_anchor_point" value="1" type="QString"/>
            <Option name="joinstyle" value="bevel" type="QString"/>
            <Option name="name" value="triangle" type="QString"/>
            <Option name="offset" value="0,0" type="QString"/>
            <Option name="offset_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="offset_unit" value="MM" type="QString"/>
            <Option name="outline_color" value="0,0,0,255,rgb:0,0,0,1" type="QString"/>
            <Option name="outline_style" value="solid" type="QString"/>
            <Option name="outline_width" value="0" type="QString"/>
            <Option name="outline_width_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="outline_width_unit" value="MM" type="QString"/>
            <Option name="scale_method" value="area" type="QString"/>
            <Option name="size" value="3" type="QString"/>
            <Option name="size_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="size_unit" value="MM" type="QString"/>
            <Option name="vertical_anchor_point" value="1" type="QString"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" value="" type="QString"/>
              <Option name="properties"/>
              <Option name="type" value="collection" type="QString"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol is_animated="0" frame_rate="10" name="3" force_rhr="0" alpha="1" clip_to_extent="1" type="marker">
        <data_defined_properties>
          <Option type="Map">
            <Option name="name" value="" type="QString"/>
            <Option name="properties"/>
            <Option name="type" value="collection" type="QString"/>
          </Option>
        </data_defined_properties>
        <layer enabled="1" class="SimpleMarker" id="{d3117e45-2f95-40f7-96e0-bbf8ca277bfd}" locked="0" pass="0">
          <Option type="Map">
            <Option name="angle" value="0" type="QString"/>
            <Option name="cap_style" value="square" type="QString"/>
            <Option name="color" value="42,212,191,255,rgb:0.1647059,0.8313725,0.7490196,1" type="QString"/>
            <Option name="horizontal_anchor_point" value="1" type="QString"/>
            <Option name="joinstyle" value="bevel" type="QString"/>
            <Option name="name" value="triangle" type="QString"/>
            <Option name="offset" value="0,0" type="QString"/>
            <Option name="offset_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="offset_unit" value="MM" type="QString"/>
            <Option name="outline_color" value="0,0,0,255,rgb:0,0,0,1" type="QString"/>
            <Option name="outline_style" value="solid" type="QString"/>
            <Option name="outline_width" value="0" type="QString"/>
            <Option name="outline_width_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="outline_width_unit" value="MM" type="QString"/>
            <Option name="scale_method" value="area" type="QString"/>
            <Option name="size" value="3" type="QString"/>
            <Option name="size_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="size_unit" value="MM" type="QString"/>
            <Option name="vertical_anchor_point" value="1" type="QString"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" value="" type="QString"/>
              <Option name="properties"/>
              <Option name="type" value="collection" type="QString"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol is_animated="0" frame_rate="10" name="4" force_rhr="0" alpha="1" clip_to_extent="1" type="marker">
        <data_defined_properties>
          <Option type="Map">
            <Option name="name" value="" type="QString"/>
            <Option name="properties"/>
            <Option name="type" value="collection" type="QString"/>
          </Option>
        </data_defined_properties>
        <layer enabled="1" class="SimpleMarker" id="{0398cd1e-46dc-4936-b399-4c34d4155326}" locked="0" pass="0">
          <Option type="Map">
            <Option name="angle" value="0" type="QString"/>
            <Option name="cap_style" value="square" type="QString"/>
            <Option name="color" value="85,255,127,255,rgb:0.3333333,1,0.4980392,1" type="QString"/>
            <Option name="horizontal_anchor_point" value="1" type="QString"/>
            <Option name="joinstyle" value="bevel" type="QString"/>
            <Option name="name" value="triangle" type="QString"/>
            <Option name="offset" value="0,0" type="QString"/>
            <Option name="offset_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="offset_unit" value="MM" type="QString"/>
            <Option name="outline_color" value="0,0,0,255,rgb:0,0,0,1" type="QString"/>
            <Option name="outline_style" value="solid" type="QString"/>
            <Option name="outline_width" value="0" type="QString"/>
            <Option name="outline_width_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="outline_width_unit" value="MM" type="QString"/>
            <Option name="scale_method" value="area" type="QString"/>
            <Option name="size" value="3" type="QString"/>
            <Option name="size_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="size_unit" value="MM" type="QString"/>
            <Option name="vertical_anchor_point" value="1" type="QString"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" value="" type="QString"/>
              <Option name="properties"/>
              <Option name="type" value="collection" type="QString"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol is_animated="0" frame_rate="10" name="5" force_rhr="0" alpha="1" clip_to_extent="1" type="marker">
        <data_defined_properties>
          <Option type="Map">
            <Option name="name" value="" type="QString"/>
            <Option name="properties"/>
            <Option name="type" value="collection" type="QString"/>
          </Option>
        </data_defined_properties>
        <layer enabled="1" class="SimpleMarker" id="{82e01d98-cced-4344-950c-1bd18696ede5}" locked="0" pass="0">
          <Option type="Map">
            <Option name="angle" value="0" type="QString"/>
            <Option name="cap_style" value="square" type="QString"/>
            <Option name="color" value="170,212,63,255,rgb:0.6666667,0.8313725,0.2470588,1" type="QString"/>
            <Option name="horizontal_anchor_point" value="1" type="QString"/>
            <Option name="joinstyle" value="bevel" type="QString"/>
            <Option name="name" value="triangle" type="QString"/>
            <Option name="offset" value="0,0" type="QString"/>
            <Option name="offset_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="offset_unit" value="MM" type="QString"/>
            <Option name="outline_color" value="0,0,0,255,rgb:0,0,0,1" type="QString"/>
            <Option name="outline_style" value="solid" type="QString"/>
            <Option name="outline_width" value="0" type="QString"/>
            <Option name="outline_width_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="outline_width_unit" value="MM" type="QString"/>
            <Option name="scale_method" value="area" type="QString"/>
            <Option name="size" value="3" type="QString"/>
            <Option name="size_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="size_unit" value="MM" type="QString"/>
            <Option name="vertical_anchor_point" value="1" type="QString"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" value="" type="QString"/>
              <Option name="properties"/>
              <Option name="type" value="collection" type="QString"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol is_animated="0" frame_rate="10" name="6" force_rhr="0" alpha="1" clip_to_extent="1" type="marker">
        <data_defined_properties>
          <Option type="Map">
            <Option name="name" value="" type="QString"/>
            <Option name="properties"/>
            <Option name="type" value="collection" type="QString"/>
          </Option>
        </data_defined_properties>
        <layer enabled="1" class="SimpleMarker" id="{1ed327e4-d189-479a-abfc-0f0957fd44ba}" locked="0" pass="0">
          <Option type="Map">
            <Option name="angle" value="0" type="QString"/>
            <Option name="cap_style" value="square" type="QString"/>
            <Option name="color" value="255,170,0,255,rgb:1,0.6666667,0,1" type="QString"/>
            <Option name="horizontal_anchor_point" value="1" type="QString"/>
            <Option name="joinstyle" value="bevel" type="QString"/>
            <Option name="name" value="triangle" type="QString"/>
            <Option name="offset" value="0,0" type="QString"/>
            <Option name="offset_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="offset_unit" value="MM" type="QString"/>
            <Option name="outline_color" value="0,0,0,255,rgb:0,0,0,1" type="QString"/>
            <Option name="outline_style" value="solid" type="QString"/>
            <Option name="outline_width" value="0" type="QString"/>
            <Option name="outline_width_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="outline_width_unit" value="MM" type="QString"/>
            <Option name="scale_method" value="area" type="QString"/>
            <Option name="size" value="3" type="QString"/>
            <Option name="size_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="size_unit" value="MM" type="QString"/>
            <Option name="vertical_anchor_point" value="1" type="QString"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" value="" type="QString"/>
              <Option name="properties"/>
              <Option name="type" value="collection" type="QString"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol is_animated="0" frame_rate="10" name="7" force_rhr="0" alpha="1" clip_to_extent="1" type="marker">
        <data_defined_properties>
          <Option type="Map">
            <Option name="name" value="" type="QString"/>
            <Option name="properties"/>
            <Option name="type" value="collection" type="QString"/>
          </Option>
        </data_defined_properties>
        <layer enabled="1" class="SimpleMarker" id="{08cf93b4-1d4c-49db-80bf-f2e595e49245}" locked="0" pass="0">
          <Option type="Map">
            <Option name="angle" value="0" type="QString"/>
            <Option name="cap_style" value="square" type="QString"/>
            <Option name="color" value="212,85,0,255,rgb:0.8313725,0.3333333,0,1" type="QString"/>
            <Option name="horizontal_anchor_point" value="1" type="QString"/>
            <Option name="joinstyle" value="bevel" type="QString"/>
            <Option name="name" value="triangle" type="QString"/>
            <Option name="offset" value="0,0" type="QString"/>
            <Option name="offset_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="offset_unit" value="MM" type="QString"/>
            <Option name="outline_color" value="0,0,0,255,rgb:0,0,0,1" type="QString"/>
            <Option name="outline_style" value="solid" type="QString"/>
            <Option name="outline_width" value="0" type="QString"/>
            <Option name="outline_width_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="outline_width_unit" value="MM" type="QString"/>
            <Option name="scale_method" value="area" type="QString"/>
            <Option name="size" value="3" type="QString"/>
            <Option name="size_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="size_unit" value="MM" type="QString"/>
            <Option name="vertical_anchor_point" value="1" type="QString"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" value="" type="QString"/>
              <Option name="properties"/>
              <Option name="type" value="collection" type="QString"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol is_animated="0" frame_rate="10" name="8" force_rhr="0" alpha="1" clip_to_extent="1" type="marker">
        <data_defined_properties>
          <Option type="Map">
            <Option name="name" value="" type="QString"/>
            <Option name="properties"/>
            <Option name="type" value="collection" type="QString"/>
          </Option>
        </data_defined_properties>
        <layer enabled="1" class="SimpleMarker" id="{25bcdf68-0db4-49ac-b26d-008726329c00}" locked="0" pass="0">
          <Option type="Map">
            <Option name="angle" value="0" type="QString"/>
            <Option name="cap_style" value="square" type="QString"/>
            <Option name="color" value="170,0,0,255,rgb:0.6666667,0,0,1" type="QString"/>
            <Option name="horizontal_anchor_point" value="1" type="QString"/>
            <Option name="joinstyle" value="bevel" type="QString"/>
            <Option name="name" value="triangle" type="QString"/>
            <Option name="offset" value="0,0" type="QString"/>
            <Option name="offset_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="offset_unit" value="MM" type="QString"/>
            <Option name="outline_color" value="0,0,0,255,rgb:0,0,0,1" type="QString"/>
            <Option name="outline_style" value="solid" type="QString"/>
            <Option name="outline_width" value="0" type="QString"/>
            <Option name="outline_width_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="outline_width_unit" value="MM" type="QString"/>
            <Option name="scale_method" value="area" type="QString"/>
            <Option name="size" value="3" type="QString"/>
            <Option name="size_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="size_unit" value="MM" type="QString"/>
            <Option name="vertical_anchor_point" value="1" type="QString"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" value="" type="QString"/>
              <Option name="properties"/>
              <Option name="type" value="collection" type="QString"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol is_animated="0" frame_rate="10" name="9" force_rhr="0" alpha="1" clip_to_extent="1" type="marker">
        <data_defined_properties>
          <Option type="Map">
            <Option name="name" value="" type="QString"/>
            <Option name="properties"/>
            <Option name="type" value="collection" type="QString"/>
          </Option>
        </data_defined_properties>
        <layer enabled="1" class="SimpleMarker" id="{f6ce1545-f3f3-44f5-ad62-fea015d60e99}" locked="0" pass="0">
          <Option type="Map">
            <Option name="angle" value="0" type="QString"/>
            <Option name="cap_style" value="square" type="QString"/>
            <Option name="color" value="96,0,1,255,rgb:0.3764706,0,0.0039216,1" type="QString"/>
            <Option name="horizontal_anchor_point" value="1" type="QString"/>
            <Option name="joinstyle" value="bevel" type="QString"/>
            <Option name="name" value="triangle" type="QString"/>
            <Option name="offset" value="0,0" type="QString"/>
            <Option name="offset_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="offset_unit" value="MM" type="QString"/>
            <Option name="outline_color" value="35,35,35,255,rgb:0.1372549,0.1372549,0.1372549,1" type="QString"/>
            <Option name="outline_style" value="solid" type="QString"/>
            <Option name="outline_width" value="0" type="QString"/>
            <Option name="outline_width_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="outline_width_unit" value="MM" type="QString"/>
            <Option name="scale_method" value="diameter" type="QString"/>
            <Option name="size" value="3" type="QString"/>
            <Option name="size_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="size_unit" value="MM" type="QString"/>
            <Option name="vertical_anchor_point" value="1" type="QString"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" value="" type="QString"/>
              <Option name="properties"/>
              <Option name="type" value="collection" type="QString"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
    </symbols>
    <data-defined-properties>
      <Option type="Map">
        <Option name="name" value="" type="QString"/>
        <Option name="properties"/>
        <Option name="type" value="collection" type="QString"/>
      </Option>
    </data-defined-properties>
  </renderer-v2>
  <selection mode="Default">
    <selectionColor invalid="1"/>
    <selectionSymbol>
      <symbol is_animated="0" frame_rate="10" name="" force_rhr="0" alpha="1" clip_to_extent="1" type="marker">
        <data_defined_properties>
          <Option type="Map">
            <Option name="name" value="" type="QString"/>
            <Option name="properties"/>
            <Option name="type" value="collection" type="QString"/>
          </Option>
        </data_defined_properties>
        <layer enabled="1" class="SimpleMarker" id="{26ef3a50-1d18-4eee-9804-9b402d5fc2cc}" locked="0" pass="0">
          <Option type="Map">
            <Option name="angle" value="0" type="QString"/>
            <Option name="cap_style" value="square" type="QString"/>
            <Option name="color" value="255,0,0,255,rgb:1,0,0,1" type="QString"/>
            <Option name="horizontal_anchor_point" value="1" type="QString"/>
            <Option name="joinstyle" value="bevel" type="QString"/>
            <Option name="name" value="circle" type="QString"/>
            <Option name="offset" value="0,0" type="QString"/>
            <Option name="offset_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="offset_unit" value="MM" type="QString"/>
            <Option name="outline_color" value="35,35,35,255,rgb:0.1372549,0.1372549,0.1372549,1" type="QString"/>
            <Option name="outline_style" value="solid" type="QString"/>
            <Option name="outline_width" value="0" type="QString"/>
            <Option name="outline_width_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="outline_width_unit" value="MM" type="QString"/>
            <Option name="scale_method" value="diameter" type="QString"/>
            <Option name="size" value="2" type="QString"/>
            <Option name="size_map_unit_scale" value="3x:0,0,0,0,0,0" type="QString"/>
            <Option name="size_unit" value="MM" type="QString"/>
            <Option name="vertical_anchor_point" value="1" type="QString"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" value="" type="QString"/>
              <Option name="properties"/>
              <Option name="type" value="collection" type="QString"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
    </selectionSymbol>
  </selection>
  <customproperties>
    <Option type="Map">
      <Option name="dualview/previewExpressions" type="List">
        <Option value="COALESCE( &quot;device_name&quot;, '&lt;NULL>' )" type="QString"/>
      </Option>
      <Option name="embeddedWidgets/count" value="0" type="int"/>
      <Option name="variableNames"/>
      <Option name="variableValues"/>
    </Option>
  </customproperties>
  <blendMode>0</blendMode>
  <featureBlendMode>0</featureBlendMode>
  <layerOpacity>1</layerOpacity>
  <geometryOptions removeDuplicateNodes="0" geometryPrecision="0">
    <activeChecks/>
    <checkConfiguration/>
  </geometryOptions>
  <legend type="default-vector" showLabelLegend="0"/>
  <referencedLayers/>
  <referencingLayers/>
  <fieldConfiguration>
    <field name="fid" configurationFlags="NoFlag">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="id" configurationFlags="NoFlag">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="device_id" configurationFlags="NoFlag">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="device_name" configurationFlags="NoFlag">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="last_reading_at" configurationFlags="NoFlag">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="type" configurationFlags="NoFlag">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="unit" configurationFlags="NoFlag">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="value" configurationFlags="NoFlag">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="unit_type" configurationFlags="NoFlag">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="CPM" configurationFlags="NoFlag">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="doserate_uSvh" configurationFlags="NoFlag">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="xcoord" configurationFlags="NoFlag">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="ycoord" configurationFlags="NoFlag">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
  </fieldConfiguration>
  <aliases>
    <alias name="" index="0" field="fid"/>
    <alias name="" index="1" field="id"/>
    <alias name="" index="2" field="device_id"/>
    <alias name="" index="3" field="device_name"/>
    <alias name="" index="4" field="last_reading_at"/>
    <alias name="" index="5" field="type"/>
    <alias name="" index="6" field="unit"/>
    <alias name="" index="7" field="value"/>
    <alias name="" index="8" field="unit_type"/>
    <alias name="" index="9" field="CPM"/>
    <alias name="" index="10" field="doserate_uSvh"/>
    <alias name="" index="11" field="xcoord"/>
    <alias name="" index="12" field="ycoord"/>
  </aliases>
  <defaults>
    <default applyOnUpdate="0" field="fid" expression=""/>
    <default applyOnUpdate="0" field="id" expression=""/>
    <default applyOnUpdate="0" field="device_id" expression=""/>
    <default applyOnUpdate="0" field="device_name" expression=""/>
    <default applyOnUpdate="0" field="last_reading_at" expression=""/>
    <default applyOnUpdate="0" field="type" expression=""/>
    <default applyOnUpdate="0" field="unit" expression=""/>
    <default applyOnUpdate="0" field="value" expression=""/>
    <default applyOnUpdate="0" field="unit_type" expression=""/>
    <default applyOnUpdate="0" field="CPM" expression=""/>
    <default applyOnUpdate="0" field="doserate_uSvh" expression=""/>
    <default applyOnUpdate="0" field="xcoord" expression=""/>
    <default applyOnUpdate="0" field="ycoord" expression=""/>
  </defaults>
  <constraints>
    <constraint unique_strength="1" constraints="3" exp_strength="0" field="fid" notnull_strength="1"/>
    <constraint unique_strength="0" constraints="0" exp_strength="0" field="id" notnull_strength="0"/>
    <constraint unique_strength="0" constraints="0" exp_strength="0" field="device_id" notnull_strength="0"/>
    <constraint unique_strength="0" constraints="0" exp_strength="0" field="device_name" notnull_strength="0"/>
    <constraint unique_strength="0" constraints="0" exp_strength="0" field="last_reading_at" notnull_strength="0"/>
    <constraint unique_strength="0" constraints="0" exp_strength="0" field="type" notnull_strength="0"/>
    <constraint unique_strength="0" constraints="0" exp_strength="0" field="unit" notnull_strength="0"/>
    <constraint unique_strength="0" constraints="0" exp_strength="0" field="value" notnull_strength="0"/>
    <constraint unique_strength="0" constraints="0" exp_strength="0" field="unit_type" notnull_strength="0"/>
    <constraint unique_strength="0" constraints="0" exp_strength="0" field="CPM" notnull_strength="0"/>
    <constraint unique_strength="0" constraints="0" exp_strength="0" field="doserate_uSvh" notnull_strength="0"/>
    <constraint unique_strength="0" constraints="0" exp_strength="0" field="xcoord" notnull_strength="0"/>
    <constraint unique_strength="0" constraints="0" exp_strength="0" field="ycoord" notnull_strength="0"/>
  </constraints>
  <constraintExpressions>
    <constraint field="fid" desc="" exp=""/>
    <constraint field="id" desc="" exp=""/>
    <constraint field="device_id" desc="" exp=""/>
    <constraint field="device_name" desc="" exp=""/>
    <constraint field="last_reading_at" desc="" exp=""/>
    <constraint field="type" desc="" exp=""/>
    <constraint field="unit" desc="" exp=""/>
    <constraint field="value" desc="" exp=""/>
    <constraint field="unit_type" desc="" exp=""/>
    <constraint field="CPM" desc="" exp=""/>
    <constraint field="doserate_uSvh" desc="" exp=""/>
    <constraint field="xcoord" desc="" exp=""/>
    <constraint field="ycoord" desc="" exp=""/>
  </constraintExpressions>
  <expressionfields/>
  <attributeactions>
    <defaultAction value="{00000000-0000-0000-0000-000000000000}" key="Canvas"/>
  </attributeactions>
  <attributetableconfig actionWidgetStyle="dropDown" sortOrder="0" sortExpression="">
    <columns>
      <column name="fid" width="-1" hidden="0" type="field"/>
      <column name="id" width="-1" hidden="0" type="field"/>
      <column name="device_id" width="-1" hidden="0" type="field"/>
      <column name="device_name" width="-1" hidden="0" type="field"/>
      <column name="last_reading_at" width="-1" hidden="0" type="field"/>
      <column name="type" width="-1" hidden="0" type="field"/>
      <column name="unit" width="-1" hidden="0" type="field"/>
      <column name="value" width="-1" hidden="0" type="field"/>
      <column name="unit_type" width="-1" hidden="0" type="field"/>
      <column name="CPM" width="-1" hidden="0" type="field"/>
      <column name="doserate_uSvh" width="-1" hidden="0" type="field"/>
      <column name="xcoord" width="-1" hidden="0" type="field"/>
      <column name="ycoord" width="-1" hidden="0" type="field"/>
      <column width="-1" hidden="1" type="actions"/>
    </columns>
  </attributetableconfig>
  <conditionalstyles>
    <rowstyles/>
    <fieldstyles/>
  </conditionalstyles>
  <storedexpressions/>
  <editform tolerant="1"></editform>
  <editforminit/>
  <editforminitcodesource>0</editforminitcodesource>
  <editforminitfilepath></editforminitfilepath>
  <editforminitcode><![CDATA[# -*- coding: utf-8 -*-
"""
QGIS forms can have a Python function that is called when the form is
opened.

Use this function to add extra logic to your forms.

Enter the name of the function in the "Python Init function"
field.
An example follows:
"""
from qgis.PyQt.QtWidgets import QWidget

def my_form_open(dialog, layer, feature):
    geom = feature.geometry()
    control = dialog.findChild(QWidget, "MyLineEdit")
]]></editforminitcode>
  <featformsuppress>0</featformsuppress>
  <editorlayout>generatedlayout</editorlayout>
  <editable>
    <field name="CPM" editable="1"/>
    <field name="device_id" editable="1"/>
    <field name="device_name" editable="1"/>
    <field name="doserate_uSvh" editable="1"/>
    <field name="fid" editable="1"/>
    <field name="id" editable="1"/>
    <field name="last_reading_at" editable="1"/>
    <field name="type" editable="1"/>
    <field name="unit" editable="1"/>
    <field name="unit_type" editable="1"/>
    <field name="value" editable="1"/>
    <field name="xcoord" editable="1"/>
    <field name="ycoord" editable="1"/>
  </editable>
  <labelOnTop>
    <field labelOnTop="0" name="CPM"/>
    <field labelOnTop="0" name="device_id"/>
    <field labelOnTop="0" name="device_name"/>
    <field labelOnTop="0" name="doserate_uSvh"/>
    <field labelOnTop="0" name="fid"/>
    <field labelOnTop="0" name="id"/>
    <field labelOnTop="0" name="last_reading_at"/>
    <field labelOnTop="0" name="type"/>
    <field labelOnTop="0" name="unit"/>
    <field labelOnTop="0" name="unit_type"/>
    <field labelOnTop="0" name="value"/>
    <field labelOnTop="0" name="xcoord"/>
    <field labelOnTop="0" name="ycoord"/>
  </labelOnTop>
  <reuseLastValue>
    <field name="CPM" reuseLastValue="0"/>
    <field name="device_id" reuseLastValue="0"/>
    <field name="device_name" reuseLastValue="0"/>
    <field name="doserate_uSvh" reuseLastValue="0"/>
    <field name="fid" reuseLastValue="0"/>
    <field name="id" reuseLastValue="0"/>
    <field name="last_reading_at" reuseLastValue="0"/>
    <field name="type" reuseLastValue="0"/>
    <field name="unit" reuseLastValue="0"/>
    <field name="unit_type" reuseLastValue="0"/>
    <field name="value" reuseLastValue="0"/>
    <field name="xcoord" reuseLastValue="0"/>
    <field name="ycoord" reuseLastValue="0"/>
  </reuseLastValue>
  <dataDefinedFieldProperties/>
  <widgets/>
  <previewExpression>COALESCE( "device_name", '&lt;NULL>' )</previewExpression>
  <mapTip enabled="1"></mapTip>
  <layerGeometryType>0</layerGeometryType>
</qgis>'''

    def tr(self, string):
        return QCoreApplication.translate("Processing", string)

    def createInstance(self):
        return SafecastFixedSensorsLoader()

    def name(self):
        return "safecast_fixed_sensors_loader"

    def displayName(self):
        return self.tr("Safecast Fixed Sensors Loader")

    def group(self):
        return self.tr("Radioactivity")

    def groupId(self):
        return "radioactivity"

    def shortHelpString(self):
        return self.tr(
            "Loads the live fixed sensors layer from the Safecast OGC API Features "
            "endpoint[](https://simplemap.safecast.org/ogc), adds longitude/latitude "
            "(and xcoord/ycoord) attributes, calculates doserate_uSvh = value / 334, "
            "and applies one of the two provided classification styles.\n\n"
            "Style 1 (default) = original Safecast default style\n"
            "Style 2 = CzechRad colours style"
        )

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterEnum(
                self.STYLE,
                self.tr("Style"),
                options=[
                    self.tr("Style 1 – default (Safecast)"),
                    self.tr("Style 2 – CzechRad colours"),
                ],
                defaultValue=0,  # Style 1
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr("Safecast fixed sensors"),
                type=QgsProcessing.TypeVectorPoint,
                defaultValue=QgsProcessing.TEMPORARY_OUTPUT,
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        style_idx = self.parameterAsEnum(parameters, self.STYLE, context)

        # ---- 1. Fetch all features from OGC API Features -------------------
        base_url = "https://simplemap.safecast.org/ogc/collections/sensors/items"
        all_features = []
        limit = 500
        offset = 0

        feedback.pushInfo("Connecting to Safecast OGC API Features …")

        while True:
            if feedback.isCanceled():
                break

            url = f"{base_url}?limit={limit}&offset={offset}"
            feedback.pushInfo(f"Requesting: {url}")

            request = QNetworkRequest(QUrl(url))
            reply = QgsNetworkAccessManager.instance().get(request)

            loop = QEventLoop()
            reply.finished.connect(loop.quit)
            loop.exec_()

            if reply.error():
                feedback.reportError(f"Network error: {reply.errorString()}")
                break

            data = json.loads(bytes(reply.readAll()).decode("utf-8"))
            features = data.get("features", [])
            all_features.extend(features)

            number_matched = data.get("numberMatched", 0)
            number_returned = data.get("numberReturned", 0)
            feedback.pushInfo(f"Received {number_returned} features (total so far: {len(all_features)})")

            if len(all_features) >= number_matched or number_returned == 0:
                break
            offset += limit

        feedback.pushInfo(f"Total features retrieved: {len(all_features)}")

        if not all_features:
            feedback.reportError("No features returned from the service.")
            return {}

        # ---- 2. Define output fields ---------------------------------------
        fields = QgsFields()
        fields.append(QgsField("id", QVariant.String))
        fields.append(QgsField("device_id", QVariant.String))
        fields.append(QgsField("device_name", QVariant.String))
        fields.append(QgsField("last_reading_at", QVariant.String))
        fields.append(QgsField("type", QVariant.String))
        fields.append(QgsField("unit", QVariant.String))
        fields.append(QgsField("value", QVariant.Double))
        fields.append(QgsField("longitude", QVariant.Double))
        fields.append(QgsField("latitude", QVariant.Double))
        fields.append(QgsField("xcoord", QVariant.Double))   # alias for styles
        fields.append(QgsField("ycoord", QVariant.Double))   # alias for styles
        fields.append(QgsField("doserate_uSvh", QVariant.Double))

        (sink, dest_id) = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            fields,
            QgsWkbTypes.Point,
            QgsCoordinateReferenceSystem("EPSG:4326"),
        )

        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT))

        # ---- 3. Build features ---------------------------------------------
        total = len(all_features)
        for i, f in enumerate(all_features):
            if feedback.isCanceled():
                break

            props = f.get("properties", {})
            geom = f.get("geometry", {})
            coords = geom.get("coordinates", [None, None])
            lon = coords[0]
            lat = coords[1]
            value = props.get("value")

            try:
                doserate = float(value) / 334.0 if value is not None else None
            except (TypeError, ValueError):
                doserate = None

            feat = QgsFeature(fields)
            feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(lon, lat)))
            feat.setAttributes([
                f.get("id"),
                props.get("device_id"),
                props.get("device_name"),
                props.get("last_reading_at"),
                props.get("type"),
                props.get("unit"),
                value,
                lon,
                lat,
                lon,   # xcoord
                lat,   # ycoord
                doserate,
            ])
            sink.addFeature(feat, QgsFeatureSink.FastInsert)

            feedback.setProgress(int(100 * i / total))

        # ---- 4. Apply style via post-processor -----------------------------
        # We register a post-processor so the style is applied after the layer
        # is loaded into the project (works for both temporary and file outputs).
        if context.willLoadLayerOnCompletion(dest_id):
            style_qml = self.STYLE_1_QML if style_idx == 0 else self.STYLE_2_QML
            context.layerToLoadOnCompletionDetails(dest_id).setPostProcessor(
                StylePostProcessor.create(style_qml)
            )

        return {self.OUTPUT: dest_id}


class StylePostProcessor(QgsProcessingLayerPostProcessorInterface):
    """Applies a QML style string to the output layer and sets a nice name."""

    instance = None
    qml = None

    def postProcessLayer(self, layer, context, feedback):
        if not layer or not layer.isValid():
            return

        layer.setName("Safecast fixed sensors")

        if self.qml:
            style = QgsMapLayerStyle(self.qml)
            if style.isValid():
                style.writeToLayer(layer)
                feedback.pushInfo("Style applied successfully.")
            else:
                feedback.pushWarning("Could not apply the selected style (QML invalid).")

    @staticmethod
    def create(qml_string):
        StylePostProcessor.instance = StylePostProcessor()
        StylePostProcessor.instance.qml = qml_string
        return StylePostProcessor.instance

# Created with Grok AI, released under CC0 1.0 Universal License
# Copyright 2026 Jan Helebrant, czechrad@suro.cz, www.suro.cz
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE
