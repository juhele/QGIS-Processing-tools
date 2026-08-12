# -*- coding: utf-8 -*-
"""
MonRas SVZ Point_Loader
Loads current public dose rate (SVZ) data from the Czech Early Warning Network
(MonRas / SÚJB GeoServer) as an in-memory point layer (EPSG:4326).
Optional save to file.
Offers two built-in styles (CzechRad detailed / SVZ 3-colour).
"""

from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.PyQt.QtGui import QColor
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterString,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink,
    QgsProcessingException,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsFields,
    QgsField,
    QgsWkbTypes,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
    QgsFeatureSink,
    QgsSymbol,
    QgsMarkerSymbol,
    QgsRuleBasedRenderer,
    QgsGraduatedSymbolRenderer,
    QgsRendererRange,
)

import json
import urllib.request
import urllib.error


class MonRasSVZPointLoader(QgsProcessingAlgorithm):
    """
    Loads latest SVZ (Síť včasného zjištění) public dose-rate points
    from https://sujb.gov.cz (MonRas / nuvia_wps:nuvia_svz).
    """

    URL = "URL"
    STYLE = "STYLE"
    OUTPUT = "OUTPUT"

    # Default request covering the Czech Republic (EPSG:3857)
    DEFAULT_URL = (
        "https://sujb.gov.cz/geoserver/ows?"
        "service=WFS&version=1.0.0&request=GetFeature"
        "&typeName=nuvia_wps:nuvia_svz"
        "&outputFormat=application/json"
        "&srsname=EPSG:3857"
        "&bbox=1104362.1846642266,5774358.864775355,"
        "2664900.5541343847,6900734.913585712,EPSG:3857"
    )

    STYLE_OPTIONS = [
        "1 – CzechRad colors (detailed)",
        "2 – SVZ 3-color",
    ]

    def tr(self, string):
        return QCoreApplication.translate("Processing", string)

    def createInstance(self):
        return MonRasSVZPointLoader()

    def name(self):
        return "monras_svz_point_loader"

    def displayName(self):
        return self.tr("MonRas SVZ Point_Loader")

    def group(self):
        return self.tr("Radioactivity")

    def groupId(self):
        return "radioactivity"

    def shortHelpString(self):
        return self.tr(
            "Downloads the latest public dose-rate measurements (SVZ) from the "
            "Czech Early Warning Network (MonRas / SÚJB GeoServer) and creates "
            "a point layer in EPSG:4326.\n\n"
            "• Only features with velicina = 'SVZ' are kept.\n"
            "• Constant / empty fields are discarded.\n"
            "• nSv/h values are converted to µSv/h (PFDE_uSvh).\n\n"
            "Styles:\n"
            "  1 – CzechRad colors (default) … 10-class rule-based, triangles\n"
            "  2 – SVZ 3-color …………… 3-class graduated, triangles\n\n"
            "Default output is a temporary/memory layer."
        )

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterString(
                self.URL,
                self.tr("WFS / GeoJSON URL"),
                defaultValue=self.DEFAULT_URL,
                multiLine=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.STYLE,
                self.tr("Style"),
                options=self.STYLE_OPTIONS,
                defaultValue=0,          # 1 – CzechRad colors
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr("SVZ points"),
                type=QgsProcessing.TypeVectorPoint,
                defaultValue="memory:",
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        url = self.parameterAsString(parameters, self.URL, context).strip()
        style_idx = self.parameterAsEnum(parameters, self.STYLE, context)

        if not url:
            raise QgsProcessingException(self.tr("URL is empty."))

        feedback.pushInfo(self.tr(f"Requesting data from:\n{url}"))

        # ------------------------------------------------------------------
        # 1. Download
        # ------------------------------------------------------------------
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "QGIS-MonRas-SVZ-Loader/1.1"},
            )
            with urllib.request.urlopen(req, timeout=60) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.URLError as e:
            raise QgsProcessingException(self.tr(f"Network error: {e}"))
        except Exception as e:
            raise QgsProcessingException(self.tr(f"Download failed: {e}"))

        # ------------------------------------------------------------------
        # 2. Parse (pure GeoJSON or old JS-callback form)
        # ------------------------------------------------------------------
        text = raw.strip()
        if text.startswith("loadFeatures."):
            start = text.find("(") + 1
            end = text.rfind(")")
            if start <= 0 or end <= start:
                raise QgsProcessingException(self.tr("Cannot extract JSON from JS callback."))
            text = text[start:end]

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise QgsProcessingException(self.tr(f"Invalid JSON: {e}"))

        features_in = data.get("features", [])
        total = len(features_in)
        feedback.pushInfo(self.tr(f"Received {total} features."))

        if total == 0:
            raise QgsProcessingException(self.tr("No features returned by the service."))

        # ------------------------------------------------------------------
        # 3. Output fields
        # ------------------------------------------------------------------
        fields = QgsFields()
        fields.append(QgsField("id", QVariant.String))
        fields.append(QgsField("datumZac", QVariant.String))
        fields.append(QgsField("lokace", QVariant.String))
        fields.append(QgsField("idLokace", QVariant.String))
        fields.append(QgsField("PFDE_uSvh", QVariant.Double))
        fields.append(QgsField("subjekt", QVariant.String))

        # ------------------------------------------------------------------
        # 4. CRS transform 3857 → 4326
        # ------------------------------------------------------------------
        crs_src = QgsCoordinateReferenceSystem("EPSG:3857")
        crs_dst = QgsCoordinateReferenceSystem("EPSG:4326")
        transform = QgsCoordinateTransform(crs_src, crs_dst, QgsProject.instance())

        (sink, dest_id) = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            fields,
            QgsWkbTypes.Point,
            crs_dst,
        )
        if sink is None:
            raise QgsProcessingException(self.tr("Could not create output sink."))

        # ------------------------------------------------------------------
        # 5. Process features
        # ------------------------------------------------------------------
        kept = 0
        for i, feat_in in enumerate(features_in):
            if feedback.isCanceled():
                break

            props = feat_in.get("properties", {})
            if props.get("velicina") != "SVZ":
                continue

            try:
                coords = feat_in["geometry"]["coordinates"]
                pt_3857 = QgsPointXY(float(coords[0]), float(coords[1]))
                pt_4326 = transform.transform(pt_3857)
                geom = QgsGeometry.fromPointXY(pt_4326)
            except Exception as e:
                feedback.pushWarning(self.tr(f"Skipping feature (bad geometry): {e}"))
                continue

            hodnota = None
            jednotka = None
            v1_raw = props.get("values1", "")
            if v1_raw:
                try:
                    v1 = json.loads(v1_raw) if isinstance(v1_raw, str) else v1_raw
                    if isinstance(v1, list) and len(v1) > 0:
                        item = v1[0]
                        hodnota = item.get("hodnota")
                        jednotka = item.get("jednotka")
                except Exception:
                    feedback.pushWarning(
                        self.tr(f"Could not parse values1 for {props.get('lokace')}")
                    )

            pfde_usvh = None
            if (
                hodnota is not None
                and jednotka == "nSv/h"
                and props.get("typDat") == "PFDE"
            ):
                pfde_usvh = float(hodnota) / 1000.0
            elif hodnota is not None:
                pfde_usvh = float(hodnota)

            out = QgsFeature(fields)
            out.setGeometry(geom)
            out.setAttribute("id", feat_in.get("id", ""))
            out.setAttribute("datumZac", props.get("datumZac") or "")
            out.setAttribute("lokace", props.get("lokace") or "")
            out.setAttribute("idLokace", props.get("idLokace") or "")
            out.setAttribute("PFDE_uSvh", pfde_usvh)
            out.setAttribute("subjekt", props.get("subjekt") or "")

            sink.addFeature(out, QgsFeatureSink.FastInsert)
            kept += 1

            if i % 20 == 0:
                feedback.setProgress(int(100 * i / total))

        feedback.pushInfo(self.tr(f"Loaded {kept} SVZ points (EPSG:4326)."))

        # ------------------------------------------------------------------
        # 6. Apply selected style
        # ------------------------------------------------------------------
        layer = context.getMapLayer(dest_id)
        if layer is not None:
            if style_idx == 0:
                self._apply_czechrad_style(layer)
                feedback.pushInfo(self.tr("Applied style: 1 – CzechRad colors"))
            else:
                self._apply_svz3_style(layer)
                feedback.pushInfo(self.tr("Applied style: 2 – SVZ 3-color"))
            layer.triggerRepaint()

        return {self.OUTPUT: dest_id}

    # ----------------------------------------------------------------------
    # Style helpers
    # ----------------------------------------------------------------------
    def _make_triangle(self, color: QColor, size: float = 3.0) -> QgsMarkerSymbol:
        return QgsMarkerSymbol.createSimple({
            "name": "triangle",
            "color": color.name(QColor.HexArgb),
            "outline_color": "0,0,0,255",
            "outline_width": "0",
            "size": str(size),
            "size_unit": "MM",
            "scale_method": "area",
        })

    def _apply_czechrad_style(self, layer):
        """Style 1 – CzechRad detailed (Rule-based, 10 classes, triangles)"""
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
            filt = f'"PFDE_uSvh" > {lower} AND "PFDE_uSvh" <= {upper}' if lower > 0 else \
                   f'"PFDE_uSvh" >= {lower} AND "PFDE_uSvh" <= {upper}'
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

    def _apply_svz3_style(self, layer):
        """Style 2 – SVZ 3-color (Graduated, triangles)"""
        ranges = [
            QgsRendererRange(
                0.0, 0.3,
                self._make_triangle(QColor(0, 255, 0)),
                "< 0,3"
            ),
            QgsRendererRange(
                0.3, 0.5,
                self._make_triangle(QColor(255, 255, 0)),
                "0,3-0,5"
            ),
            QgsRendererRange(
                0.5, 100000000.0,
                self._make_triangle(QColor(170, 0, 0)),
                "> 0,5"
            ),
        ]

        renderer = QgsGraduatedSymbolRenderer("PFDE_uSvh", ranges)
        renderer.setMode(QgsGraduatedSymbolRenderer.Custom)
        layer.setRenderer(renderer)
               
# Created with Grok AI, released under MIT No Attribution License
# Copyright 2026 Jan Helebrant, czechrad@suro.cz, www.suro.cz
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE
