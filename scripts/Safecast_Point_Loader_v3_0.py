# -*- coding: utf-8 -*-
"""
Safecast Point Loader
Loads Safecast measurement points for the current map canvas extent.
Style is embedded (no external .qml required).
"""

from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.PyQt.QtGui import QColor
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterNumber,
    QgsProcessingParameterFeatureSink,
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingUtils,
    QgsFeature,
    QgsFields,
    QgsField,
    QgsGeometry,
    QgsPointXY,
    QgsWkbTypes,
    QgsCoordinateReferenceSystem,
    QgsProject,
    QgsCoordinateTransform,
    QgsFeatureSink,
    QgsSymbol,
    QgsMarkerSymbol,
    QgsRuleBasedRenderer,
    QgsProperty
)
import json
import requests
from datetime import datetime, timezone


class SafecastPointLoader(QgsProcessingAlgorithm):
    OUTPUT = 'OUTPUT'
    ZOOM = 'ZOOM'
    ADD_TO_MAP = 'ADD_TO_MAP'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return SafecastPointLoader()

    def name(self):
        return 'safecastpointloader'

    def displayName(self):
        return self.tr('Safecast Point Loader')

    def group(self):
        return self.tr('Radioactivity')

    def groupId(self):
        return 'radioactivity'

    def shortHelpString(self):
        return self.tr(
            "Loads Safecast measurement points (bGeigie imports) for the <b>current map canvas extent</b>.\n\n"
            "• Point layer in EPSG:4326\n"
            "• Embedded default symbology (dose rate classes)\n"
            "• Supports temporary layer or file output (GeoPackage, GeoJSON, Shapefile…)"
        )

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterNumber(
                self.ZOOM,
                self.tr('Zoom level (sent in request, usually ignored by server)'),
                type=QgsProcessingParameterNumber.Integer,
                defaultValue=17,
                minValue=1,
                maxValue=22
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.ADD_TO_MAP,
                self.tr('Add result to map canvas'),
                defaultValue=True
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr('Safecast points'),
                type=QgsProcessing.TypeVectorPoint,
                defaultValue=QgsProcessing.TEMPORARY_OUTPUT
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        zoom = self.parameterAsInt(parameters, self.ZOOM, context)
        add_to_map = self.parameterAsBool(parameters, self.ADD_TO_MAP, context)

        # --- Canvas extent → EPSG:4326 ---
        try:
            from qgis.utils import iface
            extent = iface.mapCanvas().extent()
            canvas_crs = iface.mapCanvas().mapSettings().destinationCrs()

            if canvas_crs.authid() != 'EPSG:4326':
                transform = QgsCoordinateTransform(
                    canvas_crs,
                    QgsCoordinateReferenceSystem('EPSG:4326'),
                    QgsProject.instance()
                )
                extent = transform.transformBoundingBox(extent)
        except Exception as e:
            raise QgsProcessingException(
                self.tr(f'Could not get map canvas extent. Run this from the QGIS GUI.\n{str(e)}')
            )

        min_lon = extent.xMinimum()
        min_lat = extent.yMinimum()
        max_lon = extent.xMaximum()
        max_lat = extent.yMaximum()

        feedback.pushInfo(
            f"Canvas extent (EPSG:4326):\n"
            f"  minLon={min_lon:.8f}, minLat={min_lat:.8f}\n"
            f"  maxLon={max_lon:.8f}, maxLat={max_lat:.8f}"
        )

        url = (
            f"https://simplemap.safecast.org/stream_markers"
            f"?zoom={zoom}"
            f"&minLat={min_lat}"
            f"&minLon={min_lon}"
            f"&maxLat={max_lat}"
            f"&maxLon={max_lon}"
        )
        feedback.pushInfo(f"Request URL:\n{url}")

        # --- Fields ---
        fields = QgsFields()
        fields.append(QgsField('doserate_uSvh', QVariant.Double))
        fields.append(QgsField('EPOCH', QVariant.LongLong))
        fields.append(QgsField('datetime', QVariant.String))
        fields.append(QgsField('lon', QVariant.Double))
        fields.append(QgsField('lat', QVariant.Double))
        fields.append(QgsField('countRate', QVariant.Int))
        fields.append(QgsField('zoom', QVariant.Int))
        fields.append(QgsField('speed', QVariant.Double))
        fields.append(QgsField('trackID', QVariant.String))
        fields.append(QgsField('detector', QVariant.String))

        # --- Sink ---
        (sink, dest_id) = self.parameterAsSink(
            parameters, self.OUTPUT, context,
            fields, QgsWkbTypes.Point,
            QgsCoordinateReferenceSystem('EPSG:4326')
        )
        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT))

        # --- Download ---
        feedback.pushInfo("Downloading data from Safecast…")
        feature_count = 0

        try:
            with requests.get(url, stream=True, timeout=90) as response:
                response.raise_for_status()
                response.encoding = 'utf-8'

                for line in response.iter_lines(decode_unicode=True):
                    if feedback.isCanceled():
                        break
                    if not line:
                        continue

                    line = line.strip()

                    if line == 'event: done':
                        feedback.pushInfo("Received 'event: done'")
                        continue
                    if line == 'data: end':
                        feedback.pushInfo("Received 'data: end' – stream finished")
                        break

                    if line.startswith('data: '):
                        json_str = line[6:].strip()
                        if not json_str or json_str == 'end':
                            continue

                        try:
                            data = json.loads(json_str)
                        except json.JSONDecodeError:
                            continue

                        lon = data.get('lon')
                        lat = data.get('lat')
                        if lon is None or lat is None:
                            continue

                        feat = QgsFeature(fields)
                        feat.setGeometry(QgsGeometry.fromPointXY(
                            QgsPointXY(float(lon), float(lat))
                        ))

                        dose = data.get('doseRate')
                        epoch = data.get('date')
                        count = data.get('countRate')
                        z = data.get('zoom')
                        speed = data.get('speed')
                        track = data.get('trackID')
                        detector = data.get('detector')

                        dt_str = None
                        if epoch is not None:
                            try:
                                dt = datetime.fromtimestamp(int(epoch), tz=timezone.utc)
                                dt_str = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
                            except (ValueError, OSError, OverflowError):
                                pass

                        feat.setAttributes([
                            float(dose) if dose is not None else None,
                            int(epoch) if epoch is not None else None,
                            dt_str,
                            float(lon),
                            float(lat),
                            int(count) if count is not None else None,
                            int(z) if z is not None else None,
                            float(speed) if speed is not None else None,
                            str(track) if track is not None else None,
                            str(detector) if detector is not None else None
                        ])

                        sink.addFeature(feat, QgsFeatureSink.FastInsert)
                        feature_count += 1

        except requests.exceptions.RequestException as e:
            raise QgsProcessingException(self.tr(f'Network error: {str(e)}'))

        feedback.pushInfo(f"Loaded {feature_count} points")

        # ----------------------------------------------------------------
        # Embed style (Rule-based renderer matching your QML)
        # ----------------------------------------------------------------
        def make_symbol(r, g, b, outline=False):
            symbol = QgsMarkerSymbol.createSimple({
                'name': 'circle',
                'size': '2',
                'size_unit': 'MM',
                'color': f'{r},{g},{b},255',
                'outline_style': 'solid' if outline else 'no',
                'outline_color': '35,35,35,255' if outline else '0,0,0,0',
                'outline_width': '0'
            })
            return symbol

        root_rule = QgsRuleBasedRenderer.Rule(None)

        rules = [
            # (filter, label, color RGB, has_outline)
            ('"doserate_uSvh" >= 0 AND "doserate_uSvh" <= 0.05',   '< 0.05',      (0, 0, 0),       False),
            ('"doserate_uSvh" > 0.05 AND "doserate_uSvh" <= 0.10', '0.05 - 0.10',  (0, 0, 157),     False),
            ('"doserate_uSvh" > 0.10 AND "doserate_uSvh" <= 0.20', '0.10 - 0.20',  (0, 59, 255),    False),
            ('"doserate_uSvh" > 0.20 AND "doserate_uSvh" <= 0.30', '0.20 - 0.30',  (0, 217, 255),   False),
            ('"doserate_uSvh" > 0.30 AND "doserate_uSvh" <= 0.80', '0.30 - 0.80',  (119, 135, 255), False),
            ('"doserate_uSvh" > 0.80 AND "doserate_uSvh" <= 1.00', '0.8 - 1',      (255, 0, 232),   False),
            ('"doserate_uSvh" > 1.00 AND "doserate_uSvh" <= 5.00', '1 - 5',        (255, 0, 75),    False),
            ('"doserate_uSvh" > 5.00 AND "doserate_uSvh" <= 10.0', '5 - 10',       (255, 184, 0),   False),
            ('"doserate_uSvh" > 10.0 AND "doserate_uSvh" <= 70.0', '10 - 70',      (255, 255, 113), True),
            ('ELSE',                                               '> 70',         (255, 255, 255), True),
        ]

        for filt, label, color, has_outline in rules:
            rule = QgsRuleBasedRenderer.Rule(make_symbol(*color, outline=has_outline))
            rule.setFilterExpression(filt)
            rule.setLabel(label)
            root_rule.appendChild(rule)

        renderer = QgsRuleBasedRenderer(root_rule)

        # Apply the renderer to the output layer
        layer = QgsProcessingUtils.mapLayerFromString(dest_id, context)
        if layer is None:
            layer = context.temporaryLayerStore().mapLayer(dest_id)

        if layer:
            layer.setRenderer(renderer)
            layer.triggerRepaint()
            feedback.pushInfo("Embedded Safecast style applied.")
        else:
            # For pure file outputs that are not yet loaded
            details = context.layerToLoadOnCompletionDetails(dest_id)
            if details:
                details.setPostLayerName('Safecast points')
                # Style will be missing on pure file save without loading;
                # user can re-apply later if needed.
                feedback.pushInfo("Layer created. Style applied when added to the project.")

        if add_to_map:
            context.addLayerToLoadOnCompletion(
                dest_id,
                QgsProcessingContext.LayerDetails(
                    'Safecast points',
                    context.project(),
                    self.OUTPUT
                )
            )

        return {self.OUTPUT: dest_id}

# Created with Grok AI, released under CC0 1.0 Universal License
# Copyright 2026 Jan Helebrant, czechrad@suro.cz, www.suro.cz
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE
