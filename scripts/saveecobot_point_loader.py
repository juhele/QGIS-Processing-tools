import os
import csv
import json
import re
import time
import urllib.request
import tempfile
from datetime import datetime, timezone

from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsFields,
    QgsField,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsCoordinateReferenceSystem,
    QgsWkbTypes,
    QgsProcessingException,
    QgsProcessingUtils
)
from qgis.PyQt.QtCore import QMetaType

# Style 1: Detailed 10-Class Scale (Default)
SLD_STYLE_1 = """<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor xmlns="http://www.opengis.net/sld" xmlns:se="http://www.opengis.net/se" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1.0" xmlns:ogc="http://www.opengis.net/ogc" xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.1.0/StyledLayerDescriptor.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <NamedLayer>
    <se:Name>SaveEcoBot Gamma Stations</se:Name>
    <UserStyle>
      <se:Name>SaveEcoBot Gamma Stations</se:Name>
      <se:FeatureTypeStyle>
        <se:Rule>
          <se:Name>&lt; 0.08</se:Name>
          <se:Description>
            <se:Title>&lt; 0.08</se:Title>
          </se:Description>
          <ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
            <ogc:And>
              <ogc:PropertyIsGreaterThanOrEqualTo>
                <ogc:PropertyName>doserate_uSvh</ogc:PropertyName>
                <ogc:Literal>0</ogc:Literal>
              </ogc:PropertyIsGreaterThanOrEqualTo>
              <ogc:PropertyIsLessThanOrEqualTo>
                <ogc:PropertyName>doserate_uSvh</ogc:PropertyName>
                <ogc:Literal>0.08</ogc:Literal>
              </ogc:PropertyIsLessThanOrEqualTo>
            </ogc:And>
          </ogc:Filter>
          <se:PointSymbolizer>
            <se:Graphic>
              <se:Mark>
                <se:WellKnownName>triangle</se:WellKnownName>
                <se:Fill>
                  <se:SvgParameter name="fill">#00007f</se:SvgParameter>
                </se:Fill>
                <se:Stroke>
                  <se:SvgParameter name="stroke">#000000</se:SvgParameter>
                  <se:SvgParameter name="stroke-width">0.5</se:SvgParameter>
                </se:Stroke>
              </se:Mark>
              <se:Size>11</se:Size>
            </se:Graphic>
          </se:PointSymbolizer>
        </se:Rule>
        <se:Rule>
          <se:Name>0.08 - 0.10</se:Name>
          <se:Description>
            <se:Title>0.08 - 0.10</se:Title>
          </se:Description>
          <ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
            <ogc:And>
              <ogc:PropertyIsGreaterThan>
                <ogc:PropertyName>doserate_uSvh</ogc:PropertyName>
                <ogc:Literal>0.08</ogc:Literal>
              </ogc:PropertyIsGreaterThan>
              <ogc:PropertyIsLessThanOrEqualTo>
                <ogc:PropertyName>doserate_uSvh</ogc:PropertyName>
                <ogc:Literal>0.10000000000000001</ogc:Literal>
              </ogc:PropertyIsLessThanOrEqualTo>
            </ogc:And>
          </ogc:Filter>
          <se:PointSymbolizer>
            <se:Graphic>
              <se:Mark>
                <se:WellKnownName>triangle</se:WellKnownName>
                <se:Fill>
                  <se:SvgParameter name="fill">#0055bf</se:SvgParameter>
                </se:Fill>
                <se:Stroke>
                  <se:SvgParameter name="stroke">#000000</se:SvgParameter>
                  <se:SvgParameter name="stroke-width">0.5</se:SvgParameter>
                </se:Stroke>
              </se:Mark>
              <se:Size>11</se:Size>
            </se:Graphic>
          </se:PointSymbolizer>
        </se:Rule>
        <se:Rule>
          <se:Name>0.10 - 0.15</se:Name>
          <se:Description>
            <se:Title>0.10 - 0.15</se:Title>
          </se:Description>
          <ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
            <ogc:And>
              <ogc:PropertyIsGreaterThan>
                <ogc:PropertyName>doserate_uSvh</ogc:PropertyName>
                <ogc:Literal>0.10000000000000001</ogc:Literal>
              </ogc:PropertyIsGreaterThan>
              <ogc:PropertyIsLessThanOrEqualTo>
                <ogc:PropertyName>doserate_uSvh</ogc:PropertyName>
                <ogc:Literal>0.14999999999999999</ogc:Literal>
              </ogc:PropertyIsLessThanOrEqualTo>
            </ogc:And>
          </ogc:Filter>
          <se:PointSymbolizer>
            <se:Graphic>
              <se:Mark>
                <se:WellKnownName>triangle</se:WellKnownName>
                <se:Fill>
                  <se:SvgParameter name="fill">#00aaff</se:SvgParameter>
                </se:Fill>
                <se:Stroke>
                  <se:SvgParameter name="stroke">#000000</se:SvgParameter>
                  <se:SvgParameter name="stroke-width">0.5</se:SvgParameter>
                </se:Stroke>
              </se:Mark>
              <se:Size>11</se:Size>
            </se:Graphic>
          </se:PointSymbolizer>
        </se:Rule>
        <se:Rule>
          <se:Name>0.15 - 0.20</se:Name>
          <se:Description>
            <se:Title>0.15 - 0.20</se:Title>
          </se:Description>
          <ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
            <ogc:And>
              <ogc:PropertyIsGreaterThan>
                <ogc:PropertyName>doserate_uSvh</ogc:PropertyName>
                <ogc:Literal>0.14999999999999999</ogc:Literal>
              </ogc:PropertyIsGreaterThan>
              <ogc:PropertyIsLessThanOrEqualTo>
                <ogc:PropertyName>doserate_uSvh</ogc:PropertyName>
                <ogc:Literal>0.20000000000000001</ogc:Literal>
              </ogc:PropertyIsLessThanOrEqualTo>
            </ogc:And>
          </ogc:Filter>
          <se:PointSymbolizer>
            <se:Graphic>
              <se:Mark>
                <se:WellKnownName>triangle</se:WellKnownName>
                <se:Fill>
                  <se:SvgParameter name="fill">#2ad4bf</se:SvgParameter>
                </se:Fill>
                <se:Stroke>
                  <se:SvgParameter name="stroke">#000000</se:SvgParameter>
                  <se:SvgParameter name="stroke-width">0.5</se:SvgParameter>
                </se:Stroke>
              </se:Mark>
              <se:Size>11</se:Size>
            </se:Graphic>
          </se:PointSymbolizer>
        </se:Rule>
        <se:Rule>
          <se:Name>0.20 - 0.25</se:Name>
          <se:Description>
            <se:Title>0.20 - 0.25</se:Title>
          </se:Description>
          <ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
            <ogc:And>
              <ogc:PropertyIsGreaterThan>
                <ogc:PropertyName>doserate_uSvh</ogc:PropertyName>
                <ogc:Literal>0.20000000000000001</ogc:Literal>
              </ogc:PropertyIsGreaterThan>
              <ogc:PropertyIsLessThanOrEqualTo>
                <ogc:PropertyName>doserate_uSvh</ogc:PropertyName>
                <ogc:Literal>0.25</ogc:Literal>
              </ogc:PropertyIsLessThanOrEqualTo>
            </ogc:And>
          </ogc:Filter>
          <se:PointSymbolizer>
            <se:Graphic>
              <se:Mark>
                <se:WellKnownName>triangle</se:WellKnownName>
                <se:Fill>
                  <se:SvgParameter name="fill">#55ff7f</se:SvgParameter>
                </se:Fill>
                <se:Stroke>
                  <se:SvgParameter name="stroke">#000000</se:SvgParameter>
                  <se:SvgParameter name="stroke-width">0.5</se:SvgParameter>
                </se:Stroke>
              </se:Mark>
              <se:Size>11</se:Size>
            </se:Graphic>
          </se:PointSymbolizer>
        </se:Rule>
        <se:Rule>
          <se:Name>0.25 - 0.30</se:Name>
          <se:Description>
            <se:Title>0.25 - 0.30</se:Title>
          </se:Description>
          <ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
            <ogc:And>
              <ogc:PropertyIsGreaterThan>
                <ogc:PropertyName>doserate_uSvh</ogc:PropertyName>
                <ogc:Literal>0.25</ogc:Literal>
              </ogc:PropertyIsGreaterThan>
              <ogc:PropertyIsLessThanOrEqualTo>
                <ogc:PropertyName>doserate_uSvh</ogc:PropertyName>
                <ogc:Literal>0.29999999999999999</ogc:Literal>
              </ogc:PropertyIsLessThanOrEqualTo>
            </ogc:And>
          </ogc:Filter>
          <se:PointSymbolizer>
            <se:Graphic>
              <se:Mark>
                <se:WellKnownName>triangle</se:WellKnownName>
                <se:Fill>
                  <se:SvgParameter name="fill">#aad43f</se:SvgParameter>
                </se:Fill>
                <se:Stroke>
                  <se:SvgParameter name="stroke">#000000</se:SvgParameter>
                  <se:SvgParameter name="stroke-width">0.5</se:SvgParameter>
                </se:Stroke>
              </se:Mark>
              <se:Size>11</se:Size>
            </se:Graphic>
          </se:PointSymbolizer>
        </se:Rule>
        <se:Rule>
          <se:Name>0.30 - 0.50</se:Name>
          <se:Description>
            <se:Title>0.30 - 0.50</se:Title>
          </se:Description>
          <ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
            <ogc:And>
              <ogc:PropertyIsGreaterThan>
                <ogc:PropertyName>doserate_uSvh</ogc:PropertyName>
                <ogc:Literal>0.29999999999999999</ogc:Literal>
              </ogc:PropertyIsGreaterThan>
              <ogc:PropertyIsLessThanOrEqualTo>
                <ogc:PropertyName>doserate_uSvh</ogc:PropertyName>
                <ogc:Literal>0.5</ogc:Literal>
              </ogc:PropertyIsLessThanOrEqualTo>
            </ogc:And>
          </ogc:Filter>
          <se:PointSymbolizer>
            <se:Graphic>
              <se:Mark>
                <se:WellKnownName>triangle</se:WellKnownName>
                <se:Fill>
                  <se:SvgParameter name="fill">#ffaa00</se:SvgParameter>
                </se:Fill>
                <se:Stroke>
                  <se:SvgParameter name="stroke">#000000</se:SvgParameter>
                  <se:SvgParameter name="stroke-width">0.5</se:SvgParameter>
                </se:Stroke>
              </se:Mark>
              <se:Size>11</se:Size>
            </se:Graphic>
          </se:PointSymbolizer>
        </se:Rule>
        <se:Rule>
          <se:Name>0.50 - 1.00</se:Name>
          <se:Description>
            <se:Title>0.50 - 1.00</se:Title>
          </se:Description>
          <ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
            <ogc:And>
              <ogc:PropertyIsGreaterThan>
                <ogc:PropertyName>doserate_uSvh</ogc:PropertyName>
                <ogc:Literal>0.5</ogc:Literal>
              </ogc:PropertyIsGreaterThan>
              <ogc:PropertyIsLessThanOrEqualTo>
                <ogc:PropertyName>doserate_uSvh</ogc:PropertyName>
                <ogc:Literal>1</ogc:Literal>
              </ogc:PropertyIsLessThanOrEqualTo>
            </ogc:And>
          </ogc:Filter>
          <se:PointSymbolizer>
            <se:Graphic>
              <se:Mark>
                <se:WellKnownName>triangle</se:WellKnownName>
                <se:Fill>
                  <se:SvgParameter name="fill">#d45500</se:SvgParameter>
                </se:Fill>
                <se:Stroke>
                  <se:SvgParameter name="stroke">#000000</se:SvgParameter>
                  <se:SvgParameter name="stroke-width">0.5</se:SvgParameter>
                </se:Stroke>
              </se:Mark>
              <se:Size>11</se:Size>
            </se:Graphic>
          </se:PointSymbolizer>
        </se:Rule>
        <se:Rule>
          <se:Name>1.00 - 10.00</se:Name>
          <se:Description>
            <se:Title>1.00 - 10.00</se:Title>
          </se:Description>
          <ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
            <ogc:And>
              <ogc:PropertyIsGreaterThan>
                <ogc:PropertyName>doserate_uSvh</ogc:PropertyName>
                <ogc:Literal>1</ogc:Literal>
              </ogc:PropertyIsGreaterThan>
              <ogc:PropertyIsLessThanOrEqualTo>
                <ogc:PropertyName>doserate_uSvh</ogc:PropertyName>
                <ogc:Literal>10</ogc:Literal>
              </ogc:PropertyIsLessThanOrEqualTo>
            </ogc:And>
          </ogc:Filter>
          <se:PointSymbolizer>
            <se:Graphic>
              <se:Mark>
                <se:WellKnownName>triangle</se:WellKnownName>
                <se:Fill>
                  <se:SvgParameter name="fill">#aa0000</se:SvgParameter>
                </se:Fill>
                <se:Stroke>
                  <se:SvgParameter name="stroke">#000000</se:SvgParameter>
                  <se:SvgParameter name="stroke-width">0.5</se:SvgParameter>
                </se:Stroke>
              </se:Mark>
              <se:Size>11</se:Size>
            </se:Graphic>
          </se:PointSymbolizer>
        </se:Rule>
        <se:Rule>
          <se:Name>>10</se:Name>
          <se:Description>
            <se:Title>>10</se:Title>
          </se:Description>
          <se:ElseFilter xmlns:se="http://www.opengis.net/se"/>
          <se:PointSymbolizer>
            <se:Graphic>
              <se:Mark>
                <se:WellKnownName>triangle</se:WellKnownName>
                <se:Fill>
                  <se:SvgParameter name="fill">#600001</se:SvgParameter>
                </se:Fill>
                <se:Stroke>
                  <se:SvgParameter name="stroke">#232323</se:SvgParameter>
                  <se:SvgParameter name="stroke-width">0.5</se:SvgParameter>
                </se:Stroke>
              </se:Mark>
              <se:Size>11</se:Size>
            </se:Graphic>
          </se:PointSymbolizer>
        </se:Rule>
      </se:FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>"""

# Style 2: Broad 6-Class Scale (Optional)
SLD_STYLE_2 = """<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor xmlns="http://www.opengis.net/sld" xmlns:se="http://www.opengis.net/se" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1.0" xmlns:ogc="http://www.opengis.net/ogc" xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.1.0/StyledLayerDescriptor.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <NamedLayer>
    <se:Name>SaveEcoBot Gamma Stations</se:Name>
    <UserStyle>
      <se:Name>SaveEcoBot Gamma Stations</se:Name>
      <se:FeatureTypeStyle>
        <se:Rule>
          <se:Name>0 - 0,1</se:Name>
          <se:Description>
            <se:Title>0 - 0,1</se:Title>
          </se:Description>
          <ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
            <ogc:And>
              <ogc:PropertyIsGreaterThanOrEqualTo>
                <ogc:PropertyName>doserate_uSvh</ogc:PropertyName>
                <ogc:Literal>0</ogc:Literal>
              </ogc:PropertyIsGreaterThanOrEqualTo>
              <ogc:PropertyIsLessThanOrEqualTo>
                <ogc:PropertyName>doserate_uSvh</ogc:PropertyName>
                <ogc:Literal>0.10000000000000001</ogc:Literal>
              </ogc:PropertyIsLessThanOrEqualTo>
            </ogc:And>
          </ogc:Filter>
          <se:PointSymbolizer>
            <se:Graphic>
              <se:Mark>
                <se:WellKnownName>triangle</se:WellKnownName>
                <se:Fill>
                  <se:SvgParameter name="fill">#1dafaf</se:SvgParameter>
                </se:Fill>
                <se:Stroke>
                  <se:SvgParameter name="stroke">#000000</se:SvgParameter>
                  <se:SvgParameter name="stroke-width">0.5</se:SvgParameter>
                </se:Stroke>
              </se:Mark>
              <se:Size>11</se:Size>
            </se:Graphic>
          </se:PointSymbolizer>
        </se:Rule>
        <se:Rule>
          <se:Name>0,1 - 0,2</se:Name>
          <se:Description>
            <se:Title>0,1 - 0,2</se:Title>
          </se:Description>
          <ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
            <ogc:And>
              <ogc:PropertyIsGreaterThan>
                <ogc:PropertyName>doserate_uSvh</ogc:PropertyName>
                <ogc:Literal>0.10000000000000001</ogc:Literal>
              </ogc:PropertyIsGreaterThan>
              <ogc:PropertyIsLessThanOrEqualTo>
                <ogc:PropertyName>doserate_uSvh</ogc:PropertyName>
                <ogc:Literal>0.20000000000000001</ogc:Literal>
              </ogc:PropertyIsLessThanOrEqualTo>
            </ogc:And>
          </ogc:Filter>
          <se:PointSymbolizer>
            <se:Graphic>
              <se:Mark>
                <se:WellKnownName>triangle</se:WellKnownName>
                <se:Fill>
                  <se:SvgParameter name="fill">#1d8baf</se:SvgParameter>
                </se:Fill>
                <se:Stroke>
                  <se:SvgParameter name="stroke">#000000</se:SvgParameter>
                  <se:SvgParameter name="stroke-width">0.5</se:SvgParameter>
                </se:Stroke>
              </se:Mark>
              <se:Size>11</se:Size>
            </se:Graphic>
          </se:PointSymbolizer>
        </se:Rule>
        <se:Rule>
          <se:Name>0,2 - 0,3</se:Name>
          <se:Description>
            <se:Title>0,2 - 0,3</se:Title>
          </se:Description>
          <ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
            <ogc:And>
              <ogc:PropertyIsGreaterThan>
                <ogc:PropertyName>doserate_uSvh</ogc:PropertyName>
                <ogc:Literal>0.20000000000000001</ogc:Literal>
              </ogc:PropertyIsGreaterThan>
              <ogc:PropertyIsLessThanOrEqualTo>
                <ogc:PropertyName>doserate_uSvh</ogc:PropertyName>
                <ogc:Literal>0.29999999999999999</ogc:Literal>
              </ogc:PropertyIsLessThanOrEqualTo>
            </ogc:And>
          </ogc:Filter>
          <se:PointSymbolizer>
            <se:Graphic>
              <se:Mark>
                <se:WellKnownName>triangle</se:WellKnownName>
                <se:Fill>
                  <se:SvgParameter name="fill">#1d66af</se:SvgParameter>
                </se:Fill>
                <se:Stroke>
                  <se:SvgParameter name="stroke">#000000</se:SvgParameter>
                  <se:SvgParameter name="stroke-width">0.5</se:SvgParameter>
                </se:Stroke>
              </se:Mark>
              <se:Size>11</se:Size>
            </se:Graphic>
          </se:PointSymbolizer>
        </se:Rule>
        <se:Rule>
          <se:Name>0,3 - 0,5</se:Name>
          <se:Description>
            <se:Title>0,3 - 0,5</se:Title>
          </se:Description>
          <ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
            <ogc:And>
              <ogc:PropertyIsGreaterThan>
                <ogc:PropertyName>doserate_uSvh</ogc:PropertyName>
                <ogc:Literal>0.29999999999999999</ogc:Literal>
              </ogc:PropertyIsGreaterThan>
              <ogc:PropertyIsLessThanOrEqualTo>
                <ogc:PropertyName>doserate_uSvh</ogc:PropertyName>
                <ogc:Literal>0.5</ogc:Literal>
              </ogc:PropertyIsLessThanOrEqualTo>
            </ogc:And>
          </ogc:Filter>
          <se:PointSymbolizer>
            <se:Graphic>
              <se:Mark>
                <se:WellKnownName>triangle</se:WellKnownName>
                <se:Fill>
                  <se:SvgParameter name="fill">#1d41af</se:SvgParameter>
                </se:Fill>
                <se:Stroke>
                  <se:SvgParameter name="stroke">#000000</se:SvgParameter>
                  <se:SvgParameter name="stroke-width">0.5</se:SvgParameter>
                </se:Stroke>
              </se:Mark>
              <se:Size>11</se:Size>
            </se:Graphic>
          </se:PointSymbolizer>
        </se:Rule>
        <se:Rule>
          <se:Name>0,5 - 2</se:Name>
          <se:Description>
            <se:Title>0,5 - 2</se:Title>
          </se:Description>
          <ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
            <ogc:And>
              <ogc:PropertyIsGreaterThan>
                <ogc:PropertyName>doserate_uSvh</ogc:PropertyName>
                <ogc:Literal>0.5</ogc:Literal>
              </ogc:PropertyIsGreaterThan>
              <ogc:PropertyIsLessThanOrEqualTo>
                <ogc:PropertyName>doserate_uSvh</ogc:PropertyName>
                <ogc:Literal>2</ogc:Literal>
              </ogc:PropertyIsLessThanOrEqualTo>
            </ogc:And>
          </ogc:Filter>
          <se:PointSymbolizer>
            <se:Graphic>
              <se:Mark>
                <se:WellKnownName>triangle</se:WellKnownName>
                <se:Fill>
                  <se:SvgParameter name="fill">#411daf</se:SvgParameter>
                </se:Fill>
                <se:Stroke>
                  <se:SvgParameter name="stroke">#000000</se:SvgParameter>
                  <se:SvgParameter name="stroke-width">0.5</se:SvgParameter>
                </se:Stroke>
              </se:Mark>
              <se:Size>11</se:Size>
            </se:Graphic>
          </se:PointSymbolizer>
        </se:Rule>
        <se:Rule>
          <se:Name>2 - 1000</se:Name>
          <se:Description>
            <se:Title>2 - 1000</se:Title>
          </se:Description>
          <ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
            <ogc:And>
              <ogc:PropertyIsGreaterThan>
                <ogc:PropertyName>doserate_uSvh</ogc:PropertyName>
                <ogc:Literal>2</ogc:Literal>
              </ogc:PropertyIsGreaterThan>
              <ogc:PropertyIsLessThanOrEqualTo>
                <ogc:PropertyName>doserate_uSvh</ogc:PropertyName>
                <ogc:Literal>1000</ogc:Literal>
              </ogc:PropertyIsLessThanOrEqualTo>
            </ogc:And>
          </ogc:Filter>
          <se:PointSymbolizer>
            <se:Graphic>
              <se:Mark>
                <se:WellKnownName>triangle</se:WellKnownName>
                <se:Fill>
                  <se:SvgParameter name="fill">#661daf</se:SvgParameter>
                </se:Fill>
                <se:Stroke>
                  <se:SvgParameter name="stroke">#000000</se:SvgParameter>
                  <se:SvgParameter name="stroke-width">0.5</se:SvgParameter>
                </se:Stroke>
              </se:Mark>
              <se:Size>11</se:Size>
            </se:Graphic>
          </se:PointSymbolizer>
        </se:Rule>
      </se:FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>"""


class SaveEcoBotPointLoaderAlgorithm(QgsProcessingAlgorithm):
    OUTPUT = 'OUTPUT'
    FORCE_REFRESH_STATIONS = 'FORCE_REFRESH_STATIONS'
    STYLE_CHOICE = 'STYLE_CHOICE'

    def name(self):
        return 'saveecobot_point_loader'

    def displayName(self):
        return 'SaveEcoBot Point Loader'

    def group(self):
        return 'Radioactivity'

    def groupId(self):
        return 'radioactivity'

    def createInstance(self):
        return SaveEcoBotPointLoaderAlgorithm()

    def shortHelpString(self):
        return (
            "Loads live radiation gamma-dose rate data from SaveEcoBot map.\n\n"
            "Calculates 'doserate_uSvh' (gamma / 1000) and formats 'UTC_timestamp' (ISO 8601 standard).\n"
            "Creates or loads 'stations.csv' cache automatically and applies the chosen embedded SLD style upon load."
        )

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.FORCE_REFRESH_STATIONS,
                'Force refresh stations.csv cache',
                defaultValue=False
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.STYLE_CHOICE,
                'Select SLD Layer Style',
                options=[
                    'Style 1: CzechRad 10-Class style (Default)',
                    'Style 2: SaveEcoBot default style (Optional)'
                ],
                defaultValue=0
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                'SaveEcoBot Gamma Stations'
            )
        )

    def _get_script_directory(self):
        return os.path.dirname(os.path.abspath(__file__))

    def _fetch_url_content(self, url, feedback=None):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.saveecobot.com/maps',
            'X-Requested-With': 'XMLHttpRequest'
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.read().decode('utf-8')

    def _parse_js_data(self, content, feedback):
        content_clean = content.strip()

        try:
            return json.loads(content_clean)
        except json.JSONDecodeError:
            pass

        match = re.search(r'=\s*(\[.*\]|\{.*\})\s*;?$', content_clean, re.DOTALL)
        if match:
            json_str = match.group(1)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

        array_match = re.search(r'\[.*\]', content_clean, re.DOTALL)
        if array_match:
            try:
                return json.loads(array_match.group(0))
            except json.JSONDecodeError:
                pass

        feedback.pushWarning(f"Failed to parse JS/JSON payload. First 200 chars: {content_clean[:200]}")
        return None

    def _fetch_live_data(self, feedback):
        now_utc = datetime.now(timezone.utc)
        date_str = now_utc.strftime("%Y-%m-%dT%H:%M:%S")
        url = f"https://www.saveecobot.com/storage/maps_data.js?date={date_str}"

        feedback.pushInfo(f"Fetching live map data from: {url}")
        try:
            content = self._fetch_url_content(url, feedback)
            data = self._parse_js_data(content, feedback)
            if data is None:
                raise QgsProcessingException("Could not parse data from maps_data.js")
            return data
        except Exception as e:
            raise QgsProcessingException(f"Failed to download map data: {str(e)}")

    def _extract_items_list(self, raw_data, feedback):
        if isinstance(raw_data, list):
            return raw_data
        
        if isinstance(raw_data, dict):
            for key in ('devices', 'data', 'markers', 'items', 'payload', 'stations'):
                if key in raw_data:
                    val = raw_data[key]
                    if isinstance(val, list):
                        return val
                    elif isinstance(val, dict):
                        return list(val.values())

            dict_values = list(raw_data.values())
            if dict_values and isinstance(dict_values[0], dict):
                return dict_values

        return []

    def _extract_gamma_value(self, item):
        if not isinstance(item, dict):
            return None, None

        raw_gamma = item.get('gamma') or item.get('gamma_l') or item.get('gamma_usv_l') or item.get('gamma_ur_l') or item.get('g')
        raw_gamma_t = item.get('gamma_t') or item.get('gt') or item.get('t')

        if raw_gamma is None:
            for sub_key in ("p", "params", "metrics", "data", "values"):
                if sub_key in item and isinstance(item[sub_key], dict):
                    sub_dict = item[sub_key]
                    raw_gamma = sub_dict.get('gamma') or sub_dict.get('gamma_l') or sub_dict.get('gamma_usv_l') or sub_dict.get('g')
                    if raw_gamma_t is None:
                        raw_gamma_t = sub_dict.get('gamma_t') or sub_dict.get('gt') or sub_dict.get('t')
                    if raw_gamma is not None:
                        break

        return raw_gamma, raw_gamma_t

    def _get_coordinate(self, item, keys):
        for k in keys:
            if k in item and item[k] is not None:
                try:
                    return float(item[k])
                except (ValueError, TypeError):
                    pass
        return None

    def _fetch_single_station_metadata(self, station_id, feedback):
        """Fetches station profile via marker-popup-v2 endpoint and extracts exact required fields."""
        url = f"https://www.saveecobot.com/maps/marker-popup-v2/en/device/{station_id}/gamma.json"
        try:
            content = self._fetch_url_content(url, feedback)
            data = json.loads(content)
            
            payload = data.get('payload', {}) if isinstance(data, dict) else {}
            device = payload.get('device', {}) if isinstance(payload.get('device'), dict) else {}
            location = payload.get('location', {}) if isinstance(payload.get('location'), dict) else {}
            platform = payload.get('platform', {}) if isinstance(payload.get('platform'), dict) else {}

            station_name = device.get('display_name') or f"Station {station_id}"
            description = device.get('description') or ''
            city_label = location.get('city_label') or ''
            region_label = location.get('region_label') or ''
            country_name = location.get('country_name') or device.get('country_name') or ''
            datasource = platform.get('name') or ''
            datasource_url = platform.get('url') or ''

            return {
                'station_name': station_name,
                'description': str(description),
                'city_label': city_label,
                'region_label': region_label,
                'country_name': country_name,
                'datasource': datasource,
                'datasource_url': datasource_url
            }
        except Exception as e:
            return {
                'station_name': f"Station {station_id}",
                'description': '',
                'city_label': '',
                'region_label': '',
                'country_name': '',
                'datasource': '',
                'datasource_url': ''
            }

    def _ensure_stations_csv(self, csv_path, items_list, force_refresh, feedback):
        if os.path.exists(csv_path) and not force_refresh:
            if os.path.getsize(csv_path) > 50:
                feedback.pushInfo(f"Using existing non-empty stations cache: {csv_path}")
                return
            else:
                feedback.pushInfo("Existing stations.csv is empty. Rebuilding cache...")

        feedback.pushInfo("Refreshing station metadata cache from profile popup endpoints...")
        
        candidates = []
        for item in items_list:
            raw_gamma, _ = self._extract_gamma_value(item)
            if raw_gamma is not None:
                station_id = item.get("i") or item.get("id") or item.get("station_id")
                lat = self._get_coordinate(item, ("a", "lat", "latitude", "y"))
                lon = self._get_coordinate(item, ("n", "lng", "lon", "longitude", "x"))

                if station_id is not None and lat is not None and lon is not None:
                    candidates.append((int(station_id), lat, lon, item))

        total = len(candidates)
        full_stations = []

        for idx, (station_id, lat, lon, item) in enumerate(candidates, start=1):
            if feedback.isCanceled():
                break

            meta = self._fetch_single_station_metadata(station_id, feedback)

            # Delay to avoid Cloudflare 403 blocks
            time.sleep(0.15)

            full_stations.append({
                'station_ID': station_id,
                'latitude': lat,
                'longitude': lon,
                'station_name': str(meta['station_name']).strip(),
                'description': str(meta['description']).strip(),
                'city_label': str(meta['city_label']).strip(),
                'region_label': str(meta['region_label']).strip(),
                'country_name': str(meta['country_name']).strip(),
                'datasource': str(meta['datasource']).strip(),
                'datasource_url': str(meta['datasource_url']).strip()
            })

            if idx % 25 == 0 or idx == total:
                feedback.setProgress(int((idx / total) * 100))
                feedback.pushInfo(f"Processed station metadata: {idx}/{total}")

        csv_headers = [
            'station_ID', 'latitude', 'longitude',
            'station_name', 'description', 'city_label',
            'region_label', 'country_name', 'datasource', 'datasource_url'
        ]

        try:
            with open(csv_path, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=csv_headers)
                writer.writeheader()
                writer.writerows(full_stations)
            feedback.pushInfo(f"Successfully cached {len(full_stations)} stations into {csv_path}.")
        except Exception as e:
            raise QgsProcessingException(f"Failed to write CSV cache: {str(e)}")

    def _load_cached_stations(self, csv_path, feedback):
        stations = {}
        try:
            with open(csv_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    st_id = int(row['station_ID'])
                    stations[st_id] = {
                        'latitude': float(row['latitude']),
                        'longitude': float(row['longitude']),
                        'station_name': row.get('station_name', ''),
                        'description': row.get('description', ''),
                        'city_label': row.get('city_label', ''),
                        'region_label': row.get('region_label', ''),
                        'country_name': row.get('country_name', ''),
                        'datasource': row.get('datasource', ''),
                        'datasource_url': row.get('datasource_url', '')
                    }
        except Exception as e:
            raise QgsProcessingException(f"Failed to read CSV cache: {str(e)}")
        
        return stations

    def processAlgorithm(self, parameters, context, feedback):
        force_refresh = self.parameterAsBoolean(parameters, self.FORCE_REFRESH_STATIONS, context)
        self.selected_style_idx = self.parameterAsEnum(parameters, self.STYLE_CHOICE, context)
        
        csv_path = os.path.join(self._get_script_directory(), 'stations.csv')

        raw_live_data = self._fetch_live_data(feedback)
        items_list = self._extract_items_list(raw_live_data, feedback)

        self._ensure_stations_csv(csv_path, items_list, force_refresh, feedback)
        cached_stations = self._load_cached_stations(csv_path, feedback)

        fields = QgsFields()
        fields.append(QgsField('station_ID', QMetaType.Type.Int))
        fields.append(QgsField('station_name', QMetaType.Type.QString))
        fields.append(QgsField('doserate_uSvh', QMetaType.Type.Double))
        fields.append(QgsField('UTC_timestamp', QMetaType.Type.QString))
        fields.append(QgsField('gamma', QMetaType.Type.Double))
        fields.append(QgsField('gamma_t', QMetaType.Type.LongLong))
        fields.append(QgsField('description', QMetaType.Type.QString))
        fields.append(QgsField('city_label', QMetaType.Type.QString))
        fields.append(QgsField('region_label', QMetaType.Type.QString))
        fields.append(QgsField('country_name', QMetaType.Type.QString))
        fields.append(QgsField('datasource', QMetaType.Type.QString))
        fields.append(QgsField('datasource_url', QMetaType.Type.QString))
        fields.append(QgsField('latitude', QMetaType.Type.Double))
        fields.append(QgsField('longitude', QMetaType.Type.Double))

        crs = QgsCoordinateReferenceSystem("EPSG:4326")

        (sink, dest_id) = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            fields,
            QgsWkbTypes.Point,
            crs
        )

        if sink is None:
            raise QgsProcessingException('Error creating feature sink.')

        live_gamma_map = {}
        for item in items_list:
            if isinstance(item, dict):
                st_id = item.get("i") or item.get("id") or item.get("station_id")
                if st_id is not None:
                    try:
                        live_gamma_map[int(st_id)] = item
                    except (ValueError, TypeError):
                        pass

        added_count = 0
        for station_id, info in cached_stations.items():
            item = live_gamma_map.get(station_id, {})
            
            point = QgsPointXY(info['longitude'], info['latitude'])
            feature = QgsFeature(fields)
            feature.setGeometry(QgsGeometry.fromPointXY(point))

            raw_gamma, raw_gamma_t = self._extract_gamma_value(item)

            doserate_uSvh = (float(raw_gamma) / 1000.0) if raw_gamma is not None else None

            utc_timestamp = ""
            if raw_gamma_t is not None:
                try:
                    dt = datetime.fromtimestamp(int(raw_gamma_t), tz=timezone.utc)
                    utc_timestamp = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                except (ValueError, OverflowError):
                    utc_timestamp = ""

            feature.setAttribute('station_ID', station_id)
            feature.setAttribute('station_name', info['station_name'])
            feature.setAttribute('doserate_uSvh', doserate_uSvh)
            feature.setAttribute('UTC_timestamp', utc_timestamp)
            feature.setAttribute('gamma', raw_gamma)
            feature.setAttribute('gamma_t', raw_gamma_t)
            feature.setAttribute('description', info['description'])
            feature.setAttribute('city_label', info['city_label'])
            feature.setAttribute('region_label', info['region_label'])
            feature.setAttribute('country_name', info['country_name'])
            feature.setAttribute('datasource', info['datasource'])
            feature.setAttribute('datasource_url', info['datasource_url'])
            feature.setAttribute('latitude', info['latitude'])
            feature.setAttribute('longitude', info['longitude'])

            sink.addFeature(feature)
            added_count += 1

        feedback.pushInfo(f"Loaded {added_count} gamma points into QGIS vector layer.")

        self.dest_id = dest_id
        return {self.OUTPUT: dest_id}

    def postProcessAlgorithm(self, context, feedback):
        results = super().postProcessAlgorithm(context, feedback)
        
        layer = QgsProcessingUtils.mapLayerFromString(self.dest_id, context)
        if layer:
            # Select style based on user choice
            chosen_sld = SLD_STYLE_1 if self.selected_style_idx == 0 else SLD_STYLE_2
            style_name = "Detailed (10-Class)" if self.selected_style_idx == 0 else "Broad (6-Class)"

            temp_sld = os.path.join(tempfile.gettempdir(), f"saveecobot_style_{self.selected_style_idx}.sld")
            try:
                with open(temp_sld, 'w', encoding='utf-8') as f:
                    f.write(chosen_sld)
                
                message, success = layer.loadSldStyle(temp_sld)
                if success:
                    layer.triggerRepaint()
                    feedback.pushInfo(f"Applied {style_name} SLD style to output layer.")
            except Exception as e:
                feedback.pushWarning(f"Could not apply SLD style: {str(e)}")

        return results


def createInstance():
    return SaveEcoBotPointLoaderAlgorithm()

# Created with Gemini AI, released under CC0 1.0 Universal License
# Copyright 2026 Jan Helebrant, czechrad@suro.cz, www.suro.cz
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE
