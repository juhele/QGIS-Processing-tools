import json
import time
import urllib.request

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSink,
    QgsProcessingException,
    QgsFields,
    QgsField,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsCoordinateReferenceSystem,
    QgsFeatureSink,
    QgsWkbTypes,
    QgsRuleBasedRenderer,
    QgsMarkerSymbol
)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor


class ShmuRadiationLoaderAlgorithm(QgsProcessingAlgorithm):
    OUTPUT = 'OUTPUT'

    def name(self):
        return 'shmuradiationloader'

    def displayName(self):
        return 'SHMÚ Radiation Point Loader'

    def group(self):
        return 'Radioactivity'

    def groupId(self):
        return 'radioactivity'

    def shortHelpString(self):
        return "Loads current gamma radiation dose rate data from Slovak stationary stations operated by SHMU.sk (Slovenský hydrometeorologický ústav) with custom symbology."

    def createInstance(self):
        return ShmuRadiationLoaderAlgorithm()

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                'SHMÚ Radiation Stations',
                type=QgsProcessing.TypeVectorPoint,
                defaultValue='memory:'
            )
        )

    def _make_triangle(self, color: QColor, size: float = 3.0) -> QgsMarkerSymbol:
        return QgsMarkerSymbol.createSimple({
            "name": "triangle",
            "color": color.name(QColor.HexArgb),
            "outline_color": "0,0,0,255",
            "outline_width": "0.2",
            "size": str(size),
            "size_unit": "MM",
            "scale_method": "area",
        })

    def _apply_czechrad_style(self, layer):
        """Style – CzechRad detailed (Rule-based, 10 classes, triangles)"""
        root = QgsRuleBasedRenderer.Rule(None)

        rules = [
            (0.000, 0.080, QColor(0, 0, 127),   "< 0.08"),
            (0.080, 0.100, QColor(0, 85, 191),  "0.08 - 0.10"),
            (0.100, 0.150, QColor(0, 170, 255), "0.10 - 0.15"),
            (0.150, 0.200, QColor(42, 212, 191),"0.15 - 0.20"),
            (0.200, 0.250, QColor(85, 255, 127),"0.20 - 0.25"),
            (0.250, 0.300, QColor(170, 212, 63),"0.25 - 0.30"),
            (0.300, 0.500, QColor(255, 170, 0), "0.30 - 0.50"),
            (0.500, 1.000, QColor(212, 85, 0),  "0.50 - 1.00"),
            (1.000, 10.00, QColor(170, 0, 0),   "1.00 - 10.00"),
        ]

        for lower, upper, color, label in rules:
            filt = f'"doserate_uSvh" > {lower} AND "doserate_uSvh" <= {upper}' if lower > 0 else \
                   f'"doserate_uSvh" >= {lower} AND "doserate_uSvh" <= {upper}'
            rule = QgsRuleBasedRenderer.Rule(
                self._make_triangle(color),
                filterExp=filt,
                label=label,
            )
            root.appendChild(rule)

        # ELSE (> 10)
        else_rule = QgsRuleBasedRenderer.Rule(
            self._make_triangle(QColor(96, 0, 1)),
            filterExp="ELSE",
            label=">10",
        )
        root.appendChild(else_rule)

        renderer = QgsRuleBasedRenderer(root)
        layer.setRenderer(renderer)

    def processAlgorithm(self, parameters, context, feedback):
        headers = {'User-Agent': 'Mozilla/5.0 (QGIS Processing Script)'}
        station_dates = {}

        if HAS_BS4:
            feedback.pushInfo("Fetching measurement timestamps from main HTML page...")
            html_url = "https://www.shmu.sk/sk/?page=1&id=radioaktivita"
            try:
                req = urllib.request.Request(html_url, headers=headers)
                with urllib.request.urlopen(req) as response:
                    html_content = response.read().decode('utf-8')
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    for row in soup.find_all('tr'):
                        cols = row.find_all(['td', 'th'])
                        if len(cols) >= 2:
                            name_text = cols[0].get_text(strip=True)
                            datetime_text = cols[1].get_text(strip=True)
                            if name_text and datetime_text:
                                station_dates[name_text] = datetime_text
            except Exception as e:
                feedback.reportError(f"Failed to fetch or parse HTML page: {str(e)}")
        else:
            feedback.pushWarning("beautifulsoup4 (bs4) is not installed in QGIS Python environment. Datetime scraping skipped.")

        gps_epoch = int(time.time())
        geojson_url = f"https://www.shmu.sk/popups/meteo/radiacia_get_stations_geojson.php?ac={gps_epoch}"
        feedback.pushInfo(f"Fetching GeoJSON station data (Epoch: {gps_epoch})...")

        try:
            req = urllib.request.Request(geojson_url, headers=headers)
            with urllib.request.urlopen(req) as response:
                geojson_data = json.loads(response.read().decode('utf-8'))
        except Exception as e:
            raise QgsProcessingException(f"Failed to download GeoJSON: {str(e)}")

        fields = QgsFields()
        fields.append(QgsField("station_type", QVariant.String))
        fields.append(QgsField("station_name", QVariant.String))
        fields.append(QgsField("value_nSvh", QVariant.Int))
        fields.append(QgsField("doserate_uSvh", QVariant.Double))
        fields.append(QgsField("datetime", QVariant.String))

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
            raise QgsProcessingException("Could not create output sink.")

        features = geojson_data.get('features', [])
        total = len(features) if features else 1

        for i, feature in enumerate(features):
            if feedback.isCanceled():
                break

            props = feature.get('properties', {})
            geom = feature.get('geometry', {})
            coords = geom.get('coordinates', [])

            if len(coords) < 2:
                continue

            lon, lat = coords[0], coords[1]
            station_name = props.get('name', '')
            raw_val = props.get('value', None)

            doserate_uSvh = round(float(raw_val) / 1000.0, 4) if raw_val is not None else None
            measurement_datetime = station_dates.get(station_name, "N/A")

            qgs_feat = QgsFeature(fields)
            qgs_feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(lon, lat)))
            qgs_feat.setAttributes([
                "SHMU.sk",
                station_name,
                raw_val,
                doserate_uSvh,
                measurement_datetime
            ])

            sink.addFeature(qgs_feat, QgsFeatureSink.FastInsert)
            feedback.setProgress(int(((i + 1) / total) * 100))

        # Apply style directly using context map layer handle
        layer = context.getMapLayer(dest_id)
        if layer is not None:
            self._apply_czechrad_style(layer)
            layer.triggerRepaint()
            feedback.pushInfo("Applied CzechRad rule-based symbology.")

        feedback.pushInfo("Loading completed successfully.")
        return {self.OUTPUT: dest_id}

# Created with Gemini AI, released under CC0 1.0 Universal License
# Copyright 2026 Jan Helebrant, czechrad@suro.cz, www.suro.cz
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE
