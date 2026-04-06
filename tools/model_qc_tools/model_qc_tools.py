# --- [000] header ---
# -*- coding: utf-8 -*-
from __future__ import print_function, division, unicode_literals
"""
Model QC Tools - Maya model quality check tool
Maya 2018 / 2023 (Python 2.7 / 3) compatible
"""

import time
import re
import math
import os
import tempfile
import atexit
from functools import partial

try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    try:
        from PySide2 import QtWidgets, QtCore, QtGui
    except ImportError:
        from PySide import QtWidgets, QtCore, QtGui

from maya import cmds, mel
import maya.OpenMayaUI as omui

try:
    from shiboken6 import wrapInstance
except ImportError:
    try:
        from shiboken2 import wrapInstance
    except ImportError:
        from shiboken import wrapInstance

__VERSION__ = "0.4.3"
__RELEASE_DATE__ = "2026-04-06"
WINDOW_TITLE = "Model QC Tools"
WINDOW_OBJECT_NAME = "modelQCToolsWindow"
RESULTS_OBJECT_NAME = "modelQCResultsWindow"
HELP_DIALOG_OBJECT_NAME = "modelQCHelpDialog"
_LANG = "en"

# --- Arrow icon generation for dark-theme QSS ---
_ARROW_ICON_DIR = ""
_ARROW_ICON_FILES = []

def _create_arrow_icons():
    """Generate small triangle PNG icons for ComboBox/SpinBox arrows."""
    global _ARROW_ICON_DIR, _ARROW_ICON_FILES
    try:
        icon_dir = os.path.join(tempfile.gettempdir(), "modelqc_icons")
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
    """Remove temporary arrow icon files and directory on exit."""
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

# --- Global QSS (dark theme, QC Hub compatible) ---
# bg=#2b2b2b  ctrl=#3c3c3c  text=#e0e0e0
# border=#555555  accent=#7aa2f7  hover=#505050
_QSS = (
    "QWidget#" + WINDOW_OBJECT_NAME + " {"
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
    "QSpinBox::up-button, QDoubleSpinBox::up-button {"
    "  border: none;"
    "  background: transparent;"
    "  width: 16px;"
    "}"
    "QSpinBox::down-button, QDoubleSpinBox::down-button {"
    "  border: none;"
    "  background: transparent;"
    "  width: 16px;"
    "}"
    "QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,"
    "QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {"
    "  background: #505050;"
    "}"
    "QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {"
    "  image: url(" + _ARROW_CSS_DIR + "/arrow_up.png);"
    "  width: 8px;"
    "  height: 8px;"
    "}"
    "QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {"
    "  image: url(" + _ARROW_CSS_DIR + "/arrow_down.png);"
    "  width: 8px;"
    "  height: 8px;"
    "}"
    "QSpinBox, QDoubleSpinBox {"
    "  background-color: #3c3c3c;"
    "  color: #e0e0e0;"
    "  border: 1px solid #666666;"
    "  border-radius: 4px;"
    "  padding: 2px 4px;"
    "}"
    "QSpinBox:disabled, QDoubleSpinBox:disabled {"
    "  background-color: #2b2b2b;"
    "  color: #666666;"
    "  border: 1px solid #3a3a3a;"
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
    "QFrame[frameShape=\"4\"] {"
    "  color: #555555;"
    "}"
    "QListWidget {"
    "  background-color: #2b2b2b;"
    "  color: #e0e0e0;"
    "  border: 1px solid #555555;"
    "}"
    "QListWidget::item:selected {"
    "  background-color: #505050;"
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
    "QTabWidget::pane {"
    "  border: 1px solid #555555;"
    "  background-color: #2b2b2b;"
    "}"
    "QTabBar::tab {"
    "  background-color: #353535;"
    "  color: #e0e0e0;"
    "  border: 1px solid #555555;"
    "  padding: 6px 16px;"
    "}"
    "QTabBar::tab:selected {"
    "  background-color: #2b2b2b;"
    "  border-bottom: 2px solid #7aa2f7;"
    "}"
    "QScrollArea {"
    "  background-color: transparent;"
    "  border: none;"
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
)
# --- [010] i18n ---
# depends on: [000] header

