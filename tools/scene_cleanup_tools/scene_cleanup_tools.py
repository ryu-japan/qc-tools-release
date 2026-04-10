# -*- coding: utf-8 -*-
"""Scene Cleanup Tools - Maya scene cleanup checker.

Checks 15 items related to scene state, structure and settings.
Compatible with Maya 2018+ (Python 2.7 / 3, PySide2 / PySide6).
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import sys
import os
import re
import logging
import tempfile
import atexit
import fnmatch
from functools import partial

try:
    from PySide6 import QtCore, QtGui, QtWidgets
    from shiboken6 import wrapInstance
except ImportError:
    from PySide2 import QtCore, QtGui, QtWidgets
    from shiboken2 import wrapInstance

import maya.cmds as cmds
import maya.OpenMayaUI as omui

import webbrowser

try:
    from urllib.request import urlopen, Request
    from urllib.error import URLError
    from urllib.parse import quote as url_quote
except ImportError:
    from urllib2 import urlopen, Request, URLError
    from urllib import quote as url_quote

_url_quote = url_quote
# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
__VERSION__ = "0.31.0"
WINDOW_TITLE = "Scene Cleanup Tools"
WINDOW_OBJECT_NAME = "sceneCleanupToolsWindow"
RESULTS_OBJECT_NAME = "sceneCleanupResultsWindow"
HELP_DIALOG_OBJECT_NAME = "sceneCleanupHelpDialog"
WINDOW_WIDTH = 420
WINDOW_HEIGHT = 660

# Feedback form constants (Google Forms)
_FEEDBACK_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdYhrFiuiYJyLVBzRDR6pPVQihj1y8PsHt3Mg6ZnY5THUGGyQ/viewform"
_FEEDBACK_ENTRY_ID = "entry.1931722805"
_FEEDBACK_ENTRY_TOOL_NAME = "entry.1298102635"
_FEEDBACK_ENTRY_MAYA_VERSION = "entry.1146110608"
_URL_MAX_LENGTH = 8000

# Fix capability: key -> reversible (True=undo-safe, False=irreversible)
# Items not in this dict are not fixable.
_FIX_CAPABLE = {
    "transform": True,
    "instances": True,
    "smooth_preview": True,
    "intermediate_objects": True,
    "unused_nodes": True,
    "unused_mat": True,
    "unused_layers": True,
    "empty_sets": True,
    "unknown_nodes": True,
    "history": False,
    "vertex_tweaks": False,
    "namespaces": False,
    "referenced_nodes": False,
}

# Risk levels for Fix items: high=irreversible/destructive, medium=conditional, low=safe
_RISK_HIGH = "high"
_RISK_MEDIUM = "medium"
_RISK_LOW = "low"

_RISK_LEVELS = {
    "history":              _RISK_HIGH,
    "referenced_nodes":     _RISK_HIGH,
    "unknown_nodes":        _RISK_HIGH,
    "vertex_tweaks":        _RISK_MEDIUM,
    "transform":            _RISK_MEDIUM,
    "instances":            _RISK_MEDIUM,
    "intermediate_objects": _RISK_MEDIUM,
    "unused_nodes":         _RISK_MEDIUM,
    "smooth_preview":       _RISK_LOW,
    "unused_mat":           _RISK_LOW,
    "unused_layers":        _RISK_LOW,
    "empty_sets":           _RISK_LOW,
    "namespaces":           _RISK_LOW,
}



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
    "QMessageBox QLabel {"
    "  font-size: 14px;"
    "}"
    "QMessageBox QPushButton {"
    "  min-width: 80px;"
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

    "btn_reset":             {"en": "Reset",                        "ja": "\u30ea\u30bb\u30c3\u30c8"},

    # -- Check items: Geometry (5) --
    "chk_history":           {"en": "Remaining History",             "ja": "\u6b8b\u5b58\u30d2\u30b9\u30c8\u30ea"},
    "chk_transform":         {"en": "Unfreezed Transforms",          "ja": "\u672a\u30d5\u30ea\u30fc\u30ba\u30c8\u30e9\u30f3\u30b9\u30d5\u30a9\u30fc\u30e0"},
    "chk_vertex_tweaks":     {"en": "Vertex Tweaks",                 "ja": "\u9802\u70b9Tweaks\u6b8b\u7559"},
    "chk_instances":         {"en": "Remaining Instances",           "ja": "\u30a4\u30f3\u30b9\u30bf\u30f3\u30b9\u6b8b\u5b58"},
    "chk_smooth_preview":    {"en": "Smooth Mesh Preview",           "ja": "\u30b9\u30e0\u30fc\u30b9\u30e1\u30c3\u30b7\u30e5\u30d7\u30ec\u30d3\u30e5\u30fc"},

    # -- Check items: Unused (6) --
    "chk_unused_nodes":      {"en": "Empty Groups / Empty Shapes",               "ja": "\u7a7a\u30b0\u30eb\u30fc\u30d7 / \u7a7a\u30b7\u30a7\u30a4\u30d7"},
    "chk_intermediate_objects": {"en": "Intermediate Objects",       "ja": "\u4e2d\u9593\u30aa\u30d6\u30b8\u30a7\u30af\u30c8"},
    "chk_unused_mat":        {"en": "Unused Materials / Textures",   "ja": "\u672a\u4f7f\u7528\u30de\u30c6\u30ea\u30a2\u30eb / \u30c6\u30af\u30b9\u30c1\u30e3"},
    "chk_unused_layers":     {"en": "Unused Layers",                 "ja": "\u672a\u4f7f\u7528\u30ec\u30a4\u30e4\u30fc"},
    "chk_empty_sets":        {"en": "Empty Object Sets",              "ja": "\u7a7a\u30aa\u30d6\u30b8\u30a7\u30af\u30c8\u30bb\u30c3\u30c8"},
    "chk_namespaces":        {"en": "Empty Namespaces",              "ja": "\u7a7a\u30cd\u30fc\u30e0\u30b9\u30da\u30fc\u30b9"},

    # -- Check items: Scene Environment (4) --
    "chk_scene_units":       {"en": "Scene Units / Up-Axis",         "ja": "\u30b7\u30fc\u30f3\u5358\u4f4d / Up\u8ef8"},
    "chk_unknown_nodes":     {"en": "Unknown Nodes",                 "ja": "\u4e0d\u660e\u30ce\u30fc\u30c9"},
    "chk_referenced_nodes":  {"en": "Referenced Nodes",              "ja": "\u30ea\u30d5\u30a1\u30ec\u30f3\u30b9\u30ce\u30fc\u30c9\u6b8b\u5b58"},

    "chk_file_paths":        {"en": "File Paths",                    "ja": "\u30d5\u30a1\u30a4\u30eb\u30d1\u30b9\u30c1\u30a7\u30c3\u30af"},
    "file_paths_scene":      {"en": "Scene",                         "ja": "\u30b7\u30fc\u30f3"},
    "file_paths_tex":        {"en": "Tex",                           "ja": "\u30c6\u30af\u30b9\u30c1\u30e3"},
    "file_paths_relative":   {"en": "Relative",                      "ja": "\u76f8\u5bfe\u30d1\u30b9"},
    "file_paths_absolute":   {"en": "Absolute",                      "ja": "\u7d76\u5bfe\u30d1\u30b9"},
    "file_paths_missing":    {"en": "Missing File",                  "ja": "\u6b20\u640d\u30d5\u30a1\u30a4\u30eb\u691c\u51fa"},

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

    # -- Fix UI --
    "btn_fix_selected":      {"en": "Fix Selected",                   "ja": "選択項目を修正"},
    "fix_confirm_title":     {"en": "Confirm Fix",                    "ja": "修正の確認"},
    "fix_confirm_msg":       {"en": "Fix {count} item(s). Proceed?",  "ja": "{count} 件を修正します。実行しますか？"},
    "fix_result_title":      {"en": "Fix Result",                     "ja": "修正結果"},
    "fix_result_success":    {"en": "Successfully fixed {count} item(s).","ja": "{count} 件を修正しました。"},
    "fix_result_partial":    {"en": "Fixed {fixed}, {failed} failed.","ja": "{fixed} 件を修正、{failed} 件が失敗しました。"},
    "fix_result_all_failed": {"en": "Fix failed for all {count} item(s).","ja": "{count} 件すべて修正に失敗しました。"},
    "fix_confirm_irreversible_warn": {"en": "⚠ This operation cannot be undone.","ja": "⚠ この操作は元に戻せません。"},

    # -- Preflight --
    "preflight_title":       {"en": "Preflight Check",              "ja": "プリチェック"},
    "preflight_warn_header": {"en": "⚠ The following risks were detected:", "ja": "⚠ 以下のリスクを検出:"},
    "preflight_proceed":     {"en": "Proceed anyway?",              "ja": "それでも実行しますか？"},
    "preflight_history_blendshape": {"en": "blendShape {count} — targets will be destroyed", "ja": "blendShape {count} 件 — ターゲットが失われます"},
    "preflight_history_skincluster": {"en": "skinCluster {count} — skin weights will be lost", "ja": "skinCluster {count} 件 — スキンウェイトが失われます"},
    "preflight_history_deformer":   {"en": "Deformer {count} — deformation data will be lost", "ja": "デフォーマ {count} 件 — 変形情報が失われます"},
    "preflight_history_dagpose":     {"en": "bindPose {count} — Go to Bind Pose will stop working", "ja": "bindPose {count} 件 — Go to Bind Pose が機能しなくなります"},
    "preflight_unknown_plugin":     {"en": "Unloaded plugin {count} — may be unrecoverable ({plugins})", "ja": "未ロードプラグイン {count} 件 — 復元不可の可能性があります ({plugins})"},
    "preflight_ref_namespace":      {"en": "Reference {count} — will be imported into scene", "ja": "リファレンス {count} 件 — シーンにインポートされます"},
    "preflight_no_risk":            {"en": "No risky nodes were detected.", "ja": "リスクのあるノードは検出されませんでした。"},

    # -- Status --
    "status_ready":          {"en": "Standby",                       "ja": "\u5f85\u6a5f\u4e2d"},
    "status_running":        {"en": "Checking... {cur}/{total}",     "ja": "\u30c1\u30a7\u30c3\u30af\u4e2d... {cur}/{total}"},
    "status_done":           {"en": "Done. {issues} issue(s) found.","ja": "\u5b8c\u4e86\u3002{issues} \u4ef6\u306e\u554f\u984c\u3092\u691c\u51fa\u3002"},
    "status_cancelled":      {"en": "Cancelled.",                    "ja": "\u30ad\u30e3\u30f3\u30bb\u30eb\u3057\u307e\u3057\u305f\u3002"},
    "report_form_opened":    {"en": "Report copied & form opened.",  "ja": "レポートをコピーし、フォームを開きました。"},
    "report_url_too_long":   {"en": "Report too long for URL. Copied to clipboard -- please paste manually.",
                              "ja": "レポートがURL上限を超えました。クリップボードにコピー済み -- 手動で貼り付けてください。"},
    "report_form_not_configured": {"en": "Feedback form is not configured.", "ja": "フィードバックフォームが未設定です。"},
    "report_empty":          {"en": "No check results to report.",   "ja": "レポートするチェック結果がありません。"},
    "report_copied":         {"en": "Report copied to clipboard.",   "ja": "\u30ec\u30dd\u30fc\u30c8\u3092\u30af\u30ea\u30c3\u30d7\u30dc\u30fc\u30c9\u306b\u30b3\u30d4\u30fc\u3057\u307e\u3057\u305f\u3002"},

    # -- Detail messages --
    "detail_unused_display_layer":  {"en": "Unused display layer",              "ja": "\u672a\u4f7f\u7528\u30c7\u30a3\u30b9\u30d7\u30ec\u30a4\u30ec\u30a4\u30e4\u30fc"},
    "detail_unused_render_layer":   {"en": "Unused render layer",               "ja": "\u672a\u4f7f\u7528\u30ec\u30f3\u30c0\u30fc\u30ec\u30a4\u30e4\u30fc"},
    "detail_unused_animation_layer":{"en": "Unused animation layer",            "ja": "\u672a\u4f7f\u7528\u30a2\u30cb\u30e1\u30fc\u30b7\u30e7\u30f3\u30ec\u30a4\u30e4\u30fc"},
    "detail_loaded":                {"en": "Loaded: {0}",                       "ja": "\u30ed\u30fc\u30c9\u6e08\u307f: {0}"},
    "detail_unloaded":              {"en": "Unloaded: {0}",                     "ja": "\u672a\u30ed\u30fc\u30c9: {0}"},
    "detail_ref_path_unknown":      {"en": "Reference node (path unknown)",     "ja": "\u30ea\u30d5\u30a1\u30ec\u30f3\u30b9\u30ce\u30fc\u30c9\uff08\u30d1\u30b9\u4e0d\u660e\uff09"},
    "detail_vertex_tweaks":          {"en": "{0}/{1} vertices have tweaks",       "ja": "{0}/{1} \u9802\u70b9\u306bTweaks\u3042\u308a"},
    "detail_history":                {"en": "Construction history remains",       "ja": "\u30d2\u30b9\u30c8\u30ea\u3042\u308a"},
    "detail_transform":              {"en": "Transform not frozen",               "ja": "\u672a\u30d5\u30ea\u30fc\u30ba"},
    "detail_instances":              {"en": "{0} instanced shapes",               "ja": "\u30a4\u30f3\u30b9\u30bf\u30f3\u30b9 {0}\u4ef6"},
    "detail_smooth_preview":         {"en": "Smooth preview enabled",             "ja": "\u30b9\u30e0\u30fc\u30b9\u30d7\u30ec\u30d3\u30e5\u30fc\u6709\u52b9"},
    "detail_empty_group":            {"en": "Empty group",                        "ja": "\u7a7a\u30b0\u30eb\u30fc\u30d7"},
    "detail_empty_mesh":             {"en": "Empty mesh",                         "ja": "\u7a7a\u30e1\u30c3\u30b7\u30e5"},
    "detail_intermediate":           {"en": "Intermediate object found",          "ja": "\u4e2d\u9593\u30aa\u30d6\u30b8\u30a7\u30af\u30c8\u3042\u308a"},
    "detail_unused_mat":             {"en": "Unused material ({0})",              "ja": "\u672a\u4f7f\u7528\u30de\u30c6\u30ea\u30a2\u30eb\uff08{0}\uff09"},
    "detail_unused_texture":         {"en": "Unused texture ({0})",               "ja": "\u672a\u4f7f\u7528\u30c6\u30af\u30b9\u30c1\u30e3\uff08{0}\uff09"},
    "detail_unused_utility":         {"en": "Unused utility ({0})",               "ja": "\u672a\u4f7f\u7528\u30e6\u30fc\u30c6\u30a3\u30ea\u30c6\u30a3\uff08{0}\uff09"},
    "detail_empty_set":              {"en": "Empty set",                          "ja": "\u7a7a\u30bb\u30c3\u30c8"},
    "detail_empty_namespace":        {"en": "Empty namespace",                    "ja": "\u7a7a\u30cd\u30fc\u30e0\u30b9\u30da\u30fc\u30b9"},
    "detail_unit_mismatch":          {"en": "Unit: {0} (expected: {1})",           "ja": "\u5358\u4f4d: {0}\uff08\u671f\u5f85\u5024: {1}\uff09"},
    "detail_upaxis_mismatch":        {"en": "Up-axis: {0} (expected: {1})",        "ja": "Up\u8ef8: {0}\uff08\u671f\u5f85\u5024: {1}\uff09"},
    "detail_unknown_node":           {"en": "Unknown node (origType: {0})",        "ja": "\u4e0d\u660e\u30ce\u30fc\u30c9\uff08\u5143\u30bf\u30a4\u30d7: {0}\uff09"},
    "detail_unknown_node_notype":    {"en": "Unknown node",                        "ja": "\u4e0d\u660e\u30ce\u30fc\u30c9"},
    "detail_wrong_folder":           {"en": "Wrong folder name",                   "ja": "\u30d5\u30a9\u30eb\u30c0\u540d\u4e0d\u4e00\u81f4"},
    "detail_expected_relative":      {"en": "Absolute path",                      "ja": "\u7d76\u5bfe\u30d1\u30b9"},
    "detail_expected_absolute":      {"en": "Relative path",                      "ja": "\u76f8\u5bfe\u30d1\u30b9"},
    "detail_missing_file":           {"en": "File not found",                      "ja": "\u30d5\u30a1\u30a4\u30eb\u672a\u691c\u51fa"},

    "detail_editor_artifact_set":     {"en": "Isolate Select set",                 "ja": "Isolate Select セット"},

    # -- Preview risk messages (used by preview_* functions) --
    "preview_warn_anim_keys":    {"en": "Animation keys detected — values will be overwritten by freeze", "ja": "アニメーションキー検出 — フリーズで値が上書きされます"},
    "preview_warn_scale_inherit":{"en": "Non-uniform parent scale — freeze result may differ from intent", "ja": "親スケール非均一 — フリーズ結果が意図と異なる可能性"},
    "preview_warn_blendshape":   {"en": "blendShape {count} connected — removing tweaks may break deformation", "ja": "blendShape {count} 件接続 — Tweaks除去で変形が崩れる可能性"},
    "preview_warn_instance_shared":{"en": "Possibly intentional instance — shared structure will be lost", "ja": "意図的なインスタンスの可能性 — 共有構造が失われます"},
    "preview_warn_transform_intent":{"en": "Possibly intentional values — will be reset by freeze", "ja": "意図的な値の可能性 — フリーズで値がリセットされます"},
    "preview_warn_deformer_break":{"en": "Deformer connected — removal may break deformation", "ja": "デフォーマ接続中 — 削除すると変形が壊れる可能性"},
    "preview_warn_custom_attr":  {"en": "Custom attribute connected — deletion will break references", "ja": "カスタムアトリビュート接続 — 削除で参照が切れます"},
    "preview_warn_expression":   {"en": "Expression reference — deletion may cause script errors", "ja": "エクスプレッション参照 — 削除でスクリプトエラーの可能性"},

    # -- Risk default (shown when no specific per-node risk detected) --
    "risk_not_detected":     {"en": "No risks detected",               "ja": "リスク未検出"},
    "risk_not_applicable":   {"en": "—",                               "ja": "—"},

    # -- Risk / Warning --
    "risk_high":             {"en": "High",                           "ja": "高"},
    "risk_medium":           {"en": "Medium",                         "ja": "中"},
    "risk_low":              {"en": "Low",                             "ja": "低"},
    "risk_dep_col":          {"en": "Dependencies / Risks",           "ja": "依存関係 / リスク"},

    "fix_confirm_neutral_msg":{"en": "Fix {count} item(s).",              "ja": "修正を実行します。\n対象: {count} 件"},
    "warn_high_confirm":     {"en": "This is a HIGH-RISK operation. Really proceed?",
                              "ja": "高リスク操作です。本当に実行しますか？"},
    "fix_select_all_risk_confirm": {"en": "Some items have risks. Check them too?",
                              "ja": "リスクのある項目が含まれています。それらもチェックしますか？"},

    # -- Results --
    "results_summary":       {"en": "{count} issue(s)",              "ja": "{count} \u4ef6"},
    "results_pass":          {"en": "PASS",                          "ja": "OK"},
    "results_node_col":      {"en": "Node",                          "ja": "\u30ce\u30fc\u30c9"},
    "results_detail_col":    {"en": "Detail",                        "ja": "\u8a73\u7d30"},
    "results_all":           {"en": "All",                           "ja": "\u3059\u3079\u3066"},
    "results_no_issues":     {"en": "No nodes detected.",              "ja": "\u691c\u51fa\u30ce\u30fc\u30c9\u306a\u3057"},

    # -- Check item descriptions (for ResultsWindow right panel) --
    "desc_all":                 {"en": "All check results — Click an item header to view details and fix issues.",
                                 "ja": "全チェック項目の結果を表示 — 項目名をクリックで詳細の確認・修正ができます"},
    "desc_fix_hint":            {"en": "You can fix checked items with \"Fix Selected\" below.",
                                 "ja": "チェックした項目は下の「選択項目を修正」で修正できます。"},

    # -- Geometry (5) --
    "desc_history":             {"en": "Detect unnecessary history on meshes",
                                 "ja": "\u30e1\u30c3\u30b7\u30e5\u306e\u4e0d\u8981\u306a\u30d2\u30b9\u30c8\u30ea\u3092\u691c\u51fa"},
    "desc_transform":           {"en": "Detect non-frozen transforms",
                                 "ja": "\u672a\u30d5\u30ea\u30fc\u30ba\u306e\u30c8\u30e9\u30f3\u30b9\u30d5\u30a9\u30fc\u30e0\u3092\u691c\u51fa"},
    "desc_vertex_tweaks":       {"en": "Detect unnecessary vertex edit history (tweaks) on meshes",
                                 "ja": "\u30e1\u30c3\u30b7\u30e5\u306b\u6b8b\u308b\u4e0d\u8981\u306a\u9802\u70b9\u7de8\u96c6\u5c65\u6b74\uff08Tweak\uff09\u3092\u691c\u51fa"},
    "desc_instances":           {"en": "Detect instanced meshes",
                                 "ja": "\u30a4\u30f3\u30b9\u30bf\u30f3\u30b9\u30e1\u30c3\u30b7\u30e5\u3092\u691c\u51fa"},
    "desc_smooth_preview":      {"en": "Detect meshes with smooth preview enabled",
                                 "ja": "\u30b9\u30e0\u30fc\u30b9\u30d7\u30ec\u30d3\u30e5\u30fc\u304c\u6709\u52b9\u306a\u30e1\u30c3\u30b7\u30e5\u3092\u691c\u51fa"},

    # -- Unused (6) --
    "desc_unused_nodes":        {"en": "Detect unused nodes",
                                 "ja": "\u672a\u4f7f\u7528\u30ce\u30fc\u30c9\u3092\u691c\u51fa"},
    "desc_intermediate_objects":{"en": "Detect unnecessary intermediate objects",
                                 "ja": "\u4e0d\u8981\u306a\u4e2d\u9593\u30aa\u30d6\u30b8\u30a7\u30af\u30c8\u3092\u691c\u51fa"},
    "desc_unused_mat":          {"en": "Detect unused materials and textures",
                                 "ja": "\u672a\u4f7f\u7528\u30de\u30c6\u30ea\u30a2\u30eb\u30fb\u30c6\u30af\u30b9\u30c1\u30e3\u3092\u691c\u51fa"},
    "desc_unused_layers":       {"en": "Detect empty layers",
                                 "ja": "\u7a7a\u306e\u30ec\u30a4\u30e4\u30fc\u3092\u691c\u51fa"},
    "desc_empty_sets":          {"en": "Detect empty object sets",
                                 "ja": "\u7a7a\u306e\u30aa\u30d6\u30b8\u30a7\u30af\u30c8\u30bb\u30c3\u30c8\u3092\u691c\u51fa"},
    "desc_namespaces":          {"en": "Detect unnecessary namespaces",
                                 "ja": "\u4e0d\u8981\u306a\u30cd\u30fc\u30e0\u30b9\u30da\u30fc\u30b9\u3092\u691c\u51fa"},

    # -- Scene Environment (4) --
    "desc_scene_units":         {"en": "Check scene units and up-axis settings",
                                 "ja": "\u30b7\u30fc\u30f3\u5358\u4f4d\u3068Up\u8ef8\u306e\u8a2d\u5b9a\u3092\u78ba\u8a8d"},
    "desc_unknown_nodes":       {"en": "Detect unknown node types",
                                 "ja": "\u4e0d\u660e\u306a\u30ce\u30fc\u30c9\u30bf\u30a4\u30d7\u3092\u691c\u51fa"},
    "desc_referenced_nodes":    {"en": "Detect external referenced nodes",
                                 "ja": "\u5916\u90e8\u30ea\u30d5\u30a1\u30ec\u30f3\u30b9\u30ce\u30fc\u30c9\u3092\u691c\u51fa"},
    "desc_file_paths":          {"en": "Detect texture path issues",
                                 "ja": "\u30c6\u30af\u30b9\u30c1\u30e3\u30d1\u30b9\u306e\u4e0d\u5099\u3092\u691c\u51fa"},
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
# [011] help_content — How to Use dialog HTML + README rendering
# ---------------------------------------------------------------------------

# GitHub README URLs (raw content, no API required)
# JA = default README.md, EN = README_en.md (both from release repo)
_README_URLS = {
    "ja": "https://raw.githubusercontent.com/ryu-japan/qc-tools-release/main/tools/scene_cleanup_tools/README.md",
    "en": "https://raw.githubusercontent.com/ryu-japan/qc-tools-release/main/tools/scene_cleanup_tools/README_en.md",
}

# marked.js CDN (ES5 compatible, version-pinned)
_MARKED_CDN = "https://cdn.jsdelivr.net/npm/marked@4.3.0/marked.min.js"

# HTML template for rendering Markdown via marked.js in QWebView/QWebEngineView
# Uses __PLACEHOLDER__ markers to avoid curly-brace conflicts.
# Replace __CDN_URL__ and __ENCODED_MD__ at runtime via str.replace().
_HELP_RENDER_TEMPLATE = (
    '<!DOCTYPE html>'
    '<html><head><meta charset="utf-8"><style>'
    'body{background-color:#2b2b2b;color:#e0e0e0;'
    'font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,'
    'Helvetica,Arial,sans-serif;font-size:14px;line-height:1.6;'
    'padding:16px;margin:0}'
    'h1,h2,h3,h4{color:#fff}'
    'h1{font-size:22px;border-bottom:1px solid #555;padding-bottom:8px}'
    'h2{font-size:18px;border-bottom:1px solid #444;padding-bottom:6px}'
    'h3{font-size:15px}'
    'a{color:#7aa2f7}'
    'code{background-color:#3c3c3c;padding:2px 6px;border-radius:3px;font-size:13px}'
    'pre{background-color:#1e1e1e;padding:12px;border-radius:6px;overflow-x:auto}'
    'pre code{background:none;padding:0}'
    'table{border-collapse:collapse;width:100%;margin:8px 0}'
    'th,td{border:1px solid #555;padding:6px 10px;text-align:left}'
    'th{background-color:#353535}'
    'blockquote{border-left:3px solid #7aa2f7;margin:8px 0;padding:4px 12px;color:#aaa}'
    'ul,ol{padding-left:24px}'
    'li{margin:4px 0}'
    'img{max-width:100%}'
    '</style></head><body>'
    '<div id="content">Loading...</div>'
    '<script src="__CDN_URL__"></script>'
    '<script>'
    'try{'
    'var md=decodeURIComponent("__ENCODED_MD__");'
    'document.getElementById("content").innerHTML=marked.parse(md);'
    '}catch(e){'
    'document.getElementById("content").innerHTML='
    '"<p style=\'color:#ff4444\'>Markdown rendering failed: "+e.message+"</p>";'
    '}'
    '</script></body></html>'
)

# Loading HTML (shown while fetching README)
_HELP_LOADING_HTML = (
    '<!DOCTYPE html>'
    '<html><head><meta charset="utf-8"><style>'
    'body{background-color:#2b2b2b;color:#e0e0e0;'
    'font-family:sans-serif;text-align:center;padding-top:80px}'
    '.spinner{display:inline-block;width:24px;height:24px;'
    'border:3px solid #555;border-top-color:#7aa2f7;'
    'border-radius:50%;animation:spin .8s linear infinite}'
    '@keyframes spin{to{transform:rotate(360deg)}}'
    '</style></head><body>'
    '<div class="spinner"></div>'
    '<p>Loading README from GitHub...</p>'
    '</body></html>'
)

# Error HTML template (shown on fetch failure, with fallback help content)
# Replace __ERROR_MSG__ and __FALLBACK_HTML__ at runtime via str.replace().
_HELP_ERROR_TEMPLATE = (
    '<!DOCTYPE html>'
    '<html><head><meta charset="utf-8"><style>'
    'body{background-color:#2b2b2b;color:#e0e0e0;'
    'font-family:sans-serif;padding:16px}'
    '.error-banner{background-color:#3a2020;border:1px solid #ff4444;'
    'border-radius:6px;padding:8px 12px;margin-bottom:16px;'
    'color:#ff8888;font-size:12px}'
    'h2,h3{color:#fff}'
    'b{color:#e0e0e0}'
    'i{color:#aaa}'
    '</style></head><body>'
    '<div class="error-banner">\u26a0 __ERROR_MSG__</div>'
    '__FALLBACK_HTML__'
    '</body></html>'
)

# Fallback help content (original static HTML, used when offline)
_HELP_FALLBACK_HTML = {
    "en": """
<h2>Scene Cleanup Tools \u2014 How to Use</h2>
<h3>Check Scope</h3>
<p>All mesh nodes in the scene are checked automatically.</p>
<p><i>Note: Scene-wide items (Empty Groups, Unused Materials, Unused Layers,
Empty Sets, Namespaces, Unknown Nodes, Referenced Nodes,
Scene Units, File Paths) always scan the entire scene.</i></p>
<h3>Check Items (15)</h3>
<p><b>Geometry (5)</b> \u2014 History, transforms, vertex tweaks, instances,
smooth mesh preview.</p>
<p><b>Unused (6)</b> \u2014 Empty groups/shapes, intermediate objects,
unused materials, unused layers, empty sets, namespaces.</p>
<p><b>Scene Environment (4)</b> \u2014 Scene units, unknown nodes,
referenced nodes, file paths.</p>
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
<p><i>\u203b \u30b7\u30fc\u30f3\u5168\u4f53\u9805\u76ee\uff08\u7a7a\u30b0\u30eb\u30fc\u30d7\u3001\u672a\u4f7f\u7528\u30de\u30c6\u30ea\u30a2\u30eb\u3001\u672a\u4f7f\u7528\u30ec\u30a4\u30e4\u30fc\u3001\u7a7a\u30bb\u30c3\u30c8\u3001\u30cd\u30fc\u30e0\u30b9\u30da\u30fc\u30b9\u3001\u4e0d\u660e\u30ce\u30fc\u30c9\u3001\u30ea\u30d5\u30a1\u30ec\u30f3\u30b9\u30ce\u30fc\u30c9\u3001\u30b7\u30fc\u30f3\u5358\u4f4d\u3001\u30d5\u30a1\u30a4\u30eb\u30d1\u30b9\uff09\u306f\u5e38\u306b\u30b7\u30fc\u30f3\u5168\u4f53\u3092\u30b9\u30ad\u30e3\u30f3\u3057\u307e\u3059\u3002</i></p>
<h3>\u30c1\u30a7\u30c3\u30af\u9805\u76ee\uff0815\uff09</h3>
<p><b>\u30b8\u30aa\u30e1\u30c8\u30ea\uff085\uff09</b> \u2014 \u30d2\u30b9\u30c8\u30ea\u3001\u30c8\u30e9\u30f3\u30b9\u30d5\u30a9\u30fc\u30e0\u3001\u9802\u70b9Tweaks\u3001\u30a4\u30f3\u30b9\u30bf\u30f3\u30b9\u3001\u30b9\u30e0\u30fc\u30b9\u30d7\u30ec\u30d3\u30e5\u30fc\u3002</p>
<p><b>\u672a\u4f7f\u7528\u30fb\u4e0d\u8981\u30ce\u30fc\u30c9\uff086\uff09</b> \u2014 \u7a7a\u30b0\u30eb\u30fc\u30d7/\u7a7a\u30b7\u30a7\u30a4\u30d7\u3001\u4e2d\u9593\u30aa\u30d6\u30b8\u30a7\u30af\u30c8\u3001\u672a\u4f7f\u7528\u30de\u30c6\u30ea\u30a2\u30eb\u3001\u672a\u4f7f\u7528\u30ec\u30a4\u30e4\u30fc\u3001\u7a7a\u30bb\u30c3\u30c8\u3001\u30cd\u30fc\u30e0\u30b9\u30da\u30fc\u30b9\u3002</p>
<p><b>\u30b7\u30fc\u30f3\u74b0\u5883\uff084\uff09</b> \u2014 \u30b7\u30fc\u30f3\u5358\u4f4d\u3001\u4e0d\u660e\u30ce\u30fc\u30c9\u3001\u30ea\u30d5\u30a1\u30ec\u30f3\u30b9\u30ce\u30fc\u30c9\u3001\u30d5\u30a1\u30a4\u30eb\u30d1\u30b9\u3002</p>
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

# Default camera nodes (transforms + shapes) — excluded from scene-wide checks
DEFAULT_CAMERAS = frozenset([
    "|persp", "|top", "|front", "|side",
    "|persp|perspShape", "|top|topShape",
    "|front|frontShape", "|side|sideShape",
])


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



def get_top_nodes(nodes):
    """Return unique top-level transform ancestors for *nodes*."""
    tops = set()
    for n in nodes:
        parts = n.split("|")
        if len(parts) > 1:
            tops.add("|".join(parts[:2]))
    return sorted(tops)


# ---------------------------------------------------------------------------
# Preflight checks (Phase 1 — high-risk Fix items)
# ---------------------------------------------------------------------------
# Each function returns {"safe": bool, "warnings": list[str]}

def preflight_history(nodes):
    """Preflight for history deletion: detect blendShape / deformer / dagPose deps.

    Returns warnings only for specific risks (blendShape/deformer/dagPose).
    Returns empty when no risk — unified fallback handles display.
    """
    warnings = []
    bs_count = 0
    deformer_count = 0
    skin_count = 0
    dagpose_nodes = set()
    history_types = set()
    for node in nodes:
        hist = cmds.listHistory(node, pdo=True) or []
        shapes = cmds.listRelatives(node, shapes=True, fullPath=True) or []
        hist = [h for h in hist if h not in shapes]
        for h in hist:
            nt = cmds.nodeType(h)
            history_types.add(nt)
            if nt == "blendShape":
                bs_count += 1
            elif nt == "skinCluster":
                skin_count += 1
            elif nt in ("wire", "wrap", "lattice",
                        "nonLinear", "cluster", "sculpt", "ffd",
                        "deltaMush", "tension", "shrinkWrap"):
                deformer_count += 1
            # dagPose is not returned by listHistory; detect via listConnections
            conns = cmds.listConnections(h, type="dagPose") or []
            dagpose_nodes.update(conns)
        # dagPose may also be connected directly to the transform node
        direct_conns = cmds.listConnections(node, type="dagPose") or []
        dagpose_nodes.update(direct_conns)
    dagpose_count = len(dagpose_nodes)
    has_risk = (bs_count > 0 or deformer_count > 0 or skin_count > 0
                or dagpose_count > 0)
    if bs_count > 0:
        warnings.append(tr("preflight_history_blendshape", count=bs_count))
    if skin_count > 0:
        warnings.append(tr("preflight_history_skincluster", count=skin_count))
    if deformer_count > 0:
        warnings.append(tr("preflight_history_deformer", count=deformer_count))
    if dagpose_count > 0:
        warnings.append(tr("preflight_history_dagpose", count=dagpose_count))
    return {"safe": not has_risk, "warnings": warnings}


def preflight_unknown_nodes(nodes):
    """Preflight for unknown node deletion: check unloaded plugins.

    Returns warnings only for unloaded-plugin risk.
    Returns empty when no risk — unified fallback handles display.
    """
    warnings = []
    try:
        loaded_plugins = set(cmds.pluginInfo(query=True, listPlugins=True) or [])
    except Exception:
        loaded_plugins = set()
    # Build set of node types registered by loaded plugins
    loaded_types = set()
    for plug in loaded_plugins:
        try:
            types = cmds.pluginInfo(plug, query=True, dependNode=True) or []
            loaded_types.update(types)
        except Exception:
            pass
    unloaded_types = {}
    for node in nodes:
        real_type = None
        try:
            real_type = cmds.unknownNode(node, query=True, realClassName=True)
        except Exception:
            continue
        if not real_type:
            continue
        if real_type not in loaded_types:
            unloaded_types.setdefault(real_type, []).append(node)
    has_risk = bool(unloaded_types)
    if unloaded_types:
        total = sum(len(v) for v in unloaded_types.values())
        type_names = ", ".join(sorted(unloaded_types.keys()))
        warnings.append(
            tr("preflight_unknown_plugin", count=total, plugins=type_names)
        )
    return {"safe": not has_risk, "warnings": warnings}


def preflight_referenced_nodes(nodes):
    """Preflight for reference import: warn about all referenced nodes."""
    warnings = []
    # Filter out nodes that no longer exist in the scene
    ref_count = len([n for n in nodes if cmds.objExists(n)])
    if ref_count > 0:
        warnings.append(
            tr("preflight_ref_namespace", count=ref_count)
        )
    return {"safe": len(warnings) == 0, "warnings": warnings}


_PREFLIGHT_DISPATCH = {
    "history": preflight_history,
    "unknown_nodes": preflight_unknown_nodes,
    "referenced_nodes": preflight_referenced_nodes,
}


def _open_feedback_form(report_text):
    """Open feedback form with report pre-filled via URL parameter.
    Returns (success, message_key)."""
    if not _FEEDBACK_FORM_URL or not _FEEDBACK_ENTRY_ID:
        return False, "report_form_not_configured"
    try:
        encoded = _url_quote(report_text, safe='')
    except TypeError:
        # Python 2: quote() requires bytes, not unicode
        encoded = _url_quote(report_text.encode('utf-8'), safe=b'')
    # Build tool name and Maya version parameters
    tool_name = "Scene Cleanup Tools {0}".format(__VERSION__)
    maya_ver = cmds.about(version=True)
    try:
        tool_enc = _url_quote(tool_name, safe='')
        ver_enc = _url_quote(maya_ver, safe='')
    except TypeError:
        tool_enc = _url_quote(tool_name.encode('utf-8'), safe=b'')
        ver_enc = _url_quote(maya_ver.encode('utf-8'), safe=b'')
    tool_key = _FEEDBACK_ENTRY_TOOL_NAME
    tool_resp_key = tool_key + ".other_option_response"
    ver_key = _FEEDBACK_ENTRY_MAYA_VERSION
    ver_resp_key = ver_key + ".other_option_response"
    url = "{0}?{1}={2}&{3}=__other_option__&{4}={5}&{6}=__other_option__&{7}={8}".format(
        _FEEDBACK_FORM_URL,
        _FEEDBACK_ENTRY_ID, encoded,
        tool_key, tool_resp_key, tool_enc,
        ver_key, ver_resp_key, ver_enc)
    if len(url) > _URL_MAX_LENGTH:
        # Fallback: open with tool/version params only (drop report text)
        fallback = "{0}?{1}=__other_option__&{2}={3}&{4}=__other_option__&{5}={6}".format(
            _FEEDBACK_FORM_URL,
            tool_key, tool_resp_key, tool_enc,
            ver_key, ver_resp_key, ver_enc)
        webbrowser.open(fallback)
        return True, "report_url_too_long"
    webbrowser.open(url)
    return True, "report_form_opened"
# ---------------------------------------------------------------------------
# [100] geometry — Check functions A: Geometry
# ---------------------------------------------------------------------------
# Each function signature: check_<key>(targets) -> list[dict]
#   targets: list of mesh transform long-names
#   returns: list of {"node": str, "detail": str}



# Node types returned by listHistory that are NOT construction history
_HISTORY_EXCLUDE_TYPES = frozenset(["shadingEngine", "groupId", "objectSet"])


def check_history(targets):
    """Check for remaining construction history."""
    results = []
    for target in targets:
        hist = cmds.listHistory(target, pdo=True)
        if hist is None:
            continue
        shapes = cmds.listRelatives(target, shapes=True, fullPath=True) or []
        hist = [h for h in hist
                if h not in shapes
                and cmds.nodeType(h) not in _HISTORY_EXCLUDE_TYPES]
        if hist:
            results.append({"node": target, "detail": tr("detail_history")})
    return results


def check_transform(targets):
    """Check for unfreezed transforms.

    Instanced nodes are excluded because makeIdentity produces
    unpredictable results on shared shapes.
    """
    results = []
    for target in targets:
        # Skip instances (shape shared by multiple parents)
        shapes = cmds.listRelatives(target, shapes=True, fullPath=True) or []
        is_instance = False
        for shape in shapes:
            parents = cmds.listRelatives(shape, allParents=True, fullPath=True)
            if parents and len(parents) >= 2:
                is_instance = True
                break
        if is_instance:
            continue
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


# -- Preview functions (Phase 2: medium-risk impact analysis) --------------

def preview_transform(nodes):
    """Dry-run analysis for transform fix: detect anim keys & scale inheritance.

    Returns list of {node, action, risks} dicts.
    """
    previews = []
    for node in nodes:
        if not cmds.objExists(node):
            continue
        risks = []
        # Check for animation keys
        anim_curves = cmds.listConnections(node, type="animCurve") or []
        if anim_curves:
            risks.append(tr("preview_warn_anim_keys"))
        # Check parent scale inheritance
        parent = cmds.listRelatives(node, parent=True, fullPath=True)
        if parent:
            try:
                ps = cmds.getAttr(parent[0] + ".scale")[0]
                if any(abs(v - 1.0) > 1e-6 for v in ps):
                    risks.append(tr("preview_warn_scale_inherit"))
            except Exception:
                pass
        if not risks:
            risks.append(tr("preview_warn_transform_intent"))
        previews.append({
            "node": node,
            "action": "Freeze Transforms",
            "risks": risks,
        })
    return previews


def preview_vertex_tweaks(nodes):
    """Dry-run analysis for vertex_tweaks fix: detect blendShape connections.

    Returns list of {node, action, risks} dicts.
    """
    previews = []
    for node in nodes:
        if not cmds.objExists(node):
            continue
        risks = []
        shapes = cmds.listRelatives(node, shapes=True, fullPath=True,
                                    type="mesh") or []
        bs_count = 0
        for shape in shapes:
            if cmds.getAttr(shape + ".intermediateObject"):
                continue
            bs_nodes = cmds.listConnections(shape, type="blendShape") or []
            bs_count += len(set(bs_nodes))
        if bs_count > 0:
            risks.append(tr("preview_warn_blendshape", count=bs_count))
        previews.append({
            "node": node,
            "action": "Freeze pnts (polyMoveVertex + deleteHistory)",
            "risks": risks,
        })
    return previews


def preview_instances(nodes):
    """Dry-run analysis for instances fix: all instances carry shared-structure risk.

    Returns list of {node, action, risks} dicts.
    """
    previews = []
    for node in nodes:
        if not cmds.objExists(node):
            continue
        previews.append({
            "node": node,
            "action": "Uninstance (duplicate + delete original)",
            "risks": [tr("preview_warn_instance_shared")],
        })
    return previews


# -- Fix functions (Phase A: A-4, A-5 / Phase B: B-1) ---------------------

def fix_transform(nodes):
    """Freeze transforms on given nodes (makeIdentity). Undo-safe."""
    fixed = 0
    failed = 0
    for node in nodes:
        if not cmds.objExists(node):
            failed += 1
            continue
        try:
            cmds.makeIdentity(node, apply=True, translate=True,
                              rotate=True, scale=True, normal=0)
            fixed += 1
        except Exception as exc:
            log.warning("fix_transform: %s failed: %s", node, exc)
            failed += 1
    return fixed, failed


def fix_smooth_preview(nodes):
    """Reset displaySmoothMesh to 0 on given nodes. Undo-safe."""
    fixed = 0
    failed = 0
    for node in nodes:
        if not cmds.objExists(node):
            failed += 1
            continue
        shapes = cmds.listRelatives(node, shapes=True, fullPath=True) or []
        node_fixed = False
        for shape in shapes:
            try:
                if cmds.getAttr(shape + ".displaySmoothMesh") != 0:
                    cmds.setAttr(shape + ".displaySmoothMesh", 0)
                    node_fixed = True
            except Exception as exc:
                log.warning("fix_smooth_preview: %s failed: %s", shape, exc)
        if node_fixed:
            fixed += 1
        elif shapes:
            failed += 1
    return fixed, failed


def fix_history(nodes):
    """Delete all construction history on given nodes. IRREVERSIBLE."""
    fixed = 0
    failed = 0
    for node in nodes:
        if not cmds.objExists(node):
            failed += 1
            continue
        try:
            cmds.delete(node, constructionHistory=True)
            fixed += 1
        except Exception as exc:
            log.warning("fix_history: %s failed: %s", node, exc)
            failed += 1
    return fixed, failed


def fix_vertex_tweaks(nodes):
    """Freeze vertex tweaks (pnts) via polyMoveVertex + history delete. IRREVERSIBLE."""
    fixed = 0
    failed = 0
    for node in nodes:
        if not cmds.objExists(node):
            failed += 1
            continue
        shapes = cmds.listRelatives(node, shapes=True, fullPath=True,
                                    type="mesh")
        if not shapes:
            failed += 1
            continue
        node_fixed = False
        for shape in shapes:
            if cmds.getAttr(shape + ".intermediateObject"):
                continue
            try:
                pnts_size = cmds.getAttr(shape + ".pnts", size=True)
            except Exception:
                continue
            if not pnts_size:
                continue
            try:
                pnts = cmds.getAttr(shape + ".pnts[*]")
            except Exception:
                continue
            if pnts is None:
                continue
            has_tweaks = any(
                abs(pt[0]) > 1e-7 or abs(pt[1]) > 1e-7 or abs(pt[2]) > 1e-7
                for pt in pnts
            )
            if has_tweaks:
                try:
                    cmds.polyMoveVertex(shape, localTranslate=(0, 0, 0))
                    cmds.delete(shape, constructionHistory=True)
                    node_fixed = True
                except Exception as exc:
                    log.warning("fix_vertex_tweaks: %s failed: %s", shape, exc)
        if node_fixed:
            fixed += 1
        else:
            failed += 1
    return fixed, failed


def fix_instances(nodes):
    """Uninstance given nodes by duplicating unique copies. Undo-safe."""
    fixed = 0
    failed = 0
    for node in nodes:
        if not cmds.objExists(node):
            failed += 1
            continue
        try:
            parent = cmds.listRelatives(node, parent=True, fullPath=True)
            short_name = node.rsplit("|", 1)[-1] if "|" in node else node
            dup = cmds.duplicate(node, returnRootsOnly=True)
            if not dup:
                failed += 1
                continue
            cmds.delete(node)
            if parent and cmds.objExists(parent[0]):
                moved = cmds.parent(dup[0], parent[0])
                cmds.rename(moved[0], short_name)
            else:
                cmds.rename(dup[0], short_name)
            fixed += 1
        except Exception as exc:
            log.warning("fix_instances: %s failed: %s", node, exc)
            failed += 1
    return fixed, failed
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
    skip_cameras = DEFAULT_CAMERAS
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
                if cmds.objectType(ch, isAType="transform"):
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


