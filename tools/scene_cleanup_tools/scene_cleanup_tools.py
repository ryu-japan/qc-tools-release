# -*- coding: utf-8 -*-
"""Scene Cleanup Tools - Maya scene cleanup checker.

Checks 18 items related to scene state, structure and settings.
Compatible with Maya 2018+ (Python 2.7 / 3, PySide2 / PySide6).
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import sys
import os
import re
import logging
import tempfile
import atexit
from functools import partial

try:
    from PySide6 import QtCore, QtGui, QtWidgets
    from shiboken6 import wrapInstance
except ImportError:
    from PySide2 import QtCore, QtGui, QtWidgets
    from shiboken2 import wrapInstance

import maya.cmds as cmds
import maya.OpenMayaUI as omui
# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
__VERSION__ = "0.17.0"
WINDOW_TITLE = "Scene Cleanup Tools"
WINDOW_OBJECT_NAME = "sceneCleanupToolsWindow"
RESULTS_OBJECT_NAME = "sceneCleanupResultsWindow"
HELP_DIALOG_OBJECT_NAME = "sceneCleanupHelpDialog"
WINDOW_WIDTH = 420
WINDOW_HEIGHT = 735

log = logging.getLogger(WINDOW_TITLE)

# --- Arrow icon generation for dark-theme QSS ---
_ARROW_ICON_DIR = ""
_ARROW_ICON_FILES = []

def _create_arrow_icons():
    """Generate small triangle PNG icons for ComboBox/SpinBox arrows."""
    global _ARROW_ICON_DIR, _ARROW_ICON_FILES
    try:
        icon_dir = os.path.join(tempfile.gettempdir(), "sct_icons")
        if not os.path.exists(icon_dir):
            os.makedirs(icon_dir)
        arrow_color = QtGui.QColor("#aaaaaa")
        size = 10
        for name, pts in [("arrow_down.png", [(1, 2), (9, 2), (5, 8)]),
                           ("arrow_up.png", [(1, 8), (9, 8), (5, 2)])]:
            fpath = os.path.join(icon_dir, name)
            pm = QtGui.QPixmap(size, size)
            pm.fill(QtCore.Qt.transparent)
            p = QtGui.QPainter(pm)
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            p.setBrush(arrow_color)
            p.setPen(QtCore.Qt.NoPen)
            p.drawPolygon(QtGui.QPolygon([QtCore.QPoint(*pt) for pt in pts]))
            p.end()
            pm.save(fpath)
            _ARROW_ICON_FILES.append(fpath)
        return icon_dir
    except Exception:
        return ""

def _cleanup_arrow_icons():
    for f in _ARROW_ICON_FILES:
        try:
            if os.path.exists(f):
                os.remove(f)
        except Exception:
            pass
    if _ARROW_ICON_DIR:
        try:
            os.rmdir(_ARROW_ICON_DIR)
        except Exception:
            pass

_ARROW_ICON_DIR = _create_arrow_icons()
atexit.register(_cleanup_arrow_icons)
_ARROW_CSS_DIR = _ARROW_ICON_DIR.replace("\\", "/") if _ARROW_ICON_DIR else ""

# Dark theme palette (QC Hub / UV QC Tools compatible)
# bg=#2b2b2b  ctrl=#3c3c3c  text=#e0e0e0
# border=#555555  accent=#7aa2f7  hover=#505050
_QSS = (
    "QWidget#sceneCleanupToolsWindow {"
    "  background-color: #2b2b2b;"
    "}"
    "QLabel {"
    "  color: #e0e0e0;"
    "}"
    "QLabel:disabled {"
    "  color: #666666;"
    "}"
    "QPushButton {"
    "  background-color: #3c3c3c;"
    "  color: #e0e0e0;"
    "  border: 1px solid #555555;"
    "  border-radius: 6px;"
    "  padding: 4px 12px;"
    "  font-size: 13px;"
    "  font-weight: bold;"
    "}"
    "QPushButton:hover {"
    "  background-color: #505050;"
    "  border: 1px solid #7aa2f7;"
    "}"
    "QPushButton:pressed {"
    "  background-color: #7aa2f7;"
    "  color: #1a1a1a;"
    "}"
    "QPushButton:disabled {"
    "  background-color: #2b2b2b;"
    "  color: #666666;"
    "  border: 1px solid #3a3a3a;"
    "}"
    "QGroupBox {"
    "  border: 1px solid #555555;"
    "  border-radius: 4px;"
    "  margin-top: 6px;"
    "  padding: 10px 6px 6px 6px;"
    "  background-color: #353535;"
    "  color: #e0e0e0;"
    "  font-weight: bold;"
    "}"
    "QGroupBox::title {"
    "  subcontrol-origin: margin;"
    "  left: 8px;"
    "  padding: 0 4px;"
    "  color: #e0e0e0;"
    "  font-size: 13px;"
    "}"
    "QComboBox {"
    "  background-color: #3c3c3c;"
    "  color: #e0e0e0;"
    "  border: 1px solid #555555;"
    "  border-radius: 4px;"
    "  padding: 4px 8px;"
    "}"
    "QComboBox QAbstractItemView {"
    "  background-color: #3c3c3c;"
    "  color: #e0e0e0;"
    "  selection-background-color: #505050;"
    "}"
    "QComboBox::drop-down {"
    "  border: none;"
    "  background: transparent;"
    "  width: 20px;"
    "}"
    "QComboBox::down-arrow {"
    "  image: url(" + _ARROW_CSS_DIR + "/arrow_down.png);"
    "  width: 8px;"
    "  height: 8px;"
    "}"
    "QCheckBox {"
    "  color: #e0e0e0;"
    "  spacing: 6px;"
    "}"
    "QCheckBox::indicator {"
    "  width: 14px;"
    "  height: 14px;"
    "  border: 1px solid #555555;"
    "  border-radius: 3px;"
    "  background-color: #3c3c3c;"
    "}"
    "QCheckBox::indicator:checked {"
    "  background-color: #7aa2f7;"
    "  border: 1px solid #7aa2f7;"
    "}"
    "QRadioButton {"
    "  color: #e0e0e0;"
    "  spacing: 6px;"
    "}"
    "QRadioButton::indicator {"
    "  width: 14px;"
    "  height: 14px;"
    "  border: 1px solid #555555;"
    "  border-radius: 7px;"
    "  background-color: #3c3c3c;"
    "}"
    "QRadioButton::indicator:checked {"
    "  background-color: #7aa2f7;"
    "  border: 1px solid #7aa2f7;"
    "}"
    "QProgressBar {"
    "  background-color: #3c3c3c;"
    "  border: 1px solid #555555;"
    "  border-radius: 4px;"
    "  color: #ffffff;"
    "  text-align: center;"
    "}"
    "QProgressBar::chunk {"
    "  background-color: #7aa2f7;"
    "  border-radius: 3px;"
    "}"
    "QTreeWidget {"
    "  background-color: #2b2b2b;"
    "  color: #e0e0e0;"
    "  border: 1px solid #555555;"
    "}"
    "QTreeWidget::item:selected {"
    "  background-color: #505050;"
    "}"
    "QListWidget {"
    "  background-color: #2b2b2b;"
    "  color: #e0e0e0;"
    "  border: 1px solid #555555;"
    "}"
    "QListWidget::item:selected {"
    "  background-color: #505050;"
    "}"
    "QListWidget::item:hover {"
    "  background-color: #3c3c3c;"
    "}"
    "QSplitter::handle {"
    "  background-color: #555555;"
    "  width: 1px;"
    "}"
    "QTextBrowser {"
    "  background-color: #2b2b2b;"
    "  color: #e0e0e0;"
    "  border: 1px solid #555555;"
    "}"
    "QLineEdit {"
    "  background-color: #3c3c3c;"
    "  color: #e0e0e0;"
    "  border: 1px solid #555555;"
    "  border-radius: 4px;"
    "  padding: 2px 4px;"
    "}"
    "QScrollArea {"
    "  background-color: #2b2b2b;"
    "  border: none;"
    "}"
    "QScrollArea > QWidget {"
    "  background-color: #2b2b2b;"
    "}"
    "QWidget#scrollContent {"
    "  background-color: #2b2b2b;"
    "}"
    "QMessageBox QPushButton {"
    "  min-width: 80px;"
    "}"
    "QMessageBox QLabel {"
    "  font-size: 14px;"
    "}"
    "QPushButton[cssClass=\"secondary\"] {"
    "  font-weight: normal;"
    "  font-size: 11px;"
    "  background-color: #3c3c3c;"
    "  border: 1px solid #666666;"
    "  padding: 2px 8px;"
    "}"
    "QPushButton[cssClass=\"secondary\"]:hover {"
    "  background-color: #3c3c3c;"
    "  border: 1px solid #7aa2f7;"
    "}"
    "QPushButton[cssClass=\"secondary\"]:pressed {"
    "  background-color: #7aa2f7;"
    "  color: #1a1a1a;"
    "}"
    "QPushButton[cssClass=\"accent\"] {"
    "  background-color: #4D6594;"
    "  border: 1px solid #5B75AB;"
    "}"
    "QPushButton[cssClass=\"accent\"]:hover {"
    "  background-color: #5A77B0;"
    "  border: 1px solid #7aa2f7;"
    "}"
    "QPushButton[cssClass=\"accent\"]:pressed {"
    "  background-color: #7aa2f7;"
    "  color: #1a1a1a;"
    "}"
    "QPushButton[cssClass=\"prep\"] {"
    "  background-color: #333333;"
    "  border: 1px solid #666666;"
    "  font-weight: normal;"
    "}"
    "QPushButton[cssClass=\"prep\"]:hover {"
    "  background-color: #3c3c3c;"
    "  border: 1px solid #7aa2f7;"
    "}"
    "QPushButton[cssClass=\"prep\"]:pressed {"
    "  background-color: #7aa2f7;"
    "  color: #1a1a1a;"
    "}"
    "QLabel[cssClass=\"status\"] {"
    "  font-size: 11px;"
    "  color: #888888;"
    "}"
)
# ---------------------------------------------------------------------------
# [010] i18n — Translation dictionary & tr() function
# ---------------------------------------------------------------------------

_TR = {
    # -- Window --
    "results_title":         {"en": "Check Results",                 "ja": "\u30c1\u30a7\u30c3\u30af\u7d50\u679c"},

    # -- Top bar --
    "lang_label":            {"en": "Language / \u8a00\u8a9e",           "ja": "Language / \u8a00\u8a9e"},
    "lang_en_label":         {"en": "English",                      "ja": "English"},
    "lang_ja_label":         {"en": "\u65e5\u672c\u8a9e",                      "ja": "\u65e5\u672c\u8a9e"},
    "btn_howto":             {"en": "How to Use",                    "ja": "\u4f7f\u3044\u65b9"},

    # -- Category headers --
    "cat_geometry":          {"en": "Geometry",                      "ja": "\u30b8\u30aa\u30e1\u30c8\u30ea"},
    "cat_unused":            {"en": "Unused",                        "ja": "\u672a\u4f7f\u7528\u30fb\u4e0d\u8981\u30ce\u30fc\u30c9"},
    "cat_scene_env":         {"en": "Scene Environment",             "ja": "\u30b7\u30fc\u30f3\u74b0\u5883"},
    "btn_all_on":            {"en": "All ON",                        "ja": "\u3059\u3079\u3066ON"},
    "btn_all_off":           {"en": "All OFF",                       "ja": "\u3059\u3079\u3066OFF"},

    # -- Check items: Geometry (7) --
    "chk_history":           {"en": "Remaining History",             "ja": "\u6b8b\u5b58\u30d2\u30b9\u30c8\u30ea"},
    "chk_transform":         {"en": "Unfreezed Transforms",          "ja": "\u672a\u30d5\u30ea\u30fc\u30ba\u30c8\u30e9\u30f3\u30b9\u30d5\u30a9\u30fc\u30e0"},
    "chk_vertex_tweaks":     {"en": "Vertex Tweaks",                 "ja": "\u9802\u70b9Tweaks\u6b8b\u7559"},
    "chk_instances":         {"en": "Remaining Instances",           "ja": "\u30a4\u30f3\u30b9\u30bf\u30f3\u30b9\u6b8b\u5b58"},
    "chk_smooth_preview":    {"en": "Smooth Mesh Preview",           "ja": "\u30b9\u30e0\u30fc\u30b9\u30e1\u30c3\u30b7\u30e5\u30d7\u30ec\u30d3\u30e5\u30fc"},
    "chk_shape_suffix":      {"en": "Shape Suffix",                  "ja": "Shape Suffix \u30c1\u30a7\u30c3\u30af"},
    "chk_duplicate_names":   {"en": "Duplicate Names",               "ja": "\u91cd\u8907\u540d\u30c1\u30a7\u30c3\u30af"},

    # -- Check items: Unused (6) --
    "chk_unused_nodes":      {"en": "Empty Groups / Empty Shapes",               "ja": "\u7a7a\u30b0\u30eb\u30fc\u30d7 / \u7a7a\u30b7\u30a7\u30a4\u30d7"},
    "chk_intermediate_objects": {"en": "Intermediate Objects",       "ja": "\u4e2d\u9593\u30aa\u30d6\u30b8\u30a7\u30af\u30c8"},
    "chk_unused_mat":        {"en": "Unused Materials / Textures",   "ja": "\u672a\u4f7f\u7528\u30de\u30c6\u30ea\u30a2\u30eb / \u30c6\u30af\u30b9\u30c1\u30e3"},
    "chk_unused_layers":     {"en": "Unused Layers",                 "ja": "\u672a\u4f7f\u7528\u30ec\u30a4\u30e4\u30fc"},
    "chk_empty_sets":        {"en": "Empty Object Sets",              "ja": "\u7a7a\u30aa\u30d6\u30b8\u30a7\u30af\u30c8\u30bb\u30c3\u30c8"},
    "chk_namespaces":        {"en": "Empty Namespaces",              "ja": "\u7a7a\u30cd\u30fc\u30e0\u30b9\u30da\u30fc\u30b9"},

    # -- Check items: Scene Environment (5) --
    "chk_scene_units":       {"en": "Scene Units / Up-Axis",         "ja": "\u30b7\u30fc\u30f3\u5358\u4f4d / Up\u8ef8"},
    "chk_unknown_nodes":     {"en": "Unknown Nodes",                 "ja": "\u4e0d\u660e\u30ce\u30fc\u30c9"},
    "chk_referenced_nodes":  {"en": "Referenced Nodes",              "ja": "\u30ea\u30d5\u30a1\u30ec\u30f3\u30b9\u30ce\u30fc\u30c9\u6b8b\u5b58"},
    "chk_naming_check":      {"en": "Naming Check",                  "ja": "\u547d\u540d\u898f\u5247\u30c1\u30a7\u30c3\u30af"},

    "chk_file_paths":        {"en": "File Paths",                    "ja": "ファイルパスチェック"},
    "file_paths_scene":      {"en": "Scene",                         "ja": "シーン"},
    "file_paths_tex":        {"en": "Tex",                           "ja": "テクスチャ"},
    "file_paths_relative":   {"en": "Relative",                      "ja": "相対パス"},
    "file_paths_absolute":   {"en": "Absolute",                      "ja": "絶対パス"},
    "file_paths_missing":    {"en": "Missing File",                  "ja": "欠損ファイル検出"},

    # -- Naming params --
    "naming_regex":          {"en": "Regex pattern:",                "ja": "\u6b63\u898f\u8868\u73fe\u30d1\u30bf\u30fc\u30f3:"},

    # -- Scene units params --
    "unit_label":            {"en": "Unit:",                         "ja": "\u5358\u4f4d:"},
    "upaxis_label":          {"en": "Up Axis:",                      "ja": "Up\u8ef8:"},

    # -- Buttons --
    "btn_check":             {"en": "Check",                        "ja": "\u30c1\u30a7\u30c3\u30af"},
    "btn_cancel":            {"en": "\u2715 Cancel",                 "ja": "\u2715 \u30ad\u30e3\u30f3\u30bb\u30eb"},
    "btn_close":             {"en": "Close",                         "ja": "\u9589\u3058\u308b"},
    "btn_select_all":        {"en": "Select All",                    "ja": "\u5168\u9078\u629e"},
    "btn_copy_report":       {"en": "Copy Report",                   "ja": "\u30ec\u30dd\u30fc\u30c8\u3092\u30b3\u30d4\u30fc"},
    "btn_send_report":       {"en": "Send Report",                   "ja": "\u30ec\u30dd\u30fc\u30c8\u3092\u9001\u4fe1"},

    # -- Status --
    "status_ready":          {"en": "Standby",                       "ja": "\u5f85\u6a5f\u4e2d"},
    "status_running":        {"en": "Checking... {cur}/{total}",     "ja": "\u30c1\u30a7\u30c3\u30af\u4e2d... {cur}/{total}"},
    "status_done":           {"en": "Done. {issues} issue(s) found.","ja": "\u5b8c\u4e86\u3002{issues} \u4ef6\u306e\u554f\u984c\u3092\u691c\u51fa\u3002"},
    "status_cancelled":      {"en": "Cancelled.",                    "ja": "\u30ad\u30e3\u30f3\u30bb\u30eb\u3057\u307e\u3057\u305f\u3002"},
    "report_copied":         {"en": "Report copied to clipboard.",   "ja": "\u30ec\u30dd\u30fc\u30c8\u3092\u30af\u30ea\u30c3\u30d7\u30dc\u30fc\u30c9\u306b\u30b3\u30d4\u30fc\u3057\u307e\u3057\u305f\u3002"},

    # -- Detail messages --
    "detail_unused_display_layer":  {"en": "Unused display layer",              "ja": "\u672a\u4f7f\u7528\u306e\u30c7\u30a3\u30b9\u30d7\u30ec\u30a4\u30ec\u30a4\u30e4\u30fc"},
    "detail_unused_render_layer":   {"en": "Unused render layer",               "ja": "\u672a\u4f7f\u7528\u306e\u30ec\u30f3\u30c0\u30fc\u30ec\u30a4\u30e4\u30fc"},
    "detail_unused_animation_layer":{"en": "Unused animation layer",            "ja": "\u672a\u4f7f\u7528\u306e\u30a2\u30cb\u30e1\u30fc\u30b7\u30e7\u30f3\u30ec\u30a4\u30e4\u30fc"},
    "detail_loaded":                {"en": "Loaded: {0}",                       "ja": "\u30ed\u30fc\u30c9\u6e08\u307f: {0}"},
    "detail_unloaded":              {"en": "Unloaded: {0}",                     "ja": "\u672a\u30ed\u30fc\u30c9: {0}"},
    "detail_ref_path_unknown":      {"en": "Reference node (path unknown)",     "ja": "\u30ea\u30d5\u30a1\u30ec\u30f3\u30b9\u30ce\u30fc\u30c9\uff08\u30d1\u30b9\u4e0d\u660e\uff09"},
    "detail_vertex_tweaks":          {"en": "{0}/{1} vertices have tweaks",       "ja": "{0}/{1} \u9802\u70b9\u306bTweaks\u3042\u308a"},
    "detail_duplicate_name":         {"en": "Duplicate name ({0} nodes)",         "ja": "\u91cd\u8907\u540d\uff08{0} \u30ce\u30fc\u30c9\uff09"},
    "detail_shape_suffix":           {"en": "Suffix mismatch",                    "ja": "\u30b5\u30d5\u30a3\u30c3\u30af\u30b9\u4e0d\u4e00\u81f4"},
    "detail_history":                {"en": "Has construction history",            "ja": "\u30d2\u30b9\u30c8\u30ea\u3042\u308a"},
    "detail_transform":              {"en": "Not frozen",                          "ja": "\u672a\u30d5\u30ea\u30fc\u30ba"},
    "detail_instances":              {"en": "{0} instanced shape(s)",              "ja": "\u30a4\u30f3\u30b9\u30bf\u30f3\u30b9 {0}\u4ef6"},
    "detail_smooth_preview":         {"en": "Smooth preview enabled",              "ja": "\u30b9\u30e0\u30fc\u30b9\u30d7\u30ec\u30d3\u30e5\u30fc ON"},
    "detail_empty_group":            {"en": "Empty group",                         "ja": "\u7a7a\u30b0\u30eb\u30fc\u30d7"},
    "detail_empty_mesh":             {"en": "Empty mesh",                          "ja": "\u7a7a\u30e1\u30c3\u30b7\u30e5"},
    "detail_intermediate":           {"en": "Intermediate object exists",          "ja": "\u4e2d\u9593\u30aa\u30d6\u30b8\u30a7\u30af\u30c8\u3042\u308a"},
    "detail_unused_mat":             {"en": "Unused material ({0})",               "ja": "\u672a\u4f7f\u7528\u30de\u30c6\u30ea\u30a2\u30eb ({0})"},
    "detail_unused_texture":         {"en": "Unused texture ({0})",                "ja": "\u672a\u4f7f\u7528\u30c6\u30af\u30b9\u30c1\u30e3 ({0})"},
    "detail_unused_utility":         {"en": "Unused utility ({0})",                "ja": "\u672a\u4f7f\u7528\u30e6\u30fc\u30c6\u30a3\u30ea\u30c6\u30a3 ({0})"},
    "detail_empty_set":              {"en": "Empty set",                           "ja": "\u7a7a\u30bb\u30c3\u30c8"},
    "detail_empty_namespace":        {"en": "Empty namespace",                     "ja": "\u7a7a\u30cd\u30fc\u30e0\u30b9\u30da\u30fc\u30b9"},
    "detail_unit_mismatch":          {"en": "Unit: {0} (expected: {1})",           "ja": "\u5358\u4f4d: {0}\uff08\u671f\u5f85\u5024: {1}\uff09"},
    "detail_upaxis_mismatch":        {"en": "Up-axis: {0} (expected: {1})",        "ja": "Up\u8ef8: {0}\uff08\u671f\u5f85\u5024: {1}\uff09"},
    "detail_unknown_node":           {"en": "Unknown node (origType: {0})",        "ja": "\u4e0d\u660e\u30ce\u30fc\u30c9\uff08\u5143\u30bf\u30a4\u30d7: {0}\uff09"},
    "detail_unknown_node_notype":    {"en": "Unknown node",                        "ja": "\u4e0d\u660e\u30ce\u30fc\u30c9"},
    "detail_naming_mismatch":        {"en": "Name does not match pattern: {0}",    "ja": "\u547d\u540d\u898f\u5247\u306b\u4e0d\u4e00\u81f4: {0}"},

    "detail_wrong_folder":           {"en": "Wrong folder name",                   "ja": "フォルダ名不一致"},
    "detail_expected_relative":      {"en": "Absolute path detected",              "ja": "絶対パスを検出"},
    "detail_expected_absolute":      {"en": "Relative path detected",              "ja": "相対パスを検出"},
    "detail_missing_file":           {"en": "File not found",                      "ja": "ファイル未検出"},

    # -- Results --
    "results_summary":       {"en": "{count} issue(s)",              "ja": "{count} \u4ef6"},
    "results_pass":          {"en": "PASS",                          "ja": "OK"},
    "results_node_col":      {"en": "Node",                          "ja": "\u30ce\u30fc\u30c9"},
    "results_detail_col":    {"en": "Detail",                        "ja": "\u8a73\u7d30"},
    "results_all":           {"en": "All",                           "ja": "\u3059\u3079\u3066"},
    "results_no_issues":     {"en": "No issues found.",              "ja": "\u554f\u984c\u306a\u3057"},
}

_current_lang = "en"


def tr(key, **kwargs):
    """Return translated string for *key* in the active language."""
    entry = _TR.get(key, {})
    text = entry.get(_current_lang, entry.get("en", key))
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text


def set_language(lang):
    """Set active language ('en' or 'ja')."""
    global _current_lang
    _current_lang = lang
# ---------------------------------------------------------------------------
# [011] help_content — How to Use dialog HTML
# ---------------------------------------------------------------------------

_HELP_HTML = {
    "en": """
<h2>Scene Cleanup Tools \u2014 How to Use</h2>
<h3>Check Scope</h3>
<p>All mesh nodes in the scene are checked automatically.</p>
<p><i>Note: Scene-wide items (Empty Groups, Unused Materials, Unused Layers,
Empty Sets, Namespaces, Unknown Nodes, Referenced Nodes, Duplicate Names,
Scene Units) always scan the entire scene.</i></p>
<h3>Check Items (17)</h3>
<p><b>Geometry (7)</b> \u2014 History, transforms, vertex tweaks, instances,
smooth mesh preview, shape suffix, duplicate names.</p>
<p><b>Unused (6)</b> \u2014 Empty groups/shapes, intermediate objects,
unused materials, unused layers, empty sets, namespaces.</p>
<p><b>Scene Environment (4)</b> \u2014 Scene units, unknown nodes,
referenced nodes, naming check.</p>
<p>Each item can be toggled ON/OFF. Use <b>All ON</b> / <b>All OFF</b> /
<b>Reset to Defaults</b> for bulk control.</p>
<h3>Running a Check</h3>
<p>Click <b>Check</b> to start. A results window shows detected issues.</p>
<h3>Sending a Report</h3>
<p>Click <b>Send Report</b> to copy check results to the clipboard.</p>
""",
    "ja": """