_TR = {
    "en": {
        # -- UI chrome --
        "lang_label": "Language:",
        "btn_how_to_use": "How to Use",
        "ready": "Ready",
        "computing": "Computing...",
        "close": "Close",
        "select_all": "Select All",
        "cancelled": "Cancelled",
        # -- Target mode --
        "target_mode": "Target",
        "target_visible": "Visible Meshes",
        "target_selected": "Selected Meshes",
        "target_group": "Group",
        "btn_set_group": "Set",
        "group_placeholder": "Select a group node...",
        # -- Tabs --
        "tab_model": "Model",
        "tab_setup": "Setup",
        # -- Tiers --
        "tier_mandatory": "\U0001f512 Mandatory",
        "tier_standard": "\u2705 Standard",
        "tier_optional": "\u2699\ufe0f Optional",
        # -- Model > Mandatory items --
        "chk_lamina": "Lamina faces",
        "chk_nonmanifold": "Nonmanifold geometry",
        "nm_normals_geo": "Normals and geometry",
        "nm_geo_only": "Geometry only",
        "chk_zero_geo": "Zero-length edges / Zero-area faces",
        "chk_invalid": "Invalid components",
        "chk_normals": "Reversed normals",
        "chk_overlap_verts": "Overlapping vertices",
        "chk_ngon": "Ngons (5+ sided)",
        # -- Model > Standard items --
        "chk_invalid_face": "Invalid face shapes",
        "sub_concave": "Concave",
        "sub_holed": "Holed",
        "chk_history": "Remaining history",
        "chk_transform": "Unfreezed transforms",
        "chk_unused_nodes": "Unused nodes / empty groups",
        "chk_naming_check": "Naming check",
        "sub_english_only": "English only",
        "chk_unassigned_mat": "Unassigned materials / textures",
        "chk_instances": "Remaining instances",
        # -- Model > Optional items --
        "chk_triangulated": "Triangulation check (4+ sided)",
        "chk_nonplanar": "Non-planar faces",
        "chk_symmetry": "Symmetry mismatch",
        "chk_edge_align": "Edge misalignment",
        "chk_poly_count": "Polygon count exceeded",
        "chk_vertex_color": "Vertex color check",
        "vc_must_have": "Must have",
        "vc_must_not_have": "Must not have",
        "chk_scene_units": "Scene units / Up axis",
        "unit_cm": "cm",
        "unit_m": "m",
        "upaxis_y": "Y-Up",
        "upaxis_z": "Z-Up",
        "chk_origin_check": "Origin check",
        "origin_bb": "Bounding box",
        "origin_pivot": "Pivot",
        "origin_both": "Both",
        # -- Setup > Mandatory items --
        "chk_joint_rotate": "Joint non-zero rotation",
        # -- Setup > Standard items --
        "chk_weight_precision": "Weight precision / influence count",
        "wp_decimal_2": "2 decimal places",
        "wp_decimal_3": "3 decimal places",
        "chk_joint_orient": "Joint orient direction",
        # -- Setup > Optional items --
        "chk_bone_symmetry": "Bone symmetry mismatch",
        # -- Buttons / Messages --
        "btn_check": "\u2713 Check",
        "btn_copy_report": "Copy Report",
        "no_mesh": "No meshes found.",
        "no_checks": "No check items selected.",
        "no_errors": "All checks passed!",
        "result_count": "{count} issues found",
        "done_with_time": "Done ({time}s)",
        "help_title": "How to Use \u2014 Model QC Tools",
        "mock_run": "Running {count} checks... (UI mockup)",
    },
    "ja": {
        # -- UI chrome --
        "lang_label": "\u8a00\u8a9e:",
        "btn_how_to_use": "\u4f7f\u3044\u65b9",
        "ready": "\u5f85\u6a5f\u4e2d",
        "computing": "\u51e6\u7406\u4e2d...",
        "close": "\u9589\u3058\u308b",
        "select_all": "\u5168\u3066\u9078\u629e",
        "cancelled": "\u30ad\u30e3\u30f3\u30bb\u30eb\u3055\u308c\u307e\u3057\u305f",
        # -- Target mode --
        "target_mode": "\u5bfe\u8c61",
        "target_visible": "\u8868\u793a\u4e2d\u306e\u30e1\u30c3\u30b7\u30e5",
        "target_selected": "\u9078\u629e\u30e1\u30c3\u30b7\u30e5",
        "target_group": "\u30b0\u30eb\u30fc\u30d7",
        "btn_set_group": "\u8a2d\u5b9a",
        "group_placeholder": "\u30b0\u30eb\u30fc\u30d7\u30ce\u30fc\u30c9\u3092\u9078\u629e...",
        # -- Tabs --
        "tab_model": "\u30e2\u30c7\u30eb",
        "tab_setup": "\u30bb\u30c3\u30c8\u30a2\u30c3\u30d7",
        # -- Tiers --
        "tier_mandatory": "\U0001f512 \u5fc5\u9808",
        "tier_standard": "\u2705 \u6a19\u6e96",
        "tier_optional": "\u2699\ufe0f \u30aa\u30d7\u30b7\u30e7\u30f3",
        # -- Model > Mandatory items --
        "chk_lamina": "\u30e9\u30df\u30ca\u30d5\u30a7\u30fc\u30b9",
        "chk_nonmanifold": "\u975e\u591a\u69d8\u4f53\u30b8\u30aa\u30e1\u30c8\u30ea",
        "nm_normals_geo": "\u30ce\u30fc\u30de\u30eb\u3068\u30b8\u30aa\u30e1\u30c8\u30ea",
        "nm_geo_only": "\u30b8\u30aa\u30e1\u30c8\u30ea\u306e\u307f",
        "chk_zero_geo": "\u30bc\u30ed\u30b8\u30aa\u30e1\u30c8\u30ea",
        "chk_invalid": "\u7121\u52b9\u30b3\u30f3\u30dd\u30fc\u30cd\u30f3\u30c8",
        "chk_normals": "\u6cd5\u7dda\u306e\u53cd\u8ee2",
        "chk_overlap_verts": "\u91cd\u8907\u9802\u70b9\uff08\u672a\u30de\u30fc\u30b8\uff09",
        "chk_ngon": "5\u8fba\u4ee5\u4e0a\u306e\u30d5\u30a7\u30fc\u30b9 (Ngon)",
        # -- Model > Standard items --
        "chk_invalid_face": "\u4e0d\u6b63\u30d5\u30a7\u30fc\u30b9\u5f62\u72b6",
        "sub_concave": "\u51f9\u578b",
        "sub_holed": "\u7a74\u3042\u304d",
        "chk_history": "\u6b8b\u5b58\u30d2\u30b9\u30c8\u30ea",
        "chk_transform": "\u672a\u30d5\u30ea\u30fc\u30ba\u306e\u30c8\u30e9\u30f3\u30b9\u30d5\u30a9\u30fc\u30e0",
        "chk_unused_nodes": "\u4e0d\u8981\u30ce\u30fc\u30c9\u30fb\u7a7a\u30b0\u30eb\u30fc\u30d7",
        "chk_naming_check": "\u547d\u540d\u30c1\u30a7\u30c3\u30af",
        "sub_english_only": "\u82f1\u8a9e\u306e\u307f",
        "chk_unassigned_mat": "\u672a\u30a2\u30b5\u30a4\u30f3\u30de\u30c6\u30ea\u30a2\u30eb\u30fb\u30c6\u30af\u30b9\u30c1\u30e3",
        "chk_instances": "\u30a4\u30f3\u30b9\u30bf\u30f3\u30b9\u306e\u6b8b\u5b58",
        # -- Model > Optional items --
        "chk_triangulated": "\u4e09\u89d2\u5316\u30c1\u30a7\u30c3\u30af\uff084\u8fba\u4ee5\u4e0a\uff09",
        "chk_nonplanar": "\u975e\u5e73\u9762\u30d5\u30a7\u30fc\u30b9",
        "chk_symmetry": "\u30b7\u30f3\u30e1\u30c8\u30ea\u306e\u4e0d\u4e00\u81f4",
        "chk_edge_align": "\u30a8\u30c3\u30b8\u306e\u6b6a\u307f",
        "chk_poly_count": "\u30dd\u30ea\u30b4\u30f3\u6570\u306e\u8d85\u904e",
        "chk_vertex_color": "\u9802\u70b9\u30ab\u30e9\u30fc\u30c1\u30a7\u30c3\u30af",
        "vc_must_have": "\u3042\u308a\u5fc5\u9808",
        "vc_must_not_have": "\u306a\u3057\u5fc5\u9808",
        "chk_scene_units": "\u30b7\u30fc\u30f3\u5358\u4f4d / Up\u8ef8",
        "unit_cm": "cm",
        "unit_m": "m",
        "upaxis_y": "Y-Up",
        "upaxis_z": "Z-Up",
        "chk_origin_check": "\u539f\u70b9\u30c1\u30a7\u30c3\u30af",
        "origin_bb": "\u30d0\u30a6\u30f3\u30c7\u30a3\u30f3\u30b0\u30dc\u30c3\u30af\u30b9",
        "origin_pivot": "\u30d4\u30dc\u30c3\u30c8",
        "origin_both": "\u4e21\u65b9",
        # -- Setup > Mandatory items --
        "chk_joint_rotate": "\u30b8\u30e7\u30a4\u30f3\u30c8Rotate\u975e\u30bc\u30ed",
        # -- Setup > Standard items --
        "chk_weight_precision": "\u30a6\u30a7\u30a4\u30c8\u7cbe\u5ea6 / Influence\u6570",
        "wp_decimal_2": "\u5c0f\u6570\u70b9\u7b2c2\u4f4d",
        "wp_decimal_3": "\u5c0f\u6570\u70b9\u7b2c3\u4f4d",
        "chk_joint_orient": "\u30b8\u30e7\u30a4\u30f3\u30c8\u30aa\u30ea\u30a8\u30f3\u30c8\u65b9\u5411",
        # -- Setup > Optional items --
        "chk_bone_symmetry": "\u9aa8\u69cb\u9020\u306e\u5de6\u53f3\u975e\u5bfe\u79f0",
        # -- Buttons / Messages --
        "btn_check": "\u2713 \u30c1\u30a7\u30c3\u30af",
        "btn_copy_report": "\u30ec\u30dd\u30fc\u30c8\u30b3\u30d4\u30fc",
        "no_mesh": "\u30e1\u30c3\u30b7\u30e5\u304c\u898b\u3064\u304b\u308a\u307e\u305b\u3093\u3002",
        "no_checks": "\u30c1\u30a7\u30c3\u30af\u9805\u76ee\u304c\u9078\u629e\u3055\u308c\u3066\u3044\u307e\u305b\u3093\u3002",
        "no_errors": "\u5168\u3066\u306e\u30c1\u30a7\u30c3\u30af\u306b\u5408\u683c\u3057\u307e\u3057\u305f\uff01",
        "result_count": "{count} \u4ef6\u306e\u554f\u984c\u3092\u691c\u51fa",
        "done_with_time": "\u5b8c\u4e86 ({time}\u79d2)",
        "help_title": "\u4f7f\u3044\u65b9 \u2014 Model QC Tools",
        "mock_run": "{count} \u9805\u76ee\u306e\u30c1\u30a7\u30c3\u30af\u3092\u5b9f\u884c\u4e2d... (UI\u30e2\u30c3\u30af\u30a2\u30c3\u30d7)",
    },
}


def tr(key, **kwargs):
    text = _TR.get(_LANG, _TR["en"]).get(key, _TR["en"].get(key, key))
    if kwargs:
        text = text.format(**kwargs)
    return text
# --- [011] help_content ---
# (実装予定)
# --- [020] utils ---
# depends on: [000] header

def get_maya_main_window():
    """Get Maya main window as a QWidget.
    Primary: shiboken + MQtUtil.mainWindowPtr()
    Fallback: Qt top-level widget search
    """
    # --- Method 1: MQtUtil (standard) ---
    try:
        import maya.OpenMayaUI as _omui
        try:
            from shiboken2 import wrapInstance as _wrap
        except ImportError:
            from shiboken import wrapInstance as _wrap
        ptr = _omui.MQtUtil.mainWindowPtr()
        if ptr is not None:
            return _wrap(int(ptr), QtWidgets.QWidget)
    except (AttributeError, RuntimeError, ImportError):
        pass
    # --- Method 2: Qt widget search (fallback) ---
    for widget in QtWidgets.QApplication.topLevelWidgets():
        if widget.objectName() == "MayaWindow":
            return widget
    return None


def collect_target_meshes(mode, group_name=""):
    """Collect mesh transforms based on target mode.
    mode: 'visible' | 'selected' | 'group'
    Returns list of long transform names, or None if nothing found.
    """
    def _get_mesh_transforms(nodes):
        transforms = []
        for n in (nodes or []):
            if cmds.nodeType(n) == "mesh":
                p = cmds.listRelatives(n, parent=True, fullPath=True)
                if p:
                    transforms.append(p[0])
            elif cmds.nodeType(n) == "transform":
                shapes = cmds.listRelatives(n, shapes=True, type="mesh", fullPath=True)
                if shapes:
                    transforms.append(n)
        return transforms

    def _expand_hierarchy(roots):
        result = []
        for r in (roots or []):
            result.append(r)
            desc = cmds.listRelatives(r, allDescendents=True, type="mesh", fullPath=True) or []
            result.extend(_get_mesh_transforms(desc))
        return result

    if mode == "selected":
        sel = cmds.ls(sl=True, long=True)
        if not sel:
            return None
        meshes = _expand_hierarchy(_get_mesh_transforms(sel) or sel)
    elif mode == "group":
        if not group_name or not cmds.objExists(group_name):
            return None
        desc = cmds.listRelatives(group_name, allDescendents=True, type="mesh", fullPath=True) or []
        meshes = _get_mesh_transforms(desc)
    else:  # visible
        all_meshes = cmds.ls(type="mesh", long=True, visible=True) or []
        meshes = _get_mesh_transforms(all_meshes)

    return list(set(meshes)) if meshes else None
# --- [100] cleanup ---
# (実装予定)
# --- [200] normals ---
# (実装予定)
# --- [210] overlapping_verts ---
# (実装予定)
# --- [220] symmetry ---
# (実装予定)
# --- [230] edge_alignment ---
# (実装予定)
# --- [240] polygon_count ---
# (実装予定)
# --- [300] transform ---
# (実装予定)
# --- [310] history ---
# (実装予定)
# --- [320] scene_hierarchy ---
# (実装予定)
# --- [330] unused_nodes ---
# (実装予定)
# --- [340] naming ---
# (実装予定)
# --- [400] bbox_origin ---
# (実装予定)
# --- [800] ui ---
# depends on: [000] header, [010] i18n, [011] help_content, [020] utils, [810] worker

# ============================================================
# NoScroll Widget Subclasses
# ============================================================
class NoScrollDoubleSpinBox(QtWidgets.QDoubleSpinBox):
    """QDoubleSpinBox that ignores wheel events when not focused."""
    def __init__(self, *args, **kwargs):
        super(NoScrollDoubleSpinBox, self).__init__(*args, **kwargs)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

    def wheelEvent(self, event):
        if not self.hasFocus():
            event.ignore()
        else:
            super(NoScrollDoubleSpinBox, self).wheelEvent(event)


class NoScrollSpinBox(QtWidgets.QSpinBox):
    """QSpinBox that ignores wheel events when not focused."""
    def __init__(self, *args, **kwargs):
        super(NoScrollSpinBox, self).__init__(*args, **kwargs)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

    def wheelEvent(self, event):
        if not self.hasFocus():
            event.ignore()
        else:
            super(NoScrollSpinBox, self).wheelEvent(event)


class NoScrollComboBox(QtWidgets.QComboBox):
    """QComboBox that ignores wheel events when not focused."""
    def __init__(self, *args, **kwargs):
        super(NoScrollComboBox, self).__init__(*args, **kwargs)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

    def wheelEvent(self, event):
        if not self.hasFocus():
            event.ignore()
        else:
            super(NoScrollComboBox, self).wheelEvent(event)