# Editor artifact objectSet name patterns (Isolate Select auto-generated)
_EDITOR_ARTIFACT_PATTERNS = [
    "*textureEditorIsolateSelectSet*",
    "*modelPanelViewSelectedSet*",
]


def check_empty_sets():
    """Check for empty or unused object sets.

    Also detects editor artifact objectSets (Isolate Select) regardless
    of member count, as they are session data and safe to delete.
    """
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
    # Track nodes already reported as editor artifacts to avoid duplicates
    artifact_reported = set()

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
        # Editor artifact detection (Isolate Select sets — may have members)
        is_artifact = False
        for pattern in _EDITOR_ARTIFACT_PATTERNS:
            if fnmatch.fnmatchcase(short_name, pattern):
                is_artifact = True
                break
        if is_artifact:
            if short_name not in artifact_reported:
                results.append({"node": short_name, "detail": tr("detail_editor_artifact_set")})
                artifact_reported.add(short_name)
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


# -- Preview functions (Phase 2: medium-risk impact analysis) --------------

def preview_intermediate_objects(nodes):
    """Dry-run analysis for intermediate_objects fix: detect deformer-connected Orig shapes.

    Returns list of {node, action, risks} dicts.
    """
    previews = []
    for node in nodes:
        if not cmds.objExists(node):
            continue
        risks = []
        shapes = cmds.listRelatives(node, shapes=True, fullPath=True) or []
        intermediates = [s for s in shapes
                         if cmds.getAttr(s + ".intermediateObject")]
        for inter_shape in intermediates:
            # Check if connected to deformers
            deformers = cmds.listConnections(
                inter_shape, type="geometryFilter") or []
            if deformers:
                risks.append(tr("preview_warn_deformer_break"))
                break
        previews.append({
            "node": node,
            "action": "Delete intermediate objects",
            "risks": risks,
        })
    return previews


def preview_unused_nodes(nodes):
    """Dry-run analysis for unused_nodes fix: scan for custom attr / expression refs.

    Returns list of {node, action, risks} dicts.
    """
    previews = []
    # Pre-scan: build set of expression-referenced nodes.
    # NOTE: Uses simple substring match (short_name in expr_string).
    # This may produce false positives (e.g. node "box" matching "sandbox").
    # Acceptable because this is a best-effort preview — users can exclude
    # false positives via the PreviewDialog's exclude checkboxes.
    expr_referenced = set()
    try:
        all_exprs = cmds.ls(type="expression") or []
        for expr_node in all_exprs:
            try:
                expr_str = cmds.getAttr(expr_node + ".expression") or ""
            except Exception:
                continue
            for node in nodes:
                short = node.rsplit("|", 1)[-1] if "|" in node else node
                if short in expr_str:
                    expr_referenced.add(node)
    except Exception:
        pass

    for node in nodes:
        if not cmds.objExists(node):
            continue
        risks = []
        # Check custom attributes referencing this node
        try:
            user_attrs = cmds.listAttr(node, userDefined=True) or []
            if user_attrs:
                # Check if any other node connects to these attrs
                for attr in user_attrs:
                    conns = cmds.listConnections(
                        node + "." + attr, source=True,
                        destination=True) or []
                    if conns:
                        risks.append(tr("preview_warn_custom_attr"))
                        break
        except Exception:
            pass
        # Check expression references
        if node in expr_referenced:
            risks.append(tr("preview_warn_expression"))
        previews.append({
            "node": node,
            "action": "Delete node",
            "risks": risks,
        })
    return previews


# -- Fix functions (Phase A: A-6, A-7, A-8 / Phase B: B-2, B-3) -----------

def fix_namespaces(nodes):
    """Remove empty namespaces. IRREVERSIBLE."""
    fixed = 0
    failed = 0
    for node in nodes:
        ns = node.lstrip(":")
        if not ns:
            failed += 1
            continue
        try:
            cmds.namespace(removeNamespace=ns)
            fixed += 1
        except Exception as exc:
            log.warning("fix_namespaces: %s failed: %s", ns, exc)
            failed += 1
    return fixed, failed


def fix_unused_mat(nodes):
    """Delete unused material/texture nodes. Undo-safe."""
    fixed = 0
    failed = 0
    for node in nodes:
        if not cmds.objExists(node):
            failed += 1
            continue
        try:
            cmds.delete(node)
            fixed += 1
        except Exception as exc:
            log.warning("fix_unused_mat: %s failed: %s", node, exc)
            failed += 1
    return fixed, failed


def fix_unused_layers(nodes):
    """Delete unused layer nodes. Undo-safe.

    Maya may raise exceptions during layer deletion due to internal
    connection cleanup (animLayerManager, renderSetup, etc.) even when
    the node is actually removed.  Rather than relying on objExists
    (which can return stale results), we snapshot the scene's layer
    nodes before and after deletion and compare.
    """
    if not nodes:
        return 0, 0

    # Snapshot: all layer nodes currently in the scene.
    def _all_layers():
        return set(
            (cmds.ls(type="displayLayer") or [])
            + (cmds.ls(type="renderLayer") or [])
            + (cmds.ls(type="animLayer") or [])
        )

    before = _all_layers()

    # Attempt deletion — ignore exceptions (Maya may raise even on success).
    for node in nodes:
        if node not in before:
            continue
        try:
            cmds.delete(node)
        except Exception as exc:
            log.debug("fix_unused_layers: %s raised during delete: %s", node, exc)

    # Re-scan to determine actual outcome.
    after = _all_layers()

    fixed = 0
    failed = 0
    for node in nodes:
        if node not in before:
            # Was already gone before we started.
            failed += 1
        elif node not in after:
            fixed += 1
        else:
            log.warning("fix_unused_layers: %s still exists after delete", node)
            failed += 1

    return fixed, failed


def fix_empty_sets(nodes):
    """Delete empty object sets. Undo-safe.

    Handles locked nodes (e.g. Turtle plugin nodes) by unlocking
    before deletion. If deletion still fails, the node is skipped.
    """
    fixed = 0
    failed = 0
    for node in nodes:
        if not cmds.objExists(node):
            failed += 1
            continue
        try:
            # Unlock if locked (e.g. Turtle plugin nodes)
            if cmds.lockNode(node, query=True, lock=True)[0]:
                cmds.lockNode(node, lock=False)
            cmds.delete(node)
            fixed += 1
        except Exception as exc:
            log.warning("fix_empty_sets: %s failed: %s", node, exc)
            failed += 1
    return fixed, failed


def fix_intermediate_objects(nodes):
    """Delete intermediate (construction) objects on given nodes. Undo-safe."""
    fixed = 0
    failed = 0
    for node in nodes:
        if not cmds.objExists(node):
            failed += 1
            continue
        shapes = cmds.listRelatives(node, shapes=True, fullPath=True)
        if not shapes:
            failed += 1
            continue
        intermediates = [s for s in shapes
                         if cmds.getAttr(s + ".intermediateObject")]
        if not intermediates:
            failed += 1
            continue
        try:
            cmds.delete(intermediates)
            fixed += 1
        except Exception as exc:
            log.warning("fix_intermediate_objects: %s failed: %s", node, exc)
            failed += 1
    return fixed, failed


def fix_unused_nodes(nodes):
    """Delete unused nodes (empty groups, empty shapes). Undo-safe."""
    fixed = 0
    failed = 0
    for node in nodes:
        if not cmds.objExists(node):
            failed += 1
            continue
        try:
            cmds.delete(node)
            fixed += 1
        except Exception as exc:
            log.warning("fix_unused_nodes: %s failed: %s", node, exc)
            failed += 1
    return fixed, failed
# ---------------------------------------------------------------------------
# [300] scene_env — Check functions C: Scene Environment
# ---------------------------------------------------------------------------
# Scene-wide checks; they scan the entire scene.



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


# -- Fix functions (Phase B: B-4) ------------------------------------------

def fix_referenced_nodes(nodes):
    """Import references into the scene. IRREVERSIBLE."""
    fixed = 0
    failed = 0
    for node in nodes:
        if not cmds.objExists(node):
            failed += 1
            continue
        try:
            ref_file = cmds.referenceQuery(node, filename=True)
            cmds.file(ref_file, importReference=True)
            fixed += 1
        except Exception as exc:
            log.warning("fix_referenced_nodes: %s failed: %s", node, exc)
            failed += 1
    return fixed, failed


def fix_unknown_nodes(nodes):
    """Delete unknown plugin nodes. Undo-safe."""
    fixed = 0
    failed = 0
    for node in nodes:
        if not cmds.objExists(node):
            failed += 1
            continue
        try:
            locked = cmds.lockNode(node, query=True, lock=True)
            if locked and locked[0]:
                cmds.lockNode(node, lock=False)
            cmds.delete(node)
            fixed += 1
        except Exception as exc:
            log.warning("fix_unknown_nodes: %s failed: %s", node, exc)
            failed += 1
    return fixed, failed
# ---------------------------------------------------------------------------
# [800] ui — Main Window, Results Window, Help Dialog, Category UI
# ---------------------------------------------------------------------------

# Fix dispatch map (key -> fix function)
_FIX_DISPATCH = {
    "transform": fix_transform,
    "smooth_preview": fix_smooth_preview,
    "instances": fix_instances,
    "intermediate_objects": fix_intermediate_objects,
    "unused_nodes": fix_unused_nodes,
    "unused_mat": fix_unused_mat,
    "unused_layers": fix_unused_layers,
    "empty_sets": fix_empty_sets,
    "unknown_nodes": fix_unknown_nodes,
    "history": fix_history,
    "vertex_tweaks": fix_vertex_tweaks,
    "namespaces": fix_namespaces,
    "referenced_nodes": fix_referenced_nodes,
}

# Risk text colors for right-panel node rows
_RISK_TEXT_COLORS = {
    _RISK_HIGH:   "#ff4444",
    _RISK_MEDIUM: "#ffaa00",
}

# (Warning bar styles removed — risk info now shown in confirmation dialogs)

# Fallback risk messages (legacy — now empty; unified default in _on_item_selected)
_RISK_FALLBACK = {}

def _risk_sort_key(e):
    """Sort key: no-risk first, then group by risk type."""
    return (bool(e.get("risks")), (e.get("risks") or [""])[0])

# Preview dispatch for right-panel risk display (lazy evaluation)
_RISK_PREVIEW_DISPATCH = {
    "transform":            preview_transform,
    "vertex_tweaks":        preview_vertex_tweaks,
    "instances":            preview_instances,
    "intermediate_objects": preview_intermediate_objects,
    "unused_nodes":         preview_unused_nodes,
}

# Utility: show QMessageBox without built-in icon.
# Text-level emoji in tr() strings serves as the visual indicator.
# Inherits parent QSS (dark theme + custom buttons) via parent arg.
def _show_msgbox(parent, icon_type, title, text, buttons=None, default_btn=None):
    if buttons is None:
        buttons = QtWidgets.QMessageBox.Ok
    if default_btn is None:
        default_btn = buttons
    # icon_type is accepted for call-site readability (semantic intent)
    # but not passed to QMessageBox to suppress the built-in icon.
    mb = QtWidgets.QMessageBox(parent)
    mb.setWindowTitle(title)
    mb.setText(text)
    mb.setStandardButtons(buttons)
    mb.setDefaultButton(default_btn)
    return mb.exec_()

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


# ===== ReadmeWorker =========================================================

class ReadmeWorker(QtCore.QThread):
    """Fetch README.md from GitHub in a background thread."""
    finished = QtCore.Signal(str, str, str)  # (lang, markdown_text, error_message)

    def __init__(self, url, lang, parent=None):
        super(ReadmeWorker, self).__init__(parent)
        self._url = url
        self._lang = lang

    def run(self):
        try:
            req = Request(self._url)
            req.add_header("User-Agent", "Maya-SceneCleanupTools")
            resp = urlopen(req, timeout=10)
            data = resp.read()
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            self.finished.emit(self._lang, data, "")
        except URLError as e:
            self.finished.emit(self._lang, "", str(e))
        except Exception as e:
            self.finished.emit(self._lang, "", str(e))