<h2>\u30b7\u30fc\u30f3\u6574\u7406\u30c4\u30fc\u30eb \u2014 \u4f7f\u3044\u65b9</h2>
<h3>\u30c1\u30a7\u30c3\u30af\u7bc4\u56f2</h3>
<p>\u30b7\u30fc\u30f3\u5185\u306e\u5168\u30e1\u30c3\u30b7\u30e5\u30ce\u30fc\u30c9\u304c\u81ea\u52d5\u7684\u306b\u30c1\u30a7\u30c3\u30af\u5bfe\u8c61\u306b\u306a\u308a\u307e\u3059\u3002</p>
<p><i>\u203b \u30b7\u30fc\u30f3\u5168\u4f53\u9805\u76ee\uff08\u7a7a\u30b0\u30eb\u30fc\u30d7\u3001\u672a\u4f7f\u7528\u30de\u30c6\u30ea\u30a2\u30eb\u3001\u672a\u4f7f\u7528\u30ec\u30a4\u30e4\u30fc\u3001\u7a7a\u30bb\u30c3\u30c8\u3001\u30cd\u30fc\u30e0\u30b9\u30da\u30fc\u30b9\u3001\u4e0d\u660e\u30ce\u30fc\u30c9\u3001\u30ea\u30d5\u30a1\u30ec\u30f3\u30b9\u30ce\u30fc\u30c9\u3001\u91cd\u8907\u540d\u3001\u30b7\u30fc\u30f3\u5358\u4f4d\uff09\u306f\u5e38\u306b\u30b7\u30fc\u30f3\u5168\u4f53\u3092\u30b9\u30ad\u30e3\u30f3\u3057\u307e\u3059\u3002</i></p>
<h3>\u30c1\u30a7\u30c3\u30af\u9805\u76ee\uff0817\uff09</h3>
<p><b>\u30b8\u30aa\u30e1\u30c8\u30ea\uff087\uff09</b> \u2014 \u30d2\u30b9\u30c8\u30ea\u3001\u30c8\u30e9\u30f3\u30b9\u30d5\u30a9\u30fc\u30e0\u3001\u9802\u70b9Tweaks\u3001\u30a4\u30f3\u30b9\u30bf\u30f3\u30b9\u3001\u30b9\u30e0\u30fc\u30b9\u30d7\u30ec\u30d3\u30e5\u30fc\u3001Shape Suffix\u3001\u91cd\u8907\u540d\u3002</p>
<p><b>\u672a\u4f7f\u7528\u30fb\u4e0d\u8981\u30ce\u30fc\u30c9\uff086\uff09</b> \u2014 \u7a7a\u30b0\u30eb\u30fc\u30d7/\u7a7a\u30b7\u30a7\u30a4\u30d7\u3001\u4e2d\u9593\u30aa\u30d6\u30b8\u30a7\u30af\u30c8\u3001\u672a\u4f7f\u7528\u30de\u30c6\u30ea\u30a2\u30eb\u3001\u672a\u4f7f\u7528\u30ec\u30a4\u30e4\u30fc\u3001\u7a7a\u30bb\u30c3\u30c8\u3001\u30cd\u30fc\u30e0\u30b9\u30da\u30fc\u30b9\u3002</p>
<p><b>\u30b7\u30fc\u30f3\u74b0\u5883\uff084\uff09</b> \u2014 \u30b7\u30fc\u30f3\u5358\u4f4d\u3001\u4e0d\u660e\u30ce\u30fc\u30c9\u3001\u30ea\u30d5\u30a1\u30ec\u30f3\u30b9\u30ce\u30fc\u30c9\u3001\u547d\u540d\u30c1\u30a7\u30c3\u30af\u3002</p>
<p>\u5404\u9805\u76ee\u306f\u500b\u5225\u306bON/OFF\u5207\u308a\u66ff\u3048\u53ef\u80fd\u3002<b>\u3059\u3079\u3066ON</b> / <b>\u3059\u3079\u3066OFF</b> / <b>\u30c7\u30d5\u30a9\u30eb\u30c8\u306b\u623b\u3059</b>\u3067\u4e00\u62ec\u64cd\u4f5c\u3002</p>
<h3>\u30c1\u30a7\u30c3\u30af\u306e\u5b9f\u884c</h3>
<p><b>\u30c1\u30a7\u30c3\u30af</b>\u30dc\u30bf\u30f3\u3067\u958b\u59cb\u3002\u7d50\u679c\u30a6\u30a3\u30f3\u30c9\u30a6\u306b\u691c\u51fa\u3055\u308c\u305f\u554f\u984c\u304c\u8868\u793a\u3055\u308c\u307e\u3059\u3002</p>
<h3>\u30ec\u30dd\u30fc\u30c8\u306e\u9001\u4fe1</h3>
<p><b>\u30ec\u30dd\u30fc\u30c8\u3092\u9001\u4fe1</b>\u30dc\u30bf\u30f3\u3067\u30c1\u30a7\u30c3\u30af\u7d50\u679c\u3092\u30af\u30ea\u30c3\u30d7\u30dc\u30fc\u30c9\u306b\u30b3\u30d4\u30fc\u3002</p>
""",
}
# ---------------------------------------------------------------------------
# [020] utils — Common utilities
# ---------------------------------------------------------------------------

def get_maya_main_window():
    """Return the Maya main window as a QWidget."""
    ptr = omui.MQtUtil.mainWindow()
    if ptr is not None:
        return wrapInstance(int(ptr), QtWidgets.QWidget)
    return None


def collect_meshes():
    """Collect all mesh transform nodes in the scene.

    Returns:
        list[str]: Long names of mesh transform nodes.
    """
    all_meshes = cmds.ls(long=True, type="mesh") or []
    return list(set(cmds.listRelatives(all_meshes, allParents=True, fullPath=True) or []))


def collect_transform_nodes():
    """Collect all transform nodes in the scene.

    Shape nodes are excluded; their naming is validated
    by check_shape_suffix instead.

    Returns:
        list[str]: Long names of transform nodes.
    """
    return cmds.ls(dag=True, long=True, type="transform") or []


def get_top_nodes(nodes):
    """Return unique top-level transform ancestors for *nodes*."""
    tops = set()
    for n in nodes:
        parts = n.split("|")
        if len(parts) > 1:
            tops.add("|".join(parts[:2]))
    return sorted(tops)
# ---------------------------------------------------------------------------
# [100] geometry — Check functions A: Geometry
# ---------------------------------------------------------------------------
# Each function signature: check_<key>(targets) -> list[dict]
#   targets: list of mesh transform long-names
#   returns: list of {"node": str, "detail": str}
# Exception: check_duplicate_names is scene-wide (no targets parameter).


def check_history(targets):
    """Check for remaining construction history."""
    results = []
    for target in targets:
        hist = cmds.listHistory(target, pdo=True)
        if hist is None:
            continue
        shapes = cmds.listRelatives(target, shapes=True, fullPath=True) or []
        hist = [h for h in hist if h not in shapes]
        if hist:
            results.append({"node": target, "detail": tr("detail_history")})
    return results


def check_transform(targets):
    """Check for unfreezed transforms."""
    results = []
    for target in targets:
        try:
            t = cmds.getAttr(target + ".translate")[0]
            r = cmds.getAttr(target + ".rotate")[0]
            s = cmds.getAttr(target + ".scale")[0]
        except Exception as exc:
            log.warning("check_transform: %s skipped: %s", target, exc)
            continue
        non_default = (any(abs(v) > 1e-6 for v in t)
                       or any(abs(v) > 1e-6 for v in r)
                       or any(abs(v - d) > 1e-6 for v, d in zip(s, (1, 1, 1))))
        if non_default:
            results.append({"node": target, "detail": tr("detail_transform")})
    return results


def check_vertex_tweaks(targets):
    """Check for remaining vertex tweaks (pnts attribute values)."""
    results = []
    for target in targets:
        shapes = cmds.listRelatives(target, shapes=True, fullPath=True,
                                    type="mesh")
        if not shapes:
            continue
        tweaks_found = 0
        total_verts = 0
        for shape in shapes:
            if cmds.getAttr(shape + ".intermediateObject"):
                continue
            try:
                pnts_size = cmds.getAttr(shape + ".pnts", size=True)
            except Exception as exc:
                log.warning("check_vertex_tweaks: %s skipped: %s", shape, exc)
                continue
            if not pnts_size:
                continue
            try:
                pnts = cmds.getAttr(shape + ".pnts[*]")
            except Exception as exc:
                log.warning("check_vertex_tweaks: %s pnts read failed: %s",
                            shape, exc)
                continue
            if pnts is None:
                continue
            total_verts += len(pnts)
            for pt in pnts:
                if (abs(pt[0]) > 1e-7 or abs(pt[1]) > 1e-7
                        or abs(pt[2]) > 1e-7):
                    tweaks_found += 1
        if tweaks_found > 0:
            results.append({
                "node": target,
                "detail": tr("detail_vertex_tweaks").format(
                    tweaks_found, total_verts),
            })
    return results


def check_instances(targets):
    """Check for remaining instances."""
    results = []
    for target in targets:
        shapes = cmds.listRelatives(target, shapes=True, fullPath=True)
        if not shapes:
            continue
        instance_count = 0
        for shape in shapes:
            parents = cmds.listRelatives(shape, allParents=True, fullPath=True)
            if parents and len(parents) >= 2:
                instance_count += 1
        if instance_count > 0:
            results.append({"node": target, "detail": tr("detail_instances").format(instance_count)})
    return results


def check_smooth_preview(targets):
    """Check for meshes with smooth mesh preview enabled (displaySmoothMesh != 0)."""
    results = []
    for target in targets:
        try:
            shapes = cmds.listRelatives(target, shapes=True, fullPath=True) or []
        except Exception as e:
            log.warning(
                "check_smooth_preview: listRelatives failed for {0}: {1}".format(
                    target, e
                )
            )
            continue
        for shape in shapes:
            try:
                val = cmds.getAttr(shape + ".displaySmoothMesh")
            except Exception as e:
                log.warning(
                    "check_smooth_preview: getAttr failed for {0}: {1}".format(
                        shape, e
                    )
                )
                continue
            if val != 0:
                results.append(
                    {"node": target, "detail": tr("detail_smooth_preview")}
                )
                break
    return results


def check_shape_suffix(targets):
    """Check that shape names follow the <transform>Shape convention."""
    results = []
    for target in targets:
        shapes = cmds.listRelatives(target, shapes=True, fullPath=True)
        if not shapes:
            continue
        t_short = target.rsplit("|", 1)[-1]
        expected = t_short + "Shape"
        for shape in shapes:
            if cmds.getAttr(shape + ".intermediateObject"):
                continue
            s_short = shape.rsplit("|", 1)[-1]
            if s_short != expected:
                results.append({
                    "node": target,
                    "detail": tr("detail_shape_suffix"),
                })
    return results


def check_duplicate_names():
    """Check for duplicate short names across all DAG nodes (scene-wide)."""
    results = []
    all_dag = cmds.ls(dag=True, long=True) or []
    skip_defaults = {"|persp", "|top", "|front", "|side",
                     "|persp|perspShape", "|top|topShape",
                     "|front|frontShape", "|side|sideShape"}
    short_map = {}  # short_name -> [long_name, ...]
    for ln in all_dag:
        if ln in skip_defaults:
            continue
        sn = ln.rsplit("|", 1)[-1]
        if not sn:
            continue
        short_map.setdefault(sn, []).append(ln)
    for sn, lns in short_map.items():
        if len(lns) < 2:
            continue
        for ln in lns:
            results.append({
                "node": ln,
                "detail": tr("detail_duplicate_name").format(len(lns)),
            })
    return results
# ---------------------------------------------------------------------------
# [200] unused — Check functions B: Unused & Unnecessary Nodes
# ---------------------------------------------------------------------------
# Mixed check functions — some require targets, some are scene-wide.


def check_unused_nodes():
    """Check for empty groups and empty shape nodes.

    Note: Unused shader/texture/utility DG nodes are handled by
    check_unused_mat, so this function only checks DAG hierarchy.
    """
    results = []
    # --- A. Empty groups / transforms with no visible shapes ---
    skip_cameras = set(["|persp", "|top", "|front", "|side"])
    all_transforms = cmds.ls(long=True, type="transform") or []
    for node in all_transforms:
        if node in skip_cameras:
            continue
        if cmds.nodeType(node) != "transform":
            continue
        children = cmds.listRelatives(node, children=True, fullPath=True)
        shapes = cmds.listRelatives(node, shapes=True, noIntermediate=True, fullPath=True)
        if not children and not shapes:
            results.append({"node": node, "detail": tr("detail_empty_group")})
        elif children and not shapes:
            # Has children (e.g. history nodes) but no visible shapes
            has_sub_transform = False
            for ch in children:
                if cmds.nodeType(ch) == "transform":
                    has_sub_transform = True
                    break
            if not has_sub_transform:
                results.append({"node": node, "detail": tr("detail_empty_mesh")})
    # --- B. Empty mesh shapes ---
    all_meshes = cmds.ls(long=True, type="mesh") or []
    for shape in all_meshes:
        if cmds.getAttr(shape + ".intermediateObject"):
            continue
        try:
            face_count = cmds.polyEvaluate(shape, face=True) or 0
        except Exception:
            face_count = 0
        if face_count == 0:
            parent = cmds.listRelatives(shape, parent=True, fullPath=True)
            parent_name = parent[0] if parent else shape
            results.append({"node": parent_name, "detail": tr("detail_empty_mesh")})
    return results


def check_intermediate_objects(targets):
    """Check for intermediate (construction) objects on target nodes."""
    results = []
    for target in targets:
        shapes = cmds.listRelatives(target, shapes=True, fullPath=True)
        if shapes is None:
            continue
        intermediates = [s for s in shapes if cmds.getAttr(s + ".intermediateObject")]
        if intermediates:
            results.append({"node": target, "detail": tr("detail_intermediate")})
    return results


def check_unused_mat():
    """Check for unused materials and orphaned texture/utility nodes.

    Scene-wide check.
    Section A: shaders connected to SGs with no geometry (excludes lambert1).
    Section B: texture/utility nodes not connected to any shadingEngine.
    """
    results = []
    default_nodes = set(cmds.ls(defaultNodes=True) or [])
    all_sgs = cmds.ls(type="shadingEngine") or []
    sg_set = set(all_sgs)

    # --- A. Unused materials (shader connected to SG with no geometry) ---
    for sg in all_sgs:
        if sg == "initialShadingGroup":
            continue
        members = cmds.sets(sg, query=True) or []
        geo_members = [m for m in members
                       if "." in m or cmds.ls(m, dag=True)]
        if geo_members:
            continue
        shaders = cmds.listConnections(
            sg + ".surfaceShader", source=True, destination=False) or []
        for shader in shaders:
            if shader in default_nodes or shader == "lambert1":
                continue
            node_type = cmds.nodeType(shader)
            results.append({
                "node": shader,
                "detail": tr("detail_unused_mat").format(node_type),
            })

    # --- B. Orphaned texture / utility nodes (not connected to any SG) ---
    _sg_cache = {}

    def _reaches_sg(node, visited=None, depth=0):
        """Return True if *node* reaches any shadingEngine via outputs."""
        if depth > 50 or node is None:
            return False
        if node in _sg_cache:
            return _sg_cache[node]
        if visited is None:
            visited = set()
        if node in visited:
            return False
        visited.add(node)
        try:
            dests = cmds.listConnections(
                node, source=False, destination=True) or []
        except Exception:
            _sg_cache[node] = False
            return False
        for d in dests:
            if d in sg_set:
                _sg_cache[node] = True
                return True
            if _reaches_sg(d, visited, depth + 1):
                _sg_cache[node] = True
                return True
        _sg_cache[node] = False
        return False

    reported = set(r["node"] for r in results)

    try:
        tex_types = cmds.listNodeTypes("texture") or []
    except Exception:
        tex_types = []
    try:
        util_types = cmds.listNodeTypes("utility") or []
    except Exception:
        util_types = []

    for type_list, detail_key in [(tex_types, "detail_unused_texture"),
                                   (util_types, "detail_unused_utility")]:
        for nt in type_list:
            try:
                nodes = cmds.ls(type=nt) or []
            except Exception:
                continue
            for node in nodes:
                if node in default_nodes or node in reported:
                    continue
                if not _reaches_sg(node):
                    node_type = cmds.nodeType(node)
                    results.append({
                        "node": node,
                        "detail": tr(detail_key).format(node_type),
                    })
                    reported.add(node)

    return results


def check_unused_layers(check_display=True, check_render=True, check_animation=True):
    """Check for unused layers (display, render, and/or animation)."""
    results = []

    # --- A. Display Layers ---
    if check_display:
        try:
            display_layers = cmds.ls(type="displayLayer") or []
        except Exception as e:
            log.warning("check_unused_layers: ls(displayLayer) failed: {0}".format(e))
            display_layers = []
        for layer in display_layers:
            if layer == "defaultLayer":
                continue
            try:
                members = cmds.editDisplayLayerMembers(layer, query=True)
            except Exception as e:
                log.warning(
                    "check_unused_layers: editDisplayLayerMembers failed for {0}: {1}".format(
                        layer, e
                    )
                )
                continue
            if not members:
                results.append({"node": layer, "detail": tr("detail_unused_display_layer")})

    # --- B. Render Layers ---
    if check_render:
        try:
            render_layers = cmds.ls(type="renderLayer") or []
        except Exception as e:
            log.warning("check_unused_layers: ls(renderLayer) failed: {0}".format(e))
            render_layers = []
        for layer in render_layers:
            if layer == "defaultRenderLayer":
                continue
            # Skip reference layers
            try:
                is_ref = cmds.referenceQuery(layer, isNodeReferenced=True)
            except RuntimeError:
                is_ref = False
            except Exception:
                is_ref = False
            if is_ref:
                continue
            try:
                members = cmds.editRenderLayerMembers(layer, query=True)
            except Exception as e:
                log.warning(
                    "check_unused_layers: editRenderLayerMembers failed for {0}: {1}".format(
                        layer, e
                    )
                )
                continue
            if not members:
                results.append({"node": layer, "detail": tr("detail_unused_render_layer")})

    # --- C. Animation Layers ---
    if check_animation:
        try:
            anim_layers = cmds.ls(type="animLayer") or []
        except Exception as e:
            log.warning("check_unused_layers: ls(animLayer) failed: {0}".format(e))
            anim_layers = []
        for layer in anim_layers:
            if layer == "BaseAnimation":
                continue
            try:
                curves = cmds.listConnections(layer, type="animCurve")
            except Exception as e:
                log.warning(
                    "check_unused_layers: listConnections failed for {0}: {1}".format(
                        layer, e
                    )
                )
                continue
            if not curves:
                results.append({"node": layer, "detail": tr("detail_unused_animation_layer")})

    return results


def check_empty_sets():
    """Check for empty or unused object sets."""
    results = []
    try:
        all_sets = cmds.ls(type="objectSet") or []
    except Exception as e:
        log.warning("check_empty_sets: cmds.ls failed: {0}".format(e))
        return results

    default_sets = {
        "defaultLightSet", "defaultObjectSet",
        "initialParticleSE", "initialShadingGroup",
    }

    for s in all_sets:
        short_name = s.rsplit("|", 1)[-1] if "|" in s else s
        if short_name in default_sets:
            continue
        try:
            node_type = cmds.nodeType(s)
        except Exception:
            continue
        # Skip shadingEngine nodes
        if node_type == "shadingEngine":
            continue
        # Skip sets connected to display / render / animation layers
        try:
            layer_conns = (
                (cmds.listConnections(s, type="displayLayer") or [])
                + (cmds.listConnections(s, type="renderLayer") or [])
                + (cmds.listConnections(s, type="animLayer") or [])
            )
            if layer_conns:
                continue
        except Exception:
            pass
        # Check members
        try:
            members = cmds.sets(s, q=True) or []
        except Exception as e:
            log.warning(
                "check_empty_sets: cmds.sets failed for {0}: {1}".format(s, e)
            )
            continue
        if len(members) == 0:
            results.append({"node": short_name, "detail": tr("detail_empty_set")})

    return results


def check_namespaces():
    """Check for empty namespaces."""
    results = []
    try:
        all_ns = cmds.namespaceInfo(lon=True, recurse=True) or []
    except Exception as e:
        log.warning("check_namespaces: namespaceInfo failed: {0}".format(e))
        return results

    skip_ns = {"UI", "shared"}

    for ns in all_ns:
        if ns in skip_ns:
            continue
        try:
            members = cmds.namespaceInfo(ns, listNamespace=True) or []
            children = cmds.namespaceInfo(ns, listOnlyNamespaces=True) or []
        except Exception as e:
            log.warning(
                "check_namespaces: query failed for {0}: {1}".format(ns, e)
            )
            continue
        if len(members) == 0 and len(children) == 0:
            results.append({"node": ":{0}".format(ns), "detail": tr("detail_empty_namespace")})

    return results
# ---------------------------------------------------------------------------
# [300] scene_env — Check functions C: Scene Environment
# ---------------------------------------------------------------------------
# Scene-wide checks; they scan the entire scene.
# Exception: check_naming_check requires targets for regex pattern matching.


def check_scene_units(expected_unit="cm", expected_upaxis="y"):
    """Check scene linear unit and up-axis against expected values."""
    results = []
    try:
        current_unit = cmds.currentUnit(q=True, linear=True)
        current_axis = cmds.upAxis(q=True, axis=True)
    except Exception as e:
        log.warning("check_scene_units: query failed: {0}".format(e))
        return results

    unit_match = current_unit.lower() == expected_unit.lower()
    axis_match = current_axis.lower() == expected_upaxis.lower()

    if not unit_match or not axis_match:
        parts = []
        if not unit_match:
            parts.append(
                tr("detail_unit_mismatch").format(current_unit, expected_unit)
            )
        if not axis_match:
            parts.append(
                tr("detail_upaxis_mismatch").format(current_axis, expected_upaxis)
            )
        results.append({"node": "Scene", "detail": ", ".join(parts)})

    return results


def check_unknown_nodes():
    """Check for unknown nodes (from missing plugins)."""
    results = []
    unknown_nodes = cmds.ls(type="unknown") or []
    unknown_dag = cmds.ls(type="unknownDag", long=True) or []
    all_unknown = list(set(unknown_nodes + unknown_dag))
    for node in all_unknown:
        real_type = None
        try:
            real_type = cmds.unknownNode(node, query=True, realClassName=True)
        except Exception:
            pass
        if real_type:
            detail = tr("detail_unknown_node").format(real_type)
        else:
            detail = tr("detail_unknown_node_notype")
        results.append({"node": node, "detail": detail})
    return results


def check_referenced_nodes():
    """Check for remaining reference nodes (pre-delivery cleanup)."""
    results = []
    try:
        ref_nodes = cmds.ls(type="reference")
    except Exception as e:
        log.warning("check_referenced_nodes: ls(reference) failed: {0}".format(e))
        return results
    if not ref_nodes:
        return results

    skip_nodes = {"sharedReferenceNode", "_UNKNOWN_REF_NODE_"}

    for node in ref_nodes:
        short_name = node.rsplit("|", 1)[-1] if "|" in node else node
        if short_name in skip_nodes:
            continue

        # Get file path and load state
        file_path = None
        is_loaded = False
        try:
            file_path = cmds.referenceQuery(node, filename=True)
        except RuntimeError:
            file_path = None
        except Exception as e:
            log.warning(
                "check_referenced_nodes: referenceQuery(filename) failed for {0}: {1}".format(
                    node, e
                )
            )
            file_path = None

        if file_path is not None:
            try:
                is_loaded = cmds.referenceQuery(node, isLoaded=True)
            except Exception:
                is_loaded = False

            if is_loaded:
                detail = tr("detail_loaded").format(file_path)
            else:
                detail = tr("detail_unloaded").format(file_path)
        else:
            detail = tr("detail_ref_path_unknown")

        results.append({"node": node, "detail": detail})

    return results


def check_naming_check(targets, regex_pattern=""):
    """Check node naming against regex pattern.

    If regex_pattern is empty, the check is skipped (returns 0 detections).
    """
    results = []
    if not regex_pattern:
        return results

    compiled_re = None
    try:
        compiled_re = re.compile(regex_pattern)
    except re.error:
        log.warning("Invalid regex pattern: %s", regex_pattern)
        return results

    for target in targets:
        short_name = target.rsplit("|", 1)[-1]
        if not short_name:
            continue
        if not compiled_re.search(short_name):
            results.append({
                "node": target,
                "detail": tr("detail_naming_mismatch").format(regex_pattern)
            })

    return results


def check_file_paths(scene_folder="scenes", tex_folder="sourceimages",
                     expected_path_type="relative", check_missing=True):
    """Check file paths: folder name, path type, and missing files."""
    results = []

    proj_root = None
    try:
        proj_root = cmds.workspace(q=True, rd=True)
    except Exception:
        pass

    # --- 1. Scene file folder validation ---
    if scene_folder:
        try:
            scene_path = cmds.file(q=True, sceneName=True) or ""
        except Exception:
            scene_path = ""
        if scene_path:
            norm = scene_path.replace("\\", "/")
            scene_basename = norm.rsplit("/", 1)[-1] if "/" in norm else norm
            parent_dir = norm.rsplit("/", 1)[0] if "/" in norm else ""
            expected_norm = scene_folder.strip("/").replace("\\", "/")
            if parent_dir and not parent_dir.lower().endswith(expected_norm.lower()):
                results.append({
                    "node": scene_basename,
                    "detail": tr("detail_wrong_folder"),
                    "_sort": 0,
                })

    # --- 2 & 3. File node checks ---
    file_nodes = cmds.ls(type="file") or []
    check_abs = expected_path_type.lower() == "absolute"

    for node in file_nodes:
        try:
            path = cmds.getAttr(node + ".fileTextureName") or ""
        except Exception:
            continue
        if not path:
            continue

        # Folder name validation for tex
        if tex_folder:
            norm_path = path.replace("\\", "/")
            parent_dir = norm_path.rsplit("/", 1)[0] if "/" in norm_path else ""
            expected_norm = tex_folder.strip("/").replace("\\", "/")
            if parent_dir and not parent_dir.lower().endswith(expected_norm.lower()):
                results.append({
                    "node": node,
                    "detail": tr("detail_wrong_folder"),
                    "_sort": 0,
                })

        # Path type validation
        is_abs = os.path.isabs(path)
        if check_abs and not is_abs:
            results.append({
                "node": node,
                "detail": tr("detail_expected_absolute"),
                "_sort": 1,
            })
        elif not check_abs and is_abs:
            results.append({
                "node": node,
                "detail": tr("detail_expected_relative"),
                "_sort": 1,
            })

        # Missing file detection
        if check_missing:
            if "<UDIM>" in path or "<udim>" in path:
                continue
            resolved = path
            if not os.path.isabs(path) and proj_root:
                resolved = os.path.join(proj_root, path)
            if not os.path.isfile(resolved):
                results.append({
                    "node": node,
                    "detail": tr("detail_missing_file"),
                    "_sort": 2,
                })

    # Sort by category, then strip internal key
    results.sort(key=lambda r: r.get("_sort", 9))
    for r in results:
        r.pop("_sort", None)

    return results
# ---------------------------------------------------------------------------
# [800] ui — Main Window, Results Window, Help Dialog, Category UI
# ---------------------------------------------------------------------------

# ===== Utility Widgets =====================================================

class NoScrollComboBox(QtWidgets.QComboBox):
    """QComboBox that ignores scroll-wheel events."""
    def wheelEvent(self, event):
        event.ignore()


# ===== CheckCategory =================================================

class CheckCategory(QtWidgets.QWidget):
    """Category section holding check-item checkboxes."""

    def __init__(self, parent=None):
        super(CheckCategory, self).__init__(parent)
        self._item_checkboxes = []

        self._content_layout = QtWidgets.QVBoxLayout(self)
        self._content_layout.setContentsMargins(4, 4, 4, 4)
        self._content_layout.setSpacing(2)

    # -- public API --

    def add_check_item(self, key, label, default_on=True, param_widget=None):
        """Add a check item row. Returns the QCheckBox."""
        outer = QtWidgets.QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(2)
        row = QtWidgets.QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        cb = QtWidgets.QCheckBox(label)
        cb.setChecked(default_on)
        cb._check_key = key
        row.addWidget(cb)
        row.addStretch()
        outer.addLayout(row)
        if param_widget is not None:
            param_row = QtWidgets.QHBoxLayout()
            param_row.setContentsMargins(22, 0, 0, 0)
            param_row.addWidget(param_widget)
            outer.addLayout(param_row)
        container = QtWidgets.QWidget()
        container.setLayout(outer)
        self._content_layout.addWidget(container)
        self._item_checkboxes.append(cb)
        return cb

    def get_enabled_items(self):
        """Return list of check_key strings for enabled items."""
        return [
            cb._check_key
            for cb in self._item_checkboxes
            if cb.isChecked()
        ]

    def set_all(self, checked):
        """Set all item checkboxes to *checked* state."""
        for cb in self._item_checkboxes:
            cb.setChecked(checked)

    def retranslate(self, labels_map):
        """Update item labels from a {key: label} map."""
        for cb in self._item_checkboxes:
            key = cb._check_key
            if key in labels_map:
                cb.setText(labels_map[key])

    def reset_defaults(self, defaults_list):
        """Reset checkboxes to default states.

        NOTE: Currently unused — kept for potential future use.

        Args:
            defaults_list: list of (key, default_on) tuples.
        """
        key_to_cb = {}
        for cb in self._item_checkboxes:
            key_to_cb[cb._check_key] = cb
        for key, default_on in defaults_list:
            cb = key_to_cb.get(key)
            if cb is not None:
                cb.setChecked(default_on)


# ===== HelpDialog ==========================================================

class HelpDialog(QtWidgets.QDialog):
    """Simple HTML help dialog using QTextBrowser."""

    def __init__(self, parent=None):
        super(HelpDialog, self).__init__(parent)
        self.setObjectName(HELP_DIALOG_OBJECT_NAME)
        self.setWindowTitle(tr("btn_howto"))
        self.setMinimumSize(400, 480)
        layout = QtWidgets.QVBoxLayout(self)
        self._browser = QtWidgets.QTextBrowser()
        self._browser.setOpenExternalLinks(True)
        layout.addWidget(self._browser)
        btn_close = QtWidgets.QPushButton(tr("btn_close"))
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)
        self._update_content()

    def _update_content(self):
        html = _HELP_HTML.get(_current_lang, _HELP_HTML.get("en", ""))
        self._browser.setHtml(html)

    def retranslate(self):
        self.setWindowTitle(tr("btn_howto"))
        self._update_content()


# ===== ResultsWindow =======================================================

class ResultsWindow(QtWidgets.QDialog):
    """Displays check results in a left-right split layout.

    Left panel : check-item list with detection-count badges.
    Right panel: node list filtered by selected item (or all).
    """

    _BADGE_STYLE = (
        "background-color:{bg}; color:{fg}; border-radius:8px;"
        " padding:1px 6px; font-size:11px; font-weight:bold;"
    )

    def __init__(self, results=None, parent=None):
        super(ResultsWindow, self).__init__(parent)
        self.setObjectName(RESULTS_OBJECT_NAME)
        self.setWindowTitle(tr("results_title"))
        self.setMinimumSize(520, 480)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.Tool)
        self.setStyleSheet(_QSS)

        self._results = results or {}
        self._ordered_keys = [k for k in _CANONICAL_ORDER if k in self._results]
        self._build_ui()

    # ------------------------------------------------------------------ build
    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)

        # --- Summary label ---
        total = sum(len(v) for v in self._results.values())
        self._summary_label = QtWidgets.QLabel(
            tr("status_done", issues=total)
        )
        font = self._summary_label.font()
        font.setBold(True)
        self._summary_label.setFont(font)
        root.addWidget(self._summary_label)

        # --- Splitter (left / right) ---
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        # -- Left panel: check-item list --
        left_widget = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        self._item_list = QtWidgets.QListWidget()
        self._item_list.setSelectionMode(
            QtWidgets.QAbstractItemView.SingleSelection
        )
        self._item_list.currentRowChanged.connect(self._on_item_selected)
        left_layout.addWidget(self._item_list)

        splitter.addWidget(left_widget)

        # -- Right panel: node list --
        right_widget = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self._node_list = QtWidgets.QListWidget()
        self._node_list.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )
        self._node_list.itemClicked.connect(self._on_node_clicked)
        right_layout.addWidget(self._node_list)

        splitter.addWidget(right_widget)

        splitter.setSizes([190, 330])
        root.addWidget(splitter, stretch=1)

        # --- Populate left panel ---
        self._populate_item_list()

        # --- Bottom buttons ---
        btn_layout = QtWidgets.QHBoxLayout()
        self._btn_select_all = QtWidgets.QPushButton(tr("btn_select_all"))
        self._btn_select_all.clicked.connect(self._select_all_in_maya)
        btn_layout.addWidget(self._btn_select_all)
        self._btn_copy_report = QtWidgets.QPushButton(tr("btn_copy_report"))
        self._btn_copy_report.clicked.connect(self.copy_report)
        btn_layout.addWidget(self._btn_copy_report)
        btn_layout.addStretch()
        self._btn_close = QtWidgets.QPushButton(tr("btn_close"))
        self._btn_close.clicked.connect(self.close)
        btn_layout.addWidget(self._btn_close)
        root.addLayout(btn_layout)

    # ------------------------------------------------------------- left panel
    def _populate_item_list(self):
        self._item_list.clear()

        # "All" row
        total = sum(len(v) for v in self._results.values())
        all_item = QtWidgets.QListWidgetItem()
        all_widget = self._make_item_row(tr("results_all"), total, is_all=True)
        all_item.setSizeHint(all_widget.sizeHint())
        self._item_list.addItem(all_item)
        self._item_list.setItemWidget(all_item, all_widget)

        # Per-check rows
        for key in self._ordered_keys:
            items = self._results[key]
            label = tr("chk_" + key)
            count = len(items)
            row_item = QtWidgets.QListWidgetItem()
            row_widget = self._make_item_row(label, count)
            row_item.setSizeHint(row_widget.sizeHint())
            if count == 0:
                row_widget.setEnabled(False)
            self._item_list.addItem(row_item)
            self._item_list.setItemWidget(row_item, row_widget)

        # Select "All" by default
        self._item_list.setCurrentRow(0)

    def _make_item_row(self, label_text, count, is_all=False):
        """Create a widget row with label + count badge."""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(widget)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(6)

        lbl = QtWidgets.QLabel(label_text)
        lbl.setMinimumWidth(0)
        lbl.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)
        if is_all:
            f = lbl.font()
            f.setBold(True)
            lbl.setFont(f)
        layout.addWidget(lbl, stretch=1)

        badge = QtWidgets.QLabel(str(count))
        if count > 0:
            badge.setStyleSheet(
                self._BADGE_STYLE.format(bg="#7aa2f7", fg="#1a1a1a")
            )
        else:
            badge.setStyleSheet(
                self._BADGE_STYLE.format(bg="#555555", fg="#999999")
            )
        badge.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(badge)

        return widget

    # --------------------------------------------------------- node display
    @staticmethod
    def _format_node_display(entry):
        """Return display string for a result entry."""
        node = entry.get("node", "")
        short_name = node.rsplit("|", 1)[-1] if node else node
        detail = entry.get("detail", "")
        return "{n} | {d}".format(n=short_name, d=detail) if detail else short_name

    # ------------------------------------------------------------ right panel
    def _on_item_selected(self, row):
        """Update right panel when left-panel selection changes."""
        self._node_list.clear()

        # row == 0  -> "All" row selected
        # row == -1 -> selection cleared (e.g. during list rebuild); treat as "All"
        if row <= 0:
            self._populate_all_nodes()
        else:
            # Specific check item
            key_index = row - 1
            if key_index < len(self._ordered_keys):
                key = self._ordered_keys[key_index]
                entries = self._results.get(key, [])
                for entry in entries:
                    display = self._format_node_display(entry)
                    item = QtWidgets.QListWidgetItem(display)
                    item.setData(QtCore.Qt.UserRole, entry.get("node", ""))
                    self._node_list.addItem(item)

        if self._node_list.count() == 0:
            no_item = QtWidgets.QListWidgetItem(tr("results_no_issues"))
            no_item.setFlags(no_item.flags() & ~QtCore.Qt.ItemIsSelectable)
            self._node_list.addItem(no_item)

    def _populate_all_nodes(self):
        """Show all nodes grouped by check-item headers."""
        for key in self._ordered_keys:
            entries = self._results.get(key, [])
            if not entries:
                continue
            label = tr("chk_" + key)
            header_text = "\u2014 {label} ({count}) \u2014".format(
                label=label, count=len(entries)
            )
            header_item = QtWidgets.QListWidgetItem(header_text)
            header_item.setFlags(header_item.flags() & ~QtCore.Qt.ItemIsSelectable)
            f = header_item.font()
            f.setBold(True)
            header_item.setFont(f)
            header_item.setForeground(QtGui.QColor("#888888"))
            self._node_list.addItem(header_item)
            for entry in entries:
                display = self._format_node_display(entry)
                item = QtWidgets.QListWidgetItem("  " + display)
                item.setData(QtCore.Qt.UserRole, entry.get("node", ""))
                self._node_list.addItem(item)

    def _on_node_clicked(self, item):
        node = item.data(QtCore.Qt.UserRole)
        if node:
            try:
                cmds.select(node, replace=True)
            except Exception:
                pass

    # --------------------------------------------------------- Maya selection
    def _select_all_in_maya(self):
        nodes = []
        for key, items in self._results.items():
            for entry in items:
                n = entry.get("node")
                if n and cmds.objExists(n):
                    nodes.append(n)
        if nodes:
            cmds.select(nodes, replace=True)

    def has_results(self):
        """Return True if there are any check results."""
        return bool(self._results)

    def copy_report(self):
        """Copy check results as plain text to clipboard."""
        lines = []
        for key in self._ordered_keys:
            items = self._results.get(key, [])
            label = tr("chk_" + key)
            count = len(items)
            if count:
                lines.append("{label}: {summary}".format(
                    label=label,
                    summary=tr("results_summary", count=count),
                ))
                for entry in items:
                    node = entry.get("node", "")
                    detail = entry.get("detail", "")
                    if detail:
                        lines.append("  - {node} | {detail}".format(
                            node=node, detail=detail))
                    else:
                        lines.append("  - {node}".format(node=node))
            else:
                lines.append("{label}: {pass_text}".format(
                    label=label,
                    pass_text=tr("results_pass"),
                ))
        text = "\n".join(lines)
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(text)
        self._summary_label.setText(tr("report_copied"))


# ===== MainWindow ==========================================================

# Check item definitions: (key, i18n_key, default_on, has_params)
# --- Geometry (7) ---
_CHECK_ITEMS_GEOMETRY = [
    ("history",              "chk_history",              True,  False),
    ("transform",            "chk_transform",            True,  False),
    ("vertex_tweaks",        "chk_vertex_tweaks",        True,  False),
    ("instances",            "chk_instances",             True,  False),
    ("smooth_preview",       "chk_smooth_preview",       True,  False),
    ("shape_suffix",         "chk_shape_suffix",          True,  False),
    ("duplicate_names",      "chk_duplicate_names",       True,  False),
]

# --- Unused (6) ---
_CHECK_ITEMS_UNUSED = [
    ("unused_nodes",         "chk_unused_nodes",         True,  False),
    ("intermediate_objects", "chk_intermediate_objects",  True,  False),
    ("unused_mat",           "chk_unused_mat",           True,  False),
    ("unused_layers",        "chk_unused_layers",        True,  False),
    ("empty_sets",           "chk_empty_sets",            True,  False),
    ("namespaces",           "chk_namespaces",           True,  False),
]

# --- Scene Environment (5) ---
_CHECK_ITEMS_SCENE_ENV = [
    ("scene_units",          "chk_scene_units",          True,  True),
    ("unknown_nodes",        "chk_unknown_nodes",        True,  False),
    ("referenced_nodes",     "chk_referenced_nodes",     True,  False),
    ("naming_check",         "chk_naming_check",         True,  True),
    ("file_paths",           "chk_file_paths",           True,  True),
]

_CANONICAL_ORDER = (
    [k for k, _, _, _ in _CHECK_ITEMS_GEOMETRY]
    + [k for k, _, _, _ in _CHECK_ITEMS_UNUSED]
    + [k for k, _, _, _ in _CHECK_ITEMS_SCENE_ENV]
)


class MainWindow(QtWidgets.QDialog):
    """Scene Cleanup Tools main window."""

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent or get_maya_main_window())
        self.setObjectName(WINDOW_OBJECT_NAME)
        self.setWindowTitle("{0} {1}".format(WINDOW_TITLE, __VERSION__))
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.Tool)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setMinimumSize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setStyleSheet(_QSS)

        self._worker = None
        self._help_dialog = None
        self._results_window = None
        self._param_widgets = {}
        self._reset_timer = None

        self._build_ui()
        self._retranslate_ui()

    # === Build UI ===========================================================

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        # --- Top bar --------------------------------------------------------
        top_bar = QtWidgets.QHBoxLayout()
        self._lbl_lang = QtWidgets.QLabel(tr("lang_label"))
        top_bar.addWidget(self._lbl_lang)
        self._lang_combo = NoScrollComboBox()
        self._lang_combo.addItems(["English", "\u65e5\u672c\u8a9e"])
        self._lang_combo.currentIndexChanged.connect(self._on_language_changed)
        self._lang_combo.setCurrentIndex(1 if _current_lang == "ja" else 0)
        top_bar.addWidget(self._lang_combo)
        top_bar.addStretch()
        self._btn_howto = QtWidgets.QPushButton(tr("btn_howto"))
        self._btn_howto.setProperty("cssClass", "prep")
        self._btn_howto.setMinimumWidth(100)
        self._btn_howto.clicked.connect(self._show_help)
        top_bar.addWidget(self._btn_howto)
        root.addLayout(top_bar)

        # --- Check items (scrollable) ---------------------------------------
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.viewport().setAutoFillBackground(False)
        scroll_content = QtWidgets.QWidget()
        scroll_content.setObjectName("scrollContent")
        scroll_layout = QtWidgets.QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)

        # Category groups
        self._grp_geometry, self._cat_geometry = self._create_category_group(
            tr("cat_geometry"), _CHECK_ITEMS_GEOMETRY
        )
        scroll_layout.addWidget(self._grp_geometry)

        self._grp_unused, self._cat_unused = self._create_category_group(
            tr("cat_unused"), _CHECK_ITEMS_UNUSED
        )
        scroll_layout.addWidget(self._grp_unused)

        self._grp_scene_env, self._cat_scene_env = self._create_category_group(
            tr("cat_scene_env"), _CHECK_ITEMS_SCENE_ENV
        )
        scroll_layout.addWidget(self._grp_scene_env)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        root.addWidget(scroll, stretch=1)

        # --- All ON / All OFF / Reset (below checkboxes, above Check) ------
        btn_row = QtWidgets.QHBoxLayout()
        self._btn_all_on = QtWidgets.QPushButton(tr("btn_all_on"))
        self._btn_all_on.setProperty("cssClass", "prep")
        self._btn_all_on.clicked.connect(lambda: self._set_all_checks(True))
        self._btn_all_off = QtWidgets.QPushButton(tr("btn_all_off"))
        self._btn_all_off.setProperty("cssClass", "prep")
        self._btn_all_off.clicked.connect(lambda: self._set_all_checks(False))
        btn_row.addWidget(self._btn_all_on)
        btn_row.addWidget(self._btn_all_off)
        btn_row.addStretch()
        root.addLayout(btn_row)

        # --- Check button ---------------------------------------------------
        self._btn_check = QtWidgets.QPushButton(tr("btn_check"))
        self._btn_check.clicked.connect(self._run_check)
        root.addWidget(self._btn_check)

        # --- Footer: Status Row (status / progress+cancel) + Send Report ----
        status_row = QtWidgets.QHBoxLayout()
        self._lbl_status = QtWidgets.QLabel(tr("status_ready"))
        self._lbl_status.setStyleSheet("font-size: 11px; color: #666666;")
        status_row.addWidget(self._lbl_status)
        self._progress_bar = QtWidgets.QProgressBar()
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setVisible(False)
        status_row.addWidget(self._progress_bar, stretch=1)
        self._btn_cancel = QtWidgets.QPushButton("\u2715")
        self._btn_cancel.setProperty("cssClass", "secondary")
        self._btn_cancel.setFixedSize(30, 22)
        self._btn_cancel.setVisible(False)
        self._btn_cancel.clicked.connect(self._cancel_check)
        status_row.addWidget(self._btn_cancel)
        self._btn_send_report = QtWidgets.QPushButton(tr("btn_send_report"))
        self._btn_send_report.setProperty("cssClass", "accent")
        self._btn_send_report.setFixedWidth(120)
        self._btn_send_report.clicked.connect(self._send_report)
        status_row.addWidget(self._btn_send_report)
        root.addLayout(status_row)

    # === Category group helper ==============================================

    def _create_category_group(self, title, check_items):
        """Create a QGroupBox containing a CheckCategory with items."""
        grp = QtWidgets.QGroupBox(title)
        grp_layout = QtWidgets.QVBoxLayout(grp)
        grp_layout.setContentsMargins(4, 4, 4, 4)
        cat = CheckCategory()
        for key, i18n_key, default_on, has_params in check_items:
            pw = self._make_param_widget(key) if has_params else None
            cat.add_check_item(
                key, tr(i18n_key), default_on=default_on, param_widget=pw
            )
        grp_layout.addWidget(cat)
        return grp, cat

    # === Parameter widgets ==================================================

    def _make_param_widget(self, key):
        """Create parameter widget(s) for items that need them."""
        container = QtWidgets.QWidget()

        if key == "naming_check":
            layout = QtWidgets.QHBoxLayout(container)
            layout.setContentsMargins(8, 0, 0, 0)
            layout.setSpacing(4)
            lbl = QtWidgets.QLabel(tr("naming_regex"))
            regex_edit = QtWidgets.QLineEdit()
            regex_edit.setPlaceholderText("e.g. ^[A-Za-z_][A-Za-z0-9_]*$")
            regex_edit.setMinimumWidth(120)
            layout.addWidget(lbl)
            layout.addWidget(regex_edit, 1)
            self._param_widgets[key] = {
                "label": lbl,
                "regex": regex_edit,
            }

        elif key == "scene_units":
            layout = QtWidgets.QHBoxLayout(container)
            layout.setContentsMargins(8, 0, 0, 0)
            layout.setSpacing(4)
            lbl_unit = QtWidgets.QLabel(tr("unit_label"))
            combo_unit = NoScrollComboBox()
            combo_unit.addItems(["cm", "m"])
            lbl_axis = QtWidgets.QLabel(tr("upaxis_label"))
            combo_axis = NoScrollComboBox()
            combo_axis.addItems(["Y", "Z"])
            layout.addWidget(lbl_unit)
            layout.addWidget(combo_unit)
            layout.addWidget(lbl_axis)
            layout.addWidget(combo_axis)
            layout.addStretch()
            self._param_widgets[key] = {
                "label_unit": lbl_unit,
                "combo_unit": combo_unit,
                "label_axis": lbl_axis,
                "combo_axis": combo_axis,
            }

        elif key == "file_paths":
            layout = QtWidgets.QVBoxLayout(container)
            layout.setContentsMargins(8, 0, 0, 0)
            layout.setSpacing(4)
            # Row 1: Scene / Tex folder names
            row1 = QtWidgets.QHBoxLayout()
            row1.setSpacing(4)
            lbl_scene = QtWidgets.QLabel(tr("file_paths_scene"))
            edit_scene = QtWidgets.QLineEdit("scenes")
            edit_scene.setMinimumWidth(80)
            lbl_tex = QtWidgets.QLabel(tr("file_paths_tex"))
            edit_tex = QtWidgets.QLineEdit("sourceimages")
            edit_tex.setMinimumWidth(80)
            row1.addWidget(lbl_scene)
            row1.addWidget(edit_scene, 1)
            row1.addWidget(lbl_tex)
            row1.addWidget(edit_tex, 1)
            layout.addLayout(row1)
            # Row 2: Path type radio buttons
            row2 = QtWidgets.QHBoxLayout()
            row2.setSpacing(4)
            rb_relative = QtWidgets.QRadioButton(tr("file_paths_relative"))
            rb_absolute = QtWidgets.QRadioButton(tr("file_paths_absolute"))
            rb_relative.setChecked(True)
            row2.addWidget(rb_relative)
            row2.addWidget(rb_absolute)
            row2.addStretch()
            layout.addLayout(row2)
            # Row 3: Missing File checkbox
            cb_missing = QtWidgets.QCheckBox(tr("file_paths_missing"))
            cb_missing.setChecked(True)
            layout.addWidget(cb_missing)
            self._param_widgets[key] = {
                "label_scene": lbl_scene,
                "edit_scene": edit_scene,
                "label_tex": lbl_tex,
                "edit_tex": edit_tex,
                "rb_relative": rb_relative,
                "rb_absolute": rb_absolute,
                "cb_missing": cb_missing,
            }

        return container

    # === Check control ======================================================

    def _set_all_checks(self, checked):
        """Set all check items in all categories."""
        self._cat_geometry.set_all(checked)
        self._cat_unused.set_all(checked)
        self._cat_scene_env.set_all(checked)

    # === Status / Progress ==================================================

    def _set_status(self, text, state="ready"):
        """Set status label text and color based on state.

        States: ready, success, error, working.
        """
        colors = {
            "ready":   ("#666666", ""),
            "success": ("#44aa44", "#1a2e1a"),
            "error":   ("#cc4444", "#2e1a1a"),
            "working": ("#7aa2f7", ""),
        }
        fg, bg = colors.get(state, colors["ready"])
        if bg:
            self._lbl_status.setStyleSheet(
                "font-size: 11px; color: {fg}; background-color: {bg};"
                " padding: 2px 6px; border-radius: 3px;".format(
                    fg=fg, bg=bg)
            )
        else:
            self._lbl_status.setStyleSheet(
                "font-size: 11px; color: {fg};".format(fg=fg)
            )
        self._lbl_status.setText(text)

    def _schedule_status_reset(self):
        """Schedule auto-reset to ready state after 3 seconds.

        Cancels any previously scheduled reset to avoid overlapping timers.
        """
        if self._reset_timer is not None:
            self._reset_timer.stop()
        self._reset_timer = QtCore.QTimer(self)
        self._reset_timer.setSingleShot(True)
        self._reset_timer.timeout.connect(
            lambda: self._set_status(tr("status_ready"), "ready")
        )
        self._reset_timer.start(3000)

    def _show_progress(self):
        """Show progress bar + cancel, hide status label."""
        if self._reset_timer is not None:
            self._reset_timer.stop()
            self._reset_timer = None
        self._lbl_status.setVisible(False)
        self._progress_bar.setVisible(True)
        self._btn_cancel.setVisible(True)

    def _hide_progress(self):
        """Hide progress bar + cancel, show status label."""
        self._progress_bar.setVisible(False)
        self._btn_cancel.setVisible(False)
        self._lbl_status.setVisible(True)

    # === Check execution ====================================================

    def _get_enabled_checks(self):
        """Return enabled items from all check categories."""
        items = []
        items.extend(self._cat_geometry.get_enabled_items())
        items.extend(self._cat_unused.get_enabled_items())
        items.extend(self._cat_scene_env.get_enabled_items())
        return items

    def _run_check(self):
        """Start the check process via QCWorker."""
        enabled = self._get_enabled_checks()
        if not enabled:
            self._lbl_status.setText(tr("status_ready"))
            return

        targets = collect_meshes()

        # Gather params
        params = {}
        pw = self._param_widgets.get("naming_check")
        if pw:
            params["naming_regex"] = pw["regex"].text()
        pw = self._param_widgets.get("scene_units")
        if pw:
            params["expected_unit"] = pw["combo_unit"].currentText().lower()
            params["expected_upaxis"] = pw["combo_axis"].currentText().lower()
        pw = self._param_widgets.get("file_paths")
        if pw:
            params["file_paths_scene"] = pw["edit_scene"].text() or "scenes"
            params["file_paths_tex"] = pw["edit_tex"].text() or "sourceimages"
            params["file_paths_type"] = "absolute" if pw["rb_absolute"].isChecked() else "relative"
            params["file_paths_missing"] = pw["cb_missing"].isChecked()

        # Show progress
        self._progress_bar.setMaximum(len(enabled))
        self._progress_bar.setValue(0)
        self._progress_bar.setFormat("  %p%")
        self._show_progress()
        self._btn_check.setEnabled(False)

        # Launch worker
        self._worker = QCWorker(
            enabled_keys=enabled,
            targets=targets,
            params=params,
            parent=self,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_signal.connect(self._on_finished)
        self._worker.start()

    def _cancel_check(self):
        if self._worker and self._worker.is_running():
            self._worker.cancel()
            self._hide_progress()
            self._btn_check.setEnabled(True)
            self._set_status(tr("status_cancelled"), "error")
            self._schedule_status_reset()

    def _on_progress(self, current, total):
        self._progress_bar.setValue(current)
        label = tr("status_running", cur=current, total=total)
        self._progress_bar.setFormat(label + "  %p%")

    def _on_finished(self, results):
        self._hide_progress()
        self._btn_check.setEnabled(True)

        total_issues = sum(len(v) for v in results.values())
        state = "error" if total_issues > 0 else "success"
        self._set_status(tr("status_done", issues=total_issues), state)
        self._schedule_status_reset()

        self._show_results(results)

    def _show_results(self, results):
        if self._results_window:
            self._results_window.close()
        self._results_window = ResultsWindow(results=results, parent=self)
        self._results_window.show()

    # === Send report ========================================================

    def _send_report(self):
        """Copy latest check results to clipboard."""
        if not self._results_window or not self._results_window.has_results():
            return
        self._results_window.copy_report()
        self._lbl_status.setText(tr("report_copied"))

    # === Help dialog ========================================================

    def _show_help(self):
        if self._help_dialog is None:
            self._help_dialog = HelpDialog(parent=self)
        self._help_dialog.retranslate()
        self._help_dialog.show()
        self._help_dialog.raise_()

    # === Language switching ==================================================

    def _on_language_changed(self, index):
        lang = "ja" if index == 1 else "en"
        set_language(lang)
        self._retranslate_ui()

    def _retranslate_ui(self):
        self.setWindowTitle("{0} {1}".format(WINDOW_TITLE, __VERSION__))
        self._btn_howto.setText(tr("btn_howto"))
        self._btn_check.setText(tr("btn_check"))
        self._set_status(tr("status_ready"), "ready")

        # Language label + send report
        self._lbl_lang.setText(tr("lang_label"))
        self._btn_send_report.setText(tr("btn_send_report"))

        # QGroupBox titles
        self._grp_geometry.setTitle(tr("cat_geometry"))
        self._grp_unused.setTitle(tr("cat_unused"))
        self._grp_scene_env.setTitle(tr("cat_scene_env"))

        # Category item labels
        geo_labels = {k: tr(i) for k, i, _, _ in _CHECK_ITEMS_GEOMETRY}
        self._cat_geometry.retranslate(geo_labels)
        unused_labels = {k: tr(i) for k, i, _, _ in _CHECK_ITEMS_UNUSED}
        self._cat_unused.retranslate(unused_labels)
        scene_labels = {k: tr(i) for k, i, _, _ in _CHECK_ITEMS_SCENE_ENV}
        self._cat_scene_env.retranslate(scene_labels)

        self._btn_all_on.setText(tr("btn_all_on"))
        self._btn_all_off.setText(tr("btn_all_off"))

        # Param widgets
        pw = self._param_widgets.get("naming_check")
        if pw:
            pw["label"].setText(tr("naming_regex"))
        pw = self._param_widgets.get("scene_units")
        if pw:
            pw["label_unit"].setText(tr("unit_label"))
            pw["label_axis"].setText(tr("upaxis_label"))
        pw = self._param_widgets.get("file_paths")
        if pw:
            pw["label_scene"].setText(tr("file_paths_scene"))
            pw["label_tex"].setText(tr("file_paths_tex"))
            pw["rb_relative"].setText(tr("file_paths_relative"))
            pw["rb_absolute"].setText(tr("file_paths_absolute"))
            pw["cb_missing"].setText(tr("file_paths_missing"))

    # === Cleanup ============================================================

    def closeEvent(self, event):
        if self._results_window:
            self._results_window.close()
        if self._help_dialog:
            self._help_dialog.close()
        super(MainWindow, self).closeEvent(event)
# ---------------------------------------------------------------------------
# [810] worker — QTimer-based sequential check execution
# ---------------------------------------------------------------------------

# Mapping: check key -> callable
_CHECK_FUNC_MAP = {
    # Geometry items
    "history":              check_history,
    "transform":            check_transform,
    "vertex_tweaks":        check_vertex_tweaks,
    "instances":            check_instances,
    "smooth_preview":       check_smooth_preview,
    "shape_suffix":         check_shape_suffix,
    "duplicate_names":      check_duplicate_names,
    # Unused items
    "unused_nodes":         check_unused_nodes,
    "intermediate_objects": check_intermediate_objects,
    "unused_mat":           check_unused_mat,
    "unused_layers":        check_unused_layers,
    "empty_sets":           check_empty_sets,
    "namespaces":           check_namespaces,
    # Scene Environment items
    "scene_units":          check_scene_units,
    "unknown_nodes":        check_unknown_nodes,
    "referenced_nodes":     check_referenced_nodes,
    "naming_check":         check_naming_check,
    "file_paths":           check_file_paths,
}

_SCENE_WIDE_KEYS = {
    "unused_nodes", "unused_mat", "unused_layers", "empty_sets", "namespaces",
    "unknown_nodes", "referenced_nodes", "duplicate_names", "scene_units",
    "file_paths",
}


class QCWorker(QtCore.QObject):
    """Runs enabled checks sequentially on the main thread via QTimer.

    Each check function is executed directly in the main thread.
    QTimer.singleShot(0) is used between checks to keep the UI responsive.
    """

    progress = QtCore.Signal(int, int)          # (current, total)
    finished_signal = QtCore.Signal(dict)       # {key: [results]}

    def __init__(self, enabled_keys, targets, params=None, parent=None):
        super(QCWorker, self).__init__(parent)
        self._enabled = enabled_keys
        self._targets = targets
        self._params = params or {}
        self._cancelled = False
        self._results = {}
        self._current_index = 0
        self._running = False

    def cancel(self):
        self._cancelled = True

    def is_running(self):
        """Return True if checks are currently in progress."""
        return self._running

    def start(self):
        """Begin sequential check execution."""
        self._results = {}
        self._current_index = 0
        self._cancelled = False
        self._running = True
        self._run_next()

    def _run_next(self):
        """Run the next check, then schedule the following one via QTimer."""
        if self._cancelled or self._current_index >= len(self._enabled):
            self._running = False
            self.finished_signal.emit(self._results)
            return

        key = self._enabled[self._current_index]
        try:
            self._results[key] = self._run_check(key)
        except Exception as exc:
            log.warning("Check '%s' failed: %s", key, exc)
            self._results[key] = []

        self._current_index += 1
        self.progress.emit(self._current_index, len(self._enabled))

        QtCore.QTimer.singleShot(0, self._run_next)

    def _run_check(self, key):
        """Execute a single check function."""
        func = _CHECK_FUNC_MAP.get(key)
        if func is None:
            return []

        if key in _SCENE_WIDE_KEYS:
            if key == "scene_units":
                return func(
                    expected_unit=self._params.get("expected_unit", "cm"),
                    expected_upaxis=self._params.get("expected_upaxis", "y"),
                )
            elif key == "file_paths":
                return func(
                    scene_folder=self._params.get("file_paths_scene", "scenes"),
                    tex_folder=self._params.get("file_paths_tex", "sourceimages"),
                    expected_path_type=self._params.get("file_paths_type", "relative"),
                    check_missing=self._params.get("file_paths_missing", True),
                )
            else:
                return func()
        else:
            if key == "naming_check":
                transforms = collect_transform_nodes()
                return func(
                    transforms,
                    regex_pattern=self._params.get("naming_regex", ""),
                )
            else:
                return func(self._targets)
# ---------------------------------------------------------------------------
# [900] entry — Entry point
# ---------------------------------------------------------------------------

def launch():
    """Launch Scene Cleanup Tools (singleton window)."""
    global _sct_window

    # Close existing instance
    try:
        _sct_window.close()
        _sct_window.deleteLater()
    except Exception:
        pass

    _sct_window = MainWindow()
    _sct_window.show()
    _sct_window.raise_()
    return _sct_window


_sct_window = None