# ============================================================
# Collapsible Category Widget
# ============================================================
class CollapsibleCategory(QtWidgets.QWidget):
    """Collapsible section with arrow toggle.

    mandatory=True  -> no checkboxes; items always enabled (header is a label).
    mandatory=False -> header checkbox for bulk ON/OFF + individual checkboxes.
    """

    def __init__(self, title_key, item_count=0, default_expanded=True,
                 mandatory=False, parent=None):
        super(CollapsibleCategory, self).__init__(parent)
        self._expanded = default_expanded
        self._default_expanded = default_expanded
        self._title_key = title_key
        self._item_count = item_count
        self._mandatory = mandatory
        self._items = []  # (key, tr_key, widget, param_widget, default_on, default_pv)
        self._reset_callbacks = {}  # key -> callable (for compound widget reset)
        self._sep_labels = []  # (tr_key, QLabel)
        self._combo_tr_map = {}  # key -> (QComboBox, [tr_keys])

        main_lay = QtWidgets.QVBoxLayout(self)
        main_lay.setContentsMargins(0, 2, 0, 2)
        main_lay.setSpacing(0)

        # --- Header row ---
        hdr = QtWidgets.QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 0)
        hdr.setSpacing(4)

        self._arrow = QtWidgets.QToolButton()
        self._arrow.setArrowType(
            QtCore.Qt.DownArrow if default_expanded else QtCore.Qt.RightArrow)
        self._arrow.setAutoRaise(True)
        self._arrow.setFixedSize(20, 20)
        self._arrow.clicked.connect(self._toggle)
        hdr.addWidget(self._arrow)

        if mandatory:
            self._header_chk = None
            self._header_lbl = QtWidgets.QLabel(self._make_header_text())
            self._header_lbl.setStyleSheet("font-weight: bold; font-size: 12px;")
            hdr.addWidget(self._header_lbl)
        else:
            self._header_lbl = None
            self._header_chk = QtWidgets.QCheckBox(self._make_header_text())
            self._header_chk.setChecked(True)
            self._header_chk.setStyleSheet("font-weight: bold; font-size: 12px;")
            self._header_chk.toggled.connect(self._bulk_toggle)
            hdr.addWidget(self._header_chk)

        hdr.addStretch()
        main_lay.addLayout(hdr)

        # --- Body (collapsible) ---
        self._body = QtWidgets.QWidget()
        self._body_lay = QtWidgets.QVBoxLayout(self._body)
        self._body_lay.setContentsMargins(28, 4, 4, 4)
        self._body_lay.setSpacing(3)
        main_lay.addWidget(self._body)              # reparent before visibility
        self._body.setVisible(default_expanded)        # safe: now a child widget

    def _make_header_text(self):
        title = tr(self._title_key)
        if self._item_count:
            return "{0} ({1})".format(title, self._item_count)
        return title

    def add_item(self, key, tr_key, default_on=True, param_widget=None):
        """Add a check item row. Returns the QCheckBox or QLabel."""
        row = QtWidgets.QHBoxLayout()
        row.setSpacing(6)
        default_param_value = None
        if param_widget is not None:
            if isinstance(param_widget, (QtWidgets.QDoubleSpinBox, QtWidgets.QSpinBox)):
                default_param_value = param_widget.value()
            elif isinstance(param_widget, QtWidgets.QComboBox):
                default_param_value = param_widget.currentIndex()
            elif isinstance(param_widget, QtWidgets.QLineEdit):
                default_param_value = param_widget.text()
        if self._mandatory:
            lbl = QtWidgets.QLabel(tr(tr_key))
            row.addWidget(lbl)
            if param_widget is not None:
                row.addWidget(param_widget)
            row.addStretch()
            self._body_lay.addLayout(row)
            self._items.append((key, tr_key, lbl, param_widget, True, default_param_value))
            return lbl
        else:
            chk = QtWidgets.QCheckBox(tr(tr_key))
            chk.setChecked(default_on)
            row.addWidget(chk)
            if param_widget is not None:
                row.addWidget(param_widget)
            row.addStretch()
            self._body_lay.addLayout(row)
            self._items.append((key, tr_key, chk, param_widget, default_on, default_param_value))
            return chk

    def add_separator_label(self, tr_key):
        """Add a sub-header label inside the category."""
        lbl = QtWidgets.QLabel(tr(tr_key))
        lbl.setStyleSheet("font-size: 10px; color: #888; padding: 2px 0px;")
        self._body_lay.addWidget(lbl)
        self._sep_labels.append((tr_key, lbl))

    def register_combo_tr(self, key, combo, tr_keys):
        """Register a combo box for language refresh."""
        self._combo_tr_map[key] = (combo, tr_keys)

    def register_reset_callback(self, key, callback):
        """Register a callable to reset a compound param widget to defaults."""
        self._reset_callbacks[key] = callback

    # --- Toggle ---
    def _toggle(self):
        self._expanded = not self._expanded
        self._arrow.setArrowType(
            QtCore.Qt.DownArrow if self._expanded else QtCore.Qt.RightArrow)
        self._body.setVisible(self._expanded)
        w = self.window()
        if w:
            w.adjustSize()

    def _bulk_toggle(self, checked):
        if self._mandatory:
            return
        for _, _, chk, _, _, _ in self._items:
            chk.setChecked(checked)

    # --- Query ---
    def get_enabled(self):
        """Return list of (key, is_checked) tuples."""
        if self._mandatory:
            return [(k, True) for k, _, _, _, _, _ in self._items]
        return [(k, chk.isChecked()) for k, _, chk, _, _, _ in self._items]

    def get_param(self, key):
        """Return param widget value for a given item key."""
        for k, _, _, pw, _, _ in self._items:
            if k == key and pw is not None:
                if isinstance(pw, QtWidgets.QDoubleSpinBox):
                    return pw.value()
                elif isinstance(pw, QtWidgets.QSpinBox):
                    return pw.value()
                elif isinstance(pw, QtWidgets.QComboBox):
                    return pw.currentIndex()
                elif isinstance(pw, QtWidgets.QLineEdit):
                    return pw.text()
        return None

    # --- Uncheck All ---
    def uncheck_all(self):
        """Uncheck all items in this category (no-op for mandatory)."""
        if self._mandatory:
            return
        self._header_chk.blockSignals(True)
        for _, _, chk, _, _, _ in self._items:
            chk.setChecked(False)
        self._header_chk.setChecked(False)
        self._header_chk.blockSignals(False)

    # --- Reset ---
    def _reset_param(self, key, pw, default_pv):
        """Reset a single param widget. Delegates to callback for compound widgets."""
        if key in self._reset_callbacks:
            self._reset_callbacks[key]()
            return
        if pw is None or default_pv is None:
            return
        if isinstance(pw, (QtWidgets.QDoubleSpinBox, QtWidgets.QSpinBox)):
            pw.setValue(default_pv)
        elif isinstance(pw, QtWidgets.QComboBox):
            pw.setCurrentIndex(default_pv)
        elif isinstance(pw, QtWidgets.QLineEdit):
            pw.setText(default_pv)

    def reset_defaults(self):
        """Reset all items to their default states."""
        if self._mandatory:
            # Only reset param widgets
            for k, _, _, pw, _, default_pv in self._items:
                self._reset_param(k, pw, default_pv)
            return
        self._header_chk.blockSignals(True)
        for k, _, chk, pw, default_on, default_pv in self._items:
            chk.setChecked(default_on)
            self._reset_param(k, pw, default_pv)
        has_any_on = any(d for _, _, _, _, d, _ in self._items)
        self._header_chk.setChecked(has_any_on)
        self._header_chk.blockSignals(False)
        if self._expanded != self._default_expanded:
            self._toggle()

    # --- Language refresh ---
    def refresh_lang(self):
        if self._mandatory:
            self._header_lbl.setText(self._make_header_text())
        else:
            self._header_chk.setText(self._make_header_text())
        for _, tr_key, widget, _, _, _ in self._items:
            widget.setText(tr(tr_key))
        for tr_key, lbl in self._sep_labels:
            lbl.setText(tr(tr_key))
        for key, (combo, tr_keys) in self._combo_tr_map.items():
            idx = combo.currentIndex()
            combo.blockSignals(True)
            combo.clear()
            combo.addItems([tr(k) for k in tr_keys])
            combo.setCurrentIndex(idx)
            combo.blockSignals(False)