# ===== Web view import (QWebEngineView / QWebView auto-detect) ==============

_WebView = None
try:
    from PySide6.QtWebEngineWidgets import QWebEngineView as _WebView
except ImportError:
    pass
if _WebView is None:
    try:
        from PySide2.QtWebEngineWidgets import QWebEngineView as _WebView
    except ImportError:
        pass
if _WebView is None:
    try:
        from PySide2.QtWebKitWidgets import QWebView as _WebView
    except ImportError:
        pass


# ===== HelpDialog ==========================================================

class HelpDialog(QtWidgets.QDialog):
    """Help dialog that displays GitHub README via QWebView/QWebEngineView.

    Falls back to QTextBrowser with static help HTML when no web view
    widget is available or when the README fetch fails.
    """

    def __init__(self, parent=None):
        super(HelpDialog, self).__init__(parent)
        self.setObjectName(HELP_DIALOG_OBJECT_NAME)
        self.setWindowTitle(tr("btn_howto"))
        self.setMinimumSize(520, 560)
        self.setStyleSheet(_QSS)

        self._readme_cache = {}  # lang -> markdown_text
        self._current_help_lang = None
        self._worker = None
        self._use_webview = _WebView is not None

        layout = QtWidgets.QVBoxLayout(self)

        if self._use_webview:
            self._view = _WebView()
            layout.addWidget(self._view)
        else:
            self._view = QtWidgets.QTextBrowser()
            self._view.setOpenExternalLinks(True)
            layout.addWidget(self._view)

        btn_close = QtWidgets.QPushButton(tr("btn_close"))
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)

    def showEvent(self, event):
        super(HelpDialog, self).showEvent(event)
        self._load_for_lang(_current_lang)

    def _load_for_lang(self, lang):
        """Show README for the given language, fetching if needed."""
        if self._current_help_lang == lang:
            return
        self._current_help_lang = lang

        # Check cache first
        cached = self._readme_cache.get(lang)
        if cached:
            self._render_readme(cached)
            return

        if not self._use_webview:
            fallback = _HELP_FALLBACK_HTML.get(
                lang, _HELP_FALLBACK_HTML.get("en", ""))
            self._view.setHtml(fallback)
            return

        self._fetch_readme(lang)

    def _fetch_readme(self, lang):
        """Start async README fetch for the given language."""
        self._view.setHtml(_HELP_LOADING_HTML)
        url = _README_URLS.get(lang, _README_URLS.get("ja", ""))
        self._worker = ReadmeWorker(url, lang, parent=self)
        self._worker.finished.connect(self._on_readme_loaded)
        self._worker.start()

    def _on_readme_loaded(self, lang, markdown_text, error_msg):
        """Handle README fetch result.

        Caches successful results regardless of current language.
        Only renders if lang still matches the active help language
        (avoids race when user switches language mid-fetch).
        """
        self._worker = None
        if error_msg or not markdown_text:
            # Only show error if this is still the requested language
            if lang == self._current_help_lang:
                fallback = _HELP_FALLBACK_HTML.get(
                    lang, _HELP_FALLBACK_HTML.get("en", ""))
                err = error_msg or "Empty response from GitHub"
                html = (_HELP_ERROR_TEMPLATE
                        .replace("__ERROR_MSG__", err)
                        .replace("__FALLBACK_HTML__", fallback))
                self._view.setHtml(html)
            return

        self._readme_cache[lang] = markdown_text
        # Only render if this is still the requested language
        if lang == self._current_help_lang:
            self._render_readme(markdown_text)

    def _render_readme(self, markdown_text):
        """Render README markdown via marked.js template."""
        try:
            encoded = _url_quote(markdown_text.encode("utf-8"), safe="")
            html = (_HELP_RENDER_TEMPLATE
                    .replace("__CDN_URL__", _MARKED_CDN)
                    .replace("__ENCODED_MD__", encoded))
            self._view.setHtml(html)
        except Exception as e:
            log.warning("README render failed: %s", e)
            fallback = _HELP_FALLBACK_HTML.get(
                _current_lang, _HELP_FALLBACK_HTML.get("en", ""))
            self._view.setHtml(fallback)

    def retranslate(self):
        self.setWindowTitle(tr("btn_howto"))
        # Re-load README for the new language
        self._load_for_lang(_current_lang)


# ===== ResultsWindow =======================================================