# ============================================================
# Help Dialog
# ============================================================
class HelpDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(HelpDialog, self).__init__(parent)
        self.setWindowTitle(tr("help_title"))
        self.setMinimumSize(520, 480)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.Tool)
        self.setObjectName(HELP_DIALOG_OBJECT_NAME)
        layout = QtWidgets.QVBoxLayout(self)
        self._browser = QtWidgets.QTextBrowser()
        self._browser.setOpenExternalLinks(False)
        self._browser.setReadOnly(True)
        self._browser.setStyleSheet("font-size: 14px;")
        self._update_content()
        layout.addWidget(self._browser)
        btn_close = QtWidgets.QPushButton(tr("close"))
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)

    def _update_content(self):
        html = _TR.get(_LANG, _TR["en"]).get("help_html", "<p>Help content coming soon.</p>")
        self._browser.setHtml(html)

    def refresh_lang(self):
        self.setWindowTitle(tr("help_title"))
        self._update_content()


# ============================================================
# Results Window
# ============================================================
class ResultsWindow(QtWidgets.QDialog):
    def __init__(self, title, results, parent=None):
        super(ResultsWindow, self).__init__(parent)
        self.setWindowTitle("QC Results \u2014 {0}".format(title))
        self.setMinimumSize(500, 350)
        self.results = results
        self.setObjectName(RESULTS_OBJECT_NAME)
        layout = QtWidgets.QVBoxLayout(self)

        summary = QtWidgets.QLabel(tr("result_count", count=len(results)))
        summary.setStyleSheet("font-size: 13px; font-weight: bold; padding: 4px;")
        layout.addWidget(summary)

        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.setStyleSheet("font-size: 12px;")
        for r in results:
            self.list_widget.addItem(r.get("label", ""))
        self.list_widget.currentRowChanged.connect(self._on_select)
        layout.addWidget(self.list_widget)

        bl = QtWidgets.QHBoxLayout()
        bsa = QtWidgets.QPushButton(tr("select_all"))
        bsa.clicked.connect(self._select_all)
        bcl = QtWidgets.QPushButton(tr("close"))
        bcl.clicked.connect(self.close)
        bl.addWidget(bsa)
        bl.addWidget(bcl)
        layout.addLayout(bl)

    def _on_select(self, row):
        if row < 0 or row >= len(self.results):
            return
        comp = self.results[row].get("component")
        if comp:
            cmds.select(comp, r=True)

    def _select_all(self):
        sel = []
        for r in self.results:
            comp = r.get("component")
            if comp:
                sel.append(comp)
        if sel:
            cmds.select(sel, r=True)