class ResultsWindow(QtWidgets.QDialog):
    """Displays check results in a left-right split layout.

    Left panel : check-item list with detection-count badges.
    Right panel: node list filtered by selected item (or all).
    """

    _BADGE_STYLE = (
        "background-color:{bg}; color:{fg}; border-radius:3px;"
        " padding:1px 6px; font-size:11px; font-weight:bold;"
    )

    def __init__(self, results=None, parent=None):
        super(ResultsWindow, self).__init__(parent)
        self.setObjectName(RESULTS_OBJECT_NAME)
        self.setWindowTitle(tr("results_title"))
        self.setMinimumSize(800, 480)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.Tool)
        self.setStyleSheet(_QSS)

        self._results = results or {}
        self._ordered_keys = [k for k in _CANONICAL_ORDER if k in self._results]
        self._current_key = None
        self._fixed_nodes = set()
        self._preview_cache = {}  # key -> True (already enriched)
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

        # -- Right panel: description + node list --
        right_widget = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)

        # Item name label
        self._item_name_label = QtWidgets.QLabel("")
        self._item_name_label.setStyleSheet(
            "font-size: 14px; font-weight: bold; padding: 6px 6px 0 6px;"
        )
        right_layout.addWidget(self._item_name_label)

        # Item description label
        self._item_desc_label = QtWidgets.QLabel("")
        self._item_desc_label.setWordWrap(True)
        self._item_desc_label.setStyleSheet(
            "font-size: 11px; color: #aaaaaa; padding: 0 6px 4px 6px;"
        )
        right_layout.addWidget(self._item_desc_label)

        # Separator line
        sep_line = QtWidgets.QFrame()
        sep_line.setFrameShape(QtWidgets.QFrame.HLine)
        sep_line.setStyleSheet("color: #444444;")
        right_layout.addWidget(sep_line)

        self._node_table = QtWidgets.QTableWidget()
        self._node_table.setColumnCount(4)
        self._node_table.setHorizontalHeaderLabels(
            ["", tr("results_node_col"), tr("results_detail_col"),
             tr("risk_dep_col")]
        )
        _header = self._node_table.horizontalHeader()
        _header.setStretchLastSection(True)
        _header.setSectionResizeMode(
            0, QtWidgets.QHeaderView.Fixed
        )
        _header.setSectionResizeMode(
            1, QtWidgets.QHeaderView.Interactive
        )
        _header.setSectionResizeMode(
            2, QtWidgets.QHeaderView.Interactive
        )
        self._node_table.setColumnWidth(0, 24)
        self._node_table.setColumnWidth(1, 140)
        self._node_table.setColumnWidth(2, 140)
        self._node_table.verticalHeader().setVisible(False)
        self._node_table.verticalHeader().setDefaultSectionSize(22)
        self._node_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectRows
        )
        self._node_table.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )
        self._node_table.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers
        )
        self._node_table.cellClicked.connect(self._on_node_clicked)
        right_layout.addWidget(self._node_table, 1)

        # Header checkbox overlay (same widget as cell checkboxes)
        _header = self._node_table.horizontalHeader()
        self._header_cb_container = QtWidgets.QWidget(_header)
        _hcb_lay = QtWidgets.QHBoxLayout(self._header_cb_container)
        _hcb_lay.setContentsMargins(0, 0, 0, 0)
        _hcb_lay.setAlignment(QtCore.Qt.AlignCenter)
        self._header_cb = QtWidgets.QCheckBox()
        self._header_cb.setFixedSize(16, 16)
        self._header_cb.stateChanged.connect(self._on_fix_select_all)
        _hcb_lay.addWidget(self._header_cb)
        self._header_cb_container.setVisible(False)

        # Fix button (right panel bottom, shown only for fixable items)
        self._btn_fix_checked = QtWidgets.QPushButton(tr("btn_fix_selected"))
        self._btn_fix_checked.setProperty("cssClass", "accent")
        self._btn_fix_checked.setVisible(False)
        self._btn_fix_checked.clicked.connect(self._on_fix_checked)
        right_layout.addWidget(self._btn_fix_checked)

        splitter.addWidget(right_widget)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([190, 610])
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
    def _unfixed_count(self, entries):
        """Return number of entries whose node is not yet fixed."""
        return sum(
            1 for e in entries
            if e.get("node") not in self._fixed_nodes
        )

    def _populate_item_list(self):
        self._item_list.clear()

        # "All" row (badge = unfixed count)
        total = sum(
            self._unfixed_count(v) for v in self._results.values()
        )
        all_item = QtWidgets.QListWidgetItem()
        all_widget = self._make_item_row(tr("results_all"), total, is_all=True)
        all_item.setSizeHint(all_widget.sizeHint())
        self._item_list.addItem(all_item)
        self._item_list.setItemWidget(all_item, all_widget)

        # Per-check rows (badge = unfixed count)
        for key in self._ordered_keys:
            entries = self._results[key]
            label = tr("chk_" + key)
            count = self._unfixed_count(entries)
            row_item = QtWidgets.QListWidgetItem()
            row_widget = self._make_item_row(label, count, check_key=key)
            row_item.setSizeHint(row_widget.sizeHint())
            if count == 0:
                row_widget.setEnabled(False)
            self._item_list.addItem(row_item)
            self._item_list.setItemWidget(row_item, row_widget)

        # Select "All" by default
        self._item_list.setCurrentRow(0)

    def _make_item_row(self, label_text, count, is_all=False, check_key=None):
        """Create a widget row with label + count badge (no risk badges)."""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(widget)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(4)

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

    # ------------------------------------------------------------ right panel
    def _make_fixed_icon_widget(self):
        """Create a small check-mark icon widget for fixed nodes."""
        icon_w = QtWidgets.QWidget()
        icon_lay = QtWidgets.QHBoxLayout(icon_w)
        icon_lay.setContentsMargins(0, 0, 0, 0)
        icon_lay.setAlignment(QtCore.Qt.AlignCenter)
        icon_lbl = QtWidgets.QLabel("✅")
        icon_lbl.setFixedSize(16, 16)
        icon_lbl.setAlignment(QtCore.Qt.AlignCenter)
        icon_lay.addWidget(icon_lbl)
        return icon_w

    def _add_node_row(self, entry, fixable=False, check_key=None,
                      default_checked=True):
        """Append a single node row to the table.

        Args:
            entry: dict with 'node', 'detail', and optional 'risks' list.
            fixable: whether to show a fix checkbox.
            check_key: the check item key (used to look up risk level).
            default_checked: default state for the fix checkbox.
        """
        row = self._node_table.rowCount()
        self._node_table.insertRow(row)
        node = entry.get("node", "")
        short_name = node.rsplit("|", 1)[-1] if node else node
        detail = entry.get("detail", "")
        risks = entry.get("risks", [])
        is_fixed = node in self._fixed_nodes

        # Determine risk color for this row
        risk_level = _RISK_LEVELS.get(check_key) if check_key else None
        risk_color = _RISK_TEXT_COLORS.get(risk_level) if risk_level else None

        # Column 1: node name (plain text — no icon or color)
        node_item = QtWidgets.QTableWidgetItem(short_name)
        node_item.setData(QtCore.Qt.UserRole, node)
        if is_fixed:
            node_item.setForeground(QtGui.QColor("#888888"))
        self._node_table.setItem(row, 1, node_item)

        # Column 2: detail (plain — no risk info)
        detail_item = QtWidgets.QTableWidgetItem(detail)
        if is_fixed:
            detail_item.setForeground(QtGui.QColor("#888888"))
        self._node_table.setItem(row, 2, detail_item)

        # Column 3: dependencies / risks + info (⚠ prefix for risk rows)
        info = entry.get("info", [])
        display_items = list(risks) + list(info)
        if risks:
            risk_text = "⚠ " + " | ".join(display_items)
        elif display_items:
            risk_text = " | ".join(display_items)
        else:
            risk_text = ""
        risk_item = QtWidgets.QTableWidgetItem(risk_text)
        if is_fixed:
            risk_item.setForeground(QtGui.QColor("#888888"))
        elif risks and risk_color:
            risk_item.setForeground(QtGui.QColor(risk_color))
        elif info:
            risk_item.setForeground(QtGui.QColor("#999999"))
        self._node_table.setItem(row, 3, risk_item)

        # Column 0: check-mark icon (fixed) or checkbox (fixable)
        if is_fixed:
            self._node_table.setCellWidget(row, 0, self._make_fixed_icon_widget())
        elif fixable:
            cb_widget = QtWidgets.QWidget()
            cb_lay = QtWidgets.QHBoxLayout(cb_widget)
            cb_lay.setContentsMargins(0, 0, 0, 0)
            cb_lay.setAlignment(QtCore.Qt.AlignCenter)
            cb = QtWidgets.QCheckBox()
            cb.setFixedSize(16, 16)
            cb.setChecked(default_checked)
            cb.stateChanged.connect(self._on_node_cb_changed)
            cb_lay.addWidget(cb)
            cb_widget._cb = cb
            cb_widget._has_risk = bool(risks)
            self._node_table.setCellWidget(row, 0, cb_widget)
    def _on_item_selected(self, row):
        """Update right panel when left-panel selection changes."""
        self._node_table.blockSignals(True)
        self._node_table.setRowCount(0)
        self._current_key = None
        fixable = False

        # row == 0  -> "All" row selected
        # row == -1 -> selection cleared (e.g. during list rebuild); treat as "All"
        if row <= 0:
            self._item_name_label.setText(tr("results_all"))
            self._item_desc_label.setText(tr("desc_all"))
            self._populate_all_nodes()
        else:
            # Specific check item
            key_index = row - 1
            if key_index < len(self._ordered_keys):
                key = self._ordered_keys[key_index]
                self._current_key = key
                fixable = key in _FIX_CAPABLE
                self._item_name_label.setText(tr("chk_" + key))
                desc = tr("desc_" + key)
                if fixable:
                    desc += "\n" + tr("desc_fix_hint")
                self._item_desc_label.setText(desc)
                entries = self._results.get(key, [])
                risk_level = _RISK_LEVELS.get(key)
                # Lazy preview: enrich entries with per-node risk data
                if (risk_level and risk_level != _RISK_LOW
                        and key not in self._preview_cache):
                    preview_fn = _RISK_PREVIEW_DISPATCH.get(key)
                    if preview_fn is not None:
                        try:
                            node_list = [e["node"] for e in entries
                                         if e.get("node")]
                            previews = preview_fn(node_list)
                            risk_map = {}
                            for p in previews:
                                risk_map[p["node"]] = {
                                    "risks": p.get("risks", []),
                                    "info": p.get("info", []),
                                }
                            for e in entries:
                                data = risk_map.get(
                                    e.get("node"), {})
                                e["risks"] = data.get("risks", [])
                                e["info"] = data.get("info", [])
                        except Exception as exc:
                            log.warning(
                                "Preview failed for %s: %s", key, exc)
                    else:
                        # No preview function (high-risk items) — use
                        # preflight per-node to populate risks.
                        preflight_fn = _PREFLIGHT_DISPATCH.get(key)
                        if preflight_fn is not None:
                            for e in entries:
                                node = e.get("node")
                                if node:
                                    try:
                                        pf = preflight_fn([node])
                                        e["risks"] = pf.get(
                                            "warnings", [])
                                        e["info"] = pf.get(
                                            "info", [])
                                    except Exception:
                                        e["risks"] = []
                                        e["info"] = []
                    self._preview_cache[key] = True
                # Fill entries with no risks and no info
                if key in _FIX_CAPABLE:
                    _default_msg = tr("risk_not_detected")
                else:
                    _default_msg = tr("risk_not_applicable")
                for e in entries:
                    if not e.get("risks") and not e.get("info"):
                        e["info"] = [_default_msg]
                # Sort: no-risk first, then risk nodes grouped by risk type
                sorted_entries = sorted(entries, key=_risk_sort_key)
                for entry in sorted_entries:
                    has_node_risk = bool(entry.get("risks"))
                    # Default check: ON for no-risk, OFF for risk
                    default_on = not has_node_risk
                    self._add_node_row(
                        entry, fixable=fixable, check_key=key,
                        default_checked=default_on,
                    )

        self._node_table.blockSignals(False)
        has_nodes = self._node_table.rowCount() > 0
        if fixable and has_nodes:
            _h = self._node_table.horizontalHeader()
            self._header_cb_container.setGeometry(
                _h.sectionPosition(0), 0,
                _h.sectionSize(0), _h.height()
            )
            self._header_cb.blockSignals(True)
            self._header_cb.setChecked(False)
            self._header_cb.blockSignals(False)
            self._header_cb_container.setVisible(True)
        else:
            self._header_cb_container.setVisible(False)
        self._btn_fix_checked.setVisible(fixable and has_nodes)
        if fixable and has_nodes:
            self._btn_fix_checked.setEnabled(True)

        if self._node_table.rowCount() == 0:
            self._node_table.setRowCount(1)
            no_item = QtWidgets.QTableWidgetItem(tr("results_no_issues"))
            no_item.setFlags(no_item.flags() & ~QtCore.Qt.ItemIsSelectable)
            self._node_table.setItem(0, 0, no_item)
            self._node_table.setSpan(0, 0, 1, 4)

    def _populate_all_nodes(self):
        """Show all nodes grouped by check-item headers."""
        for key in self._ordered_keys:
            entries = self._results.get(key, [])
            if not entries:
                continue
            # Lazy preview: enrich entries with per-node risk data
            risk_level = _RISK_LEVELS.get(key)
            if (risk_level and risk_level != _RISK_LOW
                    and key not in self._preview_cache):
                preview_fn = _RISK_PREVIEW_DISPATCH.get(key)
                if preview_fn is not None:
                    try:
                        node_list = [e["node"] for e in entries
                                     if e.get("node")]
                        previews = preview_fn(node_list)
                        risk_map = {}
                        for p in previews:
                            risk_map[p["node"]] = {
                                "risks": p.get("risks", []),
                                "info": p.get("info", []),
                            }
                        for e in entries:
                            data = risk_map.get(
                                e.get("node"), {})
                            e["risks"] = data.get("risks", [])
                            e["info"] = data.get("info", [])
                    except Exception as exc:
                        log.warning(
                            "Preview failed for %s: %s", key, exc)
                else:
                    preflight_fn = _PREFLIGHT_DISPATCH.get(key)
                    if preflight_fn is not None:
                        for e in entries:
                            node = e.get("node")
                            if node:
                                try:
                                    pf = preflight_fn([node])
                                    e["risks"] = pf.get(
                                        "warnings", [])
                                    e["info"] = pf.get(
                                        "info", [])
                                except Exception:
                                    e["risks"] = []
                                    e["info"] = []
                self._preview_cache[key] = True
            # Default info for entries with no risks and no info
            if key in _FIX_CAPABLE:
                _default_msg = tr("risk_not_detected")
            else:
                _default_msg = tr("risk_not_applicable")
            for e in entries:
                if not e.get("risks") and not e.get("info"):
                    e["info"] = [_default_msg]
            label = tr("chk_" + key)
            header_text = "\u25b6 {label} ({count})".format(
                label=label, count=len(entries)
            )
            row = self._node_table.rowCount()
            self._node_table.insertRow(row)
            header_item = QtWidgets.QTableWidgetItem(header_text)
            header_item.setData(QtCore.Qt.UserRole + 1, key)
            f = header_item.font()
            f.setBold(True)
            header_item.setFont(f)
            header_item.setForeground(QtGui.QColor("#7aa2f7"))
            self._node_table.setItem(row, 0, header_item)
            self._node_table.setSpan(row, 0, 1, 4)
            sorted_entries = sorted(entries, key=_risk_sort_key)
            for entry in sorted_entries:
                self._add_node_row(entry, check_key=key)

    # ------------------------------------------------------------ fix controls
    def _on_fix_select_all(self, state):
        """Toggle all node checkboxes via header checkbox.

        When checking all, prompt confirmation if risk items exist.
        """
        checked = bool(state)
        if checked:
            # Check if any rows have risk
            has_risk_rows = False
            for r in range(self._node_table.rowCount()):
                w = self._node_table.cellWidget(r, 0)
                if w and hasattr(w, "_has_risk") and w._has_risk:
                    has_risk_rows = True
                    break
            if has_risk_rows:
                reply = _show_msgbox(self,
                    QtWidgets.QMessageBox.Question,
                    tr("fix_confirm_title"),
                    tr("fix_select_all_risk_confirm"),
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                    QtWidgets.QMessageBox.No,
                )
                if reply != QtWidgets.QMessageBox.Yes:
                    # Only check non-risk items
                    for r in range(self._node_table.rowCount()):
                        w = self._node_table.cellWidget(r, 0)
                        if w and hasattr(w, "_cb"):
                            w._cb.blockSignals(True)
                            is_risky = getattr(w, "_has_risk", False)
                            w._cb.setChecked(not is_risky)
                            w._cb.blockSignals(False)
                    self._header_cb.blockSignals(True)
                    self._header_cb.setChecked(False)
                    self._header_cb.blockSignals(False)
                    return
        for r in range(self._node_table.rowCount()):
            w = self._node_table.cellWidget(r, 0)
            if w and hasattr(w, "_cb"):
                w._cb.blockSignals(True)
                w._cb.setChecked(checked)
                w._cb.blockSignals(False)

    def _on_node_cb_changed(self, _state):
        """Sync header checkbox when a node checkbox changes."""
        all_checked = True
        any_checked = False
        for r in range(self._node_table.rowCount()):
            w = self._node_table.cellWidget(r, 0)
            if w and hasattr(w, "_cb"):
                if w._cb.isChecked():
                    any_checked = True
                else:
                    all_checked = False
        self._header_cb.blockSignals(True)
        self._header_cb.setChecked(all_checked and any_checked)
        self._header_cb.blockSignals(False)

    def _get_fix_checked_nodes(self):
        """Return list of node paths that are checked for fixing."""
        nodes = []
        for r in range(self._node_table.rowCount()):
            w = self._node_table.cellWidget(r, 0)
            if w and hasattr(w, "_cb") and w._cb.isChecked():
                node_item = self._node_table.item(r, 1)
                if node_item:
                    node = node_item.data(QtCore.Qt.UserRole)
                    if node:
                        nodes.append(node)
        return nodes

    def _on_fix_checked(self):
        """Execute fix for checked nodes with confirmation and result dialogs."""
        nodes = self._get_fix_checked_nodes()
        if not nodes:
            return
        key = self._current_key
        fix_fn = _FIX_DISPATCH.get(key)
        if fix_fn is None:
            return
        risk_level = _RISK_LEVELS.get(key)

        # Check if any selected nodes have risks
        has_risky_nodes = False
        for r in range(self._node_table.rowCount()):
            cw = self._node_table.cellWidget(r, 0)
            if cw and hasattr(cw, "_cb") and cw._cb.isChecked():
                if getattr(cw, "_has_risk", False):
                    has_risky_nodes = True
                    break

        # Build confirmation dialog based on risk level × detection
        if risk_level == _RISK_HIGH:
            if has_risky_nodes:
                # High × detected: preflight warnings → 2-step
                msg = ""
                preflight_fn = _PREFLIGHT_DISPATCH.get(key)
                if preflight_fn is not None:
                    pf_result = preflight_fn(nodes)
                    if not pf_result["safe"]:
                        msg = tr("preflight_warn_header")
                        for warning in pf_result["warnings"]:
                            msg += "\n• " + warning
                        msg += "\n\n"
                if not _FIX_CAPABLE.get(key, True):
                    msg += tr("fix_confirm_irreversible_warn") + "\n"
                msg += tr("fix_confirm_msg", count=len(nodes))
                reply = _show_msgbox(self,
                    QtWidgets.QMessageBox.Warning, tr("fix_confirm_title"), msg,
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                    QtWidgets.QMessageBox.No)
                if reply != QtWidgets.QMessageBox.Yes:
                    return
                # 2nd step
                reply2 = _show_msgbox(self,
                    QtWidgets.QMessageBox.Warning, tr("fix_confirm_title"),
                    tr("warn_high_confirm"),
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                    QtWidgets.QMessageBox.No)
                if reply2 != QtWidgets.QMessageBox.Yes:
                    return
            else:
                # High × not detected: no risk → 1-step
                msg = ""
                if not _FIX_CAPABLE.get(key, True):
                    msg = tr("fix_confirm_irreversible_warn") + "\n"
                msg += tr("preflight_no_risk")
                msg += "\n\n" + tr("fix_confirm_msg", count=len(nodes))
                reply = _show_msgbox(self,
                    QtWidgets.QMessageBox.Warning, tr("fix_confirm_title"), msg,
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                    QtWidgets.QMessageBox.No)
                if reply != QtWidgets.QMessageBox.Yes:
                    return
        elif risk_level == _RISK_MEDIUM:
            if has_risky_nodes:
                # Medium × detected: risk list → 1-step
                checked_set = set(nodes)
                entries = self._results.get(key, [])
                risk_texts = []
                for e in entries:
                    if e.get("node") in checked_set and e.get("risks"):
                        for rt in e["risks"]:
                            if rt not in risk_texts:
                                risk_texts.append(rt)
                msg = tr("preflight_warn_header")
                for rt in risk_texts:
                    msg += "\n• " + rt
                msg += "\n\n" + tr("fix_confirm_msg", count=len(nodes))
                if not _FIX_CAPABLE.get(key, True):
                    msg += "\n" + tr("fix_confirm_irreversible_warn")
                reply = _show_msgbox(self,
                    QtWidgets.QMessageBox.Warning, tr("fix_confirm_title"), msg,
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                    QtWidgets.QMessageBox.No)
                if reply != QtWidgets.QMessageBox.Yes:
                    return
            else:
                # Medium × not detected: neutral + no risk → 1-step
                msg = tr("preflight_no_risk")
                msg += "\n\n" + tr("fix_confirm_neutral_msg", count=len(nodes))
                if not _FIX_CAPABLE.get(key, True):
                    msg += "\n" + tr("fix_confirm_irreversible_warn")
                reply = _show_msgbox(self,
                    QtWidgets.QMessageBox.Question, tr("fix_confirm_title"), msg,
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                    QtWidgets.QMessageBox.No)
                if reply != QtWidgets.QMessageBox.Yes:
                    return
        else:
            # Low risk: simple confirmation
            msg = tr("fix_confirm_neutral_msg", count=len(nodes))
            if not _FIX_CAPABLE.get(key, True):
                msg += "\n\n" + tr("fix_confirm_irreversible_warn")
            reply = _show_msgbox(self,
                QtWidgets.QMessageBox.Question, tr("fix_confirm_title"), msg,
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No)
            if reply != QtWidgets.QMessageBox.Yes:
                return
        cmds.undoInfo(openChunk=True, chunkName="SCT_fix_{0}".format(key))
        try:
            fixed, failed = fix_fn(nodes)
        except Exception as exc:
            log.error("Fix failed for %s: %s", key, exc)
            fixed, failed = 0, len(nodes)
        finally:
            cmds.undoInfo(closeChunk=True)
        # Result dialog
        if failed == 0:
            msg = tr("fix_result_success", count=fixed)
        elif fixed == 0:
            msg = tr("fix_result_all_failed", count=failed)
        else:
            msg = tr("fix_result_partial", fixed=fixed, failed=failed)
        _show_msgbox(self,
            QtWidgets.QMessageBox.Information,
            tr("fix_result_title"),
            msg,
        )
        # Record fixed nodes and rebuild UI (keep entries for checkmark display)
        if fixed > 0:
            fixed_paths = set()
            for r in range(self._node_table.rowCount()):
                cw = self._node_table.cellWidget(r, 0)
                if cw and hasattr(cw, "_cb") and cw._cb.isChecked():
                    node_item = self._node_table.item(r, 1)
                    if node_item:
                        node_path = node_item.data(QtCore.Qt.UserRole)
                        if node_path:
                            fixed_paths.add(node_path)
                            self._fixed_nodes.add(node_path)
            # Rebuild left panel (badges show unfixed count) and right panel
            saved_key = self._current_key
            self._populate_item_list()
            # Restore selection to the same check item
            for i in range(1, self._item_list.count()):
                idx = i - 1
                if idx < len(self._ordered_keys) and self._ordered_keys[idx] == saved_key:
                    self._item_list.setCurrentRow(i)
                    break
            else:
                self._item_list.setCurrentRow(0)

    def _on_node_clicked(self, row, column):
        # Check if this is a clickable header row (All view navigation)
        header_item = self._node_table.item(row, 0)
        if header_item:
            check_key = header_item.data(QtCore.Qt.UserRole + 1)
            if check_key:
                for i, key in enumerate(self._ordered_keys):
                    if key == check_key:
                        self._item_list.setCurrentRow(i + 1)
                        return
        # Normal node click -> Maya select
        item = self._node_table.item(row, 1)
        if item:
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
        """Copy check results as plain text to clipboard and open feedback form.

        Returns:
            str: message key indicating the result ('report_form_opened',
                 'report_url_too_long', or 'report_form_not_configured').
        """
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
        success, msg_key = _open_feedback_form(text)
        if not success:
            self._summary_label.setText(tr(msg_key))
            return msg_key
        if msg_key == "report_url_too_long":
            self._summary_label.setText(tr("report_url_too_long"))
            return msg_key
        self._summary_label.setText(tr("report_form_opened"))
        return msg_key


# ===== MainWindow ==========================================================

# Check item definitions: (key, i18n_key, default_on, has_params)
# --- Geometry (5) ---
_CHECK_ITEMS_GEOMETRY = [
    ("history",              "chk_history",              True,  False),
    ("transform",            "chk_transform",            True,  False),
    ("vertex_tweaks",        "chk_vertex_tweaks",        True,  False),
    ("instances",            "chk_instances",             True,  False),
    ("smooth_preview",       "chk_smooth_preview",       True,  False),

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

# --- Scene Environment (4) ---
_CHECK_ITEMS_SCENE_ENV = [
    ("scene_units",          "chk_scene_units",          True,  True),
    ("unknown_nodes",        "chk_unknown_nodes",        True,  False),
    ("referenced_nodes",     "chk_referenced_nodes",     True,  False),

    ("file_paths",           "chk_file_paths",           True,  True),
]

_CANONICAL_ORDER = (
    [k for k, _, _, _ in _CHECK_ITEMS_GEOMETRY]
    + [k for k, _, _, _ in _CHECK_ITEMS_UNUSED]
    + [k for k, _, _, _ in _CHECK_ITEMS_SCENE_ENV]
)

_PARAM_DEFAULTS = {
    "scene_units":  {"unit": 0, "upaxis": 0},
    "file_paths":   {"scene": "scenes", "tex": "sourceimages",
                     "type": "relative", "missing": True},
}


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
        self._lang_toggle = QtWidgets.QPushButton(tr("lang_en_label") if _current_lang == "ja" else tr("lang_ja_label"))
        self._lang_toggle.setCheckable(True)
        self._lang_toggle.setChecked(_current_lang == "ja")
        self._lang_toggle.setFixedWidth(80)
        self._lang_toggle.setProperty("cssClass", "prep")
        self._lang_toggle.clicked.connect(self._on_language_toggled)
        # REMOVED: self._lang_combo.addItems(["English", "\u65e5\u672c\u8a9e"])
        top_bar.addWidget(self._lang_toggle)
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
        btn_row.addSpacing(16)
        self._btn_reset = QtWidgets.QPushButton(tr("btn_reset"))
        self._btn_reset.setProperty("cssClass", "prep")
        self._btn_reset.clicked.connect(self._reset_to_defaults)
        btn_row.addWidget(self._btn_reset)
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

        if key == "scene_units":
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

    def _reset_to_defaults(self):
        """Reset all check states and params to defaults."""
        for cat, items in [
            (self._cat_geometry,  _CHECK_ITEMS_GEOMETRY),
            (self._cat_unused,    _CHECK_ITEMS_UNUSED),
            (self._cat_scene_env, _CHECK_ITEMS_SCENE_ENV),
        ]:
            cat.reset_defaults([(k, d) for k, _, d, _ in items])
        pw = self._param_widgets.get("scene_units")
        if pw:
            pw["combo_unit"].setCurrentIndex(
                _PARAM_DEFAULTS["scene_units"]["unit"])
            pw["combo_axis"].setCurrentIndex(
                _PARAM_DEFAULTS["scene_units"]["upaxis"])
        pw = self._param_widgets.get("file_paths")
        if pw:
            d = _PARAM_DEFAULTS["file_paths"]
            pw["edit_scene"].setText(d["scene"])
            pw["edit_tex"].setText(d["tex"])
            if d["type"] == "relative":
                pw["rb_relative"].setChecked(True)
            else:
                pw["rb_absolute"].setChecked(True)
            pw["cb_missing"].setChecked(d["missing"])

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
        """Copy latest check results to clipboard and open feedback form."""
        if not self._results_window or not self._results_window.has_results():
            self._set_status(tr("report_empty"), "error")
            self._schedule_status_reset()
            return
        msg_key = self._results_window.copy_report()
        if msg_key == "report_url_too_long":
            self._set_status(tr("report_url_too_long"), "error")
        elif msg_key == "report_form_not_configured":
            self._set_status(tr("report_form_not_configured"), "error")
        else:
            self._set_status(tr("report_form_opened"), "success")
        self._schedule_status_reset()

    # === Help dialog ========================================================

    def _show_help(self):
        if self._help_dialog is None:
            self._help_dialog = HelpDialog(parent=self)
        self._help_dialog.retranslate()
        self._help_dialog.show()
        self._help_dialog.raise_()

    # === Language switching ==================================================

    def _on_language_toggled(self):
        checked = self._lang_toggle.isChecked()
        lang = "ja" if checked else "en"
        set_language(lang)
        self._lang_toggle.setText(tr("lang_en_label") if checked else tr("lang_ja_label"))
        self._retranslate_ui()

    def _retranslate_ui(self):
        self.setWindowTitle("{0} {1}".format(WINDOW_TITLE, __VERSION__))
        self._btn_howto.setText(tr("btn_howto"))
        self._btn_check.setText(tr("btn_check"))
        self._set_status(tr("status_ready"), "ready")

        # Language toggle + send report
        self._lang_toggle.setText(tr("lang_en_label") if _current_lang == "ja" else tr("lang_ja_label"))
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
        self._btn_reset.setText(tr("btn_reset"))

        # Param widgets
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

    "file_paths":           check_file_paths,
}

_SCENE_WIDE_KEYS = {
    "unused_nodes", "unused_mat", "unused_layers", "empty_sets", "namespaces",
    "unknown_nodes", "referenced_nodes", "scene_units",
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