# ============================================================
# Main Window
# ============================================================
class ModelQCToolsWindow(QtWidgets.QDialog):
    _instance = None

    @classmethod
    def show_window(cls):
        if cls._instance is not None:
            cls._instance.close()
            cls._instance = None
        cls._instance = cls(parent=get_maya_main_window())
        cls._instance.show()

    def __init__(self, parent=None):
        # Qt.Tool flag: ensures the window has no min/max buttons.
        # NOTE: The actual flicker fix is in CollapsibleCategory.__init__
        # (addWidget before setVisible to avoid orphan top-level show).
        super(ModelQCToolsWindow, self).__init__(
            parent,
            QtCore.Qt.Tool | QtCore.Qt.WindowTitleHint
            | QtCore.Qt.WindowCloseButtonHint
        )
        self.setWindowTitle("{0} {1}".format(WINDOW_TITLE, __VERSION__))
        self.setMinimumWidth(340)
        self.setObjectName(WINDOW_OBJECT_NAME)
        self.setStyleSheet(_QSS)
        self._help_dialog = None
        self._worker = None
        self._start_time = 0.0
        self._categories = {}
        self._model_cat_keys = []
        self._setup_cat_keys = []
        # Sub-option widgets for language refresh
        self._chk_concave_sub = None
        self._chk_holed_sub = None
        self._chk_eng_sub = None
        self._build_ui()
        self.adjustSize()
        self._base_min_h = self.sizeHint().height()
        self.setMinimumHeight(self._base_min_h)

    # ========================================================
    # Build UI
    # ========================================================
    def _build_ui(self):
        main = QtWidgets.QVBoxLayout(self)
        main.setContentsMargins(8, 8, 8, 10)
        main.setSpacing(8)
        self._build_top_row(main)
        self._build_target_mode(main)
        self._build_tabs(main)
        self._build_check_row(main)
        self._build_status_row(main)

    # --------------------------------------------------------
    # _build_ui sub-methods
    # --------------------------------------------------------
    def _build_top_row(self, main):
        """Build language selector and help button row."""
        # ---------- Language / Help row ----------
        top = QtWidgets.QHBoxLayout()
        self._lbl_lang = QtWidgets.QLabel(tr("lang_label"))
        top.addWidget(self._lbl_lang)
        self._combo_lang = NoScrollComboBox()
        self._combo_lang.addItems(["English", "\u65e5\u672c\u8a9e"])
        self._combo_lang.setCurrentIndex(0 if _LANG == "en" else 1)
        self._combo_lang.currentIndexChanged.connect(self._on_lang_changed)
        top.addWidget(self._combo_lang)
        top.addStretch()
        self._btn_help = QtWidgets.QPushButton(tr("btn_how_to_use"))
        self._btn_help.setProperty("cssClass", "prep")
        self._btn_help.setMinimumWidth(100)
        self._btn_help.clicked.connect(self._show_help)
        top.addWidget(self._btn_help)
        main.addLayout(top)

    def _build_target_mode(self, main):
        """Build target mode group box and separator."""
        # ---------- Target Mode ----------
        self._grp_target = QtWidgets.QGroupBox(tr("target_mode"))
        tl = QtWidgets.QVBoxLayout(self._grp_target)
        tl.setSpacing(4)
        tl.setContentsMargins(8, 8, 8, 8)
        self._radio_visible = QtWidgets.QRadioButton(tr("target_visible"))
        self._radio_visible.setChecked(True)
        self._radio_selected = QtWidgets.QRadioButton(tr("target_selected"))
        self._radio_group = QtWidgets.QRadioButton(tr("target_group"))
        self._radio_group.toggled.connect(self._on_group_toggled)
        tl.addWidget(self._radio_visible)
        tl.addWidget(self._radio_selected)
        grp_row = QtWidgets.QHBoxLayout()
        grp_row.addWidget(self._radio_group)
        self._txt_group = QtWidgets.QLineEdit()
        self._txt_group.setEnabled(False)
        self._txt_group.setPlaceholderText(tr("group_placeholder"))
        grp_row.addWidget(self._txt_group)
        self._btn_set_group = QtWidgets.QPushButton(tr("btn_set_group"))
        self._btn_set_group.setEnabled(False)
        self._btn_set_group.setFixedWidth(40)
        self._btn_set_group.clicked.connect(self._on_set_group)
        grp_row.addWidget(self._btn_set_group)
        tl.addLayout(grp_row)
        main.addWidget(self._grp_target)

        # ---------- Separator ----------
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.HLine)
        sep.setFrameShadow(QtWidgets.QFrame.Sunken)
        main.addWidget(sep)

    def _build_tabs(self, main):
        """Build tab widget with Model and Setup check item categories."""
        # ---------- Tab Widget ----------
        self._tab_widget = QtWidgets.QTabWidget()

        # ====================================================
        # Tab 1: Model (22 items = 7 mandatory + 7 std + 8 opt)
        # ====================================================
        model_scroll = QtWidgets.QScrollArea()
        model_scroll.setWidgetResizable(True)
        model_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        model_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        model_sw = QtWidgets.QWidget()
        model_sl = QtWidgets.QVBoxLayout(model_sw)
        model_sl.setContentsMargins(0, 0, 0, 0)
        model_sl.setSpacing(4)

        # ----- Mandatory (7 items, always ON, no checkboxes) -----
        cat_m_mand = CollapsibleCategory("tier_mandatory", 7, True,
                                         mandatory=True)
        cat_m_mand.add_item("lamina", "chk_lamina")
        # Nonmanifold -- mode selector
        nm_combo = NoScrollComboBox()
        nm_combo.addItems([tr("nm_normals_geo"), tr("nm_geo_only")])
        nm_combo.setFixedWidth(160)
        cat_m_mand.add_item("nonmanifold", "chk_nonmanifold", True, nm_combo)
        cat_m_mand.register_combo_tr("nonmanifold", nm_combo,
                                     ["nm_normals_geo", "nm_geo_only"])
        # Zero geometry -- tolerance
        sp_zero = NoScrollDoubleSpinBox()
        sp_zero.setRange(0.000001, 1.0)
        sp_zero.setValue(0.000010)
        sp_zero.setDecimals(6)
        sp_zero.setFixedWidth(90)
        cat_m_mand.add_item("zero_geo", "chk_zero_geo", True, sp_zero)
        cat_m_mand.add_item("invalid", "chk_invalid")
        cat_m_mand.add_item("normals", "chk_normals")
        cat_m_mand.add_item("overlap_verts", "chk_overlap_verts")
        cat_m_mand.add_item("ngon", "chk_ngon")
        self._categories["model_mandatory"] = cat_m_mand
        self._model_cat_keys.append("model_mandatory")
        model_sl.addWidget(cat_m_mand)

        # ----- Standard (7 items, default ON) -----
        cat_m_std = CollapsibleCategory("tier_standard", 7, True)
        # Invalid face shapes -- sub-options (concave + holed)
        iface_w = QtWidgets.QWidget()
        iface_lay = QtWidgets.QHBoxLayout(iface_w)
        iface_lay.setContentsMargins(0, 0, 0, 0)
        iface_lay.setSpacing(6)
        self._chk_concave_sub = QtWidgets.QCheckBox(tr("sub_concave"))
        self._chk_concave_sub.setChecked(True)
        iface_lay.addWidget(self._chk_concave_sub)
        self._chk_holed_sub = QtWidgets.QCheckBox(tr("sub_holed"))
        self._chk_holed_sub.setChecked(True)
        iface_lay.addWidget(self._chk_holed_sub)
        cat_m_std.add_item("invalid_face", "chk_invalid_face", True, iface_w)
        cat_m_std.register_reset_callback("invalid_face", lambda: (
            self._chk_concave_sub.setChecked(True),
            self._chk_holed_sub.setChecked(True)))
        cat_m_std.add_item("history", "chk_history", True)
        cat_m_std.add_item("transform", "chk_transform", True)
        cat_m_std.add_item("unused_nodes", "chk_unused_nodes", True)
        # Naming check -- regex + English only
        name_w = QtWidgets.QWidget()
        name_lay = QtWidgets.QHBoxLayout(name_w)
        name_lay.setContentsMargins(0, 0, 0, 0)
        name_lay.setSpacing(6)
        txt_regex = QtWidgets.QLineEdit()
        txt_regex.setPlaceholderText("e.g. ^[a-zA-Z].*")
        txt_regex.setFixedWidth(140)
        name_lay.addWidget(txt_regex)
        self._chk_eng_sub = QtWidgets.QCheckBox(tr("sub_english_only"))
        self._chk_eng_sub.setChecked(True)
        name_lay.addWidget(self._chk_eng_sub)
        cat_m_std.add_item("naming_check", "chk_naming_check", True, name_w)
        cat_m_std.register_reset_callback("naming_check", lambda: (
            txt_regex.setText(""),
            self._chk_eng_sub.setChecked(True)))
        cat_m_std.add_item("unassigned_mat", "chk_unassigned_mat", True)
        cat_m_std.add_item("instances", "chk_instances", True)
        self._categories["model_standard"] = cat_m_std
        self._model_cat_keys.append("model_standard")
        model_sl.addWidget(cat_m_std)

        # ----- Optional (8 items, default OFF) -----
        cat_m_opt = CollapsibleCategory("tier_optional", 8, True)
        cat_m_opt.add_item("triangulated", "chk_triangulated", False)
        cat_m_opt.add_item("nonplanar", "chk_nonplanar", False)
        cat_m_opt.add_item("symmetry", "chk_symmetry", False)
        # Edge alignment -- angle tolerance
        sp_angle = NoScrollDoubleSpinBox()
        sp_angle.setRange(0.1, 45.0)
        sp_angle.setValue(5.0)
        sp_angle.setDecimals(1)
        sp_angle.setFixedWidth(60)
        sp_angle.setSuffix("\u00b0")
        cat_m_opt.add_item("edge_align", "chk_edge_align", False, sp_angle)
        # Polygon count -- threshold
        sp_poly = NoScrollSpinBox()
        sp_poly.setRange(100, 10000000)
        sp_poly.setValue(50000)
        sp_poly.setFixedWidth(90)
        cat_m_opt.add_item("poly_count", "chk_poly_count", False, sp_poly)
        # Vertex color -- mode selector
        vc_combo = NoScrollComboBox()
        vc_combo.addItems([tr("vc_must_have"), tr("vc_must_not_have")])
        vc_combo.setFixedWidth(120)
        cat_m_opt.add_item("vertex_color", "chk_vertex_color", False, vc_combo)
        cat_m_opt.register_combo_tr("vertex_color", vc_combo,
                                    ["vc_must_have", "vc_must_not_have"])
        # Scene units / Up axis
        unit_w = QtWidgets.QWidget()
        unit_lay = QtWidgets.QHBoxLayout(unit_w)
        unit_lay.setContentsMargins(0, 0, 0, 0)
        unit_lay.setSpacing(4)
        unit_combo = NoScrollComboBox()
        unit_combo.addItems([tr("unit_cm"), tr("unit_m")])
        unit_combo.setFixedWidth(50)
        unit_lay.addWidget(unit_combo)
        upaxis_combo = NoScrollComboBox()
        upaxis_combo.addItems([tr("upaxis_y"), tr("upaxis_z")])
        upaxis_combo.setFixedWidth(60)
        unit_lay.addWidget(upaxis_combo)
        cat_m_opt.add_item("scene_units", "chk_scene_units", False, unit_w)
        cat_m_opt.register_combo_tr("scene_units_unit", unit_combo,
                                    ["unit_cm", "unit_m"])
        cat_m_opt.register_combo_tr("scene_units_upaxis", upaxis_combo,
                                    ["upaxis_y", "upaxis_z"])
        cat_m_opt.register_reset_callback("scene_units", lambda: (
            unit_combo.setCurrentIndex(0),
            upaxis_combo.setCurrentIndex(0)))
        # Origin check -- mode selector
        origin_combo = NoScrollComboBox()
        origin_combo.addItems([tr("origin_bb"), tr("origin_pivot"),
                               tr("origin_both")])
        origin_combo.setFixedWidth(140)
        cat_m_opt.add_item("origin_check", "chk_origin_check", False,
                           origin_combo)
        cat_m_opt.register_combo_tr("origin_check", origin_combo,
                                    ["origin_bb", "origin_pivot",
                                     "origin_both"])
        cat_m_opt._header_chk.setChecked(False)
        self._categories["model_optional"] = cat_m_opt
        self._model_cat_keys.append("model_optional")
        model_sl.addWidget(cat_m_opt)

        model_sl.addStretch()
        model_scroll.setWidget(model_sw)
        self._tab_widget.addTab(model_scroll, tr("tab_model"))

        # ====================================================
        # Tab 2: Setup (4 items = 1 mandatory + 2 std + 1 opt)
        # ====================================================
        setup_scroll = QtWidgets.QScrollArea()
        setup_scroll.setWidgetResizable(True)
        setup_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        setup_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        setup_sw = QtWidgets.QWidget()
        setup_sl = QtWidgets.QVBoxLayout(setup_sw)
        setup_sl.setContentsMargins(0, 0, 0, 0)
        setup_sl.setSpacing(4)

        # ----- Mandatory (1 item) -----
        cat_s_mand = CollapsibleCategory("tier_mandatory", 1, True,
                                         mandatory=True)
        cat_s_mand.add_item("joint_rotate", "chk_joint_rotate")
        self._categories["setup_mandatory"] = cat_s_mand
        self._setup_cat_keys.append("setup_mandatory")
        setup_sl.addWidget(cat_s_mand)

        # ----- Standard (2 items, default ON) -----
        cat_s_std = CollapsibleCategory("tier_standard", 2, True)
        # Weight precision / influence count
        wp_w = QtWidgets.QWidget()
        wp_lay = QtWidgets.QHBoxLayout(wp_w)
        wp_lay.setContentsMargins(0, 0, 0, 0)
        wp_lay.setSpacing(4)
        wp_combo = NoScrollComboBox()
        wp_combo.addItems([tr("wp_decimal_2"), tr("wp_decimal_3")])
        wp_combo.setFixedWidth(120)
        wp_lay.addWidget(wp_combo)
        sp_infl = NoScrollSpinBox()
        sp_infl.setRange(2, 8)
        sp_infl.setValue(4)
        sp_infl.setFixedWidth(50)
        wp_lay.addWidget(sp_infl)
        cat_s_std.add_item("weight_precision", "chk_weight_precision", True,
                           wp_w)
        cat_s_std.register_reset_callback("weight_precision", lambda: (
            wp_combo.setCurrentIndex(0),
            sp_infl.setValue(4)))
        cat_s_std.register_combo_tr("weight_precision_wp", wp_combo,
                                    ["wp_decimal_2", "wp_decimal_3"])
        # Joint orient -- aim axis
        jo_combo = NoScrollComboBox()
        jo_combo.addItems(["X", "Y", "Z"])
        jo_combo.setFixedWidth(50)
        cat_s_std.add_item("joint_orient", "chk_joint_orient", True, jo_combo)
        self._categories["setup_standard"] = cat_s_std
        self._setup_cat_keys.append("setup_standard")
        setup_sl.addWidget(cat_s_std)

        # ----- Optional (1 item, default OFF) -----
        cat_s_opt = CollapsibleCategory("tier_optional", 1, True)
        # Bone symmetry -- axis + tolerance
        sym_w = QtWidgets.QWidget()
        sym_lay = QtWidgets.QHBoxLayout(sym_w)
        sym_lay.setContentsMargins(0, 0, 0, 0)
        sym_lay.setSpacing(4)
        sym_combo = NoScrollComboBox()
        sym_combo.addItems(["X", "Y", "Z"])
        sym_combo.setFixedWidth(50)
        sym_lay.addWidget(sym_combo)
        sp_sym_tol = NoScrollDoubleSpinBox()
        sp_sym_tol.setRange(0.001, 10.0)
        sp_sym_tol.setValue(0.001)
        sp_sym_tol.setDecimals(3)
        sp_sym_tol.setFixedWidth(80)
        sym_lay.addWidget(sp_sym_tol)
        cat_s_opt.add_item("bone_symmetry", "chk_bone_symmetry", False, sym_w)
        cat_s_opt.register_reset_callback("bone_symmetry", lambda: (
            sym_combo.setCurrentIndex(0),
            sp_sym_tol.setValue(0.001)))
        cat_s_opt._header_chk.setChecked(False)
        self._categories["setup_optional"] = cat_s_opt
        self._setup_cat_keys.append("setup_optional")
        setup_sl.addWidget(cat_s_opt)

        setup_sl.addStretch()
        setup_scroll.setWidget(setup_sw)
        self._tab_widget.addTab(setup_scroll, tr("tab_setup"))

        self._tab_widget.currentChanged.connect(self._on_tab_changed)
        main.addWidget(self._tab_widget)

    def _build_check_row(self, main):
        """Build check execution button."""
        # ---------- Check Button ----------
        btn_row = QtWidgets.QHBoxLayout()
        self._btn_check = QtWidgets.QPushButton(tr("btn_check"))
        self._btn_check.setProperty("cssClass", "accent")
        self._btn_check.clicked.connect(self._run_check)
        btn_row.addWidget(self._btn_check)
        main.addLayout(btn_row)

    def _build_status_row(self, main):
        """Build status bar, progress bar, and report button row."""
        # ---------- Status & Progress ----------
        status_row = QtWidgets.QHBoxLayout()
        status_row.setContentsMargins(0, 0, 10, 0)
        self._status_bar = QtWidgets.QLabel(tr("ready"))
        self._status_bar.setStyleSheet(
            "font-size: 12px; color: #666; padding: 4px 8px;")
        self._status_bar.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                       QtWidgets.QSizePolicy.Preferred)
        status_row.addWidget(self._status_bar)
        self._progress_bar = QtWidgets.QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                         QtWidgets.QSizePolicy.Fixed)
        self._progress_bar.setVisible(False)
        status_row.addWidget(self._progress_bar)
        self._btn_cancel = QtWidgets.QPushButton("\u2715")
        self._btn_cancel.setFixedSize(30, 22)
        self._btn_cancel.setToolTip("Cancel")
        self._btn_cancel.clicked.connect(self._on_cancel)
        self._btn_cancel.setVisible(False)
        status_row.addWidget(self._btn_cancel)
        self._btn_copy_report = QtWidgets.QPushButton(tr("btn_copy_report"))
        self._btn_copy_report.setFixedWidth(120)
        self._btn_copy_report.setToolTip("Copy check results to clipboard")
        self._btn_copy_report.setCursor(QtCore.Qt.PointingHandCursor)
        self._btn_copy_report.setProperty("cssClass", "accent")
        self._btn_copy_report.clicked.connect(self._copy_report)
        status_row.addWidget(self._btn_copy_report)
        main.addLayout(status_row)

    # ========================================================
    # Tab helpers
    # ========================================================
    def _on_tab_changed(self, index):
        self._fit_height()

    def _active_cat_keys(self):
        idx = self._tab_widget.currentIndex()
        if idx == 0:
            return self._model_cat_keys
        return self._setup_cat_keys

    # ========================================================
    # Target Mode helpers
    # ========================================================
    def _on_group_toggled(self, checked):
        self._txt_group.setEnabled(checked)
        self._btn_set_group.setEnabled(checked)

    def _on_set_group(self):
        sel = cmds.ls(sl=True, long=True)
        if sel:
            self._txt_group.setText(sel[0])

    # ========================================================
    # Helpers
    # ========================================================
    def _fit_height(self):
        """Recalculate and apply optimal height, preserving current width.
        Uses setFixedHeight to snap to exact size, then loosens min/max
        so the user can still resize and the window won't shrink below
        _base_min_h on tab switch."""
        self.layout().activate()
        QtWidgets.QApplication.processEvents()
        h = self.sizeHint().height()
        # Snap to computed height, then restore flexible constraints
        self.setFixedHeight(h)
        self.setMinimumHeight(self._base_min_h)
        self.setMaximumHeight(16777215)

    def _show_progress(self):
        self._status_bar.setVisible(False)
        self._progress_bar.setFormat("%p%")
        self._progress_bar.setVisible(True)
        self._progress_bar.setValue(0)
        self._btn_cancel.setVisible(True)

    def _hide_progress(self):
        self._progress_bar.setVisible(False)
        self._progress_bar.setValue(0)
        self._btn_cancel.setVisible(False)
        self._status_bar.setVisible(True)

    _STATUS_BASE = "font-size: 12px; padding: 4px 8px;"

    def _set_status(self, text, state="ready"):
        """Set status bar text with state-based styling.
        States: ready (gray), success (green bg), error (red bg), working (accent)."""
        self._status_bar.setText(text)
        base = self._STATUS_BASE
        if state == "success":
            self._status_bar.setStyleSheet(
                base + " color: #4a4; background-color: #1a2e1a;"
                " border-radius: 3px;")
        elif state == "error":
            self._status_bar.setStyleSheet(
                base + " color: #c44; background-color: #2e1a1a;"
                " border-radius: 3px;")
        elif state == "working":
            self._status_bar.setStyleSheet(
                base + " color: #7aa2f7;")
        else:
            self._status_bar.setStyleSheet(
                base + " color: #666;")

    def _get_target_label(self):
        """Return a short label for the currently selected meshes."""
        sel = cmds.ls(sl=True, long=True, type="transform") or []
        meshes = [s for s in sel
                  if cmds.listRelatives(s, shapes=True, type="mesh")]
        names = meshes if meshes else sel
        if not names:
            return ""
        if len(names) == 1:
            return names[0].rsplit("|", 1)[-1]
        return "{0} +{1}".format(names[0].rsplit("|", 1)[-1], len(names) - 1)

    def _make_result_title(self, check_label):
        """Build result window title: '<check_label> \u2014 Results: <target>'"""
        target = getattr(self, "_target_label", "") or self._get_target_label()
        if target:
            return "{0} \u2014 Results: {1}".format(check_label, target)
        return check_label

    def _copy_report(self):
        # TODO: Port ReportLog class from UV QC Tools for full report generation
        QtWidgets.QMessageBox.information(
            self, WINDOW_TITLE, "Report feature coming soon.")

    def _get_target_mode(self):
        if self._radio_selected.isChecked():
            return "selected"
        elif self._radio_group.isChecked():
            return "group"
        return "visible"

    # ========================================================
    # Language
    # ========================================================
    def _on_lang_changed(self, index):
        global _LANG
        _LANG = "en" if index == 0 else "ja"
        self._refresh_ui_text()
        if self._help_dialog:
            self._help_dialog.refresh_lang()

    def _refresh_ui_text(self):
        self._lbl_lang.setText(tr("lang_label"))
        self._btn_help.setText(tr("btn_how_to_use"))
        self._grp_target.setTitle(tr("target_mode"))
        self._radio_visible.setText(tr("target_visible"))
        self._radio_selected.setText(tr("target_selected"))
        self._radio_group.setText(tr("target_group"))
        self._btn_set_group.setText(tr("btn_set_group"))
        self._txt_group.setPlaceholderText(tr("group_placeholder"))
        # Tab titles
        self._tab_widget.setTabText(0, tr("tab_model"))
        self._tab_widget.setTabText(1, tr("tab_setup"))
        # Categories
        for cat in self._categories.values():
            cat.refresh_lang()
        # Sub-option checkboxes
        if self._chk_concave_sub:
            self._chk_concave_sub.setText(tr("sub_concave"))
        if self._chk_holed_sub:
            self._chk_holed_sub.setText(tr("sub_holed"))
        if self._chk_eng_sub:
            self._chk_eng_sub.setText(tr("sub_english_only"))
        self._btn_check.setText(tr("btn_check"))
        self._set_status(tr("ready"))
        self._btn_copy_report.setText(tr("btn_copy_report"))

    # ========================================================
    # Help
    # ========================================================
    def _show_help(self):
        if self._help_dialog is None:
            self._help_dialog = HelpDialog(self)
        self._help_dialog.show()
        self._help_dialog.raise_()

    # ========================================================
    # Check execution (active tab only)
    # ========================================================
    def _run_check(self):
        self._target_label = self._get_target_label()
        enabled = []
        for key in self._active_cat_keys():
            for item_key, is_on in self._categories[key].get_enabled():
                if is_on:
                    enabled.append(item_key)
        if not enabled:
            QtWidgets.QMessageBox.warning(
                self, WINDOW_TITLE, tr("no_checks"))
            return
        QtWidgets.QMessageBox.information(
            self, WINDOW_TITLE,
            tr("mock_run", count=len(enabled)))

    def _set_buttons_enabled(self, enabled):
        self._btn_check.setEnabled(enabled)

    def _on_cancel(self):
        if self._worker and self._worker.isRunning():
            self._worker.cancel()

    def _on_progress(self, current, total, label):
        if total > 0:
            self._progress_bar.setValue(int(current * 100 / total))
        self._progress_bar.setFormat(label + "  %p%")
        self._set_status(label, "working")

    # ========================================================
    # Close
    # ========================================================
    def closeEvent(self, event):
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait()
        super(ModelQCToolsWindow, self).closeEvent(event)
# --- [810] worker ---
# depends on: [000] header

class QCWorker(QtCore.QThread):
    progress = QtCore.Signal(int, int, str)
    finished = QtCore.Signal(list, str)

    def __init__(self, func, *args):
        super(QCWorker, self).__init__()
        self._func = func
        self._args = args
        self._cancelled = False

    def run(self):
        try:
            results = self._func(
                *self._args,
                progress_cb=self._on_progress,
                cancel_check=lambda: self._cancelled
            )
            self.finished.emit(results or [], "")
        except Exception as e:
            self.finished.emit([], str(e))

    def _on_progress(self, current, total, label):
        self.progress.emit(current, total, label)

    def cancel(self):
        self._cancelled = True
# --- [900] entry ---
# depends on: [800] ui

def launch():
    ModelQCToolsWindow.show_window()
