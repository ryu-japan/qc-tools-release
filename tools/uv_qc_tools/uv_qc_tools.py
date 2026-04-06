# -*- coding: utf-8 -*-
# --- [000] header ---
# depends on: (none)
"""
UV QC Tools for Maya 2018/2023/2025 (Python 2.7 & 3 / PySide2 & PySide6)
Maya 2018 (Python 2.7) / Maya 2023 (Python 3) / Maya 2025 (Python 3) 対応版。
"""
from __future__ import print_function, division, unicode_literals

__VERSION__ = "1.7.12"
__RELEASE_DATE__ = "2026-04-06"
_VERSION = __VERSION__

try:
    import maya.cmds as cmds
    import maya.api.OpenMaya as om2
    import maya.OpenMayaUI as omui
    try:
        from PySide6 import QtWidgets, QtCore, QtGui
        from shiboken6 import wrapInstance
    except ImportError:
        from PySide2 import QtWidgets, QtCore, QtGui
        from shiboken2 import wrapInstance
    _IN_MAYA = True
except ImportError:
    _IN_MAYA = False

from collections import defaultdict, deque
import math
import itertools
import time
import webbrowser
import os
import tempfile
import atexit
try:
    from urllib import quote as _url_quote
except ImportError:
    from urllib.parse import quote as _url_quote
try:
    long
except NameError:
    long = int

try:
    import numpy as np
    from scipy.ndimage import distance_transform_cdt
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False


_MIN_RESOLUTION = 256
def _gcd(a, b):
    """GCD compatible with Python 2.7 / 3."""
    while b:
        a, b = b, a % b
    return a
_TD_DEFAULT_THRESHOLD_PCT = 20.0

_FEEDBACK_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdYhrFiuiYJyLVBzRDR6pPVQihj1y8PsHt3Mg6ZnY5THUGGyQ/viewform"
_FEEDBACK_ENTRY_ID = "entry.1931722805"
_FEEDBACK_ENTRY_TOOL_NAME = "entry.1298102635"
_FEEDBACK_ENTRY_MAYA_VERSION = "entry.1146110608"
_URL_MAX_LENGTH = 8000

_LANG = "en"
_UV_BOUNDARY_EPS = 1e-4

_ORIENT_HORIZONTAL_THRESHOLD = 0.7
_ORIENT_CONFIDENCE_THRESHOLD = 0.8

WINDOW_OBJECT_NAME = "uvQCToolsWindow"
WINDOW_TITLE = "UV QC Tools"
# objectName constants for result windows — used by QC Hub findChild() lookups
RESULTS_OBJECT_NAME             = "uvQCResultsWindow"
PIXEL_EDGE_RESULTS_OBJECT_NAME  = "uvQCPixelEdgeResultsWindow"
OVERLAP_RESULTS_OBJECT_NAME     = "uvQCOverlapResultsWindow"
ORIENTATION_RESULTS_OBJECT_NAME = "uvQCOrientationResultsWindow"
TD_RESULTS_OBJECT_NAME          = "uvQCTexelDensityResultsWindow"
HELP_DIALOG_OBJECT_NAME         = "uvQCHelpDialog"

# --- Arrow icon generation for dark-theme QSS ---
_ARROW_ICON_DIR = ""
_ARROW_ICON_FILES = []

def _create_arrow_icons():
    """Generate small triangle PNG icons for ComboBox/SpinBox arrows."""
    global _ARROW_ICON_DIR, _ARROW_ICON_FILES
    if not _IN_MAYA:
        return ""
    try:
        icon_dir = os.path.join(tempfile.gettempdir(), "uvqc_icons")
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

if _IN_MAYA:
    _ARROW_ICON_DIR = _create_arrow_icons()
    atexit.register(_cleanup_arrow_icons)
_ARROW_CSS_DIR = _ARROW_ICON_DIR.replace("\\", "/") if _ARROW_ICON_DIR else ""

# Dark theme palette (QC Hub compatible)
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
    "QTreeWidget {"
    "  background-color: #2b2b2b;"
    "  color: #e0e0e0;"
    "  border: 1px solid #555555;"
    "}"
    "QTreeWidget::item:selected {"
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
    "QMessageBox QPushButton {"
    "  min-width: 80px;"
    "}"
    "QMessageBox QLabel {"
    "  font-size: 14px;"
    "}"
    "QPushButton[cssClass=\"secondary\"] {"  # color inherited from QPushButton (#e0e0e0)
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
    "QPushButton[cssClass=\"accent\"] {"  # color inherited from QPushButton (#e0e0e0)
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
# NOTE: All help_* keys are maintained exclusively in [011] help_content.

# _LANG and _UV_BOUNDARY_EPS are defined in [000] header
_TR = {
    "no_mesh": {"ja": "\u30e1\u30c3\u30b7\u30e5\u304c\u9078\u629e\u3055\u308c\u3066\u3044\u307e\u305b\u3093\u3002", "en": "No mesh selected."},
    "edge_result": {"ja": "\u30c1\u30a7\u30c3\u30af\u5b8c\u4e86: {count} \u4ef6\u306e\u30a8\u30c3\u30b8\u30a8\u30e9\u30fc", "en": "Check complete: {count} edge error(s)"},
    "shell_result": {"ja": "\u30c1\u30a7\u30c3\u30af\u5b8c\u4e86: {count} \u4ef6\u306e\u30b7\u30a7\u30eb\u8ddd\u96e2\u30a8\u30e9\u30fc", "en": "Check complete: {count} shell distance error(s)"},
    "ovlp_result": {"ja": "\u91cd\u8907: {error}\u4ef6\uff08{error_groups}\u30b0\u30eb\u30fc\u30d7\uff09\u306e\u8981\u78ba\u8a8d, {intentional}\u4ef6\uff08{int_groups}\u30b0\u30eb\u30fc\u30d7\uff09\u306e\u610f\u56f3\u7684\u63a8\u5b9a", "en": "Overlaps: {error} issue(s) ({error_groups} group(s)) to review, {intentional} issue(s) ({int_groups} group(s)) likely intentional"},

    "no_errors": {"ja": "\u30a8\u30e9\u30fc\u306a\u3057 \u2714", "en": "No errors \u2714"},
    "error_count": {"ja": "\u30a8\u30e9\u30fc\u4ef6\u6570: {count}", "en": "Errors: {count}"},
    "group_count": {"ja": "\u30b0\u30eb\u30fc\u30d7\u6570: {gcount} ({ecount} \u30a8\u30c3\u30b8)", "en": "Groups: {gcount} ({ecount} edge(s))"},
    "tex_size": {"ja": "\u30c6\u30af\u30b9\u30c1\u30e3\u30b5\u30a4\u30ba", "en": "Texture Size"},
    "resolution": {"ja": "\u89e3\u50cf\u5ea6:", "en": "Resolution:"},
    "res_x": {"ja": "\u89e3\u50cf\u5ea6X:", "en": "ResolutionX:"},
    "res_y": {"ja": "\u89e3\u50cf\u5ea6Y:", "en": "ResolutionY:"},
    "nonsquare": {"ja": "\u975e\u6b63\u65b9\u5f62\uff08\u9577\u65b9\u5f62\uff09", "en": "Non-square (rectangular)"},
    "pixel_edge": {"ja": "\u30d4\u30af\u30bb\u30eb\u30a8\u30c3\u30b8\u6574\u5217", "en": "Pixel Edge Alignment"},
    "min_edge": {"ja": "\u6700\u5c0f\u30a8\u30c3\u30b8\u9577 (px):", "en": "Min edge length (px):"},
    "btn_pixel": {"ja": "\u30d4\u30af\u30bb\u30eb\u30a8\u30c3\u30b8\u30c1\u30a7\u30c3\u30af", "en": "Check Pixel Edges"},
    "btn_snap_selected": {"ja": "\u9078\u629e\u3092\u30d4\u30af\u30bb\u30eb\u5883\u754c\u306b\u30b9\u30ca\u30c3\u30d7", "en": "Snap Selected to Pixel Grid"},
    "snap_result": {"ja": "{count} \u500b\u306eUV\u9802\u70b9\u3092\u30b9\u30ca\u30c3\u30d7\u3057\u307e\u3057\u305f\u3002", "en": "Snapped {count} UV vertex(es) to pixel grid."},
    "snap_none": {"ja": "\u30b9\u30ca\u30c3\u30d7\u304c\u5fc5\u8981\u306aUV\u9802\u70b9\u306f\u3042\u308a\u307e\u305b\u3093\u3002", "en": "No UV vertices need snapping."},
    "select_all": {"ja": "\u3059\u3079\u3066\u9078\u629e", "en": "Select All"},
    "deselect_all": {"ja": "\u3059\u3079\u3066\u89e3\u9664", "en": "Deselect All"},
    "edge_horizontal": {"ja": "\u6c34\u5e73", "en": "H"},
    "edge_vertical": {"ja": "\u5782\u76f4", "en": "V"},
    "shell_dist": {"ja": "\u30b7\u30a7\u30eb\u8ddd\u96e2", "en": "Shell Distance"},
    "ignore_under": {"ja": "\u7121\u8996\u3059\u308b\u8ddd\u96e2 (px):", "en": "Ignore under (px):"},
    "ignore_unlock": {"ja": "\u624b\u52d5\u8abf\u6574", "en": "Manual adjust"},
    "error_under": {"ja": "\u30a8\u30e9\u30fc\u8ddd\u96e2 (px):", "en": "Error under (px):"},
    "btn_shell": {"ja": "\u30b7\u30a7\u30eb\u8ddd\u96e2\u30c1\u30a7\u30c3\u30af", "en": "Check Shell Distance"},
    "uv_overlap": {"ja": "UV\u91cd\u8907", "en": "UV Overlap"},
    "self_overlap": {"ja": "\u540c\u4e00\u30b7\u30a7\u30eb\u5185\u306e\u91cd\u8907\u3082\u542b\u3081\u308b", "en": "Include self-overlap (same shell)"},
    "btn_overlap": {"ja": "UV\u91cd\u8907\u30c1\u30a7\u30c3\u30af", "en": "Check UV Overlap"},

    "ovlp_group_error": {"ja": "\u26a0 \u8981\u78ba\u8a8d\u306e\u91cd\u8907\uff08{count}\u30b0\u30eb\u30fc\u30d7\uff09", "en": "\u26a0 Likely unintentional ({count} group(s))"},
    "ovlp_group_intentional": {"ja": "\u2139 \u610f\u56f3\u7684\u3068\u63a8\u5b9a\uff08{count}\u30b0\u30eb\u30fc\u30d7\uff09", "en": "\u2139 Likely intentional ({count} group(s))"},
    "ovlp_summary": {"ja": "\u91cd\u8907: {err_groups}\u30b0\u30eb\u30fc\u30d7\uff08{err_shells}\u30b7\u30a7\u30eb\uff09\u306e\u8981\u78ba\u8a8d, {int_groups}\u30b0\u30eb\u30fc\u30d7\uff08{int_shells}\u30b7\u30a7\u30eb\uff09\u306e\u610f\u56f3\u7684\u63a8\u5b9a", "en": "Overlaps: {err_groups} group(s) ({err_shells} shells) to review, {int_groups} group(s) ({int_shells} shells) likely intentional"},
    "ovlp_group_label": {"ja": "\u30b0\u30eb\u30fc\u30d7 {idx}\uff08{count}\u30b7\u30a7\u30eb \u2014 UDIM {udim}\uff09", "en": "Group {idx} ({count} shells \u2014 UDIM {udim})"},
    "ovlp_shell_label": {"ja": "{mesh} / Shell {sid} \u2014 {faces} faces", "en": "{mesh} / Shell {sid} \u2014 {faces} faces"},

    "ovlp_no_unintentional": {"ja": "\u2713 \u8981\u78ba\u8a8d\u306e\u91cd\u8907\u306f\u3042\u308a\u307e\u305b\u3093", "en": "\u2713 No likely unintentional overlaps found"},
    # --- v1.7.0-dev: Overlap tolerance filter UI ---
    "ovlp_summary_header": {"ja": "\u6982\u8981", "en": "Summary"},
    "ovlp_filter_header": {"ja": "\u30d5\u30a3\u30eb\u30bf", "en": "Filter"},
    "close": {"ja": "\u9589\u3058\u308b", "en": "Close"},
    "lang_label": {"ja": "Language / \u8a00\u8a9e:", "en": "Language / \u8a00\u8a9e:"},
    "btn_detect": {"ja": "\u30c6\u30af\u30b9\u30c1\u30e3\u304b\u3089\u81ea\u52d5\u691c\u51fa", "en": "Auto Detect from Texture"},
    "detect_result": {"ja": "\u30c6\u30af\u30b9\u30c1\u30e3\u89e3\u50cf\u5ea6\u3092\u691c\u51fa: {x} x {y}", "en": "Detected texture resolution: {x} x {y}"},
    "detect_fail": {"ja": "\u30c6\u30af\u30b9\u30c1\u30e3\u89e3\u50cf\u5ea6\u3092\u691c\u51fa\u3067\u304d\u307e\u305b\u3093\u3067\u3057\u305f\u3002", "en": "Could not detect texture resolution."},
    "detect_mixed": {"ja": "\u8907\u6570\u306e\u89e3\u50cf\u5ea6\u304c\u691c\u51fa\u3055\u308c\u307e\u3057\u305f\u3002\u624b\u52d5\u3067\u6307\u5b9a\u3057\u3066\u304f\u3060\u3055\u3044\u3002", "en": "Multiple resolutions detected. Please set manually."},
    "detect_mixed_title": {"ja": "\u8907\u6570\u306e\u89e3\u50cf\u5ea6\u3092\u691c\u51fa", "en": "Multiple Resolutions Detected"},
    "detect_mixed_msg": {"ja": "\u8907\u6570\u306e\u30c6\u30af\u30b9\u30c1\u30e3\u89e3\u50cf\u5ea6\u304c\u691c\u51fa\u3055\u308c\u307e\u3057\u305f\u3002\n\u4f7f\u7528\u3059\u308b\u89e3\u50cf\u5ea6\u3092\u9078\u629e\u3057\u3066\u304f\u3060\u3055\u3044:", "en": "Multiple texture resolutions detected.\nPlease select the resolution to use:"},
    "btn_how_to_use": {"ja": "\u4f7f\u3044\u65b9", "en": "How to Use"},
    "help_title": {"ja": "UV QC Tools \u2014 \u4f7f\u3044\u65b9", "en": "UV QC Tools \u2014 How to Use"},
    "computing": {"ja": "\u51e6\u7406\u4e2d\u2026", "en": "Processing\u2026"},
    "ready": {"ja": "\u5f85\u6a5f\u4e2d", "en": "Ready"},
    "cancelled": {"ja": "\u30ad\u30e3\u30f3\u30bb\u30eb\u3057\u307e\u3057\u305f", "en": "Cancelled"},
    "progress_pixel_scan": {"ja": "Pixel Edge: \u30a8\u30c3\u30b8\u8d70\u67fb\u4e2d\u2026 {current}/{total}", "en": "Pixel Edge: Scanning edges\u2026 {current}/{total}"},
    "progress_pixel_group": {"ja": "Pixel Edge: \u30b0\u30eb\u30fc\u30d7\u5316\u4e2d\u2026", "en": "Pixel Edge: Grouping\u2026"},
    "progress_shell_raster": {"ja": "Shell Distance: \u30e9\u30b9\u30bf\u30e9\u30a4\u30ba\u4e2d\u2026 {current}/{total}", "en": "Shell Distance: Rasterizing\u2026 {current}/{total}"},
    "progress_shell_bfs": {"ja": "Shell Distance: BFS\u8ddd\u96e2\u30de\u30c3\u30d7\u69cb\u7bc9\u4e2d\u2026 {current}/{total}", "en": "Shell Distance: Building distance maps\u2026 {current}/{total}"},
    "progress_shell_pair": {"ja": "Shell Distance: \u30da\u30a2\u5224\u5b9a\u4e2d\u2026 {current}/{total}", "en": "Shell Distance: Checking pairs\u2026 {current}/{total}"},
    "progress_ovlp_lowres": {"ja": "UV Overlap: \u4f4e\u89e3\u50cf\u5ea6\u30b9\u30ad\u30e3\u30f3\u4e2d\u2026", "en": "UV Overlap: Low-res scan\u2026"},
    "progress_ovlp_hires": {"ja": "UV Overlap: \u9ad8\u89e3\u50cf\u5ea6\u691c\u8a3c\u4e2d\u2026", "en": "UV Overlap: Hi-res verify\u2026"},
    "done_with_time": {"ja": "\u2713 {name} \u5b8c\u4e86 ({time}s)", "en": "\u2713 {name} done ({time}s)"},
    "padding_result": {"ja": "\u30c1\u30a7\u30c3\u30af\u5b8c\u4e86: {s_count} \u4ef6\u306e\u30b7\u30a7\u30eb\u8ddd\u96e2\u30a8\u30e9\u30fc, {t_count} \u4ef6\u306e\u30bf\u30a4\u30eb\u8ddd\u96e2\u30a8\u30e9\u30fc", "en": "Check complete: {s_count} shell padding error(s), {t_count} tile padding error(s)"},
    "range_result": {"ja": "\u30c1\u30a7\u30c3\u30af\u5b8c\u4e86: {cross} \u4ef6\u306e\u307e\u305f\u304e, {outside} \u4ef6\u306e\u7bc4\u56f2\u5916", "en": "Check complete: {cross} crossing(s), {outside} outside(s)"},
    "uv_padding": {"ja": "UV\u30d1\u30c7\u30a3\u30f3\u30b0", "en": "UV Padding"},
    "shell_padding": {"ja": "Shell padding", "en": "Shell padding"},
    "tile_padding": {"ja": "Tile padding", "en": "Tile padding"},
    "btn_padding": {"ja": "UV\u30d1\u30c7\u30a3\u30f3\u30b0\u30c1\u30a7\u30c3\u30af", "en": "Check UV Padding"},
    "uv_range": {"ja": "UV\u30ec\u30f3\u30b8\u30c1\u30a7\u30c3\u30af", "en": "UV Range Check"},
    "tile_crossing": {"ja": "\u30bf\u30a4\u30eb\u307e\u305f\u304e\u691c\u51fa", "en": "Check tile crossing"},
    "custom_range": {"ja": "\u30ab\u30b9\u30bf\u30e0\u7bc4\u56f2\u3092\u4f7f\u7528\uff08\u30c7\u30d5\u30a9\u30eb\u30c8: 0\u301c1\uff09", "en": "Use custom range (default: 0~1)"},
    "uv_u": {"ja": "UV U:", "en": "UV U:"},
    "uv_v": {"ja": "UV V:", "en": "UV V:"},
    "btn_range": {"ja": "UV\u30ec\u30f3\u30b8\u30c1\u30a7\u30c3\u30af", "en": "Check UV Range"},
    "progress_padding_raster": {"ja": "UV Padding: \u30e9\u30b9\u30bf\u30e9\u30a4\u30ba\u4e2d\u2026 {current}/{total}", "en": "UV Padding: Rasterizing\u2026 {current}/{total}"},
    "progress_padding_bfs": {"ja": "UV Padding: BFS\u8ddd\u96e2\u30de\u30c3\u30d7\u69cb\u7bc9\u4e2d\u2026 {current}/{total}", "en": "UV Padding: Building distance maps\u2026 {current}/{total}"},
    "progress_padding_pair": {"ja": "UV Padding: \u30da\u30a2\u5224\u5b9a\u4e2d\u2026 {current}/{total}", "en": "UV Padding: Checking pairs\u2026 {current}/{total}"},
    "progress_padding_tile": {"ja": "UV Padding: \u30bf\u30a4\u30eb\u5883\u754c\u30c1\u30a7\u30c3\u30af\u4e2d\u2026 {current}/{total}", "en": "UV Padding: Checking tile borders\u2026 {current}/{total}"},
    "progress_range": {"ja": "UV Range: \u30c1\u30a7\u30c3\u30af\u4e2d\u2026 {current}/{total}", "en": "UV Range: Checking\u2026 {current}/{total}"},

    # --- v24: Texel Density / v51: 3-mode / v56: Unified mode ---
    "texel_density": {"ja": "\u30c6\u30af\u30bb\u30eb\u5bc6\u5ea6", "en": "Texel Density"},
    "td_shell": {"ja": "\u901a\u5e38\u30e2\u30fc\u30c9\uff08\u30b7\u30a7\u30eb\u5358\u4f4d\uff09", "en": "Normal Mode (per-shell)"},
    "td_face": {"ja": "\u5747\u4e00\u6027\u30e2\u30fc\u30c9\uff08\u30d5\u30a7\u30fc\u30b9\u5358\u4f4d\uff09", "en": "Uniformity Mode (per-face)"},
    "td_shell_desc": {"ja": "\u30b7\u30a7\u30eb\u5358\u4f4d\u306e\u5e73\u5747\u5bc6\u5ea6\u3067\u5224\u5b9a", "en": "Average density per shell"},
    "td_face_desc": {"ja": "\u30d5\u30a7\u30fc\u30b9\u5358\u4f4d\u306e\u3070\u3089\u3064\u304d\u3092\u691c\u51fa", "en": "Detect per-face variation"},
    "btn_texel": {"ja": "\u30c6\u30af\u30bb\u30eb\u5bc6\u5ea6\u3092\u8a08\u6e2c", "en": "Measure Texel Density"},
    "texel_result": {"ja": "\u8a08\u6e2c\u5b8c\u4e86: {count} \u30b7\u30a7\u30eb", "en": "Measured: {count} shell(s)"},
    "progress_texel": {"ja": "Texel Density: \u8a08\u6e2c\u4e2d\u2026 {current}/{total}", "en": "Texel Density: Measuring\u2026 {current}/{total}"},
    "texel_too_low": {"ja": "\u4f4e", "en": "LOW"},
    "texel_too_high": {"ja": "\u9ad8", "en": "HIGH"},
    "td_stats_header": {"ja": "\u5bc6\u5ea6\u7d71\u8a08", "en": "Density Statistics"},
    "td_stats_weighted_avg": {"ja": "\u9762\u7a4d\u52a0\u91cd\u5e73\u5747: {val}", "en": "Weighted avg: {val}"},
    "td_stats_median": {"ja": "\u4e2d\u592e\u5024: {val}", "en": "Median: {val}"},
    "td_stats_min": {"ja": "\u6700\u5c0f: {val}", "en": "Min: {val}"},
    "td_stats_max": {"ja": "\u6700\u5927: {val}", "en": "Max: {val}"},
    "td_stats_threshold": {"ja": "\u95be\u5024\u5bc6\u5ea6: {val}", "en": "Threshold density: {val}"},
    "td_hist_drag_hint": {"ja": "\u25c0\u25b6 \u30c9\u30e9\u30c3\u30b0\u3067\u7bc4\u56f2\u3092\u5909\u66f4", "en": "\u25c0\u25b6 Drag to adjust"},
    "td_hist_legend_low": {"ja": "\u25c0 \u4f4e\u5bc6\u5ea6\u30a8\u30e9\u30fc", "en": "\u25c0 Low density error"},
    "td_hist_legend_high": {"ja": "\u9ad8\u5bc6\u5ea6\u30a8\u30e9\u30fc \u25b6", "en": "High density error \u25b6"},
    # v56: Unified result window filter panel
    "td_filter_header": {"ja": "\u30d5\u30a3\u30eb\u30bf", "en": "Filter"},
    "td_chk_min": {"ja": "\u4e0b\u9650 (px/unit):", "en": "Min (px/unit):"},
    "td_chk_max": {"ja": "\u4e0a\u9650 (px/unit):", "en": "Max (px/unit):"},
    "td_target_input": {"ja": "\u57fa\u6e96\u5024 (px/unit):", "en": "Target (px/unit):"},
    "td_tolerance_input": {"ja": "\u00b1 \u8a31\u5bb9\u5024:", "en": "\u00b1 Tolerance:"},
    "td_threshold_input": {"ja": "\u4f4e\u5bc6\u5ea6\u306e\u57fa\u6e96 (\u5e73\u5747\u306e %):", "en": "Low density cutoff (% of avg):"},
    "td_filter_count": {"ja": "{below} \u4ef6\u304c\u4e0b\u9650\u672a\u6e80, {above} \u4ef6\u304c\u4e0a\u9650\u8d85\u904e ({total} \u30b7\u30a7\u30eb\u4e2d)", "en": "{below} below min, {above} above max (of {total})"},
    "td_filter_count_min_only": {"ja": "{below} / {total} \u30b7\u30a7\u30eb\u304c\u4e0b\u9650\u672a\u6e80", "en": "{below} / {total} shell(s) below min"},
    "td_filter_count_max_only": {"ja": "{above} / {total} \u30b7\u30a7\u30eb\u304c\u4e0a\u9650\u8d85\u904e", "en": "{above} / {total} shell(s) above max"},
    "td_filter_none": {"ja": "\u30d5\u30a3\u30eb\u30bf\u306a\u3057\uff08\u5168\u30b7\u30a7\u30eb\u8868\u793a\uff09", "en": "No filter (showing all shells)"},
    "td_set_by_target": {"ja": "\u57fa\u6e96\u5024 \u00b1 \u8a31\u5bb9\u5024\u3067\u8a2d\u5b9a", "en": "Set by Target \u00b1 Tol"},
    "td_set_by_threshold": {"ja": "\u5e73\u5747\u306e%\u3092\u4e0b\u9650\u306b\u8a2d\u5b9a", "en": "Set by Threshold %"},
    "td_set_by_direct": {"ja": "\u76f4\u63a5\u5165\u529b / \u30c9\u30e9\u30c3\u30b0", "en": "Direct input / Drag"},
    # --- v29: UVSet Check ---
    "uvset_check": {"ja": "UVSet\u30c1\u30a7\u30c3\u30af", "en": "UVSet Check"},
    "btn_uvset": {"ja": "UVSet\u78ba\u8a8d\u30fb\u9078\u629e", "en": "Verify & Select UVSet"},
    "uvset_result": {"ja": "\u30c1\u30a7\u30c3\u30af\u5b8c\u4e86: {count} \u4ef6\u306e\u4e0d\u8981UVSet", "en": "Check complete: {count} extra UVSet(s)"},
    # --- v31: UVSet Check enhancements ---
    "uvset_single": {"ja": "UVSet\u306f map1 \u306e\u307f\u3067\u3059 \u2714", "en": "Only default UVSet (map1) found \u2714"},
    "uvset_list_count": {"ja": "UVSet\u4e00\u89a7: {count} \u4ef6", "en": "UVSets: {count}"},
    "uvset_default_marker": {"ja": "(\u30c7\u30d5\u30a9\u30eb\u30c8)", "en": "(default)"},
    "uvset_mesh_count": {"ja": "{count}/{total} \u30e1\u30c3\u30b7\u30e5", "en": "{count}/{total} mesh(es)"},
    # --- v33: Material Separator confirmation dialogs ---
    "mat_sep_single_mat_title": {"ja": "\u78ba\u8a8d", "en": "Confirm"},
    "mat_sep_single_mat_msg": {
        "ja": "\u30de\u30c6\u30ea\u30a2\u30eb\u304c1\u3064\u306e\u307f\u306e\u305f\u3081\u3001\u5206\u5272\u3092\u30b9\u30ad\u30c3\u30d7\u3057\u307e\u3057\u305f\u3002",
        "en": "Only one material found. Separation was skipped."},
    "mat_sep_multi_mat_title": {"ja": "\u78ba\u8a8d", "en": "Confirm"},
    "mat_sep_multi_mat_msg": {
        "ja": "\u9078\u629e\u30e1\u30c3\u30b7\u30e5\u3092\u8907\u88fd\u3057\u3001\u30de\u30c6\u30ea\u30a2\u30eb\u3054\u3068\u306b\u30e1\u30c3\u30b7\u30e5\u3092\u5206\u5272\u3057\u307e\u3059\u3002\u5143\u306e\u30e1\u30c3\u30b7\u30e5\u306f\u5909\u66f4\u3055\u308c\u307e\u305b\u3093\u3002",
        "en": "This will duplicate the selected mesh and separate it by material. The original mesh will not be modified."},
    # --- v30: Section Labels ---
    "section_prep": {"ja": "\u6e96\u5099", "en": "Preparation"},
    "section_check": {"ja": "\u30c1\u30a7\u30c3\u30af", "en": "Check"},
    # --- v28: Material Separator ---
    "mat_sep_btn": {"ja": "1\u30e1\u30c3\u30b7\u30e51\u30de\u30c6\u30ea\u30a2\u30eb\u5316", "en": "1 Material per Mesh"},
    "mat_sep_run": {"ja": "\u5b9f\u884c", "en": "Run"},
    "mat_sep_settings_title": {"ja": "1\u30e1\u30c3\u30b7\u30e51\u30de\u30c6\u30ea\u30a2\u30eb\u5316 \u8a2d\u5b9a", "en": "1 Material per Mesh Settings"},
    "mat_sep_combine_opts": {"ja": "\u7d50\u5408\u30aa\u30d7\u30b7\u30e7\u30f3", "en": "Combine Options"},
    "mat_sep_merge_uv": {"ja": "UV\u7d71\u5408", "en": "Merge UVs"},
    "mat_sep_del_hist": {"ja": "\u30d2\u30b9\u30c8\u30ea\u524a\u9664", "en": "Delete History"},
    "mat_sep_separate_opts": {"ja": "\u5206\u96e2\u30aa\u30d7\u30b7\u30e7\u30f3", "en": "Separate Options"},
    "mat_sep_naming": {"ja": "\u547d\u540d\u898f\u5247:", "en": "Naming:"},
    "mat_sep_grouping": {"ja": "\u30b0\u30eb\u30fc\u30d7\u5316", "en": "Group"},
    "mat_sep_group_name": {"ja": "\u30b0\u30eb\u30fc\u30d7\u540d\uff08\u7a7a\u6b04\u3067\u81ea\u52d5\uff09:", "en": "Group name (blank=auto):"},
    "mat_sep_freeze_tf": {"ja": "\u30d5\u30ea\u30fc\u30ba\u30c8\u30e9\u30f3\u30b9\u30d5\u30a9\u30fc\u30e0", "en": "Freeze Transform"},
    "mat_sep_naming_mesh_mat": {"ja": "{\u5143\u30e1\u30c3\u30b7\u30e5}_{\u30de\u30c6\u30ea\u30a2\u30eb}", "en": "{OrigMesh}_{Material}"},
    "mat_sep_naming_mat": {"ja": "{\u30de\u30c6\u30ea\u30a2\u30eb}", "en": "{Material}"},
    "mat_sep_naming_mat_idx": {"ja": "{\u30de\u30c6\u30ea\u30a2\u30eb}_{\u9023\u756a}", "en": "{Material}_{Index}"},
    "mat_sep_no_mesh": {"ja": "\u30e1\u30c3\u30b7\u30e5\u3092\u9078\u629e\u3057\u3066\u304f\u3060\u3055\u3044\u3002", "en": "Please select a mesh."},
    "mat_sep_no_sg": {"ja": "ShadingGroup \u304c\u898b\u3064\u304b\u308a\u307e\u305b\u3093\u3002", "en": "No ShadingGroup found."},
    "mat_sep_summary_title": {"ja": "\u7d50\u679c", "en": "Result"},
    "mat_sep_summary_ok": {
        "ja": "\u5b8c\u4e86 \u2714\n\n\u691c\u51fa\u30de\u30c6\u30ea\u30a2\u30eb\u6570: {mat_count}\n{mat_list}\n\n\u751f\u6210\u30e1\u30c3\u30b7\u30e5\u6570: {mesh_count}\n\u30b0\u30eb\u30fc\u30d7: {group}",
        "en": "Complete \u2714\n\nMaterials: {mat_count}\n{mat_list}\n\nGenerated: {mesh_count} mesh(es)\nGroup: {group}"},
    "mat_sep_summary_cancel": {
        "ja": "\u30ad\u30e3\u30f3\u30bb\u30eb\u3055\u308c\u307e\u3057\u305f\u3002\n\u751f\u6210\u30e1\u30c3\u30b7\u30e5\u6570: {mesh_count}\uff08\u9014\u4e2d\uff09",
        "en": "Operation was cancelled.\nGenerated: {mesh_count} mesh(es) (partial)"},
    "mat_sep_progress_combine": {"ja": "\u30e1\u30c3\u30b7\u30e5\u7d50\u5408\u4e2d\u2026", "en": "Combining meshes\u2026"},
    "mat_sep_progress_analyze": {"ja": "\u30de\u30c6\u30ea\u30a2\u30eb\u89e3\u6790\u4e2d\u2026", "en": "Analyzing materials\u2026"},
    "mat_sep_progress_separate": {"ja": "\u5206\u96e2\u4e2d\u2026 {current}/{total}", "en": "Separating\u2026 {current}/{total}"},
    "mat_sep_progress_cleanup": {"ja": "\u30af\u30ea\u30fc\u30f3\u30a2\u30c3\u30d7\u4e2d\u2026", "en": "Cleaning up\u2026"},
    # --- v46: Mode reorganization ---
    "mode_normal": {"ja": "\u901a\u5e38\u30e2\u30fc\u30c9", "en": "Normal Mode"},
    "high_precision": {"ja": "\u9ad8\u7cbe\u5ea6\u30e2\u30fc\u30c9", "en": "High Precision Mode"},
    "normal_mode_desc": {"ja": "\u7cbe\u5ea6\u304c\u308f\u305a\u304b\u306b\u4f4e\u4e0b\u3059\u308b\u5834\u5408\u304c\u3042\u308a\u307e\u3059", "en": "Accuracy may be slightly reduced"},
    "high_precision_desc": {"ja": "\u6b63\u78ba\u3067\u3059\u304c\u51e6\u7406\u304c\u9045\u304f\u306a\u308a\u307e\u3059", "en": "Accurate, but slower"},
    "phase1": {"ja": "Phase 1: \u9ad8\u901f\u30b9\u30ad\u30e3\u30f3\u4e2d\u2026", "en": "Phase 1: Fast scanning\u2026"},
    "phase2": {"ja": "Phase 2: \u7cbe\u67fb\u4e2d\u2026 ({count} \u5bfe\u8c61)", "en": "Phase 2: Verifying\u2026 ({count} target(s))"},
    # --- v62: UV Orientation Check ---
    "btn_orientation": {"ja": "UV\u65b9\u5411\u30c1\u30a7\u30c3\u30af", "en": "Check UV Orientation"},
    "uv_orientation": {"ja": "UV\u65b9\u5411 (Beta)", "en": "UV Orientation (Beta)"},
    "orientation_result": {"ja": "\u30c1\u30a7\u30c3\u30af\u5b8c\u4e86: {total} \u30b7\u30a7\u30eb\u4e2d {issues} \u4ef6\u306e\u65b9\u5411\u554f\u984c", "en": "Check complete: {issues} issue(s) in {total} shell(s)"},
    "orient_normal": {"ja": "\u2705 \u6b63\u5e38", "en": "\u2705 Normal"},
    "orient_rotated": {"ja": "\u274c \u56de\u8ee2\u305a\u308c", "en": "\u274c Rotated"},
    "orient_needs_review": {"ja": "\u26a0 \u8981\u78ba\u8a8d\uff08\u5224\u5b9a\u304c\u4e0d\u78ba\u5b9f\uff09", "en": "\u26a0 Needs Review (uncertain)"},
    "orient_indeterminate": {"ja": "\u2753 \u5224\u5b9a\u4e0d\u80fd", "en": "\u2753 Indeterminate"},
    "orient_flipped_suffix": {"ja": "(\u53cd\u8ee2)", "en": "(Flipped)"},
    "progress_orientation": {"ja": "UV Orientation: \u30c1\u30a7\u30c3\u30af\u4e2d\u2026 {current}/{total}", "en": "UV Orientation: Checking\u2026 {current}/{total}"},
    "check_error": {"ja": "\u30c1\u30a7\u30c3\u30af\u4e2d\u306b\u30a8\u30e9\u30fc\u304c\u767a\u751f\u3057\u307e\u3057\u305f\u3002", "en": "An error occurred during the check."},
    # --- v59: Report Log ---
    "btn_copy_report": {"ja": "\u30ec\u30dd\u30fc\u30c8\u3092\u9001\u4fe1", "en": "Send Report"},

    "report_empty": {"ja": "\u30b3\u30d4\u30fc\u3059\u308b\u30c1\u30a7\u30c3\u30af\u7d50\u679c\u304c\u3042\u308a\u307e\u305b\u3093\u3002", "en": "No check results to copy."},
    "report_form_opened": {"ja": "\u30d5\u30a9\u30fc\u30e0\u3092\u30d6\u30e9\u30a6\u30b6\u3067\u958b\u304d\u307e\u3057\u305f\u3002", "en": "Feedback form opened in browser."},
    "report_url_too_long": {"ja": "\u30ec\u30dd\u30fc\u30c8\u304c\u9577\u3059\u304e\u308b\u305f\u3081\u3001\u30d5\u30a9\u30fc\u30e0\u306b\u81ea\u52d5\u5165\u529b\u3067\u304d\u307e\u305b\u3093\u3067\u3057\u305f\u3002\n\u30af\u30ea\u30c3\u30d7\u30dc\u30fc\u30c9\u306b\u30b3\u30d4\u30fc\u6e08\u307f\u3067\u3059\u3002\u30d5\u30a9\u30fc\u30e0\u306e\u30ec\u30dd\u30fc\u30c8\u6b04\u306b\u8cbc\u308a\u4ed8\u3051\u3066\u304f\u3060\u3055\u3044\u3002", "en": "Report too long for auto-fill.\nCopied to clipboard. Please paste into the report field."},
    "report_form_not_configured": {"ja": "\u30d5\u30a9\u30fc\u30e0\u306eURL\u307e\u305f\u306fEntry ID\u304c\u672a\u8a2d\u5b9a\u3067\u3059\u3002\n[000] header \u306e _FEEDBACK_FORM_URL \u3068 _FEEDBACK_ENTRY_ID \u3092\u8a2d\u5b9a\u3057\u3066\u304f\u3060\u3055\u3044\u3002", "en": "Feedback form URL or Entry ID not configured.\nPlease set _FEEDBACK_FORM_URL and _FEEDBACK_ENTRY_ID in [000] header."},
    # --- v63: Result window title ---
    "results_word": {"ja": "\u7d50\u679c", "en": "Results"},
    # --- v1.7.1-dev: Overlap tolerance UX improvements ---
    "ovlp_preset_default": {"ja": "\u30c7\u30d5\u30a9\u30eb\u30c8", "en": "Default"},
    "ovlp_tol_desc_strict": {"ja": "\u5fae\u5c0f\u306a\u9802\u70b9\u305a\u308c\u3082\u30a8\u30e9\u30fc\u3068\u3057\u3066\u691c\u51fa", "en": "Detects even tiny vertex misalignment as error"},
    "ovlp_tol_desc_default": {"ja": "\u4e00\u822c\u7684\u306a\u91cd\u8907\u691c\u51fa\u306b\u9069\u3057\u305f\u30d0\u30e9\u30f3\u30b9", "en": "Balanced setting for general overlap detection"},
    "ovlp_tol_desc_loose": {"ja": "\u5927\u304d\u306a\u305a\u308c\u306e\u307f\u8981\u78ba\u8a8d\u3068\u3057\u3066\u691c\u51fa", "en": "Only flags large misalignment for review"},

    # v1.7.4-dev: Overlap histogram legend labels
    "ovlp_hist_legend_strict": {"ja": "\u25c0 \u53b3\u5bc6\uff08\u8981\u78ba\u8a8d \u5897\uff09", "en": "\u25c0 Strict (more to review)"},
    "ovlp_hist_legend_loose": {"ja": "\u7de9\u548c\uff08\u610f\u56f3\u7684 \u5897\uff09 \u25b6", "en": "Relaxed (more intentional) \u25b6"},
    # ~1.7.7-dev: Drag summary (lightweight shell count during histogram drag)

    # ~1.7.11-dev: Vertical summary labels + drag hint
    "ovlp_stat_err_groups": {"ja": "\u8981\u78ba\u8a8d\u30b0\u30eb\u30fc\u30d7: {val}", "en": "Groups to review: {val}"},
    "ovlp_stat_err_shells": {"ja": "\u8981\u78ba\u8a8d\u30b7\u30a7\u30eb: {val}", "en": "Shells to review: {val}"},
    "ovlp_stat_int_groups": {"ja": "\u610f\u56f3\u7684\u30b0\u30eb\u30fc\u30d7: {val}", "en": "Intentional groups: {val}"},
    "ovlp_stat_int_shells": {"ja": "\u610f\u56f3\u7684\u30b7\u30a7\u30eb: {val}", "en": "Intentional shells: {val}"},
    "ovlp_stat_err_pairs": {"ja": "\u8981\u78ba\u8a8d\u30da\u30a2: ~{val}", "en": "Pairs to review: ~{val}"},
    "ovlp_stat_int_pairs": {"ja": "\u610f\u56f3\u7684\u30da\u30a2: ~{val}", "en": "Intentional pairs: ~{val}"},
    "ovlp_hist_drag_hint": {"ja": "\u25c0\u25b6 \u30c9\u30e9\u30c3\u30b0\u3067\u95be\u5024\u3092\u5909\u66f4", "en": "\u25c0\u25b6 Drag to adjust threshold"},
}

def tr(key, **kwargs):
    text = _TR.get(key, {}).get(_LANG, key)
    if isinstance(text, bytes):
        text = text.decode('utf-8')
    if kwargs:
        text = text.format(**kwargs)
    return text
# --- [011] help_content ---
# depends on: [010] i18n
# note    : _TR dict へヘルプ用 HTML エントリを追加。
#           [010] i18n で定義済みの _TR に .update() でマージする。
#           表示順は [800] ui の HelpDialog._update_content() で制御。

_TR.update({
    # ========== 概要 ==========
    "help_overview": {
        "ja": "<h2>\u57fa\u672c\u306e\u6d41\u308c</h2>"
              "<ol>"
              "<li>\u30c1\u30a7\u30c3\u30af\u5bfe\u8c61\u306e<b>\u30e1\u30c3\u30b7\u30e5\u3092\u9078\u629e</b>\uff08\u30c8\u30c3\u30d7\u30ce\u30fc\u30c9\u9078\u629e\u3067\u5b50\u30e1\u30c3\u30b7\u30e5\u3092\u81ea\u52d5\u53ce\u96c6\uff09</li>"
              "<li>\u5fc5\u8981\u306b\u5fdc\u3058\u3066<b>\u6e96\u5099</b>\u3092\u5b9f\u884c\uff08UVSet\u78ba\u8a8d\u30fb1\u30e1\u30c3\u30b7\u30e51\u30de\u30c6\u30ea\u30a2\u30eb\u5316\uff09</li>"
              "<li><b>\u30c6\u30af\u30b9\u30c1\u30e3\u89e3\u50cf\u5ea6</b>\u3092\u8a2d\u5b9a\uff08\u81ea\u52d5\u691c\u51fa\u3082\u53ef\u80fd\uff09</li>"
              "<li>\u5404<b>\u30c1\u30a7\u30c3\u30af</b>\u30dc\u30bf\u30f3\u3092\u5b9f\u884c</li>"
              "<li>\u7d50\u679c\u30a6\u30a3\u30f3\u30c9\u30a6\u3067\u30a8\u30e9\u30fc\u3092\u78ba\u8a8d\u30fb\u9078\u629e</li>"
              "<li><b>\u30d2\u30f3\u30c8</b>: \u3059\u3079\u3066\u306e\u30c1\u30a7\u30c3\u30af\u306f\u975e\u540c\u671f\u3067\u5b9f\u884c\u3055\u308c\u3001\u30d7\u30ed\u30b0\u30ec\u30b9\u30d0\u30fc\u3067\u9032\u6357\u3092\u78ba\u8a8d\u3067\u304d\u307e\u3059\u3002\u51e6\u7406\u4e2d\u306f\u00d7\u30dc\u30bf\u30f3\u3067\u30ad\u30e3\u30f3\u30bb\u30eb\u53ef\u80fd\u3067\u3059\u3002</li>"
              "</ol>",
        "en": "<h2>Basic Workflow</h2>"
              "<ol>"
              "<li><b>Select meshes</b> to check (selecting a top node auto-gathers child meshes)</li>"
              "<li>Run <b>Preparation</b> if needed (UVSet check, 1 Material per Mesh)</li>"
              "<li>Set the <b>texture resolution</b> (auto-detect available)</li>"
              "<li>Run each <b>Check</b> button</li>"
              "<li>Review and select errors in the results window</li>"
              "<li><b>Tip</b>: All checks run asynchronously with a progress bar. You can cancel with the \u00d7 button during processing.</li>"
              "</ol>",
    },
    # ========== 準備（Preparation） ==========
    "help_section_prep": {
        "ja": "<hr><h2>\u6e96\u5099\uff08Preparation\uff09</h2>",
        "en": "<hr><h2>Preparation</h2>",
    },
    "help_uvset_check": {
        "ja": "<h3>UVSet\u30c1\u30a7\u30c3\u30af</h3>"
              "<p>\u9078\u629e\u30e1\u30c3\u30b7\u30e5\u306e\u5168UVSet\uff08map1\u542b\u3080\uff09\u3092\u4e00\u89a7\u8868\u793a\u3057\u307e\u3059\u3002</p>"
              "<ul>"
              "<li>\u5404UVSet\u306e\u8a72\u5f53\u30e1\u30c3\u30b7\u30e5\u6570\u3092\u8868\u793a\u3002\u30c7\u30d5\u30a9\u30eb\u30c8(map1)\u306b\u306f\u30de\u30fc\u30ab\u30fc\u4ed8\u304d</li>"
              "<li>\u30af\u30ea\u30c3\u30af\u3067\u30e1\u30c3\u30b7\u30e5\u3092\u9078\u629e\u3057\u3001UV\u30a8\u30c7\u30a3\u30bf\u306eUVSet\u3092\u5207\u66ff</li>"
              "<li>\u524a\u9664\u6a5f\u80fd\u306a\u3057\uff08\u8aa4\u524a\u9664\u9632\u6b62\u306e\u305f\u3081\u624b\u52d5\u3067\u5bfe\u5fdc\uff09</li>"
              "</ul>",
        "en": "<h3>UVSet Check</h3>"
              "<p>Lists all UV sets (including map1) on the selected meshes.</p>"
              "<ul>"
              "<li>Shows mesh count per UV set. Default (map1) is marked</li>"
              "<li>Click to select the mesh and switch the UV set in the UV Editor</li>"
              "<li>No delete function (use polyUVSet -delete manually if needed)</li>"
              "</ul>",
    },
    "help_mat_sep": {
        "ja": "<h3>1\u30e1\u30c3\u30b7\u30e51\u30de\u30c6\u30ea\u30a2\u30eb\u5316</h3>"
              "<p>\u30e1\u30c3\u30b7\u30e5\u304c\u8907\u6570\u30de\u30c6\u30ea\u30a2\u30eb\u3092\u542b\u3080\u5834\u5408\u3001\u30de\u30c6\u30ea\u30a2\u30eb\u3054\u3068\u306b\u5206\u5272\u3057\u3066\u304b\u3089\u30c1\u30a7\u30c3\u30af\u3059\u308b\u3068\u78ba\u8a8d\u3057\u3084\u3059\u304f\u306a\u308a\u307e\u3059\u3002</p>"
              "<ul>"
              "<li><b>1\u30e1\u30c3\u30b7\u30e51\u30de\u30c6\u30ea\u30a2\u30eb\u5316</b>\u30dc\u30bf\u30f3\u3067\u30ef\u30f3\u30af\u30ea\u30c3\u30af\u5b9f\u884c\u3002<b>\u2699 \u30dc\u30bf\u30f3</b>\u3067\u8a73\u7d30\u8a2d\u5b9a</li>"
              "<li>\u5b8c\u4e86\u6642\u306b\u30de\u30c6\u30ea\u30a2\u30eb\u540d\u30fb\u30e1\u30c3\u30b7\u30e5\u6570\u30fb\u30b0\u30eb\u30fc\u30d7\u540d\u306e\u30b5\u30de\u30ea\u30fc\u3092\u8868\u793a</li>"
              "</ul>",
        "en": "<h3>1 Material per Mesh</h3>"
              "<p>When a mesh contains multiple materials, separating by material before checks makes review easier.</p>"
              "<ul>"
              "<li>Click the <b>1 Material per Mesh</b> button for one-click execution. Use the <b>\u2699 button</b> for detailed settings</li>"
              "<li>Shows a summary on completion (material names, mesh count, group name)</li>"
              "</ul>",
    },
    # ========== テクスチャサイズ ==========
    "help_tex_size": {
        "ja": "<h3>\u30c6\u30af\u30b9\u30c1\u30e3\u30b5\u30a4\u30ba</h3>"
              "<ul>"
              "<li>\u30d7\u30ea\u30bb\u30c3\u30c8\u304b\u3089\u9078\u629e\u3001\u307e\u305f\u306fCustom\u3067\u4efb\u610f\u306e\u6570\u5024\u3092\u76f4\u63a5\u6307\u5b9a</li>"
              "<li><b>\u30c6\u30af\u30b9\u30c1\u30e3\u304b\u3089\u81ea\u52d5\u691c\u51fa</b>: \u9078\u629e\u30e1\u30c3\u30b7\u30e5\u306e\u30c6\u30af\u30b9\u30c1\u30e3\u304b\u3089\u89e3\u50cf\u5ea6\u3092\u81ea\u52d5\u53d6\u5f97</li>"
              "<li><b>\u975e\u6b63\u65b9\u5f62</b>: \u30c1\u30a7\u30c3\u30af\u3092\u5165\u308c\u308b\u3068 X / Y \u3092\u500b\u5225\u306b\u6307\u5b9a\u53ef\u80fd</li>"
              "</ul>",
        "en": "<h3>Texture Size</h3>"
              "<ul>"
              "<li>Select from presets, or enter any value directly via Custom</li>"
              "<li><b>Auto Detect</b>: Reads resolution from selected mesh textures</li>"
              "<li><b>Non-square</b>: Check to set X / Y independently</li>"
              "</ul>",
    },
    # ========== チェック（Check） ==========
    "help_section_check": {
        "ja": "<hr><h2>\u30c1\u30a7\u30c3\u30af\uff08Check\uff09</h2>",
        "en": "<hr><h2>Check</h2>",
    },
    "help_pixel_edge": {
        "ja": "<h3>\u30d4\u30af\u30bb\u30eb\u30a8\u30c3\u30b8\u6574\u5217</h3>"
              "<p>UV\u5883\u754c\u30a8\u30c3\u30b8\u304c\u30d4\u30af\u30bb\u30eb\u5883\u754c\u7dda\u306b\u63c3\u3063\u3066\u3044\u308b\u304b\u30c1\u30a7\u30c3\u30af\u3057\u307e\u3059\u3002</p>"
              "<ul>"
              "<li>\u6c34\u5e73(H) / \u5782\u76f4(V)\u306e\u5883\u754c\u30a8\u30c3\u30b8\uff08\u30b7\u30fc\u30e0\u542b\u3080\uff09\u304c\u5bfe\u8c61</li>"
              "<li>\u9023\u7d9a\u30a8\u30c3\u30b8\u3092\u81ea\u52d5\u30b0\u30eb\u30fc\u30d7\u5316\u30571\u9805\u76ee\u3068\u3057\u3066\u8868\u793a</li>"
              "<li><b>\u6700\u5c0f\u30a8\u30c3\u30b8\u9577(px)</b>: \u3053\u306e\u9577\u3055\u672a\u6e80\u306e\u30a8\u30c3\u30b8\u306f\u9664\u5916\uff08\u30c7\u30d5\u30a9\u30eb\u30c8: 1.0\uff09</li>"
              "<li>\u7d50\u679c\u30a6\u30a3\u30f3\u30c9\u30a6\u3067\u30c1\u30a7\u30c3\u30af\u30dc\u30c3\u30af\u30b9\u3067\u500b\u5225\u9078\u629e\u30fb\u89e3\u9664\u304c\u53ef\u80fd</li>"
              "<li><b>\u9078\u629e\u3092\u30d4\u30af\u30bb\u30eb\u5883\u754c\u306b\u30b9\u30ca\u30c3\u30d7</b>: \u30c1\u30a7\u30c3\u30af\u3057\u305f\u30a8\u30e9\u30fc\u3092\u30d4\u30af\u30bb\u30eb\u5883\u754c\u306b\u81ea\u52d5\u4fee\u6b63\uff08Ctrl+Z\u3067\u5143\u306b\u623b\u305b\u307e\u3059\uff09</li>"
              "</ul>",
        "en": "<h3>Pixel Edge Alignment</h3>"
              "<p>Checks if UV boundary edges align to pixel grid lines.</p>"
              "<ul>"
              "<li>Targets horizontal(H) / vertical(V) boundary edges (including seams)</li>"
              "<li>Consecutive edges are auto-grouped into a single item</li>"
              "<li><b>Min edge length(px)</b>: Edges shorter than this are excluded (default: 1.0)</li>"
              "<li>Results window allows individual selection/deselection via checkboxes</li>"
              "<li><b>Snap Selected to Pixel Grid</b>: Auto-fix checked errors to pixel boundaries (Ctrl+Z to undo)</li>"
              "</ul>",
    },
    "help_uv_padding": {
        "ja": "<h3>UV\u30d1\u30c7\u30a3\u30f3\u30b0</h3>"
              "<p>UV\u30b7\u30a7\u30eb\u9593\u304a\u3088\u3073UDIM\u30bf\u30a4\u30eb\u5883\u754c\u304b\u3089\u306e\u30d1\u30c7\u30a3\u30f3\u30b0\u8ddd\u96e2\u3092\u30c1\u30a7\u30c3\u30af\u3057\u307e\u3059\u3002</p>"
              "<ul>"
              "<li><b>\u7121\u8996\u3059\u308b\u8ddd\u96e2 (px)</b>: \u3053\u306e\u8ddd\u96e2\u672a\u6e80\u306f\u7121\u8996\uff08\u30c7\u30d5\u30a9\u30eb\u30c8: 0.05\u3001\u30ed\u30c3\u30af\u72b6\u614b\uff09\u3002\u300c\u624b\u52d5\u8abf\u6574\u300d\u3067\u89e3\u9664</li>"
              "<li><b>Shell padding \u2014 \u30a8\u30e9\u30fc\u8ddd\u96e2 (px)</b>: \u30b7\u30a7\u30eb\u9593\u3067\u3053\u306e\u8ddd\u96e2\u672a\u6e80\u3092\u30a8\u30e9\u30fc\u691c\u51fa\uff08\u30c7\u30d5\u30a9\u30eb\u30c8: 5\uff09\u203b\u6574\u6570\u306e\u307f</li>"
              "<li><b>Tile padding \u2014 \u30a8\u30e9\u30fc\u8ddd\u96e2 (px)</b>: \u30bf\u30a4\u30eb\u5883\u754c\u304b\u3089\u3053\u306e\u8ddd\u96e2\u672a\u6e80\u3092\u30a8\u30e9\u30fc\u691c\u51fa\uff08\u30c7\u30d5\u30a9\u30eb\u30c8: 2\uff09\u203b\u6574\u6570\u306e\u307f</li>"
              "<li>\u7d50\u679c\u30af\u30ea\u30c3\u30af \u2192 \u30a8\u30e9\u30fc\u7b87\u6240\u306e\u9802\u70b9\u304c\u30cf\u30a4\u30e9\u30a4\u30c8</li>"
              "<li><b>\u901a\u5e38\u30e2\u30fc\u30c9</b>\uff08\u30c7\u30d5\u30a9\u30eb\u30c8\uff09: \u9ad8\u901f\u304b\u3064\u9ad8\u7cbe\u5ea6\u3002\u307b\u3068\u3093\u3069\u306e\u5834\u5408\u306f\u3053\u3061\u3089\u3067\u5341\u5206\u3067\u3059</li>"
              "<li><b>\u9ad8\u7cbe\u5ea6\u30e2\u30fc\u30c9</b>: \u30d5\u30eb\u89e3\u50cf\u5ea6\u3067\u30c1\u30a7\u30c3\u30af\u3002\u901a\u5e38\u30e2\u30fc\u30c9\u3068\u7d50\u679c\u304c\u7570\u306a\u308b\u5834\u5408\u306b\u4f7f\u7528</li>"
              "</ul>",
        "en": "<h3>UV Padding</h3>"
              "<p>Checks padding distances between UV shells and from UDIM tile borders.</p>"
              "<ul>"
              "<li><b>Ignore under (px)</b>: Distances below this are ignored (default: 0.05, locked). Unlock with 'Manual adjust'</li>"
              "<li><b>Shell padding \u2014 Error under (px)</b>: Distances below this are flagged (default: 5) <i>Integer only</i></li>"
              "<li><b>Tile padding \u2014 Error under (px)</b>: Distances from tile border below this are flagged (default: 2) <i>Integer only</i></li>"
              "<li>Click a result to highlight error vertices</li>"
              "<li><b>Normal mode</b> (default): Fast and accurate. Sufficient for most cases</li>"
              "<li><b>High Precision mode</b>: Full-resolution check. Use when normal mode results seem off</li>"
              "</ul>",
    },
    "help_uv_range": {
        "ja": "<h3>UV\u30ec\u30f3\u30b8\u30c1\u30a7\u30c3\u30af</h3>"
              "<p>UV\u30d5\u30a7\u30fc\u30b9\u304cUDIM\u30bf\u30a4\u30eb\u5883\u754c\u3092\u307e\u305f\u3044\u3067\u3044\u306a\u3044\u304b\u3001\u6709\u52b9\u7bc4\u56f2\u5916\u306b\u306a\u3044\u304b\u3092\u30c1\u30a7\u30c3\u30af\u3057\u307e\u3059\u3002</p>"
              "<ul>"
              "<li><b>\u30bf\u30a4\u30eb\u307e\u305f\u304e\u691c\u51fa</b>: \u30d5\u30a7\u30fc\u30b9\u304c\u8907\u6570\u30bf\u30a4\u30eb\u306b\u307e\u305f\u304c\u308b\u5834\u5408\u306b\u30a8\u30e9\u30fc</li>"
              "<li><b>\u6709\u52b9\u7bc4\u56f2\u5916\u691c\u51fa</b>: \u30d5\u30a7\u30fc\u30b9\u304c\u6709\u52b9UV\u7bc4\u56f2\u5916\u306b\u5b8c\u5168\u306b\u5b58\u5728\u3059\u308b\u5834\u5408\u306b\u30a8\u30e9\u30fc</li>"
              "<li>UV U / V: min ~ max \u3092\u305d\u308c\u305e\u308c\u6307\u5b9a\uff08\u30c7\u30d5\u30a9\u30eb\u30c8: 0 ~ 1\uff09\u3002\u30de\u30a4\u30ca\u30b9\u5024\u5bfe\u5fdc</li>"
              "<li>\u4e21\u65b9\u306e\u30c1\u30a7\u30c3\u30af\u3092\u500b\u5225\u306b ON/OFF \u53ef\u80fd</li>"
              "</ul>",
        "en": "<h3>UV Range Check</h3>"
              "<p>Checks if UV faces cross UDIM tile borders or lie outside the valid UV range.</p>"
              "<ul>"
              "<li><b>Check tile crossing</b>: Error when a face spans multiple tiles</li>"
              "<li><b>Check fully outside</b>: Error when a face is entirely outside the valid UV range</li>"
              "<li>UV U / V: specify min ~ max separately (default: 0 ~ 1). Supports negative values</li>"
              "<li>Each check can be toggled ON/OFF independently</li>"
              "</ul>",
    },
    "help_uv_overlap": {
        "ja": "<h3>UV\u91cd\u8907</h3>"
              "<p>UV\u30d5\u30a7\u30fc\u30b9\u306e\u91cd\u8907\u3092\u691c\u51fa\u3057\u307e\u3059\u3002</p>"
              "<ul>"
              "<li>\u7d50\u679c\u306f\u300c\u26a0 \u8981\u78ba\u8a8d\u306e\u91cd\u8907\u300d\u3068\u300c\u2139 \u610f\u56f3\u7684\u3068\u63a8\u5b9a\u300d\u306e2\u30b0\u30eb\u30fc\u30d7\u306b\u81ea\u52d5\u5206\u985e\u3057\u3066\u8868\u793a\u3002\u30af\u30ea\u30c3\u30af\u3067\u8a72\u5f53\u30b7\u30a7\u30eb\u306e\u5168\u30d5\u30a7\u30fc\u30b9\u3092\u9078\u629e</li>"
              "<li><b>\u540c\u4e00\u30b7\u30a7\u30eb\u5185\u306e\u91cd\u8907\u3082\u542b\u3081\u308b</b>: ON\u3067\u540c\u4e00\u30b7\u30a7\u30eb\u5185\u306e\u81ea\u5df1\u91cd\u8907\u3082\u691c\u51fa\uff08\u30c7\u30d5\u30a9\u30eb\u30c8: OFF\uff09</li>"
              "</ul>",
        "en": "<h3>UV Overlap</h3>"
              "<p>Detects overlapping UV faces.</p>"
              "<ul>"
              "<li>Results are automatically classified into two groups: '\u26a0 Likely unintentional' and '\u2139 Likely intentional'. Click to select all faces of overlapping shells</li>"
              "<li><b>Include self-overlap</b>: When ON, also detects overlap within the same shell (default: OFF)</li>"
              "</ul>",
    },
    "help_texel_density": {
        "ja": "<h3>\u30c6\u30af\u30bb\u30eb\u5bc6\u5ea6</h3>"
              "<p>\u30c6\u30af\u30bb\u30eb\u5bc6\u5ea6 (px/unit) \u3092\u8a08\u6e2c\u3057\u307e\u3059\u3002\u30e2\u30fc\u30c9\u3092\u9078\u3093\u3067\u8a08\u6e2c\u3059\u308b\u3068\u3001\u7d50\u679c\u30a6\u30a3\u30f3\u30c9\u30a6\u306b\u7d71\u8a08\u3068\u30d2\u30b9\u30c8\u30b0\u30e9\u30e0\u304c\u8868\u793a\u3055\u308c\u307e\u3059\u3002</p>"
              "<ul>"
              "<li><b>\u901a\u5e38\u30e2\u30fc\u30c9\uff08\u30b7\u30a7\u30eb\u5358\u4f4d\uff09</b>: \u30b7\u30a7\u30eb\u3054\u3068\u306e\u9762\u7a4d\u52a0\u91cd\u5e73\u5747\u3067\u5bc6\u5ea6\u3092\u8a08\u6e2c\u3002\u4ed5\u69d8\u4e0a\u306e\u30c6\u30af\u30bb\u30eb\u5bc6\u5ea6\u306b\u5bfe\u3059\u308b\u9069\u5408\u30c1\u30a7\u30c3\u30af\u306b\u4f7f\u7528\uff08\u30c7\u30d5\u30a9\u30eb\u30c8\uff09</li>"
              "<li><b>\u5747\u4e00\u6027\u30e2\u30fc\u30c9\uff08\u30d5\u30a7\u30fc\u30b9\u5358\u4f4d\uff09</b>: \u30d5\u30a7\u30fc\u30b9\u3054\u3068\u306b\u5bc6\u5ea6\u3092\u8a08\u6e2c\u3002\u30b7\u30a7\u30eb\u5185\u306e\u6975\u7aef\u306a\u5bc6\u5ea6\u30e0\u30e9\u3092\u691c\u51fa\u3059\u308b\u88dc\u52a9\u30c1\u30a7\u30c3\u30af</li>"
              "</ul>"
              "<ul>"
              "<li><b>\u7d50\u679c\u306f\u30d5\u30a3\u30eb\u30bf\u8868\u793a</b>: \u30a8\u30e9\u30fc\u30ea\u30b9\u30c8\u306b\u306f\u30d5\u30a3\u30eb\u30bf\u6761\u4ef6\u306b\u8a72\u5f53\u3059\u308b\u3082\u306e\u3060\u3051\u304c\u8868\u793a\u3055\u308c\u307e\u3059\u3002\u6761\u4ef6\u3092\u5909\u3048\u308b\u3068\u30ea\u30b9\u30c8\u3082\u5373\u5ea7\u306b\u66f4\u65b0\u3055\u308c\u307e\u3059</li>"
              "<li>\u30c7\u30d5\u30a9\u30eb\u30c8\u3067\u306f\u5e73\u5747\u5bc6\u5ea6\u306e20%\u672a\u6e80\u306e\u5c0f\u3055\u3044\u30b7\u30a7\u30eb\u3092\u691c\u51fa\u3057\u307e\u3059\uff08%\u306f\u8abf\u6574\u53ef\u80fd\uff09</li>"
              "<li><b>\u57fa\u6e96\u5024 \u00b1 \u8a31\u5bb9\u5024\u3067\u8a2d\u5b9a</b>: \u76ee\u6a19\u5bc6\u5ea6\u304b\u3089\u306e\u30ba\u30ec\u3092\u30c1\u30a7\u30c3\u30af\u3057\u305f\u3044\u5834\u5408\u306b</li>"
              "<li><b>\u4e0b\u9650\u30fb\u4e0a\u9650\u3092\u500b\u5225\u6307\u5b9a</b>: \u4efb\u610f\u306e\u7bc4\u56f2\u3067\u30c1\u30a7\u30c3\u30af\u3057\u305f\u3044\u5834\u5408\u306b\u3002\u30d2\u30b9\u30c8\u30b0\u30e9\u30e0\u4e0a\u306e\u30c9\u30e9\u30c3\u30b0\u3067\u3082\u8abf\u6574\u53ef\u80fd</li>"
              "<li>\u30a8\u30e9\u30fc\u306f\u30d2\u30fc\u30c8\u30de\u30c3\u30d7\u8272\uff08\u4f4e=\u8d64\u3001\u9ad8=\u9752\uff09\u3067\u8272\u5206\u3051\u8868\u793a\u3002\u30af\u30ea\u30c3\u30af\u3067\u30d3\u30e5\u30fc\u30dd\u30fc\u30c8\u9078\u629e</li>"
              "</ul>"
              "<p>\u26a0\ufe0f <b>\u6ce8\u610f</b>: Maya\u306e\u6d6e\u52d5\u5c0f\u6570\u70b9\u306e\u7279\u6027\u4e0a\u3001\u30c6\u30af\u30bb\u30eb\u5bc6\u5ea6\u306e\u5024\u306b\u306f\u3054\u304f\u50c5\u304b\u306a\u63fa\u3089\u304e\u304c\u3042\u308a\u307e\u3059\u3002\u30d5\u30a3\u30eb\u30bf\u5883\u754c\u304e\u308a\u304e\u308a\u306e\u5024\u304c\u610f\u56f3\u305b\u305a\u691c\u51fa\u3055\u308c\u308b\u5834\u5408\u306f\u3001\u30d5\u30a3\u30eb\u30bf\u7bc4\u56f2\u3092\u5c11\u3057\u5e83\u3081\u306b\u8a2d\u5b9a\u3057\u3066\u304f\u3060\u3055\u3044\u3002</p>",
        "en": "<h3>Texel Density</h3>"
              "<p>Measures texel density (px/unit). Choose a mode and run the measurement; a results window opens with statistics and a histogram.</p>"
              "<ul>"
              "<li><b>Normal (per-shell)</b>: Measures area-weighted average density per shell. Use this to check conformance to a target texel density (default)</li>"
              "<li><b>Uniformity (per-face)</b>: Measures density per face. Use this to detect extreme density variations within shells</li>"
              "</ul>"
              "<ul>"
              "<li><b>Results are filtered</b>: The error list only shows items matching the current filter. Changing the filter updates the list instantly</li>"
              "<li>By default, shells below 20% of average density are flagged (percentage is adjustable)</li>"
              "<li><b>Target \u00b1 Tolerance</b>: Use this to check deviation from a target density</li>"
              "<li><b>Min / Max individually</b>: Use this to check a custom range. You can also drag the lines on the histogram</li>"
              "<li>Errors are color-coded (low = red, high = blue). Click to select in viewport</li>"
              "</ul>"
              "<p>\u26a0\ufe0f <b>Note</b>: Due to Maya's floating-point precision, texel density values may have very slight fluctuations. If values near the filter boundary are flagged unexpectedly, try widening the filter range slightly.</p>",
    },
    # ========== UV方向チェック（UV Orientation Check）==========
    "help_orientation": {
        "ja": "<h3>UV\u65b9\u5411\u30c1\u30a7\u30c3\u30af (Beta)</h3>"
              "<p>\u5404UV\u30b7\u30a7\u30eb\u306e\u30ef\u30fc\u30eb\u30c9\u7a7a\u9593\u4e0a\u306e\u4e0a\u4e0b\u3068UV\u7a7a\u9593\u4e0a\u306e\u4e0a\u4e0b\u306e\u5bfe\u5fdc\u3092\u691c\u8a3c\u3057\u3001\u56de\u8ee2\u305a\u308c\u3084\u53cd\u8ee2\u3092\u691c\u51fa\u3057\u307e\u3059\u3002</p>"
              "<ul>"
              "<li>\u30e1\u30c3\u30b7\u30e5\u3054\u3068\u306b\u9762\u7a4d\u6700\u5927\u306e\u4e3b\u8981\u9762\u3092\u57fa\u6e96\u306b\u4e0a\u4e0b\u65b9\u5411\u3092\u6c7a\u5b9a\u3057\u307e\u3059</li>"
              "<li>\u4e3b\u8981\u9762\u304c\u5782\u76f4\u306b\u8fd1\u3044\u5834\u5408\u306f\u9762\u7a4d\u52a0\u91cd\u6cd5\u7dda\u304b\u3089\u4e0a\u4e0b\u3092\u6c7a\u5b9a\u3001\u6c34\u5e73\u306b\u8fd1\u3044\u5834\u5408\u306f\u624b\u524d\u304cUV\u306e\u4e0b\u3001\u5965\u304cUV\u306e\u4e0a\u306b\u76f8\u5f53</li>"
              "<li><b>\u5206\u985e</b>: \u6b63\u5e38 / \u56de\u8ee2\u305a\u308c\uff08+ \u53cd\u8ee2 \u30e9\u30d9\u30eb\uff09/ \u5224\u5b9a\u4e0d\u80fd</li>"
              "<li><b>\u6b63\u5e38 (Normal)</b>: UV\u306e\u4e0a\u65b9\u5411\u304c\u30e1\u30c3\u30b7\u30e5\u306e\u4e0a\u65b9\u5411\u3068\u00b145\u00b0\u4ee5\u5185\u3067\u4e00\u81f4</li>"
              "<li><b>\u56de\u8ee2\u305a\u308c (Rotated)</b>: UV\u306e\u4e0a\u65b9\u5411\u304c\u00b145\u00b0\u3092\u8d85\u3048\u3066\u305a\u308c\u3066\u3044\u308b\uff08\u4e0a\u4e0b\u9006\u8ee2\u30fb90\u00b0\u56de\u8ee2\u7b49\uff09</li>"
              "<li><b>(\u53cd\u8ee2)</b>: UV\u304c\u53cd\u8ee2\u3057\u3066\u3044\u308b\u30b7\u30a7\u30eb\u306f\u30ea\u30b9\u30c8\u306b\u300c(\u53cd\u8ee2)\u300d\u30e9\u30d9\u30eb\u304c\u4ed8\u304d\u307e\u3059</li>"
              "<li><b>\u5224\u5b9a\u4e0d\u80fd (Indeterminate)</b>: \u9000\u5316\u30d5\u30a7\u30fc\u30b9\u306a\u3069\u3067\u5224\u5b9a\u4e0d\u80fd</li>"
              "<li>\u5404\u30a8\u30f3\u30c8\u30ea\u306b\u30e1\u30c3\u30b7\u30e5\u540d\u30fb\u30b7\u30a7\u30ebID\u3092\u8868\u793a\u3002\u30af\u30ea\u30c3\u30af\u3067\u8a72\u5f53\u30d5\u30a7\u30fc\u30b9\u3092\u9078\u629e</li>"
              "</ul>",
        "en": "<h3>UV Orientation Check (Beta)</h3>"
              "<p>Verifies the up/down correspondence between world space and UV space, detecting rotation misalignment and UV flipping for each shell.</p>"
              "<ul>"
              "<li>Determines the up direction based on the dominant face (largest area) of each mesh</li>"
              "<li>For near-vertical dominant faces, up/down is determined from the area-weighted normal. For near-horizontal faces, the front maps to UV bottom and the back to UV top</li>"
              "<li><b>Classifications</b>: Normal / Rotated (+ Flipped label) / Indeterminate</li>"
              "<li><b>Normal</b>: UV up direction is within \u00b145\u00b0 of the mesh's expected up</li>"
              "<li><b>Rotated</b>: UV up direction deviates more than \u00b145\u00b0 (upside down, 90\u00b0 rotation, etc.)</li>"
              "<li><b>(Flipped)</b>: Shells with flipped UVs are labeled with '(Flipped)' in the results list</li>"
              "<li><b>Indeterminate</b>: Cannot determine due to degenerate faces etc.</li>"
              "<li>Each entry shows mesh name and shell ID. Click to select the corresponding faces</li>"
              "</ul>",
    },
    # ========== 結果ウィンドウ ==========
    "help_results": {
        "ja": "<hr><h3>\u7d50\u679c\u30a6\u30a3\u30f3\u30c9\u30a6</h3>"
              "<ul>"
              "<li>\u9805\u76ee\u30af\u30ea\u30c3\u30af: \u8a72\u5f53\u7b87\u6240\u304c\u30d3\u30e5\u30fc\u30dd\u30fc\u30c8 / UV\u30a8\u30c7\u30a3\u30bf\u3067\u9078\u629e\u3055\u308c\u307e\u3059</li>"
              "<li><b>\u3059\u3079\u3066\u9078\u629e</b>: \u5168\u30a8\u30e9\u30fc\u3092\u4e00\u62ec\u9078\u629e</li>"
              "<li>\u30a8\u30e9\u30fc\u306a\u3057 \u2192 \u300c\u30a8\u30e9\u30fc\u306a\u3057 \u2714\u300d\u30c0\u30a4\u30a2\u30ed\u30b0\u3092\u8868\u793a</li>"
              "<li>\u30b9\u30c6\u30fc\u30bf\u30b9\u30d0\u30fc\u306b\u30c1\u30a7\u30c3\u30af\u540d\u3068\u51e6\u7406\u6642\u9593\u3092\u8868\u793a</li>"
              "<li>\u30c6\u30af\u30bb\u30eb\u5bc6\u5ea6\u306f\u5c02\u7528\u306e\u7d50\u679c\u30a6\u30a3\u30f3\u30c9\u30a6\u3067\u3001\u30d2\u30b9\u30c8\u30b0\u30e9\u30e0\u3068\u30d5\u30a3\u30eb\u30bf\u3067\u6761\u4ef6\u3092\u8abf\u6574\u3067\u304d\u307e\u3059</li>"
              "</ul>",
        "en": "<h3>Results Window</h3>"
              "<ul>"
              "<li>Click an item: the component is selected in viewport / UV editor</li>"
              "<li><b>Select All</b>: Select all errors at once</li>"
              "<li>No errors found: a 'No errors' dialog is shown</li>"
              "<li>Status bar shows check name and elapsed time</li>"
              "<li>Texel Density uses a dedicated results window with histogram and filter panel</li>"
              "</ul>",
    },
    # ========== レポート送信 ==========
    "help_report": {
        "ja": "<hr><h3>\u30ec\u30dd\u30fc\u30c8\u3092\u9001\u4fe1</h3>"
              "<p>\u5b9f\u884c\u6e08\u307f\u30c1\u30a7\u30c3\u30af\u306e\u7d50\u679c\u3068\u74b0\u5883\u60c5\u5831\u3092\u30d5\u30a3\u30fc\u30c9\u30d0\u30c3\u30af\u30d5\u30a9\u30fc\u30e0\u306b\u9001\u4fe1\u3057\u307e\u3059\u3002</p>"
              "<ul>"
              "<li>\u30d6\u30e9\u30a6\u30b6\u3067\u30d5\u30a9\u30fc\u30e0\u304c\u958b\u304d\u3001\u30ec\u30dd\u30fc\u30c8\u304c\u81ea\u52d5\u5165\u529b\u3055\u308c\u307e\u3059</li>"
              "<li>\u30ec\u30dd\u30fc\u30c8\u304c\u9577\u3059\u304e\u308b\u5834\u5408\u306f\u30af\u30ea\u30c3\u30d7\u30dc\u30fc\u30c9\u306b\u30b3\u30d4\u30fc\u3055\u308c\u308b\u306e\u3067\u3001\u30d5\u30a9\u30fc\u30e0\u306e\u30ec\u30dd\u30fc\u30c8\u6b04\u306b\u8cbc\u308a\u4ed8\u3051\u3066\u304f\u3060\u3055\u3044</li>"
              "</ul>",
        "en": "<hr><h3>Send Report</h3>"
              "<p>Sends check results and environment info to the feedback form.</p>"
              "<ul>"
              "<li>The form opens in your browser with the report pre-filled</li>"
              "<li>If the report is too long, it is copied to clipboard \u2014 paste it into the report field on the form</li>"
              "</ul>",
    },
})
# --- [020] utils ---
# depends on: [000] header
# === Utility ===

def get_maya_main_window():
    ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(long(ptr), QtWidgets.QWidget)

def get_mesh_fn(dag_path):
    return om2.MFnMesh(dag_path)

def get_selected_meshes():
    sel = om2.MGlobal.getActiveSelectionList()
    dag_paths = []
    visited = set()
    for i in range(sel.length()):
        try:
            dag = sel.getDagPath(i)
            if dag.apiType() == om2.MFn.kMesh:  # Shape node only (not transform)
                xform = om2.MDagPath(dag); xform.pop()
                fp = xform.fullPathName()
                if fp not in visited:
                    visited.add(fp); dag_paths.append(xform)
                continue
            try:
                dag_copy = om2.MDagPath(dag)
                dag_copy.extendToShape()
                if dag_copy.hasFn(om2.MFn.kMesh):
                    fp = dag.fullPathName()
                    if fp not in visited:
                        visited.add(fp); dag_paths.append(dag)
                    continue
            except Exception:
                pass
            node_name = dag.fullPathName()
            children = cmds.listRelatives(node_name, allDescendents=True, fullPath=True, type="mesh") or []
            for child in children:
                xforms = cmds.listRelatives(child, parent=True, fullPath=True) or [child]
                xform_path = xforms[0]
                if xform_path in visited: continue
                visited.add(xform_path)
                sl = om2.MSelectionList(); sl.add(xform_path)
                dag_paths.append(sl.getDagPath(0))
        except Exception:
            pass
    return dag_paths

# === Texture Resolution Detection ===
def _get_texture_resolution():
    """Detect texture resolution from selected meshes.
    Returns:
        (rx, ry)               -- single resolution
        ("mixed", dict)        -- multiple resolutions: {(rx,ry): [tex_name, ...]}
        None                   -- nothing detected
    """
    sel = cmds.ls(sl=True, long=True)
    if not sel: return None
    res_to_textures = {}  # {(rx, ry): [texture_basename, ...]}
    for node in sel:
        shapes = cmds.listRelatives(node, shapes=True, fullPath=True, type="mesh") or []
        if not shapes:
            if cmds.nodeType(node) == "mesh": shapes = [node]
            else: shapes = cmds.listRelatives(node, allDescendents=True, fullPath=True, type="mesh") or []
        for shape in shapes:
            sgs = cmds.listConnections(shape, type="shadingEngine") or []
            for sg in set(sgs):
                mats = cmds.ls(cmds.listConnections(sg) or [], materials=True)
                for mat in mats:
                    file_nodes = cmds.ls(cmds.listHistory(mat, future=False) or [], type="file")
                    for fn in file_nodes:
                        try:
                            ox = cmds.getAttr(fn + ".outSizeX")
                            oy = cmds.getAttr(fn + ".outSizeY")
                            if ox and oy and ox > 0 and oy > 0:
                                key = (int(ox), int(oy))
                                tex_path = cmds.getAttr(fn + ".fileTextureName") or fn
                                tex_name = tex_path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
                                if key not in res_to_textures:
                                    res_to_textures[key] = []
                                if tex_name not in res_to_textures[key]:
                                    res_to_textures[key].append(tex_name)
                        except Exception:
                            pass
    if len(res_to_textures) == 1: return list(res_to_textures.keys())[0]
    elif len(res_to_textures) > 1: return ("mixed", res_to_textures)
    return None

# === Unified floating-point epsilon ===
_GRID_SNAP_EPS = 1e-2

def _snap_to_grid(val):
    rounded = round(val)
    if abs(val - rounded) < _GRID_SNAP_EPS: return float(rounded)
    return val

def _snap_floor(val):
    rounded = round(val)
    if abs(val - rounded) < _GRID_SNAP_EPS: return int(rounded)
    return int(math.floor(val))

def _local_vert_index(mesh_fn, face_id, vert_id):
    verts = mesh_fn.getPolygonVertices(face_id)
    for i, v in enumerate(verts):
        if v == vert_id: return i
    raise ValueError("Vertex {0} not in face {1}".format(vert_id, face_id))

# =====================================================================
# v24 (pre-1.0): Geometry area helpers for Texel Density
# =====================================================================

def _triangle_area_2d(ax, ay, bx, by, cx, cy):
    return abs((bx - ax) * (cy - ay) - (cx - ax) * (by - ay)) * 0.5

def _triangle_area_3d(ax, ay, az, bx, by, bz, cx, cy, cz):
    ex1 = bx - ax; ey1 = by - ay; ez1 = bz - az
    ex2 = cx - ax; ey2 = cy - ay; ez2 = cz - az
    nx = ey1 * ez2 - ez1 * ey2
    ny = ez1 * ex2 - ex1 * ez2
    nz = ex1 * ey2 - ey1 * ex2
    return math.sqrt(nx * nx + ny * ny + nz * nz) * 0.5

# === Pixel Grid Rasterization ===
def _rasterize_segment(x0, y0, x1, y1):
    x0, y0 = _snap_to_grid(x0), _snap_to_grid(y0)
    x1, y1 = _snap_to_grid(x1), _snap_to_grid(y1)
    dx, dy = x1 - x0, y1 - y0
    if abs(dx) < 1e-12 and abs(dy) < 1e-12:
        return {(_snap_floor(x0), _snap_floor(y0))}
    if abs(dy) < 1e-12:
        iy = _snap_floor(y0)
        sx, ex = _snap_floor(x0), _snap_floor(x1)
        if sx > ex: sx, ex = ex, sx
        return {(x, iy) for x in range(sx, ex + 1)}
    if abs(dx) < 1e-12:
        ix = _snap_floor(x0)
        sy, ey = _snap_floor(y0), _snap_floor(y1)
        if sy > ey: sy, ey = ey, sy
        return {(ix, y) for y in range(sy, ey + 1)}
    pixels = set()
    ix, iy = _snap_floor(x0), _snap_floor(y0); pixels.add((ix, iy))
    sx = (1 if dx > 0 else -1) if abs(dx) > 1e-12 else 0
    sy = (1 if dy > 0 else -1) if abs(dy) > 1e-12 else 0
    cell_x = int(math.floor(x0)) if abs(x0 - round(x0)) >= _GRID_SNAP_EPS else int(round(x0))
    cell_y = int(math.floor(y0)) if abs(y0 - round(y0)) >= _GRID_SNAP_EPS else int(round(y0))
    t_max_x = ((cell_x + (1 if sx > 0 else 0)) - x0) / dx if abs(dx) > 1e-12 else float('inf')
    t_delta_x = abs(1.0 / dx) if abs(dx) > 1e-12 else float('inf')
    t_max_y = ((cell_y + (1 if sy > 0 else 0)) - y0) / dy if abs(dy) > 1e-12 else float('inf')
    t_delta_y = abs(1.0 / dy) if abs(dy) > 1e-12 else float('inf')
    t_limit = 1.0 - _GRID_SNAP_EPS
    while True:
        if t_max_x < t_max_y:
            if t_max_x > t_limit: break
            ix += sx; t_max_x += t_delta_x
        elif t_max_y < t_max_x:
            if t_max_y > t_limit: break
            iy += sy; t_max_y += t_delta_y
        else:
            if t_max_x > t_limit: break
            ix += sx; iy += sy; t_max_x += t_delta_x; t_max_y += t_delta_y
        pixels.add((ix, iy))
    pixels.add((_snap_floor(x1), _snap_floor(y1)))
    return pixels

def _rasterize_shell_edges(edges):
    pixels = set(); pixel_to_uvs = defaultdict(set); uv_pixel_coords = {}
    _rast = _rasterize_segment
    _sf = _snap_floor; _sg = _snap_to_grid
    for x0, y0, x1, y1, uv0, uv1 in edges:
        seg_px = _rast(x0, y0, x1, y1)
        pixels.update(seg_px)
        for p in seg_px:
            pixel_to_uvs[p].add(uv0); pixel_to_uvs[p].add(uv1)
        uv_pixel_coords[uv0] = (_sf(_sg(x0)), _sf(_sg(y0)))
        uv_pixel_coords[uv1] = (_sf(_sg(x1)), _sf(_sg(y1)))
    return pixels, pixel_to_uvs, uv_pixel_coords

def _filter_uvs_by_proximity(uv_ids, uv_coords, target_pixels, radius):
    result = set()
    for uv_id in uv_ids:
        uv_px = uv_coords.get(uv_id)
        if uv_px is None: result.add(uv_id); continue
        for tp in target_pixels:
            if max(abs(uv_px[0] - tp[0]), abs(uv_px[1] - tp[1])) <= radius:
                result.add(uv_id); break
    return result

_CHEB_DIRS = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]

# === v35 (pre-1.0) S級: SciPy Chebyshev distance map wrapper ===
class _NpDistMap(object):
    """Dict-compatible wrapper around a 2D numpy Chebyshev distance array."""
    # __slots__: suppress per-instance __dict__ to reduce memory overhead;
    # thousands of instances may be created during BFS distance map builds.
    __slots__ = ('_arr', '_ox', '_oy', '_h', '_w')
    def __init__(self, arr, ox, oy):
        self._arr = arr; self._ox = ox; self._oy = oy
        self._h = arr.shape[0]; self._w = arr.shape[1]
    def get(self, key, default=None):
        i = key[0] - self._ox; j = key[1] - self._oy
        if 0 <= i < self._w and 0 <= j < self._h:
            return int(self._arr[j, i])
        return default
    def __contains__(self, key):
        i = key[0] - self._ox; j = key[1] - self._oy
        return 0 <= i < self._w and 0 <= j < self._h
    def __getitem__(self, key):
        i = key[0] - self._ox; j = key[1] - self._oy
        if 0 <= i < self._w and 0 <= j < self._h:
            return int(self._arr[j, i])
        raise KeyError(key)

def _build_distance_map_scipy(pixels, max_dist):
    """SciPy accelerated Chebyshev distance map (10-100x faster than BFS)."""
    xs = [p[0] for p in pixels]; ys = [p[1] for p in pixels]
    x_min = min(xs); x_max = max(xs)
    y_min = min(ys); y_max = max(ys)
    ox = x_min - max_dist; oy = y_min - max_dist
    w = (x_max - x_min) + 2 * max_dist + 1
    h = (y_max - y_min) + 2 * max_dist + 1
    # 0=shell pixels (background), 1=other (foreground)
    # distance_transform_cdt: foreground -> nearest background distance
    mask = np.ones((h, w), dtype=np.uint8)
    for px, py in pixels:
        mask[py - oy, px - ox] = 0
    dt = distance_transform_cdt(mask, metric='chessboard')
    return _NpDistMap(dt, ox, oy)

def _build_distance_map(pixels, max_dist):
    # S級: scipy available -> fast path
    if _HAS_SCIPY and pixels:
        return _build_distance_map_scipy(pixels, max_dist)
    # Fallback: pure-Python BFS (Maya 2018)
    dist_map = {p: 0 for p in pixels}
    queue = deque(pixels)
    while queue:
        cx, cy = queue.popleft()
        d = dist_map[(cx, cy)]
        if d >= max_dist - 1: continue
        nd = d + 1
        for dx, dy in _CHEB_DIRS:
            nb = (cx + dx, cy + dy)
            if nb not in dist_map:
                dist_map[nb] = nd; queue.append(nb)
    return dist_map

# === v53 (pre-1.0): Heatmap color utility (shared by [800] ui) ===
def _td_heatmap_color(t):
    """Return (r, g, b) heatmap color for normalized value t (0.0-1.0).
    Gradient: red (low) -> yellow (mid) -> blue (high)."""
    t = max(0.0, min(1.0, t))
    if t < 0.5:
        s = t * 2.0
        return (int(200 + (220 - 200) * s),
                int(50 + (200 - 50) * s),
                int(50 + (50 - 50) * s))
    else:
        s = (t - 0.5) * 2.0
        return (int(220 + (50 - 220) * s),
                int(200 + (100 - 200) * s),
                int(50 + (200 - 50) * s))

def _get_selected_mesh_transforms():
    """Collect mesh transforms from current selection, recursing into groups."""
    sel = cmds.ls(sl=True, long=True, type="transform") or []
    meshes = []; visited = set()
    def _collect(node):
        if node in visited: return
        visited.add(node)
        shapes = cmds.listRelatives(node, shapes=True, type="mesh", fullPath=True) or []
        if shapes: meshes.append(node)
        else:
            children = cmds.listRelatives(node, children=True, fullPath=True, type="transform") or []
            for child in children: _collect(child)
    for s in sel: _collect(s)
    return meshes

def _pair_distance_from_map(dist_map_a, pixels_a, pixels_b, ptu_a, ptu_b, max_dist, uv_coords_a=None, uv_coords_b=None):
    if not pixels_a or not pixels_b: return max_dist, [], []
    overlap = pixels_a & pixels_b
    if overlap:
        ua, ub = set(), set()
        for p in overlap: ua.update(ptu_a.get(p, ())); ub.update(ptu_b.get(p, ()))
        if uv_coords_a:
            f = _filter_uvs_by_proximity(ua, uv_coords_a, overlap, 1)
            if f: ua = f
        if uv_coords_b:
            f = _filter_uvs_by_proximity(ub, uv_coords_b, overlap, 1)
            if f: ub = f
        return 0, list(ua), list(ub)
    min_dist = max_dist; hit_pixels = set()
    for p in pixels_b:
        d = dist_map_a.get(p, max_dist)
        if d < min_dist: min_dist = d; hit_pixels = {p}
        elif d == min_dist and d < max_dist: hit_pixels.add(p)
    if min_dist >= max_dist: return max_dist, [], []
    uvs_a, uvs_b = set(), set(); closest_a = set()
    for pb in hit_pixels:
        uvs_b.update(ptu_b.get(pb, ()))
        for sx in range(-min_dist, min_dist + 1):
            for sy in range(-min_dist, min_dist + 1):
                ca_ = (pb[0] + sx, pb[1] + sy)
                if ca_ in pixels_a: closest_a.add(ca_); uvs_a.update(ptu_a.get(ca_, ()))
    if uv_coords_a:
        f = _filter_uvs_by_proximity(uvs_a, uv_coords_a, closest_a, 1)
        if f: uvs_a = f
    if uv_coords_b:
        f = _filter_uvs_by_proximity(uvs_b, uv_coords_b, hit_pixels, 1)
        if f: uvs_b = f
    return min_dist, list(uvs_a), list(uvs_b)

# === v59 (pre-1.0): Report Log ===
class ReportLog(object):
    """Accumulates check results for plain-text report output."""
    def __init__(self):
        self._entries = []
        self._errors = []
        self._env = self._collect_env()

    def _collect_env(self):
        import sys, platform
        maya_ver = cmds.about(version=True) if _IN_MAYA else "N/A"
        os_info = platform.platform()
        py_ver = "{0}.{1}.{2}".format(*sys.version_info[:3])
        return {"tool": _VERSION, "maya": maya_ver,
                "os": os_info, "python": py_ver}

    def clear(self):
        self._entries = []
        self._errors = []
        self._env = self._collect_env()

    def add_entry(self, name, params, target_info, elapsed,
                  result_ok, error_count, profiles=None):
        self._entries.append({
            "name": name, "params": params,
            "target": target_info, "time": elapsed,
            "ok": result_ok, "errors": error_count,
            "profiles": profiles or []})

    def add_error(self, check_name, traceback_text):
        self._errors.append({
            "name": check_name, "traceback": traceback_text})

    def generate(self):
        import datetime
        lines = []
        lines.append("=" * 42)
        lines.append("UV QC Tools - Report Log")
        lines.append("=" * 42)
        e = self._env
        lines.append("Tool Version : {0}".format(e["tool"]))
        lines.append("Maya Version : {0}".format(e["maya"]))
        lines.append("OS           : {0}".format(e["os"]))
        lines.append("Python       : {0}".format(e["python"]))
        lines.append("Date         : {0}".format(
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))
        if not self._entries:
            lines.append("")
            lines.append("(No checks executed)")
        else:
            lines.append("")
            lines.append("-" * 42)
            lines.append("Executed Checks")
            lines.append("-" * 42)
            for ent in self._entries:
                lines.append("[{0}]".format(ent["name"]))
                lines.append("  Parameters : {0}".format(ent["params"]))
                lines.append("  Target     : {0}".format(ent["target"]))
                lines.append("  Time       : {0}s".format(ent["time"]))
                if ent.get("profiles"):
                    lines.append("  Profile:")
                    for prof in ent["profiles"]:
                        label = prof.get("label", "")
                        total = prof.get("total", 0)
                        if label:
                            lines.append("    --- {0}: {1}s ---".format(label, total))
                        summary = prof.get("summary", "")
                        if summary:
                            pfx = "      " if label else "    "
                            lines.append("{0}{1}".format(pfx, summary))
                        phases = prof.get("phases", [])
                        if phases:
                            pfx = "      " if label else "    "
                            parts = ["{0}: {1}s".format(p["name"], p["time"]) for p in phases]
                            lines.append("{0}{1}".format(pfx, " | ".join(parts)))
                if ent["ok"]:
                    tag = "OK"
                else:
                    tag = "NG - {0} errors".format(ent["errors"])
                lines.append("  Result     : {0}".format(tag))
                lines.append("")
        if self._errors:
            lines.append("-" * 42)
            lines.append("Errors / Warnings")
            lines.append("-" * 42)
            for err in self._errors:
                lines.append("[{0}] Exception:".format(err["name"]))
                for tb_line in err["traceback"].splitlines():
                    lines.append("  {0}".format(tb_line))
                lines.append("")
        lines.append("=" * 42)
        return "\n".join(lines)

    def has_entries(self):
        return len(self._entries) > 0 or len(self._errors) > 0

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
    tool_name = "UV QC Tools {0}".format(__VERSION__)
    maya_ver = cmds.about(version=True) if _IN_MAYA else "unknown"
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
# --- [100] pixel_edge ---
# depends on: [000] header, [010] i18n, [020] utils (_GRID_SNAP_EPS, _snap_to_grid, _local_vert_index, get_selected_meshes, get_mesh_fn)
# === Pixel Edge Alignment ===

def collect_pixel_edge_data():
    """Collect UV boundary edge data from selected meshes.

    Returns list of edge records (mesh, edge_id, face_id, face_count,
    uv0, uv1, u0, v0, u1, v1) or None if no mesh selected.
    """
    dag_paths = get_selected_meshes()
    if not dag_paths: return None
    records = []
    for dag in dag_paths:
        mesh_fn = get_mesh_fn(dag)
        mesh_name = dag.fullPathName()
        us, vs = mesh_fn.getUVs()
        edge_iter = om2.MItMeshEdge(dag)
        while not edge_iter.isDone():
            edge_id = edge_iter.index()
            connected_faces = edge_iter.getConnectedFaces()
            if not connected_faces:
                edge_iter.next(); continue
            vert_ids = [edge_iter.vertexId(0), edge_iter.vertexId(1)]
            is_boundary = len(connected_faces) < 2
            if not is_boundary:
                try:
                    fa, fb = connected_faces[0], connected_faces[1]
                    uv0_a = mesh_fn.getPolygonUVid(fa, _local_vert_index(mesh_fn, fa, vert_ids[0]))
                    uv0_b = mesh_fn.getPolygonUVid(fb, _local_vert_index(mesh_fn, fb, vert_ids[0]))
                    uv1_a = mesh_fn.getPolygonUVid(fa, _local_vert_index(mesh_fn, fa, vert_ids[1]))
                    uv1_b = mesh_fn.getPolygonUVid(fb, _local_vert_index(mesh_fn, fb, vert_ids[1]))
                    is_boundary = (uv0_a != uv0_b) or (uv1_a != uv1_b)
                except Exception:
                    is_boundary = True
            if not is_boundary:
                edge_iter.next(); continue
            for face_id in connected_faces:
                try:
                    uv0 = mesh_fn.getPolygonUVid(face_id, _local_vert_index(mesh_fn, face_id, vert_ids[0]))
                    uv1 = mesh_fn.getPolygonUVid(face_id, _local_vert_index(mesh_fn, face_id, vert_ids[1]))
                    records.append((mesh_name, edge_id, face_id, len(connected_faces),
                                    uv0, uv1, float(us[uv0]), float(vs[uv0]),
                                    float(us[uv1]), float(vs[uv1])))
                except Exception:
                    continue
            edge_iter.next()
    return records

def compute_pixel_edges(records, res_x, res_y, min_edge_length, progress_cb=None, cancel_check=None):
    """Check boundary edges for pixel-grid alignment at given resolution.

    Returns (errors, summary_string). Each error is a misaligned
    horizontal or vertical edge with its distance from the grid.
    """
    if not records:
        return [], tr("edge_result", count=0)
    _t0_total = time.time()
    errors = []
    _sg = _snap_to_grid
    _eps = _GRID_SNAP_EPS
    total = len(records)
    report_interval = max(1, total // 50)
    for idx, r in enumerate(records):
        if cancel_check and cancel_check():
            return errors, tr("cancelled")
        if progress_cb and idx % report_interval == 0:
            progress_cb(idx, total, tr("progress_pixel_scan", current=idx, total=total))
        mesh_name, edge_id, face_id, fcount, uv0_id, uv1_id, u0, v0, u1, v1 = r
        px0 = _sg(u0 * res_x); py0 = _sg(v0 * res_y)
        px1 = _sg(u1 * res_x); py1 = _sg(v1 * res_y)
        elen = math.sqrt((px1 - px0)**2 + (py1 - py0)**2)
        if elen < min_edge_length:
            continue
        is_h = abs(py1 - py0) < _eps
        is_v = abs(px1 - px0) < _eps
        if is_h:
            h_dist = max(abs(py0 - round(py0)), abs(py1 - round(py1)))
            if h_dist > _eps:
                comp = "{0}.e[{1}] (f{2})".format(mesh_name, edge_id, face_id) if fcount > 1 else "{0}.e[{1}]".format(mesh_name, edge_id)
                errors.append({"component": comp, "distance": round(h_dist, 4),
                    "type": "pixel_edge", "mesh": mesh_name, "edge_id": edge_id,
                    "uv_ids": [uv0_id, uv1_id],
                    "uv_data": [(uv0_id, u0, v0), (uv1_id, u1, v1)],
                    "direction": "horizontal"})
        elif is_v:
            v_dist = max(abs(px0 - round(px0)), abs(px1 - round(px1)))
            if v_dist > _eps:
                comp = "{0}.e[{1}] (f{2})".format(mesh_name, edge_id, face_id) if fcount > 1 else "{0}.e[{1}]".format(mesh_name, edge_id)
                errors.append({"component": comp, "distance": round(v_dist, 4),
                    "type": "pixel_edge", "mesh": mesh_name, "edge_id": edge_id,
                    "uv_ids": [uv0_id, uv1_id],
                    "uv_data": [(uv0_id, u0, v0), (uv1_id, u1, v1)],
                    "direction": "vertical"})
    if progress_cb:
        progress_cb(total, total, tr("progress_pixel_group"))
    # --- Grouping (on worker thread to avoid UI freeze) ---
    groups = _group_edge_errors(errors, res_x, res_y) if errors else []
    # --- Profile ---
    _elapsed = time.time() - _t0_total
    _profile = {
        "summary": "records={0} | errors={1}".format(total, len(errors)),
        "phases": [{"name": "Scan", "time": round(_elapsed, 2)}],
        "total": round(_elapsed, 2)
    }
    return errors, tr("edge_result", count=len(errors)), _profile, groups

def snap_selected_edges(selected_items, res_x, res_y):
    """Snap selected UV boundary edges to the nearest pixel grid.

    Returns the number of UV points adjusted.
    """
    cmds.undoInfo(openChunk=True, chunkName="UV Pixel Snap Selected")
    try:
        adjustments = {}
        for item in selected_items:
            mesh_name = item["mesh"]; direction = item["direction"]
            endpoint_uv_ids = item.get("endpoint_uv_ids", set())
            for uv_id, orig_u, orig_v in item["uv_data"]:
                key = (mesh_name, uv_id)
                if key not in adjustments:
                    adjustments[key] = {"ou": orig_u, "ov": orig_v, "nu": orig_u, "nv": orig_v}
                if uv_id in endpoint_uv_ids:
                    adjustments[key]["nu"] = math.floor(orig_u * res_x) / res_x
                    adjustments[key]["nv"] = math.ceil(orig_v * res_y) / res_y
                elif direction == "horizontal":
                    adjustments[key]["nv"] = math.ceil(orig_v * res_y) / res_y
                elif direction == "vertical":
                    adjustments[key]["nu"] = math.floor(orig_u * res_x) / res_x
        count = 0
        for (mesh_name, uv_id), adj in adjustments.items():
            du = adj["nu"] - adj["ou"]; dv = adj["nv"] - adj["ov"]
            if abs(du) > 1e-10 or abs(dv) > 1e-10:
                cmds.polyEditUV("{0}.map[{1}]".format(mesh_name, uv_id), u=du, v=dv); count += 1
        return count
    finally:
        cmds.undoInfo(closeChunk=True)

# === Edge Grouping ===
def _group_edge_errors(errors, res_x, res_y):
    if not errors: return []
    line_bins = defaultdict(list)
    _sg = _snap_to_grid
    for i, err in enumerate(errors):
        mesh = err["mesh"]; direction = err["direction"]
        if direction == "horizontal":
            py_avg = _sg(sum(v * res_y for _, _, v in err["uv_data"]) / len(err["uv_data"]))
            line_key = (mesh, direction, round(py_avg))
        else:
            px_avg = _sg(sum(u * res_x for _, u, _ in err["uv_data"]) / len(err["uv_data"]))
            line_key = (mesh, direction, round(px_avg))
        line_bins[line_key].append(i)
    groups = []
    for line_key, indices in line_bins.items():
        uv_to_edges = defaultdict(set)
        for idx in indices:
            for uv_id, _, _ in errors[idx]["uv_data"]:
                uv_to_edges[uv_id].add(idx)
        parent = {idx: idx for idx in indices}
        def find(x):
            while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
            return x
        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb: parent[ra] = rb
        for uv_id, edge_set in uv_to_edges.items():
            edge_list = list(edge_set)
            for j in range(1, len(edge_list)): union(edge_list[0], edge_list[j])
        components = defaultdict(list)
        for idx in indices: components[find(idx)].append(idx)
        for comp_indices in components.values():
            all_uv_ids = []; all_uv_data = []; all_edge_ids = []; seen_uv = set(); max_dist = 0.0
            mesh = errors[comp_indices[0]]["mesh"]; direction = errors[comp_indices[0]]["direction"]
            for idx in comp_indices:
                err = errors[idx]; all_edge_ids.append(err["edge_id"])
                max_dist = max(max_dist, err["distance"])
                for uv_id, u, v in err["uv_data"]:
                    if uv_id not in seen_uv:
                        seen_uv.add(uv_id); all_uv_ids.append(uv_id); all_uv_data.append((uv_id, u, v))
            all_edge_ids.sort()
            uv_edge_count = defaultdict(int)
            for idx in comp_indices:
                for uv_id, _, _ in errors[idx]["uv_data"]:
                    uv_edge_count[uv_id] += 1
            endpoint_uv_ids = set(uid for uid, cnt in uv_edge_count.items() if cnt == 1)
            groups.append({"indices": comp_indices, "edge_ids": all_edge_ids, "direction": direction,
                "mesh": mesh, "uv_ids": all_uv_ids, "uv_data": all_uv_data,
                "max_distance": round(max_dist, 4), "edge_count": len(comp_indices),
                "endpoint_uv_ids": endpoint_uv_ids})
    groups.sort(key=lambda g: (g["mesh"], g["edge_ids"][0] if g["edge_ids"] else 0))
    return groups
# --- [110] uv_padding ---
# depends on: [000] header, [010] i18n, [020] utils (_rasterize_shell_edges, _build_distance_map, _pair_distance_from_map, _filter_uvs_by_proximity, get_selected_meshes, get_mesh_fn)
# === Shell Distance & UV Padding ===
# --- v38 (pre-1.0): Fast Mode calculation ---
def calc_fast_params(res_x, res_y, shell_padding, tile_padding):
    """Compute reduced resolution and padding for fast mode.
    Returns (new_res_x, new_res_y, new_shell, new_tile, is_approx).
    Uses GCD of all non-zero values. Falls back to ceil() halving if GCD=1.
    Ensures resolution >= _MIN_RESOLUTION.
    """
    values = [v for v in [res_x, res_y, shell_padding, tile_padding] if v > 0]
    if not values:
        return res_x, res_y, shell_padding, tile_padding, False
    divisor = values[0]
    for v in values[1:]:
        divisor = _gcd(divisor, v)
    # Shrink divisor until both resolutions stay above minimum
    while divisor > 1 and (res_x // divisor < _MIN_RESOLUTION or res_y // divisor < _MIN_RESOLUTION):
        # Divide by smallest prime factor
        for p in range(2, divisor + 1):
            if divisor % p == 0:
                divisor //= p
                break
    if divisor > 1:
        return res_x // divisor, res_y // divisor, shell_padding // divisor, tile_padding // divisor, False
    else:
        # Fallback: halve resolution, ceil padding
        _ceil = math.ceil
        new_shell = int(_ceil(shell_padding / 2.0)) if shell_padding > 0 else 0
        new_tile = int(_ceil(tile_padding / 2.0)) if tile_padding > 0 else 0
        return res_x // 2, res_y // 2, new_shell, new_tile, True

def collect_shell_data(res_x, res_y):
    """Collect UV shell edge segments from selected meshes.

    Returns dict keyed by (mesh_name, shell_id) with lists of
    pixel-space edge segments, or None if no mesh selected.
    """
    dag_paths = get_selected_meshes()
    if not dag_paths: return None
    all_shell_edges = {}
    for dag in dag_paths:
        mesh_fn = get_mesh_fn(dag); mesh_name = dag.fullPathName()
        num_uvs = mesh_fn.numUVs()
        if num_uvs == 0: continue
        us, vs = mesh_fn.getUVs()
        uv_counts, uv_ids = mesh_fn.getAssignedUVs()
        shell_map = mesh_fn.getUvShellsIds()[1]
        uv_offset = 0
        for face_idx in range(mesh_fn.numPolygons):
            count = uv_counts[face_idx]
            for k in range(count):
                idx_a = uv_ids[uv_offset + k]
                idx_b = uv_ids[uv_offset + (k + 1) % count]
                if shell_map[idx_a] != shell_map[idx_b]: continue
                key = (mesh_name, shell_map[idx_a])
                all_shell_edges.setdefault(key, []).append(
                    (float(us[idx_a]) * res_x, float(vs[idx_a]) * res_y,
                     float(us[idx_b]) * res_x, float(vs[idx_b]) * res_y,
                     idx_a, idx_b))
            uv_offset += count
    return all_shell_edges

def compute_shell_distance(all_shell_edges, ignore_under, error_under, progress_cb=None, cancel_check=None):
    """Compute minimum Chebyshev distances between all shell pairs.

    Returns (errors, summary_string). Errors are shell pairs closer
    than error_under pixels but not below ignore_under.
    """
    if not all_shell_edges: return [], tr("shell_result", count=0)
    all_pixels = {}; all_ptu = {}; all_uv_coords = {}; all_bboxes = {}
    shell_keys_list = list(all_shell_edges.keys()); total_shells = len(shell_keys_list)
    for si, key in enumerate(shell_keys_list):
        if cancel_check and cancel_check(): return [], tr("cancelled")
        if progress_cb: progress_cb(si, total_shells * 3, tr("progress_shell_raster", current=si + 1, total=total_shells))
        edges = all_shell_edges[key]
        px_set, ptu, uvc = _rasterize_shell_edges(edges)
        all_pixels[key] = px_set; all_ptu[key] = ptu; all_uv_coords[key] = uvc
        if px_set:
            xs = [p[0] for p in px_set]; ys = [p[1] for p in px_set]
            all_bboxes[key] = (min(xs), min(ys), max(xs), max(ys))
    int_err = int(math.ceil(error_under)); _floor = math.floor
    cell_size = max(int_err * 2, 1); grid = defaultdict(set)
    for key in shell_keys_list:
        if key not in all_bboxes: continue
        bx0, by0, bx1, by1 = all_bboxes[key]
        cx0 = int(_floor(bx0 / cell_size)); cy0 = int(_floor(by0 / cell_size))
        cx1 = int(_floor(bx1 / cell_size)); cy1 = int(_floor(by1 / cell_size))
        for cx in range(cx0, cx1 + 1):
            for cy in range(cy0, cy1 + 1): grid[(cx, cy)].add(key)
    candidate_pairs = set()
    for cell_keys in grid.values():
        cell_list = list(cell_keys)
        for ii in range(len(cell_list)):
            for jj in range(ii + 1, len(cell_list)):
                ka, kb = cell_list[ii], cell_list[jj]
                candidate_pairs.add((ka, kb) if ka < kb else (kb, ka))
    needed_shells = set()
    for ka, kb in candidate_pairs: needed_shells.add(ka); needed_shells.add(kb)
    dist_maps = {}; needed_list = [k for k in shell_keys_list if k in needed_shells]
    for si, key in enumerate(needed_list):
        if cancel_check and cancel_check(): return [], tr("cancelled")
        if progress_cb: progress_cb(total_shells + si, total_shells + len(needed_list) + len(candidate_pairs), tr("progress_shell_bfs", current=si + 1, total=len(needed_list)))
        if key in all_bboxes and all_pixels[key]: dist_maps[key] = _build_distance_map(all_pixels[key], int_err)
    errors = []; pair_count = 0; total_pairs = len(candidate_pairs); report_interval = max(1, total_pairs // 50)
    for key_i, key_j in candidate_pairs:
        pair_count += 1
        if cancel_check and cancel_check(): return errors, tr("cancelled")
        if progress_cb and pair_count % report_interval == 0:
            progress_cb(total_shells + len(needed_list) + pair_count, total_shells + len(needed_list) + total_pairs, tr("progress_shell_pair", current=pair_count, total=total_pairs))
        if key_i not in all_bboxes or key_j not in all_bboxes: continue
        bb_i, bb_j = all_bboxes[key_i], all_bboxes[key_j]
        bb_dx = max(0, max(bb_i[0] - bb_j[2], bb_j[0] - bb_i[2]))
        bb_dy = max(0, max(bb_i[1] - bb_j[3], bb_j[1] - bb_i[3]))
        if max(bb_dx, bb_dy) >= int_err: continue
        px_i = all_pixels[key_i]; px_j = all_pixels[key_j]
        if len(px_j) <= len(px_i):
            dm = dist_maps.get(key_i)
            if dm is None: continue
            dist, close_i, close_j = _pair_distance_from_map(dm, px_i, px_j, all_ptu[key_i], all_ptu[key_j], int_err, all_uv_coords.get(key_i), all_uv_coords.get(key_j))
        else:
            dm = dist_maps.get(key_j)
            if dm is None: continue
            dist, close_j, close_i = _pair_distance_from_map(dm, px_j, px_i, all_ptu[key_j], all_ptu[key_i], int_err, all_uv_coords.get(key_j), all_uv_coords.get(key_i))
        if dist < ignore_under or dist >= int_err: continue
        mesh_i, sid_i = key_i; mesh_j, sid_j = key_j
        short_i = mesh_i.rsplit("|", 1)[-1]; short_j = mesh_j.rsplit("|", 1)[-1]
        label = ("{0} (Shell {1} <-> Shell {2})".format(short_i, sid_i, sid_j) if mesh_i == mesh_j
                else "{0} Shell {1} <-> {2} Shell {3}".format(short_i, sid_i, short_j, sid_j))
        errors.append({"component": label, "distance": dist, "type": "shell_distance", "shell_a": sid_i, "shell_b": sid_j, "mesh": mesh_i, "mesh_b": mesh_j, "shell_uvs_a": close_i, "shell_uvs_b": close_j})
    return errors, tr("shell_result", count=len(errors))

# === v35 (pre-1.0): UV Padding (A級 + B級 最適化) ===
# A級: _shell_to_border_distance — タイル境界座標の逆引き化
# B級: compute_uv_padding — BFS遅延構築 + BBOX事前刈り込み

def _shell_to_border_distance(dist_map, pixels, ptu, uv_coords, res_x, res_y, tile_ox, tile_oy, max_dist):
    bx_lo = tile_ox; bx_hi = tile_ox + res_x; by_lo = tile_oy; by_hi = tile_oy + res_y
    min_d = max_dist; hit_pixels = set()
    _get = dist_map.get
    # A級: タイル境界座標をイテレートし dist_map を O(1) ルックアップ
    # 左辺 (x=bx_lo)
    for y in range(by_lo, by_hi + 1):
        p = (bx_lo, y)
        d = _get(p, max_dist)
        if d < min_d: min_d = d; hit_pixels = {p}
        elif d == min_d and d < max_dist: hit_pixels.add(p)
    # 右辺 (x=bx_hi)
    for y in range(by_lo, by_hi + 1):
        p = (bx_hi, y)
        d = _get(p, max_dist)
        if d < min_d: min_d = d; hit_pixels = {p}
        elif d == min_d and d < max_dist: hit_pixels.add(p)
    # 下辺 (y=by_lo) — 角は左辺・右辺ループで処理済み
    for x in range(bx_lo + 1, bx_hi):
        p = (x, by_lo)
        d = _get(p, max_dist)
        if d < min_d: min_d = d; hit_pixels = {p}
        elif d == min_d and d < max_dist: hit_pixels.add(p)
    # 上辺 (y=by_hi) — 角は左辺・右辺ループで処理済み
    for x in range(bx_lo + 1, bx_hi):
        p = (x, by_hi)
        d = _get(p, max_dist)
        if d < min_d: min_d = d; hit_pixels = {p}
        elif d == min_d and d < max_dist: hit_pixels.add(p)
    if min_d >= max_dist: return max_dist, []
    close_uvs = set()
    for bp in hit_pixels:
        for sx in range(-min_d, min_d + 1):
            for sy in range(-min_d, min_d + 1):
                ca_ = (bp[0] + sx, bp[1] + sy)
                if ca_ in pixels: close_uvs.update(ptu.get(ca_, ()))
    if uv_coords:
        closest_shell_px = set()
        for bp in hit_pixels:
            for sx in range(-min_d, min_d + 1):
                for sy in range(-min_d, min_d + 1):
                    ca_ = (bp[0] + sx, bp[1] + sy)
                    if ca_ in pixels: closest_shell_px.add(ca_)
        f = _filter_uvs_by_proximity(close_uvs, uv_coords, closest_shell_px, 1)
        if f: close_uvs = f
    return min_d, list(close_uvs)

def _get_shell_tile(edges, res_x, res_y):
    tile_votes = defaultdict(int)
    for x0, y0, x1, y1, uv0, uv1 in edges:
        mx = (x0 + x1) * 0.5; my = (y0 + y1) * 0.5
        tile_votes[(int(math.floor(mx / res_x)), int(math.floor(my / res_y)))] += 1
    return max(tile_votes, key=tile_votes.get) if tile_votes else (0, 0)

def _bbox_to_border_chebyshev(bx0, by0, bx1, by1, lx0, ly0, lx1, ly1):
    """BBOXから線分 (lx0,ly0)-(lx1,ly1) へのチェビシェフ距離（軸整列線分専用）"""
    dx = max(0, bx0 - lx1, lx0 - bx1)
    dy = max(0, by0 - ly1, ly0 - by1)
    return max(dx, dy)


# --- v41 (pre-1.0): compute_uv_padding phase split refactoring ---
# Phase 1: _padding_phase1_collect  — rasterize + fast-mode dilation
# Phase 2: _padding_phase2_distances — candidate pairs + overlap filter + BFS
# Phase 3: _padding_phase3_results  — pair comparison + tile border + profile

def _padding_phase1_collect(ctx):
    """Phase 1: Rasterize shells and (optionally) dilate for fast mode.

    Populates ctx with all_pixels, all_ptu, all_uv_coords, all_bboxes,
    shell_tiles, shell_keys_list, total_shells, int_shell_err, int_tile_err.
    Returns (errors, summary) tuple on cancel, None on success.
    """
    all_shell_edges = ctx["all_shell_edges"]
    res_x = ctx["res_x"]; res_y = ctx["res_y"]
    shell_error = ctx["shell_error"]; tile_error = ctx["tile_error"]
    target_shell_pairs = ctx["target_shell_pairs"]
    target_tile_shells = ctx["target_tile_shells"]
    dilate_for_fast_mode = ctx["dilate_for_fast_mode"]
    progress_cb = ctx["progress_cb"]; cancel_check = ctx["cancel_check"]
    _prof = ctx["_prof"]
    int_shell_err = int(math.ceil(shell_error))
    int_tile_err = int(math.ceil(tile_error))
    ctx["int_shell_err"] = int_shell_err
    ctx["int_tile_err"] = int_tile_err
    _t0 = time.time()
    all_pixels = {}; all_ptu = {}; all_uv_coords = {}; all_bboxes = {}; shell_tiles = {}
    shell_keys_list = list(all_shell_edges.keys()); total_shells = len(shell_keys_list)
    # v40: Selective rasterization — only rasterize needed shells when both targets provided
    if target_shell_pairs is not None and target_tile_shells is not None:
        _raster_set = set()
        for _ka, _kb in target_shell_pairs:
            _raster_set.add(_ka); _raster_set.add(_kb)
        _raster_set.update(target_tile_shells)
    else:
        _raster_set = None
    for si, key in enumerate(shell_keys_list):
        if cancel_check and cancel_check(): return [], tr("cancelled")
        if _raster_set is not None and key not in _raster_set:
            continue
        if progress_cb: progress_cb(si, total_shells * 4, tr("progress_padding_raster", current=si + 1, total=total_shells))
        edges = all_shell_edges[key]; px_set, ptu, uvc = _rasterize_shell_edges(edges)
        all_pixels[key] = px_set; all_ptu[key] = ptu; all_uv_coords[key] = uvc
        shell_tiles[key] = _get_shell_tile(edges, res_x, res_y)
        if px_set:
            xs = [p[0] for p in px_set]; ys = [p[1] for p in px_set]
            all_bboxes[key] = (min(xs), min(ys), max(xs), max(ys))
    _prof["1_rasterize"] = time.time() - _t0
    # v38: Fast mode — dilate shell pixels to prevent false negatives
    if dilate_for_fast_mode:
        for key in shell_keys_list:
            original_px = all_pixels[key]
            if not original_px: continue
            dilated = set(original_px)
            for x, y in original_px:
                for dx, dy in _CHEB_DIRS:
                    dilated.add((x + dx, y + dy))
            ptu = all_ptu[key]
            for np_ in dilated - original_px:
                for dx, dy in _CHEB_DIRS:
                    neighbor = (np_[0] + dx, np_[1] + dy)
                    if neighbor in ptu:
                        ptu[np_] = ptu[neighbor]
                        break
            all_pixels[key] = dilated
            if dilated:
                xs = [p[0] for p in dilated]; ys = [p[1] for p in dilated]
                all_bboxes[key] = (min(xs), min(ys), max(xs), max(ys))
    ctx["all_pixels"] = all_pixels; ctx["all_ptu"] = all_ptu
    ctx["all_uv_coords"] = all_uv_coords; ctx["all_bboxes"] = all_bboxes
    ctx["shell_tiles"] = shell_tiles
    ctx["shell_keys_list"] = shell_keys_list; ctx["total_shells"] = total_shells
    return None


def _padding_phase2_distances(ctx):
    """Phase 2: Candidate pair generation, overlap pre-filter, BFS construction.

    Populates ctx with candidate_pairs, needs_tile_bfs, dist_maps,
    needed_list, _overlap_skip.
    Returns (errors, summary) tuple on cancel, None on success.
    """
    all_pixels = ctx["all_pixels"]; all_ptu = ctx["all_ptu"]
    all_bboxes = ctx["all_bboxes"]; shell_tiles = ctx["shell_tiles"]
    shell_keys_list = ctx["shell_keys_list"]; total_shells = ctx["total_shells"]
    int_shell_err = ctx["int_shell_err"]; int_tile_err = ctx["int_tile_err"]
    res_x = ctx["res_x"]; res_y = ctx["res_y"]
    target_shell_pairs = ctx["target_shell_pairs"]
    target_tile_shells = ctx["target_tile_shells"]
    progress_cb = ctx["progress_cb"]; cancel_check = ctx["cancel_check"]
    _prof = ctx["_prof"]
    # --- Candidate pairs ---
    _t0 = time.time()
    # v39: target_shell_pairs / target_tile_shells — skip generation if provided
    if target_shell_pairs is not None:
        candidate_pairs = target_shell_pairs
    else:
        tile_shells = defaultdict(list)
        for key in shell_keys_list: tile_shells[shell_tiles[key]].append(key)
        _floor = math.floor; shell_cell_size = max(int_shell_err * 2, 1); candidate_pairs = set()
        for t, keys in tile_shells.items():
            tile_grid = defaultdict(set)
            for key in keys:
                if key not in all_bboxes: continue
                bx0, by0, bx1, by1 = all_bboxes[key]
                for cx in range(int(_floor(bx0 / shell_cell_size)), int(_floor(bx1 / shell_cell_size)) + 1):
                    for cy in range(int(_floor(by0 / shell_cell_size)), int(_floor(by1 / shell_cell_size)) + 1):
                        tile_grid[(cx, cy)].add(key)
            for cell_keys in tile_grid.values():
                cell_list = list(cell_keys)
                for ii in range(len(cell_list)):
                    for jj in range(ii + 1, len(cell_list)):
                        ka, kb = cell_list[ii], cell_list[jj]
                        candidate_pairs.add((ka, kb) if ka < kb else (kb, ka))
    needed_for_pairs = set()
    for ka, kb in candidate_pairs: needed_for_pairs.add(ka); needed_for_pairs.add(kb)
    if target_tile_shells is not None:
        needs_tile_bfs = target_tile_shells
    else:
        # B級: BBOXからタイル各辺へのチェビシェフ距離を計算し、遠いシェルのタイルBFSをスキップ
        needs_tile_bfs = set()
        _cheb = _bbox_to_border_chebyshev
        for key in shell_keys_list:
            if key not in all_bboxes: continue
            bx0, by0, bx1, by1 = all_bboxes[key]
            tu, tv = shell_tiles[key]
            tox = tu * res_x; toy = tv * res_y
            bl = tox; br = tox + res_x; bb = toy; bt = toy + res_y
            d_min = min(_cheb(bx0, by0, bx1, by1, bl, bb, bl, bt),
                        _cheb(bx0, by0, bx1, by1, br, bb, br, bt),
                        _cheb(bx0, by0, bx1, by1, bl, bb, br, bb),
                        _cheb(bx0, by0, bx1, by1, bl, bt, br, bt))
            if d_min < int_tile_err:
                needs_tile_bfs.add(key)
    _prof["2_candidate"] = time.time() - _t0
    # --- Overlap pre-filter (fast-mode dist=0 pairs) ---
    _overlap_skip = 0
    if target_shell_pairs is not None:
        _t0 = time.time()
        remaining_pairs = set()
        for ka, kb in candidate_pairs:
            px_a = all_pixels.get(ka); px_b = all_pixels.get(kb)
            if not px_a or not px_b: _overlap_skip += 1; continue
            if len(px_a) <= len(px_b):
                has_overlap = any(p in px_b for p in px_a)
            else:
                has_overlap = any(p in px_a for p in px_b)
            if has_overlap: _overlap_skip += 1
            else: remaining_pairs.add((ka, kb) if ka < kb else (kb, ka))
        candidate_pairs = remaining_pairs
        needed_for_pairs = set()
        for ka, kb in candidate_pairs: needed_for_pairs.add(ka); needed_for_pairs.add(kb)
        _prof["25_overlap"] = time.time() - _t0
    else:
        _prof["25_overlap"] = 0.0
    _prof["_overlap_skip"] = _overlap_skip
    # --- BFS ---
    _t0 = time.time()
    # Always build dist_map for LARGER shell → cheaper pair iteration (smaller shell iterated)
    _map_shells = set()
    for _ka, _kb in candidate_pairs:
        _pa = all_pixels.get(_ka); _pb = all_pixels.get(_kb)
        if not _pa or not _pb: continue
        if len(_pa) > len(_pb): _map_shells.add(_ka)
        else: _map_shells.add(_kb)
    needs_bfs = _map_shells | needs_tile_bfs
    dist_maps = {}; needed_list = [k for k in shell_keys_list if k in needs_bfs and k in all_bboxes and all_pixels[k]]
    for si, key in enumerate(needed_list):
        if cancel_check and cancel_check(): return [], tr("cancelled")
        if progress_cb: progress_cb(total_shells + si, total_shells + len(needed_list) + len(candidate_pairs), tr("progress_padding_bfs", current=si + 1, total=len(needed_list)))
        # v40: Per-shell BFS depth — use minimum required depth
        _depth = 0
        if key in _map_shells: _depth = int_shell_err
        if key in needs_tile_bfs: _depth = max(_depth, int_tile_err)
        dist_maps[key] = _build_distance_map(all_pixels[key], _depth)
    _prof["3_bfs"] = time.time() - _t0
    ctx["candidate_pairs"] = candidate_pairs; ctx["needs_tile_bfs"] = needs_tile_bfs
    ctx["dist_maps"] = dist_maps; ctx["needed_list"] = needed_list
    ctx["_overlap_skip"] = _overlap_skip
    return None


def _padding_phase3_results(ctx):
    """Phase 3: Pair distance comparison, tile border check, profile summary.

    Returns (errors, summary_string, _profile).
    """
    all_pixels = ctx["all_pixels"]; all_ptu = ctx["all_ptu"]
    all_uv_coords = ctx["all_uv_coords"]; all_bboxes = ctx["all_bboxes"]
    shell_tiles = ctx["shell_tiles"]
    shell_keys_list = ctx["shell_keys_list"]; total_shells = ctx["total_shells"]
    int_shell_err = ctx["int_shell_err"]; int_tile_err = ctx["int_tile_err"]
    res_x = ctx["res_x"]; res_y = ctx["res_y"]
    shell_ignore = ctx["shell_ignore"]; tile_ignore = ctx["tile_ignore"]
    scale_factor = ctx["scale_factor"]
    candidate_pairs = ctx["candidate_pairs"]; needs_tile_bfs = ctx["needs_tile_bfs"]
    dist_maps = ctx["dist_maps"]; needed_list = ctx["needed_list"]
    _overlap_skip = ctx["_overlap_skip"]
    progress_cb = ctx["progress_cb"]; cancel_check = ctx["cancel_check"]
    _prof = ctx["_prof"]
    # --- Pair comparison ---
    _t0 = time.time()
    shell_errors = []; pair_count = 0; total_pairs = len(candidate_pairs); report_interval = max(1, total_pairs // 50)
    for key_i, key_j in candidate_pairs:
        pair_count += 1
        if cancel_check and cancel_check(): return [], tr("cancelled")
        if progress_cb and pair_count % report_interval == 0: progress_cb(total_shells + len(needed_list) + pair_count, total_shells + len(needed_list) + total_pairs + len(needs_tile_bfs), tr("progress_padding_pair", current=pair_count, total=total_pairs))
        if key_i not in all_bboxes or key_j not in all_bboxes: continue
        bb_i, bb_j = all_bboxes[key_i], all_bboxes[key_j]
        if max(max(0, max(bb_i[0] - bb_j[2], bb_j[0] - bb_i[2])), max(0, max(bb_i[1] - bb_j[3], bb_j[1] - bb_i[3]))) >= int_shell_err: continue
        px_i = all_pixels[key_i]; px_j = all_pixels[key_j]
        if len(px_j) > len(px_i):
            dm = dist_maps.get(key_j)
            if dm is None: continue
            dist, close_j, close_i = _pair_distance_from_map(dm, px_j, px_i, all_ptu[key_j], all_ptu[key_i], int_shell_err, all_uv_coords.get(key_j), all_uv_coords.get(key_i))
        else:
            dm = dist_maps.get(key_i)
            if dm is None: continue
            dist, close_i, close_j = _pair_distance_from_map(dm, px_i, px_j, all_ptu[key_i], all_ptu[key_j], int_shell_err, all_uv_coords.get(key_i), all_uv_coords.get(key_j))
        if dist >= int_shell_err: continue
        if dist < shell_ignore:
            if scale_factor <= 1: continue
            # v40: fast mode — dist=0 at reduced res may be dist>=1 at full res
            # Pass all sub-ignore pairs to Phase 2 for accurate full-res check
        mesh_i, sid_i = key_i; mesh_j, sid_j = key_j
        short_i = mesh_i.rsplit("|", 1)[-1]; short_j = mesh_j.rsplit("|", 1)[-1]
        label = ("{0} (Shell {1} <-> Shell {2})".format(short_i, sid_i, sid_j) if mesh_i == mesh_j else "{0} Shell {1} <-> {2} Shell {3}".format(short_i, sid_i, short_j, sid_j))
        shell_errors.append({"component": label, "distance": dist, "type": "shell_distance", "shell_a": sid_i, "shell_b": sid_j, "mesh": mesh_i, "mesh_b": mesh_j, "shell_uvs_a": close_i, "shell_uvs_b": close_j})
    _prof["4_pair"] = time.time() - _t0
    # --- Tile border ---
    _t0 = time.time()
    tile_errors = []
    for si, key in enumerate(shell_keys_list):
        if cancel_check and cancel_check(): return [], tr("cancelled")
        if progress_cb: progress_cb(total_shells + len(needed_list) + total_pairs + si, total_shells + len(needed_list) + total_pairs + total_shells, tr("progress_padding_tile", current=si + 1, total=total_shells))
        if key not in needs_tile_bfs: continue
        dm = dist_maps.get(key)
        if dm is None: continue
        tu, tv = shell_tiles[key]; tile_ox = tu * res_x; tile_oy = tv * res_y
        dist, close_uvs = _shell_to_border_distance(dm, all_pixels[key], all_ptu[key], all_uv_coords.get(key), res_x, res_y, tile_ox, tile_oy, int_tile_err)
        if dist < tile_ignore or dist >= int_tile_err: continue
        mesh_name, sid = key
        short_name = mesh_name.rsplit("|", 1)[-1]
        tile_errors.append({"component": "{0} Shell {1} -> Tile({2},{3}) border".format(short_name, sid, tu, tv), "distance": dist, "type": "tile_distance", "shell_a": sid, "mesh": mesh_name, "shell_uvs_a": close_uvs})
    _prof["5_tile"] = time.time() - _t0
    # --- Profile summary ---
    _prof["total"] = time.time() - ctx["_t0_total"]
    _profile = {
        "summary": "shells={0} | bfs_built={1} | pairs={2} | overlap_skip={3} | tile_bfs={4} | scipy={5}".format(
            total_shells, len(needed_list), total_pairs, _overlap_skip, len(needs_tile_bfs), _HAS_SCIPY),
        "phases": [
            {"name": "Rasterize", "time": round(_prof["1_rasterize"], 2)},
            {"name": "Candidate", "time": round(_prof["2_candidate"], 2)},
            {"name": "Overlap", "time": round(_prof["25_overlap"], 2)},
            {"name": "BFS", "time": round(_prof["3_bfs"], 2)},
            {"name": "Pair", "time": round(_prof["4_pair"], 2)},
            {"name": "Tile", "time": round(_prof["5_tile"], 2)},
        ],
        "total": round(_prof["total"], 2)
    }
    return shell_errors + tile_errors, tr("padding_result", s_count=len(shell_errors), t_count=len(tile_errors)), _profile


def compute_uv_padding(all_shell_edges, shell_ignore, shell_error, tile_ignore, tile_error, res_x, res_y, dilate_for_fast_mode=False, target_shell_pairs=None, target_tile_shells=None, scale_factor=1, progress_cb=None, cancel_check=None):
    """Check UV padding for shell-to-shell and shell-to-tile-border distances.

    Returns (errors, summary_string, _profile). Combines shell distance errors
    and tile border distance errors via three internal phases:
      Phase 1 (_padding_phase1_collect): rasterize + fast-mode dilation
      Phase 2 (_padding_phase2_distances): candidate pairs + overlap filter + BFS
      Phase 3 (_padding_phase3_results): pair comparison + tile border + profile
    """
    if not all_shell_edges: return [], tr("padding_result", s_count=0, t_count=0)
    ctx = {
        "all_shell_edges": all_shell_edges,
        "shell_ignore": shell_ignore, "shell_error": shell_error,
        "tile_ignore": tile_ignore, "tile_error": tile_error,
        "res_x": res_x, "res_y": res_y,
        "dilate_for_fast_mode": dilate_for_fast_mode,
        "target_shell_pairs": target_shell_pairs,
        "target_tile_shells": target_tile_shells,
        "scale_factor": scale_factor,
        "progress_cb": progress_cb, "cancel_check": cancel_check,
        "_prof": {}, "_t0_total": time.time(),
    }
    result = _padding_phase1_collect(ctx)
    if result is not None: return result
    result = _padding_phase2_distances(ctx)
    if result is not None: return result
    return _padding_phase3_results(ctx)
# --- [120] uv_overlap ---
# depends on: [000] header, [010] i18n, [020] utils (get_selected_meshes, get_mesh_fn)
# =====================================================================
# v45 (pre-1.0): UV Overlap — Two-stage rasterization + BBox pre-filter
#                   + Intentional overlap exclusion (face vertex tolerance)
#                   + LowRes 512
# v50 (pre-1.0): Intentional overlap filter → optional (classify instead of exclude)
# ~1.5.8-dev: Hotfix — Layer 1: require >=2 shared positions; Layer 2: >0.95 + min 3 matches
# ~1.5.8-dev: Hotfix — Layer 1: remove immediate classification, delegate to Layer 2
# ~1.6.0-dev: hotfix-1: Layer 2: skip boundary-adjacent pairs with zero face matches
# ~1.6.0-dev: hotfix-2: boundary-adjacent-only pairs silently skipped (no longer reported as intentional)
# ~1.6.0-dev: hotfix-3: partial match branch requires matched_count >= 3 (fewer matches = all error)
# ~1.6.3-dev: _FP_TOLERANCE 1e-4 -> 3e-4 (relax vertex tolerance to ~1.2px @4096)
# ~1.7.1-dev: Refactor — extract _build_overlap_results helper (deduplicate Phase 4-5)
# ~1.7.1-dev: Remove dead deep copy of overlap_shell_pairs in _run_phase4
# ~1.7.1-dev: Move summary into _build_overlap_results; add Args/Returns docstring
# ~1.7.1-dev: Consolidate error/intentional dict loops into single unified loop
# ~1.7.2-dev: Perf — cache self_face_uv, self_filtered_pairs, shell_global_bbox after Phase 3
# ~1.7.2-dev: Perf — replace _build_overlap_results with _build_overlap_results_from_cache
# ~1.7.5-dev: hotfix — _fast_classify_counts: add no-match/low-match always-error corrections
# ~1.7.6-dev: Remove _fast_classify_counts + F-1~F-4 cache (drag summary disabled)
# ~1.7.7-dev: Simplify _classify_by_tolerance to per-pair min_dist comparison
# =====================================================================
import array as _array_mod

_OVERLAP_RESOLUTION = 4096
_OVERLAP_LOWRES = 512
_FP_TOLERANCE = 3e-4  # Max per-vertex UV distance for intentional match (~1.2px @4096)

# --- v1.7.0-dev: Cache for Phase 1-3 results (reused by tolerance slider) ---
_overlap_cache = {}


def clear_overlap_cache():
    """Invalidate cached Phase 1-3 results.
    Called on: new check / mesh change / OverlapResultsWindow close."""
    global _overlap_cache
    _overlap_cache = {}


def collect_overlap_data(include_self_overlap):
    """Collect triangulated UV data from selected meshes for overlap detection.

    Returns dict with 'tris', 'shell_faces', 'face_uvs', and flags,
    or None if no mesh selected.
    """
    dag_paths = get_selected_meshes()
    if not dag_paths:
        return None
    all_tris = []
    all_shell_faces = {}
    face_uvs = {}  # (mesh_name, face_idx) -> tuple of (u, v)
    for dag in dag_paths:
        mesh_fn = get_mesh_fn(dag)
        mesh_name = dag.fullPathName()
        num_uvs = mesh_fn.numUVs()
        if num_uvs == 0:
            continue
        us, vs = mesh_fn.getUVs()
        uv_counts, uv_ids = mesh_fn.getAssignedUVs()
        shell_map = mesh_fn.getUvShellsIds()[1]
        # Compute shell_faces inline (reuses already-fetched UV data)
        _sf_offset = 0
        for _sf_fi in range(mesh_fn.numPolygons):
            _sf_count = uv_counts[_sf_fi]
            if _sf_count > 0:
                _sf_key = (mesh_name, shell_map[uv_ids[_sf_offset]])
                if _sf_key not in all_shell_faces:
                    all_shell_faces[_sf_key] = []
                all_shell_faces[_sf_key].append(_sf_fi)
            _sf_offset += _sf_count
        uv_offset = 0
        for face_idx in range(mesh_fn.numPolygons):
            count = uv_counts[face_idx]
            if count < 3:
                uv_offset += count
                continue
            fids = [uv_ids[uv_offset + k] for k in range(count)]
            s_id = shell_map[fids[0]]
            # Store raw UV coords for tolerance-based matching
            face_uvs[(mesh_name, face_idx)] = tuple(
                (float(us[fid]), float(vs[fid])) for fid in fids)
            u0f, v0f = float(us[fids[0]]), float(vs[fids[0]])
            for k in range(1, count - 1):
                all_tris.append((
                    mesh_name, face_idx, s_id,
                    (u0f, v0f),
                    (float(us[fids[k]]), float(vs[fids[k]])),
                    (float(us[fids[k + 1]]), float(vs[fids[k + 1]])),
                    [fids[0], fids[k], fids[k + 1]]))
            uv_offset += count
    return {"tris": all_tris, "shell_faces": all_shell_faces,
            "include_self": include_self_overlap, "face_uvs": face_uvs}


def _faces_match(uvs_a, uvs_b, tol):
    """Check if two faces have matching UV vertices within tolerance.
    Uses greedy nearest-neighbor matching (finds closest B for each A).
    Returns max vertex Chebyshev distance if matched, -1.0 if not."""
    if len(uvs_a) != len(uvs_b):
        return -1.0
    n = len(uvs_a)
    used = [False] * n
    max_d = 0.0
    for au, av in uvs_a:
        best_j = -1
        best_d = float('inf')
        for j in range(n):
            if used[j]:
                continue
            du = au - uvs_b[j][0]
            if du < 0: du = -du
            dv = av - uvs_b[j][1]
            if dv < 0: dv = -dv
            d = du if du > dv else dv
            if d < best_d:
                best_d = d
                best_j = j
        if best_j == -1 or best_d > tol:
            return -1.0
        used[best_j] = True
        if best_d > max_d:
            max_d = best_d
    return max_d


def _rasterize_tile(tris, shell_to_idx, idx_to_shell, RES, tx, ty,
                    include_self, active_shells):
    """Rasterize triangles for one tile and detect overlaps.

    Scanline rasterization approach: each triangle is sorted by Y,
    then swept row-by-row filling a 2D grid (shell_grid × face_grid)
    backed by flat array.array('i') for cache-friendly O(1) pixel
    writes.  When a pixel is already claimed by a different shell,
    the pair is recorded as an overlap candidate.

    Args:
        tris: list of (mesh_name, face_idx, shell_id, p0, p1, p2, uv_ids)
        shell_to_idx: dict mapping (mesh_name, shell_id) -> int index
        idx_to_shell: list mapping int index -> (mesh_name, shell_id)
        RES: rasterization resolution (pixels per UDIM tile edge)
        tx, ty: UDIM tile origin (integer tile coordinates)
        include_self: bool — whether to detect self-overlap within a shell
        active_shells: set of int shell indices to process; others skipped

    Returns:
        (overlap_pairs, self_candidates)
        overlap_pairs: defaultdict((shell_a, shell_b) -> set of (mesh, face))
        self_candidates: defaultdict(shell_key -> set of (face_a, face_b))
    """
    _floor = math.floor
    gs = RES * RES
    sg = _array_mod.array('i', [-1]) * gs
    fg = _array_mod.array('i', [-1]) * gs
    overlap_pairs = defaultdict(set)
    self_cands = defaultdict(set)
    for tri in tris:
        mn = tri[0]; fi = tri[1]; si = tri[2]
        sidx = shell_to_idx[(mn, si)]
        if sidx not in active_shells:
            continue
        p0x = (tri[3][0] - tx) * RES; p0y = (tri[3][1] - ty) * RES
        p1x = (tri[4][0] - tx) * RES; p1y = (tri[4][1] - ty) * RES
        p2x = (tri[5][0] - tx) * RES; p2y = (tri[5][1] - ty) * RES
        if p0y > p1y: p0x, p0y, p1x, p1y = p1x, p1y, p0x, p0y
        if p0y > p2y: p0x, p0y, p2x, p2y = p2x, p2y, p0x, p0y
        if p1y > p2y: p1x, p1y, p2x, p2y = p2x, p2y, p1x, p1y
        dy02 = p2y - p0y
        if dy02 < 1e-10:
            xl = min(p0x, p1x, p2x); xr = max(p0x, p1x, p2x)
            iy = int(_floor(p0y))
            if 0 <= iy < RES:
                ix0 = max(0, int(_floor(xl)))
                ix1 = min(RES - 1, int(_floor(xr)))
                row = iy * RES
                for ix in range(ix0, ix1 + 1):
                    pidx = row + ix; es = sg[pidx]
                    if es == -1:
                        sg[pidx] = sidx; fg[pidx] = fi
                    elif es != sidx:
                        sa = idx_to_shell[es]; sb = idx_to_shell[sidx]
                        sp = (sa, sb) if sa <= sb else (sb, sa)
                        overlap_pairs[sp].add((sa[0], fg[pidx]))
                        overlap_pairs[sp].add((mn, fi))
                    elif include_self and fg[pidx] != fi:
                        ef = fg[pidx]; skey = idx_to_shell[sidx]
                        self_cands[skey].add(
                            (ef, fi) if ef < fi else (fi, ef))
                        fg[pidx] = fi
            continue
        dy01 = p1y - p0y; dy12 = p2y - p1y
        inv02 = 1.0 / dy02
        inv01 = 1.0 / dy01 if dy01 > 1e-10 else 0.0
        inv12 = 1.0 / dy12 if dy12 > 1e-10 else 0.0
        iy_s = max(0, int(_floor(p0y)))
        iy_e = min(RES - 1, int(_floor(p2y)))
        for iy in range(iy_s, iy_e + 1):
            yf = iy + 0.5
            t = (yf - p0y) * inv02
            if t < 0.0: t = 0.0
            elif t > 1.0: t = 1.0
            x_long = p0x + t * (p2x - p0x)
            if yf < p1y:
                t2 = (yf - p0y) * inv01
                if t2 < 0.0: t2 = 0.0
                elif t2 > 1.0: t2 = 1.0
                x_short = p0x + t2 * (p1x - p0x)
            else:
                t2 = (yf - p1y) * inv12
                if t2 < 0.0: t2 = 0.0
                elif t2 > 1.0: t2 = 1.0
                x_short = p1x + t2 * (p2x - p1x)
            if x_long > x_short:
                xl = x_short; xr = x_long
            else:
                xl = x_long; xr = x_short
            ix0 = max(0, int(_floor(xl)))
            ix1 = min(RES - 1, int(_floor(xr)))
            row = iy * RES
            for ix in range(ix0, ix1 + 1):
                pidx = row + ix; es = sg[pidx]
                if es == -1:
                    sg[pidx] = sidx; fg[pidx] = fi
                elif es != sidx:
                    sa = idx_to_shell[es]; sb = idx_to_shell[sidx]
                    sp = (sa, sb) if sa <= sb else (sb, sa)
                    overlap_pairs[sp].add((sa[0], fg[pidx]))
                    overlap_pairs[sp].add((mn, fi))
                elif include_self and fg[pidx] != fi:
                    ef = fg[pidx]; skey = idx_to_shell[sidx]
                    self_cands[skey].add(
                        (ef, fi) if ef < fi else (fi, ef))
                    fg[pidx] = fi
    return overlap_pairs, self_cands


def _compute_pair_distances(overlap_shell_pairs, all_shell_faces,
                             face_uvs, max_tol):
    """Pre-compute all face-pair distances for each shell pair.

    For each shell pair, compute ALL valid A-B face matches (with distance)
    regardless of tolerance, plus boundary-adjacency flag.
    Results are cached so that re-filtering by tolerance needs no _faces_match calls.

    Args:
        overlap_shell_pairs: dict of (shell_a, shell_b) -> set of (mesh, face)
        all_shell_faces: dict of shell_key -> list of face indices
        face_uvs: dict of (mesh, face) -> tuple of (u,v)
        max_tol: maximum tolerance to consider (use a generous upper bound)

    Returns:
        dict of sp_key -> {
            "all_matches": [(dist, fi_a, fi_b), ...],  # sorted by dist
            "is_boundary_adjacent": bool,
            "faces_a": set, "faces_b": set,
            "faces": set  # original overlap face set
        }
    """
    pair_data = {}
    if not face_uvs:
        for sp_key, faces in overlap_shell_pairs.items():
            pair_data[sp_key] = {
                "all_matches": [], "is_boundary_adjacent": False,
                "faces_a": set(), "faces_b": set(), "faces": faces}
        return pair_data
    for sp_key, faces in overlap_shell_pairs.items():
        sa_key, sb_key = sp_key
        if sa_key == sb_key:
            pair_data[sp_key] = {
                "all_matches": [], "is_boundary_adjacent": False,
                "faces_a": set(), "faces_b": set(), "faces": faces}
            continue
        sa_set = set(all_shell_faces.get(sa_key, []))
        sb_set = set(all_shell_faces.get(sb_key, []))
        faces_a = set(); faces_b = set()
        for mn, fi in faces:
            if fi in sa_set and mn == sa_key[0]: faces_a.add(fi)
            elif fi in sb_set and mn == sb_key[0]: faces_b.add(fi)
        is_boundary_adjacent = False
        if sa_key[0] == sb_key[0] and faces_a and faces_b:
            _q = 100000
            va = set()
            for fi in faces_a:
                uvs = face_uvs.get((sa_key[0], fi))
                if uvs:
                    for u, v in uvs:
                        va.add((int(u * _q + 0.5), int(v * _q + 0.5)))
            shared = set()
            for fi in faces_b:
                uvs = face_uvs.get((sb_key[0], fi))
                if uvs:
                    for u, v in uvs:
                        pt = (int(u * _q + 0.5), int(v * _q + 0.5))
                        if pt in va:
                            shared.add(pt)
                            if len(shared) >= 2: break
                if len(shared) >= 2: break
            if len(shared) >= 2:
                is_boundary_adjacent = True
        b_by_count = {}
        for fi in faces_b:
            uvs = face_uvs.get((sb_key[0], fi))
            if uvs is not None:
                nc = len(uvs)
                if nc not in b_by_count: b_by_count[nc] = []
                b_by_count[nc].append((fi, uvs))
        all_matches = []
        for fi_a in faces_a:
            uvs_a = face_uvs.get((sa_key[0], fi_a))
            if uvs_a is None: continue
            nc = len(uvs_a)
            cands = b_by_count.get(nc)
            if not cands: continue
            for fi_b, uvs_b in cands:
                d = _faces_match(uvs_a, uvs_b, max_tol)
                if d >= 0:
                    all_matches.append((d, fi_a, fi_b))
        all_matches.sort()
        pair_data[sp_key] = {
            "all_matches": all_matches,
            "is_boundary_adjacent": is_boundary_adjacent,
            "faces_a": faces_a, "faces_b": faces_b,
            "faces": faces}
    return pair_data


def _classify_by_tolerance(pair_data, tol):
    """Classify shell pairs as error/intentional by per-pair min distance.

    Simplified for refilter: min_dist < tol -> intentional, else -> error.
    Boundary-adjacent pairs with no face matches are silently skipped.

    Returns (filtered_pairs, intentional_pairs, int_skip_count).
    """
    # ~1.7.7-dev: Simplified — per-pair min_dist comparison replaces
    # face-matching ratio logic.  Slider now directly controls which
    # pairs are classified as intentional.
    filtered_pairs = {}
    intentional_pairs = {}
    int_skip = 0
    for sp_key, pd in pair_data.items():
        faces = pd["faces"]
        if sp_key[0] == sp_key[1]:
            filtered_pairs[sp_key] = faces
            continue
        # Boundary-adjacent with no face matches: skip (seam artifact only)
        if pd.get("is_boundary_adjacent", False) and not pd["all_matches"]:
            int_skip += len(faces)
            continue
        min_dist = pd["all_matches"][0][0] if pd["all_matches"] else float('inf')
        if min_dist < tol:
            intentional_pairs[sp_key] = faces
            int_skip += len(faces)
        else:
            filtered_pairs[sp_key] = faces
    return filtered_pairs, intentional_pairs, int_skip


def _group_overlap_shells(errors, intentional_errors, shell_global_bbox):
    """Group overlapping shells using Union-Find + UDIM tile sub-grouping.

    Builds connected components from shell pairs, then sub-divides each
    component by the representative UDIM tile of each shell (BBox center).

    Args:
        errors: list of error dicts (unintentional overlaps)
        intentional_errors: list of error dicts (intentional overlaps)
        shell_global_bbox: dict mapping (mesh_name, shell_id) -> [min_u, min_v, max_u, max_v]

    Returns:
        list of group dicts with keys: group_id, udim_tile, shell_keys,
        faces, errors, intentional
    """
    _floor = math.floor
    all_items = []
    for e in errors:
        all_items.append((e, False))
    for e in intentional_errors:
        all_items.append((e, True))
    if not all_items:
        return []
    # Union-Find
    _par = {}
    def _uf_find(x):
        while _par[x] != x:
            _par[x] = _par[_par[x]]
            x = _par[x]
        return x
    def _uf_union(a, b):
        ra = _uf_find(a); rb = _uf_find(b)
        if ra != rb:
            _par[ra] = rb
    for e, _ in all_items:
        ka = (e["mesh"], e["shell_a"])
        kb = (e.get("mesh_b", e["mesh"]), e["shell_b"])
        if ka not in _par:
            _par[ka] = ka
        if kb not in _par:
            _par[kb] = kb
        _uf_union(ka, kb)
    # Shell -> representative UDIM tile (from BBox center)
    def _udim(skey):
        bb = shell_global_bbox.get(skey)
        if bb:
            cx = (bb[0] + bb[2]) / 2.0
            cy = (bb[1] + bb[3]) / 2.0
            return 1001 + int(_floor(cx)) + int(_floor(cy)) * 10
        return 1001
    # Sub-groups: (component_root, udim_tile) -> set of shell_keys
    sub_groups = defaultdict(set)
    for sk in _par:
        sub_groups[(_uf_find(sk), _udim(sk))].add(sk)
    # Assign errors to sub-groups via shell_a's sub-group
    sg_errors = defaultdict(list)
    for e, is_int in all_items:
        ka = (e["mesh"], e["shell_a"])
        sg_key = (_uf_find(ka), _udim(ka))
        sg_errors[sg_key].append((e, is_int))
    # Build group list
    groups = []
    gid = 0
    for sg_key in sorted(sub_groups.keys()):
        items = sg_errors.get(sg_key, [])
        if not items:
            continue
        _, tile = sg_key
        shells = sub_groups[sg_key]
        grp_errors = [e for e, _ in items]
        grp_intentional = all(is_int for _, is_int in items)
        grp_faces = set()
        for e, _ in items:
            for f in e.get("shell_faces_a", []):
                grp_faces.add((e["mesh"], f))
            mb = e.get("mesh_b", e["mesh"])
            for f in e.get("shell_faces_b", []):
                grp_faces.add((mb, f))
        groups.append({
            "group_id": gid,
            "udim_tile": str(tile),
            "shell_keys": sorted(shells),
            "faces": grp_faces,
            "errors": grp_errors,
            "intentional": grp_intentional,
        })
        gid += 1
    return groups


def _build_overlap_results_from_cache(overlap_shell_pairs, intentional_pairs,
                                       cached_self_pairs, all_shell_faces,
                                       include_self, idx_to_shell,
                                       cached_global_bbox):
    """Build error lists, shell groups, and summary from cached data.

    Lightweight version that uses pre-computed self_filtered_pairs and
    shell_global_bbox instead of re-scanning all_tris and tile_shell_bbox.

    Args:
        overlap_shell_pairs: dict of (shell_a, shell_b) -> set of (mesh, face)
            Unintentional overlap pairs from _classify_by_tolerance.
            Modified in-place to merge self-overlap pairs.
        intentional_pairs: dict of (shell_a, shell_b) -> set of (mesh, face)
            Intentional overlap pairs from _classify_by_tolerance.
        cached_self_pairs: dict of (skey, skey) -> set of (mesh, face)
            Pre-filtered self-overlap pairs (adjacency filter already applied).
        all_shell_faces: dict of shell_key -> list of face indices
        include_self: bool -- whether to merge self-overlap pairs
        idx_to_shell: list mapping int index -> (mesh_name, shell_id)
        cached_global_bbox: dict of shell_key -> [min_u, min_v, max_u, max_v]

    Returns:
        (all_groups, summary)
        all_groups: list of group dicts from _group_overlap_shells
        summary: str -- localized result summary via tr("ovlp_result", ...)
    """
    # Merge pre-filtered self-overlap pairs
    if include_self and cached_self_pairs:
        for sp, faces in cached_self_pairs.items():
            if sp not in overlap_shell_pairs:
                overlap_shell_pairs[sp] = set()
            overlap_shell_pairs[sp].update(faces)
    # Build error / intentional error lists (unified loop)
    errors = []
    intentional_errors = []
    for src, is_int, target in (
        (overlap_shell_pairs, False, errors),
        (intentional_pairs, True, intentional_errors),
    ):
        for sp_key, faces in src.items():
            (ma, sa), (mb, sb) = sp_key
            oc = len(faces)
            sfa = all_shell_faces.get((ma, sa), [])
            sfb = all_shell_faces.get((mb, sb), [])
            short_a = ma.rsplit("|", 1)[-1]; short_b = mb.rsplit("|", 1)[-1]
            if ma == mb:
                label = "{0} (Shell {1} <-> Shell {2})  \u2014  {3} faces".format(
                    short_a, sa, sb, oc)
            else:
                label = "{0} Shell {1} <-> {2} Shell {3}  \u2014  {4} faces".format(
                    short_a, sa, short_b, sb, oc)
            target.append({"component": label, "distance": 0, "type": "uv_overlap",
                "mesh": ma, "mesh_b": mb, "shell_a": sa, "shell_b": sb,
                "shell_faces_a": sfa, "shell_faces_b": sfb,
                "overlap_face_count": oc, "intentional": is_int})
    all_groups = _group_overlap_shells(errors, intentional_errors, cached_global_bbox)
    # Summary stats (single pass)
    n_errors = 0; n_intentional = 0; n_error_groups = 0; n_int_groups = 0
    for g in all_groups:
        if g["intentional"]:
            n_intentional += len(g["errors"]); n_int_groups += 1
        else:
            n_errors += len(g["errors"]); n_error_groups += 1
    summary = tr("ovlp_result", error=n_errors, error_groups=n_error_groups,
                  intentional=n_intentional, int_groups=n_int_groups)
    return all_groups, summary


def _run_phase4(tolerance, cache_data):
    """Re-run Phase 4 (intentional filter) + Phase 5 (grouping) with given tolerance.
    Uses cached Phase 1-3 results. Returns (all_groups, summary, profile)."""
    _t0_total = time.time()
    raw_pairs = cache_data["raw_overlap_pairs"]
    all_shell_faces = cache_data["all_shell_faces"]
    face_uvs = cache_data["face_uvs"]
    include_self = cache_data["include_self"]
    idx_to_shell = cache_data["idx_to_shell"]
    cached_self_pairs = cache_data.get("self_filtered_pairs", {})
    cached_global_bbox = cache_data.get("shell_global_bbox", {})
    # Deep copy self pairs (modified in-place by _build_overlap_results_from_cache)
    self_pairs = {k: set(v) for k, v in cached_self_pairs.items()}
    # --- Phase 4: Intentional overlap filter (cached distances) ---
    _t0 = time.time()
    pair_data = cache_data.get("pair_data", {})
    if not pair_data:
        # Fallback: compute pair distances.
        # Reachable if _run_phase4 is called directly without a full
        # compute_uv_overlap run, or if the cache is incomplete.
        pair_data = _compute_pair_distances(
            raw_pairs, all_shell_faces, face_uvs, 1e-2)
    overlap_shell_pairs, intentional_pairs, int_skip = _classify_by_tolerance(
        pair_data, tolerance)
    all_groups, summary = _build_overlap_results_from_cache(
        overlap_shell_pairs, intentional_pairs, self_pairs,
        all_shell_faces, include_self, idx_to_shell, cached_global_bbox)
    _p4 = time.time() - _t0
    _total = time.time() - _t0_total
    _profile = {
        "summary": "refilter | tol={0:.1e} | int_skip={1} | groups={2}".format(
            tolerance, int_skip, len(all_groups)),
        "phases": [
            {"name": "Result", "time": round(_p4, 2)},
        ],
        "total": round(_total, 2)
    }
    return all_groups, summary, _profile


def compute_uv_overlap(data, progress_cb=None, cancel_check=None):
    """Detect UV overlap using two-stage rasterization with BBox pre-filter
    and intentional overlap exclusion (face vertex tolerance in Phase 4).

    Phase 1-3 results are cached in _overlap_cache for tolerance slider refilter."""
    clear_overlap_cache()
    all_tris = data["tris"]
    all_shell_faces = data["shell_faces"]
    include_self = data["include_self"]
    face_uvs = data.get("face_uvs", {})
    if not all_tris:
        return [], tr("ovlp_result", error=0, error_groups=0, intentional=0, int_groups=0), {}
    RES_HI = _OVERLAP_RESOLUTION
    RES_LO = _OVERLAP_LOWRES
    n_tris = len(all_tris)
    _t0_total = time.time()
    _floor = math.floor
    # --- Phase 1: Shell indexing + UDIM tile grouping + BBox pre-filter ---
    _t0 = time.time()
    if progress_cb:
        progress_cb(0, 100, tr("progress_ovlp_lowres"))
    shell_to_idx = {}
    idx_to_shell = []
    for tri in all_tris:
        skey = (tri[0], tri[2])
        if skey not in shell_to_idx:
            shell_to_idx[skey] = len(idx_to_shell)
            idx_to_shell.append(skey)
    tile_tris = defaultdict(list)
    tile_shell_bbox = defaultdict(dict)
    for tri in all_tris:
        cx = (tri[3][0] + tri[4][0] + tri[5][0]) / 3.0
        cy = (tri[3][1] + tri[4][1] + tri[5][1]) / 3.0
        tkey = (int(_floor(cx)), int(_floor(cy)))
        tile_tris[tkey].append(tri)
        sidx = shell_to_idx[(tri[0], tri[2])]
        u0 = tri[3][0]; u1 = tri[4][0]; u2 = tri[5][0]
        v0 = tri[3][1]; v1 = tri[4][1]; v2 = tri[5][1]
        mn_u = min(u0, u1, u2); mx_u = max(u0, u1, u2)
        mn_v = min(v0, v1, v2); mx_v = max(v0, v1, v2)
        bb = tile_shell_bbox[tkey]
        if sidx in bb:
            b = bb[sidx]
            if mn_u < b[0]: b[0] = mn_u
            if mn_v < b[1]: b[1] = mn_v
            if mx_u > b[2]: b[2] = mx_u
            if mx_v > b[3]: b[3] = mx_v
        else:
            bb[sidx] = [mn_u, mn_v, mx_u, mx_v]
    # BBox overlap test -> active shells per tile
    tile_active = {}
    bbox_skipped = 0
    for tkey, bb in tile_shell_bbox.items():
        sidxs = list(bb.keys())
        active = set()
        n_s = len(sidxs)
        for i in range(n_s):
            for j in range(i + 1, n_s):
                a = bb[sidxs[i]]; b = bb[sidxs[j]]
                if a[0] <= b[2] and b[0] <= a[2] and a[1] <= b[3] and b[1] <= a[3]:
                    active.add(sidxs[i])
                    active.add(sidxs[j])
        if include_self:
            active = active | set(sidxs)
        tile_active[tkey] = active
        bbox_skipped += len(bb) - len(active)
    _p1 = time.time() - _t0
    # --- Phase 2: Low-res rasterize (candidate detection) ---
    _t0 = time.time()
    lo_pairs = defaultdict(set)
    lo_self = defaultdict(set)
    total_tiles = len(tile_tris)
    tile_count = 0
    for tkey, tris in tile_tris.items():
        tile_count += 1
        if cancel_check and cancel_check():
            return [], tr("cancelled")
        if progress_cb and total_tiles > 0:
            pct = 5 + int(tile_count * 40 / total_tiles)
            progress_cb(pct, 100, tr("progress_ovlp_lowres"))
        active = tile_active.get(tkey, set())
        if not active:
            continue
        tx, ty = tkey
        pairs, scands = _rasterize_tile(
            tris, shell_to_idx, idx_to_shell, RES_LO, tx, ty,
            include_self, active)
        for sp, faces in pairs.items():
            lo_pairs[sp].update(faces)
        for sk, fps in scands.items():
            lo_self[sk].update(fps)
    # Collect hires candidate shells from Phase 2 results
    hires_shells = set()
    for (sa, sb) in lo_pairs:
        hires_shells.add(shell_to_idx[sa])
        hires_shells.add(shell_to_idx[sb])
    if include_self:
        for sk in lo_self:
            hires_shells.add(shell_to_idx[sk])
    _p2 = time.time() - _t0
    # --- Phase 3: Hi-res verify (candidate shells only) ---
    _t0 = time.time()
    overlap_shell_pairs = defaultdict(set)
    self_candidates = defaultdict(set)
    tile_count = 0
    for tkey, tris in tile_tris.items():
        tile_count += 1
        if cancel_check and cancel_check():
            return [], tr("cancelled")
        if progress_cb and total_tiles > 0:
            pct = 50 + int(tile_count * 40 / total_tiles)
            progress_cb(pct, 100, tr("progress_ovlp_hires"))
        active = tile_active.get(tkey, set())
        if not active:
            continue
        # Intersect with hires candidates from Phase 2
        hi_active = active & hires_shells
        if not hi_active:
            continue
        tx, ty = tkey
        pairs, scands = _rasterize_tile(
            tris, shell_to_idx, idx_to_shell, RES_HI, tx, ty,
            include_self, hi_active)
        for sp, faces in pairs.items():
            overlap_shell_pairs[sp].update(faces)
        for sk, fps in scands.items():
            self_candidates[sk].update(fps)
    _p3 = time.time() - _t0
    # --- Cache Phase 1-3 results for tolerance slider refilter ---
    global _overlap_cache
    _overlap_cache = {
        "raw_overlap_pairs": {k: set(v) for k, v in overlap_shell_pairs.items()},
        "all_shell_faces": all_shell_faces,
        "face_uvs": face_uvs,
        "include_self": include_self,
        "idx_to_shell": idx_to_shell,
        "shell_to_idx": shell_to_idx,
    }
    # --- A-1: Pre-compute self_face_uv (face -> UV ID set per shell) ---
    _cached_self_face_uv = defaultdict(lambda: defaultdict(set))
    if include_self and self_candidates:
        for tri in all_tris:
            skey = (tri[0], tri[2])
            if skey in self_candidates:
                _cached_self_face_uv[skey][tri[1]].update(tri[6])
    # --- A-2: Pre-compute self_filtered_pairs (adjacency-filtered) ---
    _cached_self_pairs = defaultdict(set)
    if include_self and self_candidates:
        for skey, pairs in self_candidates.items():
            mn = skey[0]; fuv = _cached_self_face_uv[skey]
            for fa, fb in pairs:
                if len(fuv.get(fa, set()) & fuv.get(fb, set())) < 2:
                    sp = (skey, skey)
                    _cached_self_pairs[sp].add((mn, fa))
                    _cached_self_pairs[sp].add((mn, fb))
    # --- A-3: Pre-compute shell_global_bbox ---
    _cached_global_bbox = {}
    for tkey, bb in tile_shell_bbox.items():
        for sidx, box in bb.items():
            skey = idx_to_shell[sidx]
            if skey in _cached_global_bbox:
                b = _cached_global_bbox[skey]
                if box[0] < b[0]: b[0] = box[0]
                if box[1] < b[1]: b[1] = box[1]
                if box[2] > b[2]: b[2] = box[2]
                if box[3] > b[3]: b[3] = box[3]
            else:
                _cached_global_bbox[skey] = list(box)
    _overlap_cache["self_face_uv"] = dict(_cached_self_face_uv)
    _overlap_cache["self_filtered_pairs"] = {k: set(v) for k, v in _cached_self_pairs.items()}
    _overlap_cache["shell_global_bbox"] = _cached_global_bbox
    # --- Phase 4: Intentional overlap filter + result ---
    # v1.7.1-dev: Pre-compute ALL pair distances (max_tol=1e-2) and cache.
    # Re-filtering by tolerance only uses _classify_by_tolerance (no _faces_match).
    # v1.7.2-dev: Self-overlap adjacency filter and shell_global_bbox pre-computed above.
    _t0 = time.time()
    _pair_data = _compute_pair_distances(
        dict(overlap_shell_pairs), all_shell_faces, face_uvs, 1e-2)
    _overlap_cache["pair_data"] = _pair_data
    overlap_shell_pairs, intentional_pairs, int_skip = _classify_by_tolerance(
        _pair_data, _FP_TOLERANCE)
    # Deep copy cached self pairs (modified in-place by merge)
    _self_pairs = {k: set(v) for k, v in _cached_self_pairs.items()}
    all_groups, summary = _build_overlap_results_from_cache(
        overlap_shell_pairs, intentional_pairs, _self_pairs,
        all_shell_faces, include_self, idx_to_shell, _cached_global_bbox)
    _p4 = time.time() - _t0
    _total = time.time() - _t0_total
    _profile = {
        "summary": "tris={0} | tiles={1} | res={2}/{3} | bbox_skip={4} | lo_pairs={5} | hi_pairs={6} | int_skip={7} | groups={8}".format(
            n_tris, total_tiles, RES_LO, RES_HI,
            bbox_skipped, len(lo_pairs), len(overlap_shell_pairs), int_skip,
            len(all_groups)),
        "phases": [
            {"name": "Index+BBox", "time": round(_p1, 2)},
            {"name": "LowRes", "time": round(_p2, 2)},
            {"name": "HiRes", "time": round(_p3, 2)},
            {"name": "Result", "time": round(_p4, 2)},
        ],
        "total": round(_total, 2)
    }
    return all_groups, summary, _profile
# --- [130] uv_range ---
# depends on: [000] header, [010] i18n, [020] utils
# =====================================================================
# v23 (pre-1.0): UV Range Check
# =====================================================================

def collect_range_data():
    """Collect per-face UV bounding boxes from selected meshes.

    Returns list of (mesh_name, face_idx, u_min, u_max, v_min, v_max)
    records, or None if no mesh selected.
    """
    dag_paths = get_selected_meshes()
    if not dag_paths: return None
    face_records = []
    for dag in dag_paths:
        mesh_fn = get_mesh_fn(dag); mesh_name = dag.fullPathName()
        num_uvs = mesh_fn.numUVs()
        if num_uvs == 0: continue
        us, vs = mesh_fn.getUVs()
        uv_counts, uv_ids = mesh_fn.getAssignedUVs()
        uv_offset = 0
        for face_idx in range(mesh_fn.numPolygons):
            count = uv_counts[face_idx]
            if count < 3: uv_offset += count; continue
            face_us = [float(us[uv_ids[uv_offset + k]]) for k in range(count)]
            face_vs = [float(vs[uv_ids[uv_offset + k]]) for k in range(count)]
            face_records.append((mesh_name, face_idx, min(face_us), max(face_us),
                                 min(face_vs), max(face_vs)))
            uv_offset += count
    return face_records

def _face_crosses_tile(u_min, u_max, v_min, v_max):
    eps = _UV_BOUNDARY_EPS
    u_lo = int(math.floor(u_min + eps)); u_hi = int(math.floor(u_max - eps))
    if u_hi > u_lo: return True
    v_lo = int(math.floor(v_min + eps)); v_hi = int(math.floor(v_max - eps))
    if v_hi > v_lo: return True
    return False

def compute_range_check(face_records, check_crossing, check_outside,
                        valid_u_min, valid_u_max, valid_v_min, valid_v_max,
                        progress_cb=None, cancel_check=None):
    """Check faces for UDIM tile boundary crossing and out-of-range UVs.

    Returns (errors, summary_string). Errors include crossing and
    outside violations based on the valid tile range.
    """
    if not face_records: return [], tr("range_result", cross=0, outside=0)
    _t0_total = time.time()
    crossing_errors = []; outside_errors = []
    total = len(face_records); report_interval = max(1, total // 50)
    for idx, rec in enumerate(face_records):
        if cancel_check and cancel_check(): return [], tr("cancelled")
        if progress_cb and idx % report_interval == 0:
            progress_cb(idx, total, tr("progress_range", current=idx, total=total))
        mesh_name, face_idx, u_min, u_max, v_min, v_max = rec
        if check_crossing and _face_crosses_tile(u_min, u_max, v_min, v_max):
            short_name = mesh_name.rsplit("|", 1)[-1]
            crossing_errors.append({"component": "{0}.f[{1}]".format(mesh_name, face_idx),
                "label": "{0}.f[{1}] (crossing)".format(short_name, face_idx),
                "type": "range_crossing", "mesh": mesh_name, "face": face_idx})
        if check_outside:
            eps = _UV_BOUNDARY_EPS
            tile_u = int(math.floor(u_min + eps)); tile_v = int(math.floor(v_min + eps))
            tile_u2 = int(math.floor(u_max - eps)); tile_v2 = int(math.floor(v_max - eps))
            if (tile_u < valid_u_min or tile_u > valid_u_max or
                tile_v < valid_v_min or tile_v > valid_v_max) and \
               (tile_u2 < valid_u_min or tile_u2 > valid_u_max or
                tile_v2 < valid_v_min or tile_v2 > valid_v_max):
                short_name = mesh_name.rsplit("|", 1)[-1]
                outside_errors.append({"component": "{0}.f[{1}]".format(mesh_name, face_idx),
                    "label": "{0}.f[{1}] (outside)".format(short_name, face_idx),
                    "type": "range_outside", "mesh": mesh_name, "face": face_idx})
    # --- Profile ---
    _elapsed = time.time() - _t0_total
    _profile = {
        "summary": "faces={0} | crossing={1} | outside={2}".format(
            total, len(crossing_errors), len(outside_errors)),
        "phases": [{"name": "Check", "time": round(_elapsed, 2)}],
        "total": round(_elapsed, 2)
    }
    return crossing_errors + outside_errors, tr("range_result", cross=len(crossing_errors), outside=len(outside_errors)), _profile
# --- [140] texel_density ---
# depends on: [000] header, [010] i18n, [020] utils (_triangle_area_2d, _triangle_area_3d, get_selected_meshes, get_mesh_fn)
# =====================================================================
# v24 (pre-1.0): Texel Density Check
# v51 (pre-1.0): 3-mode check + statistics summary + color-coded results
# v52 (pre-1.0): td_values in stats + all_entries for histogram refilter
# v56 (pre-1.0): Unified mode — measure-only, filtering moved to result window
# =====================================================================

_td_last_stats = {}

def collect_texel_density_data(res_x, res_y):
    """Collect per-face UV and world-space area data for texel density.

    Returns list of (mesh_name, face_idx, shell_id, uv_area, world_area, fids)
    records, or None if no mesh selected.
    """
    dag_paths = get_selected_meshes()
    if not dag_paths: return None
    face_records = []
    for dag in dag_paths:
        mesh_fn = get_mesh_fn(dag); mesh_name = dag.fullPathName()
        num_uvs = mesh_fn.numUVs()
        if num_uvs == 0: continue
        us, vs = mesh_fn.getUVs()
        points = mesh_fn.getPoints(om2.MSpace.kWorld)
        uv_counts, uv_ids = mesh_fn.getAssignedUVs()
        shell_map = mesh_fn.getUvShellsIds()[1]
        uv_offset = 0
        for face_idx in range(mesh_fn.numPolygons):
            count = uv_counts[face_idx]
            if count < 3: uv_offset += count; continue
            fids = [uv_ids[uv_offset + k] for k in range(count)]
            verts = mesh_fn.getPolygonVertices(face_idx)
            shell_id = shell_map[fids[0]]
            uv_area = 0.0; u0px = float(us[fids[0]]) * res_x; v0px = float(vs[fids[0]]) * res_y
            for k in range(1, count - 1):
                uv_area += _triangle_area_2d(u0px, v0px,
                    float(us[fids[k]]) * res_x, float(vs[fids[k]]) * res_y,
                    float(us[fids[k + 1]]) * res_x, float(vs[fids[k + 1]]) * res_y)
            world_area = 0.0; p0 = points[verts[0]]
            for k in range(1, len(verts) - 1):
                p1 = points[verts[k]]; p2 = points[verts[k + 1]]
                world_area += _triangle_area_3d(p0.x, p0.y, p0.z, p1.x, p1.y, p1.z, p2.x, p2.y, p2.z)
            face_records.append((mesh_name, face_idx, shell_id, uv_area, world_area, fids))
            uv_offset += count
    return face_records

def _compute_td_stats(shell_data):
    """Compute texel density statistics across all shells."""
    total_uv = 0.0; total_world = 0.0; td_values = []
    for key in shell_data:
        uv_sum, world_sum, _ = shell_data[key]
        if world_sum < 1e-12: continue
        td = math.sqrt(uv_sum / world_sum)
        td_values.append(td)
        total_uv += uv_sum; total_world += world_sum
    if not td_values:
        return {"weighted_avg": 0.0, "median": 0.0, "min": 0.0, "max": 0.0, "td_values": []}
    weighted_avg = math.sqrt(total_uv / total_world) if total_world > 1e-12 else 0.0
    td_sorted = sorted(td_values)
    n = len(td_sorted)
    median = td_sorted[n // 2] if n % 2 == 1 else (td_sorted[n // 2 - 1] + td_sorted[n // 2]) / 2.0
    return {"weighted_avg": round(weighted_avg, 4), "median": round(median, 4),
            "min": round(td_sorted[0], 4), "max": round(td_sorted[-1], 4), "td_values": td_values}

def _build_shell_data(face_records):
    """Build shell_data dict from face_records."""
    shell_data = {}
    for rec in face_records:
        mesh_name, face_idx, shell_id, uv_area, world_area = rec[:5]
        key = (mesh_name, shell_id)
        if key not in shell_data: shell_data[key] = [0.0, 0.0, []]
        shell_data[key][0] += uv_area; shell_data[key][1] += world_area
        shell_data[key][2].append(face_idx)
    return shell_data

def compute_texel_density(face_records, by_shell,
                          progress_cb=None, cancel_check=None):
    """Measure texel density for all shells/faces. No error filtering.

    v56: Unified mode. Returns (all_entries, summary_string).
    Stats are stored in module-level _td_last_stats.
    Filtering is performed interactively in TexelDensityResultsWindow.
    """
    global _td_last_stats
    if not face_records:
        _td_last_stats = {}
        return [], tr("texel_result", count=0)
    _t0_total = time.time()
    all_entries = []
    shell_data = _build_shell_data(face_records)
    stats = _compute_td_stats(shell_data)
    # Default threshold density for initial Min filter
    stats["threshold_density"] = round(
        stats["weighted_avg"] * (_TD_DEFAULT_THRESHOLD_PCT / 100.0), 4)
    if by_shell:
        shell_keys = list(shell_data.keys()); total_shells = len(shell_keys)
        for si, key in enumerate(shell_keys):
            if cancel_check and cancel_check():
                _td_last_stats = stats; return [], tr("cancelled")
            if progress_cb:
                progress_cb(si, total_shells,
                            tr("progress_texel", current=si + 1, total=total_shells))
            mesh_name, shell_id = key; uv_sum, world_sum, faces = shell_data[key]
            if world_sum < 1e-12: continue
            td = math.sqrt(uv_sum / world_sum)
            short_mesh = mesh_name.rsplit("|", 1)[-1]
            entry = {"component": "{0} Shell {1} \u2014 TD: {2}".format(
                        short_mesh, shell_id, round(td, 2)),
                "distance": round(td, 2), "type": "texel_density",
                "mesh": mesh_name, "shell_a": shell_id,
                "shell_faces_a": faces, "td_value": td}
            all_entries.append(entry)
        all_entries.sort(key=lambda e: e["td_value"])
        _elapsed = time.time() - _t0_total
        _profile = {
            "summary": "shells={0}".format(total_shells),
            "phases": [{"name": "Measure", "time": round(_elapsed, 2)}],
            "total": round(_elapsed, 2)
        }
    else:
        total = len(face_records); report_interval = max(1, total // 50)
        for idx, rec in enumerate(face_records):
            if cancel_check and cancel_check():
                _td_last_stats = stats; return [], tr("cancelled")
            if progress_cb and idx % report_interval == 0:
                progress_cb(idx, total,
                            tr("progress_texel", current=idx, total=total))
            mesh_name, face_idx, shell_id, uv_area, world_area, fids = rec
            if world_area < 1e-12: continue
            td = math.sqrt(uv_area / world_area)
            short_mesh = mesh_name.rsplit("|", 1)[-1]
            entry = {"component": "{0}.f[{1}]".format(mesh_name, face_idx),
                "label": "{0}.f[{1}] \u2014 TD: {2}".format(
                    short_mesh, face_idx, round(td, 2)),
                "type": "texel_density_face",
                "mesh": mesh_name, "face": face_idx, "td_value": td,
                "face_uvs": fids}
            all_entries.append(entry)
        all_entries.sort(key=lambda e: e["td_value"])
        _elapsed = time.time() - _t0_total
        _profile = {
            "summary": "faces={0}".format(total),
            "phases": [{"name": "Measure", "time": round(_elapsed, 2)}],
            "total": round(_elapsed, 2)
        }
    _td_last_stats = stats
    _td_last_stats["all_entries"] = all_entries
    return all_entries, tr("texel_result", count=len(all_entries)), _profile
# --- [150] uvset_check ---
# depends on: [000] header, [010] i18n, [020] utils

# --- v29 (pre-1.0): UVSet Check ---
# v31 (pre-1.0): Lists ALL UVSets (including default map1) for selection.
# Clicking a result switches the current UVSet in the UV Editor.
# Intentionally does NOT provide delete functionality
# to prevent accidental removal of needed UVSets.
# v37 (pre-1.0): Group by UVSet name across all meshes instead of per-mesh listing.
# Clicking a result selects all meshes that have the UVSet and switches it.

def collect_all_uvsets():
    """Collect all UVSets from selected meshes, grouped by UVSet name.

    Returns list of grouped entry dicts, None if no mesh selected,
    or empty list if no UVSets found.
    Each entry includes a 'meshes' list and 'is_default' flag.
    """
    meshes = _get_selected_mesh_transforms()
    if not meshes:
        return None
    # Collect per-mesh UVSets and group by name
    uvset_meshes = {}
    for mesh in meshes:
        uvsets = cmds.polyUVSet(
            mesh, query=True, allUVSets=True) or []
        for uvset in uvsets:
            if uvset not in uvset_meshes:
                uvset_meshes[uvset] = []
            uvset_meshes[uvset].append(mesh)
    # Build grouped entries
    total_meshes = len(meshes)
    entries = []
    for uvset in sorted(uvset_meshes.keys()):
        mesh_list = uvset_meshes[uvset]
        is_default = (uvset == "map1")
        marker = (" " + tr("uvset_default_marker")
                  if is_default else "")
        count_str = tr("uvset_mesh_count",
                       count=len(mesh_list),
                       total=total_meshes)
        entries.append({
            "type": "uvset_entry",
            "mesh": mesh_list[0],
            "meshes": mesh_list,
            "component": uvset,
            "uvset_name": uvset,
            "is_default": is_default,
            "label": "{0}{1} \u2014 {2}".format(
                uvset, marker, count_str),
        })
    return entries
# --- [160] uv_orientation ---
# depends on: [000] header, [010] i18n, [020] utils

def collect_orientation_data(meshes):
    """Collect UV/vertex data for orientation check (main thread only).

    Args:
        meshes: list of MDagPath objects from get_selected_meshes()

    Returns:
        list of dicts with keys: mesh (str), num_shells, shell_face_data, shell_faces
        shell_face_data[sid] = list of (v0,v1,v2, u0,v0uv, u1,v1uv, u2,v2uv, nx,ny,nz)
    """
    mesh_data_list = []
    for dag in meshes:
        try:
            fn_mesh = om2.MFnMesh(dag)
        except Exception:
            continue

        try:
            num_uvs = fn_mesh.numUVs()
        except Exception:
            continue
        if num_uvs < 3:
            continue

        try:
            uv_shell_ids, num_shells = fn_mesh.getUvShellsIds()
        except Exception:
            continue
        if isinstance(uv_shell_ids, int):
            uv_shell_ids, num_shells = num_shells, uv_shell_ids

        try:
            mesh_name = dag.fullPathName()
        except Exception:
            continue

        shell_face_data = defaultdict(list)
        shell_faces = defaultdict(set)

        try:
            num_polys = fn_mesh.numPolygons
        except Exception:
            continue

        for fi in range(num_polys):
            try:
                poly_verts = fn_mesh.getPolygonVertices(fi)
            except Exception:
                continue
            nv = len(poly_verts)
            if nv < 3:
                continue

            # Gather UV IDs for this face to determine shell
            uv_ids = []
            for lv in range(nv):
                try:
                    uv_ids.append(fn_mesh.getPolygonUVid(fi, lv))
                except Exception:
                    uv_ids.append(-1)
            if any(uid < 0 or uid >= len(uv_shell_ids) for uid in uv_ids):
                continue
            sid = uv_shell_ids[uv_ids[0]]
            shell_faces[sid].add(fi)

            # Get face normal (world space)
            try:
                normal = fn_mesh.getPolygonNormal(fi, om2.MSpace.kWorld)
                nx, ny, nz = normal.x, normal.y, normal.z
            except Exception:
                continue

            # Triangulate the polygon into (nv-2) triangles
            for tri in range(nv - 2):
                idx0, idx1, idx2 = 0, tri + 1, tri + 2
                try:
                    p0 = fn_mesh.getPoint(poly_verts[idx0], om2.MSpace.kWorld)
                    p1 = fn_mesh.getPoint(poly_verts[idx1], om2.MSpace.kWorld)
                    p2 = fn_mesh.getPoint(poly_verts[idx2], om2.MSpace.kWorld)
                    u0, v0uv = fn_mesh.getPolygonUV(fi, idx0)
                    u1, v1uv = fn_mesh.getPolygonUV(fi, idx1)
                    u2, v2uv = fn_mesh.getPolygonUV(fi, idx2)
                except Exception:
                    continue
                shell_face_data[sid].append((
                    p0.x, p0.y, p0.z,
                    p1.x, p1.y, p1.z,
                    p2.x, p2.y, p2.z,
                    u0, v0uv, u1, v1uv, u2, v2uv,
                    nx, ny, nz))

        mesh_data_list.append({
            "mesh": mesh_name,
            "num_shells": num_shells,
            "shell_face_data": dict(shell_face_data),
            "shell_faces": dict((k, sorted(v)) for k, v in shell_faces.items()),
        })
    return mesh_data_list


def compute_uv_orientation(mesh_data_list, progress_cb=None, cancel_check=None):
    """Compute UV orientation from pre-collected mesh data.

    Algorithm:
      1. Area-weighted average normal per shell -> representative normal N
      2. Determine 3D ref_up from N:
         - abs(N.y) > _ORIENT_HORIZONTAL_THRESHOLD (horizontal face):
           N.y > 0 -> ref_up = (0,0,-1); N.y < 0 -> ref_up = (0,0,+1)
         - else (vertical face): ref_up = (0,+1,0)
      3. Project ref_up to UV space via area-weighted Jacobian -> uv_up
         Compute cos(θ) = uv_up_v / |uv_up| for angle-based classification
      4. Check flip via Jacobian determinant sign (area-weighted)

    Classifications:
      normal (cos(θ) > 0.7071), rotated (otherwise), indeterminate
      Plus flipped boolean flag (Jacobian determinant < 0)

    Args:
        mesh_data_list: list of dicts from collect_orientation_data()
        progress_cb: callback(current, total, label)
        cancel_check: callable returning True if cancelled

    Returns:
        (list, str, dict) -- (results, summary_message, profile)
    """
    results = []
    total_meshes = len(mesh_data_list)
    _t0_total = time.time()

    for mi, md in enumerate(mesh_data_list):
        if cancel_check and cancel_check():
            return results, tr("cancelled"), {}
        if progress_cb:
            progress_cb(mi, total_meshes,
                        tr("progress_orientation", current=mi + 1, total=total_meshes))

        mesh = md["mesh"]
        num_shells = md["num_shells"]
        shell_face_data = md["shell_face_data"]
        shell_faces = md["shell_faces"]

        for sid in range(num_shells):
            if cancel_check and cancel_check():
                return results, tr("cancelled"), {}

            tri_data = shell_face_data.get(sid, [])
            face_list = shell_faces.get(sid, [])

            if len(tri_data) < 1:
                results.append(_make_orient_result(
                    mesh, sid, "indeterminate", 0.0, face_list, {}))
                continue

            # Step 1: Area-weighted average normal
            sum_nx, sum_ny, sum_nz = 0.0, 0.0, 0.0
            total_area = 0.0
            # Step 4 prep: area-weighted Jacobian determinant sum
            sum_det = 0.0
            sum_abs_det = 0.0
            # Step 3 prep: area-weighted Jacobian columns sum
            # Jacobian: dU/d3D, dV/d3D  (2x3 matrix)
            # We accumulate J^T * area for projection
            sum_j00, sum_j01, sum_j02 = 0.0, 0.0, 0.0  # dU/dx, dU/dy, dU/dz
            sum_j10, sum_j11, sum_j12 = 0.0, 0.0, 0.0  # dV/dx, dV/dy, dV/dz

            for tri in tri_data:
                (p0x, p0y, p0z, p1x, p1y, p1z, p2x, p2y, p2z,
                 u0, v0, u1, v1, u2, v2, nx, ny, nz) = tri

                # 3D edge vectors
                e1x, e1y, e1z = p1x - p0x, p1y - p0y, p1z - p0z
                e2x, e2y, e2z = p2x - p0x, p2y - p0y, p2z - p0z

                # Triangle area (3D)
                cx = e1y * e2z - e1z * e2y
                cy = e1z * e2x - e1x * e2z
                cz = e1x * e2y - e1y * e2x
                area = 0.5 * math.sqrt(cx * cx + cy * cy + cz * cz)
                if area < 1e-12:
                    continue

                total_area += area
                sum_nx += nx * area
                sum_ny += ny * area
                sum_nz += nz * area

                # UV edge vectors
                du1, dv1 = u1 - u0, v1 - v0
                du2, dv2 = u2 - u0, v2 - v0

                # UV-space signed area (determinant of UV triangle)
                uv_det = du1 * dv2 - du2 * dv1
                sum_det += uv_det  # note: not area-weighted, uses UV area directly
                sum_abs_det += abs(uv_det)

                # Jacobian: maps 3D edge vectors to UV edge vectors
                # Using pseudo-inverse approach for the triangle
                # [du1 dv1] = J * [e1]
                # [du2 dv2] = J * [e2]
                # J = [du dv]^T * [e1 e2]^(-T)  (for the 2D->3D mapping)
                # For area-weighting, we accumulate per-triangle contribution
                inv_det_3d = 1.0 / (2.0 * area * area) if area > 1e-12 else 0.0
                # Gram matrix inverse components (e1,e2 dot products)
                g11 = e1x * e1x + e1y * e1y + e1z * e1z
                g12 = e1x * e2x + e1y * e2y + e1z * e2z
                g22 = e2x * e2x + e2y * e2y + e2z * e2z
                det_g = g11 * g22 - g12 * g12
                if abs(det_g) < 1e-18:
                    continue
                inv_g = 1.0 / det_g
                # Inverse Gram: [[g22, -g12], [-g12, g11]] / det_g
                # Jacobian row for U: (du1 * g22 - du2 * g12) * inv_g * e1 + (-du1 * g12 + du2 * g11) * inv_g * e2
                a_u = (du1 * g22 - du2 * g12) * inv_g
                b_u = (-du1 * g12 + du2 * g11) * inv_g
                a_v = (dv1 * g22 - dv2 * g12) * inv_g
                b_v = (-dv1 * g12 + dv2 * g11) * inv_g

                j_u_x = a_u * e1x + b_u * e2x
                j_u_y = a_u * e1y + b_u * e2y
                j_u_z = a_u * e1z + b_u * e2z
                j_v_x = a_v * e1x + b_v * e2x
                j_v_y = a_v * e1y + b_v * e2y
                j_v_z = a_v * e1z + b_v * e2z

                sum_j00 += j_u_x * area
                sum_j01 += j_u_y * area
                sum_j02 += j_u_z * area
                sum_j10 += j_v_x * area
                sum_j11 += j_v_y * area
                sum_j12 += j_v_z * area

            if total_area < 1e-12:
                results.append(_make_orient_result(
                    mesh, sid, "indeterminate", 0.0, face_list, {}))
                continue

            # Normalize weighted normal
            inv_a = 1.0 / total_area
            avg_nx, avg_ny, avg_nz = sum_nx * inv_a, sum_ny * inv_a, sum_nz * inv_a
            n_len = math.sqrt(avg_nx * avg_nx + avg_ny * avg_ny + avg_nz * avg_nz)
            if n_len < 1e-9:
                results.append(_make_orient_result(
                    mesh, sid, "indeterminate", 0.0, face_list, {}))
                continue
            avg_nx /= n_len
            avg_ny /= n_len
            avg_nz /= n_len

            # Step 2: Determine ref_up
            if abs(avg_ny) > _ORIENT_HORIZONTAL_THRESHOLD:
                # Horizontal face
                if avg_ny > 0:
                    ref_up = (0.0, 0.0, -1.0)  # front-facing up -> back is UV up
                else:
                    ref_up = (0.0, 0.0, 1.0)
            else:
                # Vertical face
                ref_up = (0.0, 1.0, 0.0)  # world Y up

            # Step 3: Project ref_up through averaged Jacobian -> uv_up
            # Averaged Jacobian (area-weighted)
            j_u = (sum_j00 * inv_a, sum_j01 * inv_a, sum_j02 * inv_a)
            j_v = (sum_j10 * inv_a, sum_j11 * inv_a, sum_j12 * inv_a)

            # uv_up = J * ref_up
            uv_up_u = j_u[0] * ref_up[0] + j_u[1] * ref_up[1] + j_u[2] * ref_up[2]
            uv_up_v = j_v[0] * ref_up[0] + j_v[1] * ref_up[1] + j_v[2] * ref_up[2]

            uv_up_len = math.sqrt(uv_up_u * uv_up_u + uv_up_v * uv_up_v)
            if uv_up_len < 1e-9:
                results.append(_make_orient_result(
                    mesh, sid, "indeterminate", 0.0, face_list, {}))
                continue

            # Step 4: Flip check via determinant
            is_flipped = (sum_det < 0)

            # Classification: angle-based (cos(θ) = uv_up_v / |uv_up|)
            cos_theta = uv_up_v / uv_up_len
            if cos_theta > 0.7071:
                cls = "normal"
            else:
                cls = "rotated"

            # Confidence: single-pass metrics from accumulated data
            # normal_consistency: magnitude of area-weighted average normal (1.0 = perfectly aligned)
            # flip_consistency: ratio of net determinant to total absolute determinant
            normal_consistency = n_len  # already computed above
            if sum_abs_det > 1e-12:
                flip_consistency = abs(sum_det) / sum_abs_det
            else:
                flip_consistency = 0.0
            conf = min(1.0, max(0.0, min(normal_consistency, flip_consistency)))

            scores = {
                "avg_normal": (round(avg_nx, 4), round(avg_ny, 4), round(avg_nz, 4)),
                "ref_up": ref_up,
                "uv_up": (round(uv_up_u, 4), round(uv_up_v, 4)),
                "cos_theta": round(cos_theta, 4),
                "sum_det": round(sum_det, 6),
            }
            results.append(_make_orient_result(
                mesh, sid, cls, round(conf, 3), face_list, scores, is_flipped))

    n_total = len(results)
    n_normal = sum(1 for r in results if r["classification"] == "normal")
    msg = tr("orientation_result", total=n_total, issues=n_total - n_normal)
    _elapsed = time.time() - _t0_total
    _profile = {
        "summary": "meshes={0}, shells={1}".format(total_meshes, n_total),
        "phases": [{"name": "Measure", "time": round(_elapsed, 2)}],
        "total": round(_elapsed, 2)
    }
    return results, msg, _profile


def _make_orient_result(mesh, shell_id, classification, confidence, face_list, scores, flipped=False):
    """Build a single orientation result dict."""
    return {
        "mesh": mesh,
        "shell_id": shell_id,
        "classification": classification,
        "flipped": flipped,
        "confidence": confidence,
        "faces": ["{0}.f[{1}]".format(mesh, f) for f in face_list],
        "scores": scores,
        "type": "uv_orientation",
    }
# --- [200] mat_separator ---
# depends on: [000] header, [010] i18n, [020] utils
# =====================================================================
# v29 (pre-1.0): Material Separator Core (integrated from Material Separator v4)
#   - Group selection now duplicates meshes before combining
#     (originals are never modified)
# =====================================================================

_MS_NAMING_PATTERNS = ["{mesh}_{mat}", "{mat}", "{mat}_{idx:03d}"]

def _ms_check_single_material():
    """Return (base_name, meshes, needs_separate).
    needs_separate is True if any mesh has more than 1 SG,
    or if multiple meshes share the same material."""
    base_name, meshes = _ms_get_selected_meshes()
    if not meshes:
        return base_name, meshes, False
    seen_sgs = set()
    for mesh in meshes:
        sg_faces = _ms_get_sg_face_map(mesh)
        if len(sg_faces) > 1:
            return base_name, meshes, True
        for sg in sg_faces:
            if sg in seen_sgs:
                return base_name, meshes, True
            seen_sgs.add(sg)
    return base_name, meshes, False
def _ms_get_selected_meshes():
    meshes = _get_selected_mesh_transforms()
    sel = cmds.ls(sl=True, long=True, type="transform") or []
    if sel: base_name = sel[0].split("|")[-1]
    elif meshes: base_name = meshes[0].split("|")[-1]
    else: base_name = ""
    return base_name, meshes

def _ms_get_material_name(shading_group):
    connections = cmds.listConnections(shading_group + ".surfaceShader") or []
    if connections: return connections[0]
    return shading_group

def _ms_get_sg_face_map(mesh_transform):
    shapes = cmds.listRelatives(mesh_transform, shapes=True, type="mesh", fullPath=True) or []
    if not shapes: return {}
    sel = om2.MSelectionList(); sel.add(shapes[0])
    dag_path = sel.getDagPath(0)
    fn_mesh = om2.MFnMesh(dag_path)
    sg_objs, face_sg_ids = fn_mesh.getConnectedShaders(dag_path.instanceNumber())
    if not sg_objs: return {}
    sg_names = [om2.MFnDependencyNode(sg_obj).name() for sg_obj in sg_objs]
    sg_faces = {}
    for face_id, sg_idx in enumerate(face_sg_ids):
        sg_name = sg_names[sg_idx]
        sg_faces.setdefault(sg_name, []).append(face_id)
    return sg_faces

def _ms_ids_to_range(mesh_name, face_ids):
    if not face_ids: return []
    components = []; sorted_ids = sorted(face_ids)
    start = end = sorted_ids[0]
    for i in range(1, len(sorted_ids)):
        if sorted_ids[i] == end + 1: end = sorted_ids[i]
        else:
            if start == end: components.append("{0}.f[{1}]".format(mesh_name, start))
            else: components.append("{0}.f[{1}:{2}]".format(mesh_name, start, end))
            start = end = sorted_ids[i]
    if start == end: components.append("{0}.f[{1}]".format(mesh_name, start))
    else: components.append("{0}.f[{1}:{2}]".format(mesh_name, start, end))
    return components

def _ms_run_separate(merge_uv=True, delete_history_combine=True,
                     naming_index=0, do_group=True, group_name="",
                     freeze_tf=True, delete_history_separate=True,
                     progress_cb=None, cancel_check=None):
    base_name, meshes = _ms_get_selected_meshes()
    if not meshes:
        cmds.warning(tr("mat_sep_no_mesh"))
        return None
    cmds.undoInfo(openChunk=True, chunkName="MaterialSeparator")
    cancelled = False
    try:
        if progress_cb: progress_cb(0, 0, tr("mat_sep_progress_combine"))
        if len(meshes) > 1:
            # v41: duplicate meshes into temp group to avoid leftover transforms
            dup_meshes = [cmds.duplicate(m)[0] for m in meshes]
            dup_grp = cmds.group(dup_meshes, name="_ms_temp_grp")
            grp_children = cmds.listRelatives(dup_grp, children=True, fullPath=True, type="transform") or []
            combined = cmds.polyUnite(*grp_children, ch=(not delete_history_combine),
                mergeUVSets=merge_uv, name=base_name + "_combined")
            combined_mesh = combined[0]
            if delete_history_combine:
                cmds.delete(combined_mesh, constructionHistory=True)
            if cmds.objExists(dup_grp):
                cmds.delete(dup_grp)
        else:
            combined_mesh = cmds.duplicate(meshes[0], name=base_name + "_combined")[0]
            if delete_history_combine:
                cmds.delete(combined_mesh, constructionHistory=True)
        if progress_cb: progress_cb(0, 0, tr("mat_sep_progress_analyze"))
        sg_faces = _ms_get_sg_face_map(combined_mesh)
        if not sg_faces:
            cmds.warning(tr("mat_sep_no_sg"))
            if cmds.objExists(combined_mesh): cmds.delete(combined_mesh)
            cmds.undoInfo(closeChunk=True)
            return None
        mat_names = [_ms_get_material_name(sg) for sg in sg_faces]
        pattern = _MS_NAMING_PATTERNS[naming_index]
        created_meshes = []
        num_total_faces = cmds.polyEvaluate(combined_mesh, face=True)
        num_sgs = len(sg_faces)
        for idx, (sg, face_ids) in enumerate(sg_faces.items()):
            if cancel_check and cancel_check():
                cancelled = True; break
            if progress_cb:
                progress_cb(idx, num_sgs, tr("mat_sep_progress_separate", current=idx + 1, total=num_sgs))
            mat_name = _ms_get_material_name(sg)
            new_name = pattern.format(mesh=base_name, mat=mat_name, idx=idx)
            # v31: Ensure unique name to avoid collision on re-run
            if cmds.objExists(new_name):
                suffix = 1
                while cmds.objExists("{0}_{1:03d}".format(new_name, suffix)):
                    suffix += 1
                new_name = "{0}_{1:03d}".format(new_name, suffix)
            dup = cmds.duplicate(combined_mesh, name=new_name)[0]
            keep_set = set(face_ids)
            delete_ids = [i for i in range(num_total_faces) if i not in keep_set]
            if delete_ids:
                del_components = _ms_ids_to_range(dup, delete_ids)
                cmds.delete(del_components)
            dup_shapes = cmds.listRelatives(dup, shapes=True, type="mesh") or []
            if dup_shapes: cmds.sets(dup_shapes[0], edit=True, forceElement=sg)
            if delete_history_separate: cmds.delete(dup, constructionHistory=True)
            if freeze_tf: cmds.makeIdentity(dup, apply=True, translate=True, rotate=True, scale=True)
            created_meshes.append(dup)
        if progress_cb: progress_cb(num_sgs, num_sgs, tr("mat_sep_progress_cleanup"))
        if cmds.objExists(combined_mesh): cmds.delete(combined_mesh)
        grp_result = ""
        if do_group and created_meshes:
            grp_name = group_name if group_name else (base_name + "_separated")
            grp_result = cmds.group(created_meshes, name=grp_name)
        cmds.select(created_meshes)
        return {"cancelled": cancelled, "mat_count": num_sgs, "mat_names": mat_names,
                "mesh_count": len(created_meshes), "group": grp_result}
    except Exception as e:
        print("[ERROR] {0}".format(e))
        cmds.warning("MaterialSeparator: {0}".format(e))
    finally:
        cmds.undoInfo(closeChunk=True)
# --- [800] ui ---
# depends on: [000] header, [010] i18n, [011] help_content, [020] utils, [100]-[150], [200]
# ~1.7.6-dev: Remove drag-time summary update (_refilter_summary_only, _debounce)
# ~1.7.7-dev: Add histogram margin (_plot_lo/_plot_hi), re-add drag summary (_update_drag_summary)
# ~1.7.8-dev: Log10 histogram scale, _val_to_x bin positioning, pair-based drag summary
# ~1.7.9-dev: Remove _plot_lo/_plot_hi margin, use bin_edges range (TD-style bar movement)
# ~1.7.10-dev: Initial threshold = bin_edges[0] (leftmost, strictest)
# ~1.7.11-dev: Remove Default btn, vertical summary, gray legend, drag hint

# --- Help Dialog ---
class HelpDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(HelpDialog, self).__init__(parent)
        self.setWindowTitle(tr("help_title")); self.setMinimumSize(520, 480)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.Tool)
        self.setObjectName(HELP_DIALOG_OBJECT_NAME)
        layout = QtWidgets.QVBoxLayout(self)
        self._browser = QtWidgets.QTextBrowser()
        self._browser.setOpenExternalLinks(False); self._browser.setReadOnly(True)
        self._browser.setStyleSheet("font-size: 14px;")
        self._update_content(); layout.addWidget(self._browser)
        btn_close = QtWidgets.QPushButton(tr("close"))
        btn_close.clicked.connect(self.close); layout.addWidget(btn_close)
    def _update_content(self):
        _css = "<style>p,ul,ol{margin:4px 0;}hr{margin:6px 0;}h2{margin:8px 0 4px;}h3{margin:8px 0 4px;}</style>"
        self._browser.setHtml(_css + tr("help_overview")
            + tr("help_section_prep") + tr("help_uvset_check") + tr("help_mat_sep")
            + tr("help_tex_size")
            + tr("help_section_check") + tr("help_pixel_edge")
            + tr("help_uv_padding") + tr("help_uv_range")
            + tr("help_uv_overlap") + tr("help_texel_density")
            + tr("help_orientation")
            + tr("help_results")
            + tr("help_report"))
    def refresh_lang(self):
        self.setWindowTitle(tr("help_title")); self._update_content()

# --- Material Separator Settings Dialog ---
class MaterialSepSettingsDialog(QtWidgets.QDialog):
    def __init__(self, settings=None, parent=None):
        super(MaterialSepSettingsDialog, self).__init__(parent)
        self.setWindowTitle(tr("mat_sep_settings_title"))
        self.setMinimumWidth(320)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.Tool)
        s = settings or {}
        layout = QtWidgets.QVBoxLayout(self)
        grp_c = QtWidgets.QGroupBox(tr("mat_sep_combine_opts"))
        cl = QtWidgets.QVBoxLayout(grp_c); cl.setSpacing(4); cl.setContentsMargins(8,8,8,8)
        self.chk_merge_uv = QtWidgets.QCheckBox(tr("mat_sep_merge_uv"))
        self.chk_merge_uv.setChecked(s.get("merge_uv", True)); cl.addWidget(self.chk_merge_uv)
        self.chk_del_hist_c = QtWidgets.QCheckBox(tr("mat_sep_del_hist"))
        self.chk_del_hist_c.setChecked(s.get("del_hist_combine", True)); cl.addWidget(self.chk_del_hist_c)
        layout.addWidget(grp_c)
        grp_s = QtWidgets.QGroupBox(tr("mat_sep_separate_opts"))
        sl = QtWidgets.QVBoxLayout(grp_s); sl.setSpacing(4); sl.setContentsMargins(8,8,8,8)
        nr = QtWidgets.QHBoxLayout()
        nr.addWidget(QtWidgets.QLabel(tr("mat_sep_naming")))
        self.combo_naming = QtWidgets.QComboBox()
        self.combo_naming.addItems([tr("mat_sep_naming_mesh_mat"), tr("mat_sep_naming_mat"), tr("mat_sep_naming_mat_idx")])
        self.combo_naming.setCurrentIndex(s.get("naming_index", 0))
        nr.addWidget(self.combo_naming); nr.addStretch(); sl.addLayout(nr)
        self.chk_group = QtWidgets.QCheckBox(tr("mat_sep_grouping"))
        self.chk_group.setChecked(s.get("do_group", True)); sl.addWidget(self.chk_group)
        gnr = QtWidgets.QHBoxLayout()
        gnr.addWidget(QtWidgets.QLabel(tr("mat_sep_group_name")))
        self.txt_grp_name = QtWidgets.QLineEdit(s.get("group_name", ""))
        gnr.addWidget(self.txt_grp_name); sl.addLayout(gnr)
        self.chk_freeze = QtWidgets.QCheckBox(tr("mat_sep_freeze_tf"))
        self.chk_freeze.setChecked(s.get("freeze_tf", True)); sl.addWidget(self.chk_freeze)
        self.chk_del_hist_s = QtWidgets.QCheckBox(tr("mat_sep_del_hist"))
        self.chk_del_hist_s.setChecked(s.get("del_hist_separate", True)); sl.addWidget(self.chk_del_hist_s)
        layout.addWidget(grp_s)
        btn_row = QtWidgets.QHBoxLayout()
        btn_ok = QtWidgets.QPushButton("OK"); btn_ok.clicked.connect(self.accept)
        btn_cancel = QtWidgets.QPushButton(tr("close")); btn_cancel.clicked.connect(self.reject)
        btn_row.addStretch(); btn_row.addWidget(btn_ok); btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)
    def get_settings(self):
        return {"merge_uv": self.chk_merge_uv.isChecked(),
            "del_hist_combine": self.chk_del_hist_c.isChecked(),
            "naming_index": self.combo_naming.currentIndex(),
            "do_group": self.chk_group.isChecked(),
            "group_name": self.txt_grp_name.text(),
            "freeze_tf": self.chk_freeze.isChecked(),
            "del_hist_separate": self.chk_del_hist_s.isChecked()}

# --- Base Results Dialog ---
class _BaseResultsDialog(QtWidgets.QDialog):
    """Common base for all QC result dialog windows."""
    def _get_selection_widget(self):
        """Return the main selection widget. Subclasses must override."""
        raise NotImplementedError
    def _deselect_all(self):
        """Clear selection in both the widget and Maya viewport."""
        self._get_selection_widget().clearSelection()
        cmds.select(clear=True)
    def _build_button_row(self, layout, select_all_cb, extra_buttons=None):
        """Build standard button row: Select All | Deselect All | [extra...] | Close."""
        bl = QtWidgets.QHBoxLayout()
        bsa = QtWidgets.QPushButton(tr("select_all"))
        bsa.clicked.connect(select_all_cb)
        bl.addWidget(bsa)
        bda = QtWidgets.QPushButton(tr("deselect_all"))
        bda.clicked.connect(self._deselect_all)
        bl.addWidget(bda)
        if extra_buttons:
            for btn in extra_buttons:
                bl.addWidget(btn)
        bcl = QtWidgets.QPushButton(tr("close"))
        bcl.clicked.connect(self.close)
        bl.addWidget(bcl)
        layout.addLayout(bl)

# --- Pixel Edge Results Window ---
class PixelEdgeResultsWindow(_BaseResultsDialog):
    def __init__(self, title, errors, res_x, res_y, groups=None, parent=None):
        super(PixelEdgeResultsWindow, self).__init__(parent)
        self.setWindowTitle("QC Results \u2014 {0}".format(title)); self.setMinimumSize(540, 420)
        self.raw_errors = errors; self.res_x = res_x; self.res_y = res_y
        self.groups = groups if groups is not None else _group_edge_errors(errors, res_x, res_y)
        self.setObjectName(PIXEL_EDGE_RESULTS_OBJECT_NAME)
        layout = QtWidgets.QVBoxLayout(self)
        summary = QtWidgets.QLabel(tr("group_count", gcount=len(self.groups), ecount=len(errors)))
        summary.setStyleSheet("font-size: 13px; font-weight: bold; padding: 4px;"); layout.addWidget(summary)
        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.setStyleSheet("font-size: 12px; QListWidget::item { padding: 3px 2px; }")
        self.list_widget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        dl = {"horizontal": tr("edge_horizontal"), "vertical": tr("edge_vertical")}
        for i, grp in enumerate(self.groups):
            eids = grp["edge_ids"]
            es = "e[{0}]".format(eids[0]) if len(eids) == 1 else "e[{0}..{1}] ({2})".format(eids[0], eids[-1], len(eids))
            ms = grp["mesh"].rsplit("|", 1)[-1]
            item = QtWidgets.QListWidgetItem("{0} {1}  [{2}]  {3}px".format(ms, es, dl.get(grp['direction'],''), grp['max_distance']))
            item.setSizeHint(QtCore.QSize(-1, 26))
            self.list_widget.addItem(item)
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.list_widget)
        bn = QtWidgets.QPushButton(tr("btn_snap_selected")); bn.clicked.connect(self._snap_selected)
        self._build_button_row(layout, self._select_all, extra_buttons=[bn])
    def _get_selection_widget(self):
        return self.list_widget
    def _on_selection_changed(self):
        rows = [idx.row() for idx in self.list_widget.selectedIndexes()]
        if not rows:
            cmds.select(clear=True)
            return
        sel = []
        for row in rows:
            if row < 0 or row >= len(self.groups): continue
            grp = self.groups[row]
            sel.extend(["{0}.map[{1}]".format(grp['mesh'], uid) for uid in grp["uv_ids"]])
        if sel: cmds.select(sel, r=True)
    def _select_all(self):
        self.list_widget.blockSignals(True)
        self.list_widget.selectAll()
        self.list_widget.blockSignals(False)
        sel = []
        for grp in self.groups: sel.extend(["{0}.map[{1}]".format(grp['mesh'], uid) for uid in grp["uv_ids"]])
        if sel: cmds.select(sel, r=True)
    def _snap_selected(self):
        rows = [idx.row() for idx in self.list_widget.selectedIndexes()]
        sg = [self.groups[i] for i in rows if 0 <= i < len(self.groups)]
        if not sg: QtWidgets.QMessageBox.information(self, tr("pixel_edge"), tr("snap_none")); return
        si = [{"mesh": g["mesh"], "direction": g["direction"], "uv_data": g["uv_data"], "endpoint_uv_ids": g.get("endpoint_uv_ids", set())} for g in sg]
        count = snap_selected_edges(si, self.res_x, self.res_y)
        QtWidgets.QMessageBox.information(self, tr("pixel_edge"),
            tr("snap_result", count=count) if count > 0 else tr("snap_none"))

# --- Resolution Picker Dialog (v48, pre-1.0) ---
class ResolutionPickerDialog(QtWidgets.QDialog):
    """Dialog for selecting texture resolution when multiple resolutions are detected."""
    def __init__(self, res_to_textures, parent=None):
        super(ResolutionPickerDialog, self).__init__(parent)
        self.setWindowTitle(tr("detect_mixed_title"))
        self.setMinimumWidth(360)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.Tool)
        self._res_to_textures = res_to_textures
        self._sorted_res = sorted(res_to_textures.keys(),
                                   key=lambda r: r[0] * r[1], reverse=True)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel(tr("detect_mixed_msg")))
        self._combo = QtWidgets.QComboBox()
        for rx, ry in self._sorted_res:
            textures = res_to_textures[(rx, ry)]
            res_label = "{0} x {0}".format(rx) if rx == ry else "{0} x {1}".format(rx, ry)
            if len(textures) == 1:
                label = "{0} \u2014 {1}".format(res_label, textures[0])
            else:
                label = "{0} \u2014 {1} +{2}".format(
                    res_label, textures[0], len(textures) - 1)
            self._combo.addItem(label)
        self._combo.currentIndexChanged.connect(self._update_info)
        layout.addWidget(self._combo)
        self._info_label = QtWidgets.QLabel()
        self._info_label.setStyleSheet(
            "color: #888; font-size: 11px; padding: 4px 8px;")
        self._info_label.setWordWrap(True)
        layout.addWidget(self._info_label)
        self._update_info(0)
        btn_row = QtWidgets.QHBoxLayout()
        btn_ok = QtWidgets.QPushButton("OK")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QtWidgets.QPushButton(tr("close"))
        btn_cancel.clicked.connect(self.reject)
        btn_row.addStretch()
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)
        self.selected_resolution = self._sorted_res[0]
    def _update_info(self, index):
        if index < 0 or index >= len(self._sorted_res): return
        res = self._sorted_res[index]
        textures = self._res_to_textures[res]
        self._info_label.setText("\n".join(textures))
        self.selected_resolution = res

# --- Results Window ---
class ResultsWindow(_BaseResultsDialog):
    def __init__(self, title, errors, parent=None):
        super(ResultsWindow, self).__init__(parent)
        self.setWindowTitle("QC Results \u2014 {0}".format(title))
        self.setMinimumSize(500, 350); self.errors = errors
        self.setObjectName(RESULTS_OBJECT_NAME)
        layout = QtWidgets.QVBoxLayout(self)
        # v31: Use uvset_list_count for UVSet entries, error_count for others
        if errors and errors[0].get("type") == "uvset_entry":
            summary = QtWidgets.QLabel(tr("uvset_list_count", count=len(errors)))
        else:
            summary = QtWidgets.QLabel(tr("error_count", count=len(errors)))
        summary.setStyleSheet("font-size: 13px; font-weight: bold; padding: 4px;"); layout.addWidget(summary)
        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.setStyleSheet("font-size: 12px;")
        self.list_widget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        for err in errors:
            if err["type"] == "uv_overlap": it = "{0}".format(err['component'])
            elif err["type"] in ("range_crossing", "range_outside", "texel_density_face"): it = err.get("label", err["component"])
            elif err["type"] == "texel_density": it = err["component"]
            elif err["type"] in ("extra_uvset", "uvset_entry"): it = err["label"]
            else: it = "{0}  \u2014  {1} px".format(err['component'], err['distance'])
            self.list_widget.addItem(it)
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed); layout.addWidget(self.list_widget)
        self._build_button_row(layout, self._select_all)
    def _get_selection_widget(self):
        return self.list_widget
    @staticmethod
    def _collect_selection(errors):
        """Collect Maya selection components from error entries."""
        sel = []
        for err in errors:
            mesh = err["mesh"]; mb = err.get("mesh_b", mesh)
            if err["type"] == "shell_distance":
                sel.extend(["{0}.map[{1}]".format(mesh, i) for i in err.get("shell_uvs_a", [])])
                sel.extend(["{0}.map[{1}]".format(mb, i) for i in err.get("shell_uvs_b", [])])
            elif err["type"] == "tile_distance":
                sel.extend(["{0}.map[{1}]".format(mesh, i) for i in err.get("shell_uvs_a", [])])
            elif err["type"] == "uv_overlap":
                sel.extend(["{0}.f[{1}]".format(mesh, f) for f in err.get("shell_faces_a", [])])
                sel.extend(["{0}.f[{1}]".format(mb, f) for f in err.get("shell_faces_b", [])])
            elif err["type"] == "texel_density":
                sel.extend(["{0}.f[{1}]".format(mesh, f) for f in err.get("shell_faces_a", [])])
            elif err["type"] == "texel_density_face":
                sel.append(err["component"])
            elif err["type"] in ("extra_uvset", "uvset_entry"):
                sel.extend(err.get("meshes", [err["mesh"]]))
            else:
                sel.append(err["component"])
        return sel
    def _on_selection_changed(self):
        rows = [idx.row() for idx in self.list_widget.selectedIndexes()]
        if not rows:
            cmds.select(clear=True)
            return
        selected = [self.errors[r] for r in rows if 0 <= r < len(self.errors)]
        sel = self._collect_selection(selected)
        for err in selected:
            if err["type"] == "uvset_entry":
                for m in err.get("meshes", [err["mesh"]]):
                    cmds.polyUVSet(m, currentUVSet=True, uvSet=err["uvset_name"])
        if sel: cmds.select(sel, r=True)
    def _select_all(self):
        self.list_widget.blockSignals(True)
        self.list_widget.selectAll()
        self.list_widget.blockSignals(False)
        sel = self._collect_selection(self.errors)
        if sel: cmds.select(sel, r=True)

# --- v1.7.0-dev: Overlap Tolerance Slider (log-scale) ---
# --- v1.7.1-dev: Semantic labels, presets, debounce, histogram ---
_OVLP_PRESET_DEFAULT = 3e-4


# --- v1.7.1-dev: Overlap Distance Histogram Widget ---
class _OverlapDistanceHistogram(QtWidgets.QWidget):
    """Histogram of per-pair minimum face-match distances.
    X-axis: distance, Y-axis: shell pair count.
    Draggable threshold line synced with tolerance slider."""
    thresholdDragging = QtCore.Signal(float)   # emitted during drag
    thresholdChanged = QtCore.Signal(float)     # emitted on release only
    _NUM_BINS = 30
    _PAD = 6
    def __init__(self, parent=None):
        super(_OverlapDistanceHistogram, self).__init__(parent)
        self._distances = []
        self._bins = []; self._bin_edges = []; self._max_count = 1
        self._threshold = _OVLP_PRESET_DEFAULT
        self._dragging = False
        self.setMinimumHeight(60); self.setMinimumWidth(200)
    def set_data(self, distances, threshold):
        """Update histogram data. distances: list of per-pair min distances."""
        self._distances = sorted(distances) if distances else []
        self._threshold = threshold
        self._build_histogram()
        self.update()
    def set_threshold(self, val):
        self._threshold = val; self.update()
    def _build_histogram(self):
        if not self._distances:
            self._bins = []; self._bin_edges = []; return
        lo = self._distances[0]; hi = self._distances[-1]
        if hi - lo < 1e-8: hi = lo + 1e-4
        # ~1.7.8-dev: log10 scale for bin edges (distances ~1e-5 to ~1e-2)
        log_lo = math.log10(max(lo, 1e-7))
        log_hi = math.log10(max(hi, 1e-7))
        if log_hi - log_lo < 1e-6: log_hi = log_lo + 1.0
        log_step = (log_hi - log_lo) / self._NUM_BINS
        self._bin_edges = [10 ** (log_lo + i * log_step) for i in range(self._NUM_BINS + 1)]
        self._bins = [0] * self._NUM_BINS
        for v in self._distances:
            if v <= 0: v = 1e-7
            log_v = math.log10(v)
            idx = int((log_v - log_lo) / log_step)
            if idx >= self._NUM_BINS: idx = self._NUM_BINS - 1
            if idx < 0: idx = 0
            self._bins[idx] += 1
        self._max_count = max(self._bins) if self._bins else 1
    def _val_to_x(self, val):
        if not self._bin_edges: return self._PAD
        # ~1.7.9-dev: log10 coordinate mapping (bin_edges range, TD-style)
        lo = math.log10(max(self._bin_edges[0], 1e-7))
        hi = math.log10(max(self._bin_edges[-1], 1e-7))
        if hi - lo < 1e-6: return self._PAD
        usable = self.width() - 2 * self._PAD
        log_val = math.log10(max(val, 1e-7))
        return int(self._PAD + (log_val - lo) / (hi - lo) * max(1, usable))
    def _x_to_val(self, x):
        if not self._bin_edges: return 0.0
        # ~1.7.9-dev: log10 coordinate mapping (bin_edges range, TD-style)
        lo = math.log10(max(self._bin_edges[0], 1e-7))
        hi = math.log10(max(self._bin_edges[-1], 1e-7))
        usable = max(1, self.width() - 2 * self._PAD)
        log_val = lo + (float(x - self._PAD) / usable) * (hi - lo)
        return 10 ** log_val
    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        w = self.width(); h = self.height()
        p.fillRect(0, 0, w, h, QtGui.QColor("#2a2a2a"))
        if self._bins and self._max_count > 0:
            # ~1.7.8-dev: position bins using _val_to_x (log-scale aware, TD-style)
            for i, count in enumerate(self._bins):
                if count == 0: continue
                bar_h = max(2, int(float(count) / self._max_count * (h - 20)))
                x = self._val_to_x(self._bin_edges[i])
                x2 = self._val_to_x(self._bin_edges[i + 1]) if i + 1 < len(self._bin_edges) else w - self._PAD
                bw = max(1, x2 - x - 1)
                bc = self._bin_edges[i + 1] if i + 1 < len(self._bin_edges) else self._bin_edges[-1]
                bm = (self._bin_edges[i] + bc) / 2.0
                if bm < self._threshold:
                    clr = QtGui.QColor(120, 180, 120, 200)  # green = intentional zone
                else:
                    clr = QtGui.QColor(200, 100, 80, 200)  # red = error zone
                p.fillRect(int(x), h - bar_h - 2, bw, bar_h, clr)
        # Threshold line
        tx = max(6, min(self._val_to_x(self._threshold), w - 7))
        _lc = QtGui.QColor("#ddd")
        pen = QtGui.QPen(_lc, 2)
        p.setPen(pen); p.drawLine(tx, 10, tx, h)
        p.setBrush(_lc); p.setPen(QtCore.Qt.NoPen)
        tri = QtGui.QPolygon([QtCore.QPoint(tx - 4, 0), QtCore.QPoint(tx + 4, 0), QtCore.QPoint(tx, 10)])
        p.drawPolygon(tri)
        # ~1.7.11-dev: Drag hint (top-right, subtle)
        p.setPen(QtGui.QColor(180, 180, 180, 120))
        p.setFont(QtGui.QFont("sans-serif", 8))
        _hint = tr("ovlp_hist_drag_hint")
        _hw = p.fontMetrics().boundingRect(_hint).width()
        p.drawText(w - _hw - 6, 10, _hint)
        p.end()
    def enterEvent(self, event): self.setCursor(QtCore.Qt.SizeHorCursor)
    def leaveEvent(self, event): self.unsetCursor()
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._dragging = True; self.grabMouse(); self._update_from_x(event.x())
    def mouseMoveEvent(self, event):
        if self._dragging: self._update_from_x(event.x())
    def mouseReleaseEvent(self, event):
        if self._dragging:
            self.releaseMouse(); self._dragging = False
            self.thresholdChanged.emit(self._threshold)
    def _update_from_x(self, x):
        val = self._x_to_val(x)
        if self._bin_edges:
            val = max(self._bin_edges[0], min(val, self._bin_edges[-1]))
        val = max(1e-7, min(1e-2, val))
        self._threshold = val; self.update()
        self.thresholdDragging.emit(val)

# --- Overlap Results Window (v50, pre-1.0 -> ~1.6.0-dev: 3-tier group display) ---
class OverlapResultsWindow(_BaseResultsDialog):
    """Results window with 3-tier grouped display for UV overlap results.
    Category -> Group -> Individual Shell."""
    def __init__(self, title, groups, parent=None):
        super(OverlapResultsWindow, self).__init__(parent)
        self.setWindowTitle("QC Results \u2014 {0}".format(title))
        self.setMinimumSize(540, 520)
        self.setObjectName(OVERLAP_RESULTS_OBJECT_NAME)
        self._groups = groups
        self._error_groups = [g for g in groups if not g.get("intentional", False)]
        self._int_groups = [g for g in groups if g.get("intentional", False)]
        n_err_shells = sum(len(g["shell_keys"]) for g in self._error_groups)
        n_int_shells = sum(len(g["shell_keys"]) for g in self._int_groups)
        layout = QtWidgets.QVBoxLayout(self)
        # ~1.7.11-dev: Vertical summary (TD-style)
        _summary_grp = QtWidgets.QGroupBox(tr("ovlp_summary_header"))
        _summary_grp.setStyleSheet("QGroupBox { font-weight: bold; }")
        _sg = QtWidgets.QVBoxLayout(_summary_grp)
        _sg.setContentsMargins(8, 4, 8, 4); _sg.setSpacing(2)
        self._lbl_err_groups = QtWidgets.QLabel(tr("ovlp_stat_err_groups", val=len(self._error_groups)))
        self._lbl_err_shells = QtWidgets.QLabel(tr("ovlp_stat_err_shells", val=n_err_shells))
        self._lbl_int_groups = QtWidgets.QLabel(tr("ovlp_stat_int_groups", val=len(self._int_groups)))
        self._lbl_int_shells = QtWidgets.QLabel(tr("ovlp_stat_int_shells", val=n_int_shells))
        for _lbl in [self._lbl_err_groups, self._lbl_err_shells, self._lbl_int_groups, self._lbl_int_shells]:
            _sg.addWidget(_lbl)
        layout.addWidget(_summary_grp)
        # --- v1.7.4-dev: Histogram + legend (TD-style layout) ---
        self._ovlp_hist = _OverlapDistanceHistogram(self)
        self._ovlp_hist.thresholdDragging.connect(self._on_hist_dragging)
        self._ovlp_hist.thresholdChanged.connect(self._on_hist_released)
        self._ovlp_hist.setVisible(bool(_overlap_cache))
        layout.addWidget(self._ovlp_hist)
        # Legend row: strict (left, red) / loose (right, green)
        _legend = QtWidgets.QHBoxLayout(); _legend.setContentsMargins(0,0,0,0)
        _lbl_s = QtWidgets.QLabel()
        _lbl_s.setTextFormat(QtCore.Qt.RichText)
        _lbl_s.setText("<span style='color:#888;font-size:11px;'>{0}</span>".format(
            tr("ovlp_hist_legend_strict").replace("<", "&lt;").replace(">", "&gt;")))
        _legend.addWidget(_lbl_s)
        _legend.addStretch()
        _lbl_l = QtWidgets.QLabel()
        _lbl_l.setTextFormat(QtCore.Qt.RichText)
        _lbl_l.setText("<span style='color:#888;font-size:11px;'>{0}</span>".format(
            tr("ovlp_hist_legend_loose").replace("<", "&lt;").replace(">", "&gt;")))
        _legend.addWidget(_lbl_l)
        layout.addLayout(_legend)
        # --- Filter panel ---
        _flt_grp = QtWidgets.QGroupBox(tr("ovlp_filter_header"))
        _fl = QtWidgets.QVBoxLayout(_flt_grp); _fl.setSpacing(4); _fl.setContentsMargins(8, 6, 8, 6)
        # Dynamic description label
        self._lbl_desc = QtWidgets.QLabel(tr("ovlp_tol_desc_default"))
        self._lbl_desc.setStyleSheet("font-size: 10px; color: #888; padding-left: 4px;")
        _fl.addWidget(self._lbl_desc)
        # ~1.7.11-dev: Default button removed (initial=strictest, user relaxes by drag)
        # Internal tolerance state (replaces SpinBox)
        self._current_tolerance = _OVLP_PRESET_DEFAULT
        self._update_histogram()
        # ~1.7.10-dev: Initial threshold = leftmost bin edge (strictest)
        if self._ovlp_hist._bin_edges:
            self._current_tolerance = self._ovlp_hist._bin_edges[0]
            self._ovlp_hist.set_threshold(self._current_tolerance)
            self._update_desc(self._current_tolerance)
        layout.addWidget(_flt_grp)
        # --- Tree ---
        self._tree = QtWidgets.QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setStyleSheet("font-size: 12px;")
        self._tree.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self._tree.itemSelectionChanged.connect(self._on_selection_changed)
        self._tree.itemExpanded.connect(self._on_group_expanded)
        self._rebuild_tree()
        layout.addWidget(self._tree)
        # --- Buttons ---
        self._build_button_row(layout, self._select_all_errors)
    def _get_selection_widget(self):
        return self._tree
    def _add_group_node(self, parent_item, grp, idx):
        """Add a group node with lazy-loaded children."""
        gnode = QtWidgets.QTreeWidgetItem(parent_item)
        gnode.setText(0, tr("ovlp_group_label", idx=idx,
                            count=len(grp["shell_keys"]),
                            udim=grp["udim_tile"]))
        gnode.setData(0, QtCore.Qt.UserRole,
                      {"type": "group", "group": grp, "populated": False})
        _fg = gnode.font(0); _fg.setBold(True); gnode.setFont(0, _fg)
        # Dummy child for expand arrow visibility
        _dummy = QtWidgets.QTreeWidgetItem(gnode)
        _dummy.setData(0, QtCore.Qt.UserRole, {"type": "dummy"})
        gnode.setExpanded(False)
        return gnode
    def _on_group_expanded(self, item):
        """Lazily populate group children on first expand."""
        data = item.data(0, QtCore.Qt.UserRole)
        if data is None or data.get("type") != "group":
            return
        if data.get("populated"):
            return
        item.takeChildren()
        grp = data["group"]
        self._populate_group_children(item, grp)
        data["populated"] = True
        item.setData(0, QtCore.Qt.UserRole, data)
    def _populate_group_children(self, gnode, grp):
        """Create shell child nodes for a group."""
        is_int = grp.get("intentional", False)
        for mesh_name, shell_id in grp["shell_keys"]:
            child = QtWidgets.QTreeWidgetItem(gnode)
            short = mesh_name.rsplit("|", 1)[-1]
            face_set = set()
            for e in grp["errors"]:
                if e["mesh"] == mesh_name and e["shell_a"] == shell_id:
                    for f in e.get("shell_faces_a", []):
                        face_set.add(f)
                mb = e.get("mesh_b", e["mesh"])
                if mb == mesh_name and e["shell_b"] == shell_id:
                    for f in e.get("shell_faces_b", []):
                        face_set.add(f)
            n_faces = len(face_set)
            child.setText(0, tr("ovlp_shell_label", mesh=short,
                               sid=shell_id, faces=n_faces))
            child.setData(0, QtCore.Qt.UserRole, {
                "type": "shell", "mesh": mesh_name, "shell_id": shell_id,
                "group": grp})
            if is_int:
                child.setForeground(0, QtGui.QColor("#888"))
    @staticmethod
    def _collect_overlap_selection(items):
        """Collect Maya face selection components from tree items."""
        sel = set()
        for item in items:
            data = item.data(0, QtCore.Qt.UserRole)
            if data is None:
                continue
            if data["type"] == "group":
                grp = data["group"]
                for mn, fi in grp["faces"]:
                    sel.add("{0}.f[{1}]".format(mn, fi))
            elif data["type"] == "shell":
                mesh = data["mesh"]; sid = data["shell_id"]
                grp = data["group"]
                for e in grp["errors"]:
                    if e["mesh"] == mesh and e["shell_a"] == sid:
                        for f in e.get("shell_faces_a", []):
                            sel.add("{0}.f[{1}]".format(mesh, f))
                    mb = e.get("mesh_b", e["mesh"])
                    if mb == mesh and e["shell_b"] == sid:
                        for f in e.get("shell_faces_b", []):
                            sel.add("{0}.f[{1}]".format(mb, f))
        return list(sel)
    def _on_selection_changed(self):
        items = self._tree.selectedItems()
        if not items:
            cmds.select(clear=True)
            return
        sel = self._collect_overlap_selection(items)
        if sel:
            cmds.select(sel, r=True)
    def _select_all_errors(self):
        self._tree.blockSignals(True)
        self._tree.clearSelection()
        if hasattr(self, '_cat_err'):
            for i in range(self._cat_err.childCount()):
                self._cat_err.child(i).setSelected(True)
        self._tree.blockSignals(False)
        sel = []
        for grp in self._error_groups:
            for mn, fi in grp["faces"]:
                sel.append("{0}.f[{1}]".format(mn, fi))
        if sel:
            cmds.select(sel, r=True)
    def _rebuild_tree(self):
        """Rebuild the tree widget from current _groups data."""
        self._tree.clear()
        if self._error_groups:
            self._cat_err = QtWidgets.QTreeWidgetItem(self._tree)
            self._cat_err.setText(0, tr("ovlp_group_error", count=len(self._error_groups)))
            self._cat_err.setFlags(self._cat_err.flags() & ~QtCore.Qt.ItemIsSelectable)
            _fe = self._cat_err.font(0); _fe.setBold(True); self._cat_err.setFont(0, _fe)
            for i, grp in enumerate(self._error_groups):
                self._add_group_node(self._cat_err, grp, i + 1)
            self._cat_err.setExpanded(True)
        else:
            _ni = QtWidgets.QTreeWidgetItem(self._tree)
            _ni.setText(0, tr("ovlp_no_unintentional"))
            _ni.setFlags(_ni.flags() & ~QtCore.Qt.ItemIsSelectable)
            _fn = _ni.font(0); _fn.setBold(True); _ni.setFont(0, _fn)
            _ni.setForeground(0, QtGui.QColor("#4a4"))
        if self._int_groups:
            self._cat_int = QtWidgets.QTreeWidgetItem(self._tree)
            self._cat_int.setText(0, tr("ovlp_group_intentional", count=len(self._int_groups)))
            self._cat_int.setFlags(self._cat_int.flags() & ~QtCore.Qt.ItemIsSelectable)
            _fi = self._cat_int.font(0); _fi.setBold(True); self._cat_int.setFont(0, _fi)
            self._cat_int.setForeground(0, QtGui.QColor("#888"))
            for i, grp in enumerate(self._int_groups):
                gnode = self._add_group_node(self._cat_int, grp, i + 1)
                gnode.setForeground(0, QtGui.QColor("#888"))
            self._cat_int.setExpanded(False)
    def _update_histogram(self):
        """Extract per-pair min distances from cached pair_data and populate histogram."""
        pd = _overlap_cache.get("pair_data", {})
        distances = []
        for sp_key, data in pd.items():
            if sp_key[0] == sp_key[1]:
                continue  # self-overlap pair — skip
            if data["all_matches"]:
                distances.append(data["all_matches"][0][0])  # min distance per pair
            elif not data.get("is_boundary_adjacent", False):
                distances.append(1e-2)  # no face match — error zone
        if distances:
            self._ovlp_hist.set_data(distances, self._current_tolerance)
            self._ovlp_hist.setVisible(True)
        else:
            self._ovlp_hist.setVisible(False)
    def _tolerance(self):
        """Return current tolerance value."""
        return max(1e-4, min(1e-2, self._current_tolerance))
    def _update_desc(self, val):
        """Update dynamic description based on current tolerance value."""
        if val <= 1.5e-4:
            self._lbl_desc.setText(tr("ovlp_tol_desc_strict"))
        elif val >= 1.5e-3:
            self._lbl_desc.setText(tr("ovlp_tol_desc_loose"))
        else:
            self._lbl_desc.setText(tr("ovlp_tol_desc_default"))
    def _on_hist_dragging(self, val):
        """Histogram threshold being dragged — update tolerance + drag summary."""
        self._current_tolerance = val
        self._update_desc(val)
        self._update_drag_summary(val)
    def _update_drag_summary(self, tolerance):
        """Lightweight pair count update during drag (no Union-Find).
        ~1.7.8-dev: Changed from shell count to pair count for
        better histogram-to-number correlation."""
        pd = _overlap_cache.get("pair_data", {})
        if not pd:
            return
        err_pairs = 0; int_pairs = 0
        for sp_key, data in pd.items():
            if sp_key[0] == sp_key[1]:
                continue
            if not data["all_matches"] and data.get("is_boundary_adjacent", False):
                continue
            min_dist = data["all_matches"][0][0] if data["all_matches"] else float('inf')
            if min_dist < tolerance:
                int_pairs += 1
            else:
                err_pairs += 1
        self._lbl_err_groups.setText(tr("ovlp_stat_err_pairs", val=err_pairs))
        self._lbl_err_shells.setText("")
        self._lbl_int_groups.setText(tr("ovlp_stat_int_pairs", val=int_pairs))
        self._lbl_int_shells.setText("")
    def _on_hist_released(self, val):
        """Histogram threshold drag finished — full rebuild."""
        self._current_tolerance = val
        self._update_desc(val)
        self._refilter_full()
    def _refilter_full(self):
        """Full refilter: run Phase 4 + rebuild tree."""
        if not _overlap_cache:
            return
        tolerance = self._tolerance()
        groups, summary_txt, profile = _run_phase4(tolerance, _overlap_cache)
        self._groups = groups
        self._error_groups = [g for g in groups if not g.get("intentional", False)]
        self._int_groups = [g for g in groups if g.get("intentional", False)]
        n_err_shells = sum(len(g["shell_keys"]) for g in self._error_groups)
        n_int_shells = sum(len(g["shell_keys"]) for g in self._int_groups)
        self._lbl_err_groups.setText(tr("ovlp_stat_err_groups", val=len(self._error_groups)))
        self._lbl_err_shells.setText(tr("ovlp_stat_err_shells", val=n_err_shells))
        self._lbl_int_groups.setText(tr("ovlp_stat_int_groups", val=len(self._int_groups)))
        self._lbl_int_shells.setText(tr("ovlp_stat_int_shells", val=n_int_shells))
        self._tree.setUpdatesEnabled(False)
        self._rebuild_tree()
        self._tree.setUpdatesEnabled(True)
    def closeEvent(self, event):
        clear_overlap_cache()
        super(OverlapResultsWindow, self).closeEvent(event)

# --- Orientation Results Window ---
class OrientationResultsWindow(_BaseResultsDialog):
    """Results window for UV Orientation Check with 4-group classification display.
    Groups: Rotated -> Needs Review -> Indeterminate -> Normal
    Normal items with confidence < _ORIENT_CONFIDENCE_THRESHOLD are split into Needs Review."""
    _CLS_KEYS = {
        "normal": "orient_normal",
        "rotated": "orient_rotated",
        "needs_review": "orient_needs_review",
        "indeterminate": "orient_indeterminate",
    }
    _CLS_ORDER = ["rotated", "needs_review", "indeterminate", "normal"]

    def __init__(self, title, results, parent=None):
        super(OrientationResultsWindow, self).__init__(parent)
        self.setWindowTitle("QC Results \u2014 {0}".format(title))
        self.setMinimumSize(560, 420)
        self.setObjectName(ORIENTATION_RESULTS_OBJECT_NAME)
        self.results = results
        # Split normal results by confidence threshold into normal vs needs_review
        self._classified = []
        for r in results:
            cls = r["classification"]
            if cls == "normal" and r.get("confidence", 1.0) < _ORIENT_CONFIDENCE_THRESHOLD:
                rc = dict(r)
                rc["_display_cls"] = "needs_review"
                self._classified.append(rc)
            else:
                rc = dict(r)
                rc["_display_cls"] = cls
                self._classified.append(rc)
        self._non_normal = [r for r in self._classified if r["_display_cls"] != "normal"]
        layout = QtWidgets.QVBoxLayout(self)
        n_total = len(results)
        n_issues = len(self._non_normal)
        summary = QtWidgets.QLabel(
            tr("orientation_result", total=n_total, issues=n_issues))
        summary.setStyleSheet("font-size: 13px; font-weight: bold; padding: 4px;")
        layout.addWidget(summary)
        self._tree = QtWidgets.QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setStyleSheet("font-size: 12px;")
        self._tree.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        groups = defaultdict(list)
        for r in self._classified:
            groups[r["_display_cls"]].append(r)
        for cls in self._CLS_ORDER:
            items = groups.get(cls, [])
            if not items:
                continue
            grp = QtWidgets.QTreeWidgetItem(self._tree)
            cls_label = tr(self._CLS_KEYS.get(cls, "orient_indeterminate"))
            grp.setText(0, "{0} ({1})".format(cls_label, len(items)))
            grp.setFlags(grp.flags() & ~QtCore.Qt.ItemIsSelectable)
            _f = grp.font(0); _f.setBold(True); grp.setFont(0, _f)
            if cls == "normal":
                grp.setForeground(0, QtGui.QColor("#4a4"))
                grp.setExpanded(False)
            else:
                grp.setExpanded(True)
            for r in items:
                child = QtWidgets.QTreeWidgetItem(grp)
                ms = r["mesh"].rsplit("|", 1)[-1]
                _flipped_suffix = "  " + tr("orient_flipped_suffix") if r.get("flipped", False) else ""
                child.setText(0, "{0}  shell:{1}{2}".format(
                    ms, r["shell_id"], _flipped_suffix))
                child.setData(0, QtCore.Qt.UserRole, r)
        self._tree.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self._tree)
        self._build_button_row(layout, self._select_all_issues)

    def _get_selection_widget(self):
        return self._tree

    def _on_selection_changed(self):
        items = self._tree.selectedItems()
        if not items:
            cmds.select(clear=True)
            return
        sel = []
        for item in items:
            r = item.data(0, QtCore.Qt.UserRole)
            if r is not None:
                sel.extend(r.get("faces", []))
        if sel: cmds.select(sel, r=True)

    def _select_all_issues(self):
        self._tree.blockSignals(True)
        self._tree.clearSelection()
        for i in range(self._tree.topLevelItemCount()):
            grp = self._tree.topLevelItem(i)
            for j in range(grp.childCount()):
                child = grp.child(j)
                r = child.data(0, QtCore.Qt.UserRole)
                if r is not None and r.get("_display_cls") != "normal":
                    child.setSelected(True)
        self._tree.blockSignals(False)
        sel = []
        for r in self._non_normal:
            sel.extend(r.get("faces", []))
        if sel:
            cmds.select(sel, r=True)


# --- v56 (pre-1.0): TD Histogram Dual Slider Widget ---
class _TDHistogramDualSlider(QtWidgets.QWidget):
    """Histogram with two draggable threshold lines (min/max)."""
    minChanged = QtCore.Signal(float)
    maxChanged = QtCore.Signal(float)
    dragFinished = QtCore.Signal()
    _NUM_BINS = 40
    def __init__(self, td_values, init_min, init_max, min_enabled, max_enabled, parent=None):
        super(_TDHistogramDualSlider, self).__init__(parent)
        self._td_values = sorted(td_values) if td_values else []
        self._min_val = init_min; self._max_val = init_max
        self._min_enabled = min_enabled; self._max_enabled = max_enabled
        self._dragging = None  # None, 'min', or 'max'
        self.setMinimumHeight(70); self.setMinimumWidth(200)
        self._bins = []; self._bin_edges = []; self._max_count = 1
        self._build_histogram()
    def _build_histogram(self):
        if not self._td_values:
            self._bins = []; self._bin_edges = []; return
        lo = self._td_values[0]; hi = self._td_values[-1]
        if hi - lo < 1e-6: hi = lo + 1.0
        step = (hi - lo) / self._NUM_BINS
        self._bin_edges = [lo + i * step for i in range(self._NUM_BINS + 1)]
        self._bins = [0] * self._NUM_BINS
        for v in self._td_values:
            idx = int((v - lo) / step)
            if idx >= self._NUM_BINS: idx = self._NUM_BINS - 1
            if idx < 0: idx = 0
            self._bins[idx] += 1
        self._max_count = max(self._bins) if self._bins else 1
    _PAD = 6  # horizontal padding to match line clamp range
    def _val_to_x(self, val):
        if not self._bin_edges: return self._PAD
        lo = self._bin_edges[0]; hi = self._bin_edges[-1]
        if hi - lo < 1e-6: return self._PAD
        usable = self.width() - 2 * self._PAD
        return int(self._PAD + (val - lo) / (hi - lo) * max(1, usable))
    def _x_to_val(self, x):
        if not self._bin_edges: return 0.0
        lo = self._bin_edges[0]; hi = self._bin_edges[-1]
        usable = max(1, self.width() - 2 * self._PAD)
        return lo + (float(x - self._PAD) / usable) * (hi - lo)
    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        w = self.width(); h = self.height()
        p.fillRect(0, 0, w, h, QtGui.QColor("#2a2a2a"))
        if self._bins and self._max_count > 0:
            usable_w = w - 2 * self._PAD
            bar_w = max(1, float(usable_w) / self._NUM_BINS)
            for i, count in enumerate(self._bins):
                if count == 0: continue
                bar_h = max(2, int(float(count) / self._max_count * (h - 20)))
                x = int(self._PAD + i * bar_w)
                t = float(i) / max(1, self._NUM_BINS - 1)
                r_c, g_c, b_c = _td_heatmap_color(t)
                # Dim bars whose bin-center falls in error zone
                _bc = self._bin_edges[i + 1] if i + 1 < len(self._bin_edges) else self._bin_edges[-1]
                _bm = (self._bin_edges[i] + _bc) / 2.0
                _in_err = False
                if self._min_enabled and _bm < self._min_val: _in_err = True
                if self._max_enabled and _bm > self._max_val: _in_err = True
                _a = 100 if _in_err else 255
                p.fillRect(int(x), h - bar_h - 2, max(1, int(bar_w) - 1), bar_h, QtGui.QColor(r_c, g_c, b_c, _a))
        # Draw error-zone overlays (semi-transparent, use raw positions)
        if self._min_enabled:
            _mx_raw = self._val_to_x(self._min_val)
            if _mx_raw > 0:
                ov = QtGui.QColor(200, 60, 60, 45)
                p.fillRect(0, 12, _mx_raw, h - 12, ov)
        if self._max_enabled:
            _xx_raw = self._val_to_x(self._max_val)
            if _xx_raw < w - 1:
                ov = QtGui.QColor(60, 100, 200, 45)
                p.fillRect(_xx_raw, 12, w - _xx_raw, h - 12, ov)
        # Draw min/max lines (unified white, clamped to visible area)
        _line_color = QtGui.QColor("#ddd")
        if self._min_enabled:
            mx = max(6, min(self._val_to_x(self._min_val), w - 7))
            pen = QtGui.QPen(_line_color, 2)
            p.setPen(pen); p.drawLine(mx, 12, mx, h)
            p.setBrush(_line_color); p.setPen(QtCore.Qt.NoPen)
            tri = QtGui.QPolygon([QtCore.QPoint(mx - 5, 0), QtCore.QPoint(mx + 5, 0), QtCore.QPoint(mx, 12)])
            p.drawPolygon(tri)
            p.setPen(_line_color); p.setFont(QtGui.QFont("sans-serif", 8))
            lbl = "{0:.2f}".format(self._min_val)
            lbl_x = mx + 8 if mx < w - 60 else mx - 50
            p.drawText(lbl_x, 10, lbl)
        if self._max_enabled:
            xx = max(6, min(self._val_to_x(self._max_val), w - 7))
            pen = QtGui.QPen(_line_color, 2)
            p.setPen(pen); p.drawLine(xx, 12, xx, h)
            p.setBrush(_line_color); p.setPen(QtCore.Qt.NoPen)
            tri = QtGui.QPolygon([QtCore.QPoint(xx - 5, 0), QtCore.QPoint(xx + 5, 0), QtCore.QPoint(xx, 12)])
            p.drawPolygon(tri)
            p.setPen(_line_color); p.setFont(QtGui.QFont("sans-serif", 8))
            lbl = "{0:.2f}".format(self._max_val)
            lbl_x = xx + 8 if xx < w - 60 else xx - 50
            p.drawText(lbl_x, 10, lbl)
        # Drag hint (top-right, subtle)
        p.setPen(QtGui.QColor(180, 180, 180, 120))
        p.setFont(QtGui.QFont("sans-serif", 8))
        _hint = tr("td_hist_drag_hint")
        _hw = p.fontMetrics().boundingRect(_hint).width()
        p.drawText(w - _hw - 6, 10, _hint)
        p.end()
    def enterEvent(self, event): self.setCursor(QtCore.Qt.SizeHorCursor)
    def leaveEvent(self, event): self.unsetCursor()
    def mousePressEvent(self, event):
        if event.button() != QtCore.Qt.LeftButton: return
        x = event.x()
        # Determine which line is closer
        d_min = abs(x - self._val_to_x(self._min_val)) if self._min_enabled else 9999
        d_max = abs(x - self._val_to_x(self._max_val)) if self._max_enabled else 9999
        if d_min <= d_max and self._min_enabled:
            self._dragging = 'min'
        elif self._max_enabled:
            self._dragging = 'max'
        elif self._min_enabled:
            self._dragging = 'min'
        if self._dragging:
            self.grabMouse()
            self._update_from_x(x)
    def mouseMoveEvent(self, event):
        if self._dragging: self._update_from_x(event.x())
    def mouseReleaseEvent(self, event):
        if self._dragging:
            self.releaseMouse()
            self._dragging = None
            self.dragFinished.emit()
    def _update_from_x(self, x):
        val = self._x_to_val(x)
        if self._bin_edges:
            val = max(self._bin_edges[0], min(val, self._bin_edges[-1]))
        if self._dragging == 'min':
            if self._max_enabled: val = min(val, self._max_val)
            self._min_val = val; self.update(); self.minChanged.emit(val)
        elif self._dragging == 'max':
            if self._min_enabled: val = max(val, self._min_val)
            self._max_val = val; self.update(); self.maxChanged.emit(val)
    def set_min(self, val): self._min_val = val; self.update()
    def set_max(self, val): self._max_val = val; self.update()
    def set_min_enabled(self, on): self._min_enabled = on; self.update()
    def set_max_enabled(self, on): self._max_enabled = on; self.update()

# --- v56 (pre-1.0): Texel Density Results Window (unified) ---
class TexelDensityResultsWindow(_BaseResultsDialog):
    """Unified results window: stats + dual-slider histogram + filter panel + error list."""
    _INPUT_DIRECT = 0; _INPUT_TARGET = 1; _INPUT_THRESHOLD = 2
    def __init__(self, title, all_entries, stats, parent=None):
        super(TexelDensityResultsWindow, self).__init__(parent)
        self.setWindowTitle("QC Results \u2014 {0}".format(title))
        self.setMinimumSize(560, 520)
        self.setObjectName(TD_RESULTS_OBJECT_NAME)
        self._all_entries = all_entries; self._stats = stats
        self._min_source = self._INPUT_THRESHOLD  # default: threshold sets min
        self._block_signals = False
        self.errors = []
        layout = QtWidgets.QVBoxLayout(self)
        # --- Stats summary ---
        stats_grp = QtWidgets.QGroupBox(tr("td_stats_header"))
        stats_grp.setStyleSheet("QGroupBox { font-weight: bold; }")
        sg = QtWidgets.QVBoxLayout(stats_grp); sg.setSpacing(2); sg.setContentsMargins(8,4,8,4)
        sg.addWidget(QtWidgets.QLabel(tr("td_stats_weighted_avg", val=stats.get("weighted_avg", 0))))
        sg.addWidget(QtWidgets.QLabel(tr("td_stats_median", val=stats.get("median", 0))))
        sg.addWidget(QtWidgets.QLabel(tr("td_stats_min", val=stats.get("min", 0))))
        sg.addWidget(QtWidgets.QLabel(tr("td_stats_max", val=stats.get("max", 0))))
        layout.addWidget(stats_grp)
        # --- Histogram ---
        td_vals = [e["td_value"] for e in all_entries] if all_entries else []
        init_min = stats.get("threshold_density", 0.0)
        init_max = stats.get("max", 10.0)
        self._hist = _TDHistogramDualSlider(td_vals, init_min, init_max, True, False, self)
        self._hist.minChanged.connect(self._on_hist_min_changed)
        self._hist.maxChanged.connect(self._on_hist_max_changed)
        self._hist.dragFinished.connect(self._on_drag_finished)
        layout.addWidget(self._hist)
        # Legend: 3-zone labels (low error | OK | high error) + drag hint
        hist_info = QtWidgets.QHBoxLayout(); hist_info.setContentsMargins(0,0,0,0)
        lbl_low = QtWidgets.QLabel()
        lbl_low.setTextFormat(QtCore.Qt.RichText)
        lbl_low.setText("<span style='color:#c44;font-size:11px;'>{0}</span>".format(
            tr("td_hist_legend_low").replace("<", "&lt;").replace(">", "&gt;")))
        hist_info.addWidget(lbl_low)
        hist_info.addStretch()
        lbl_high = QtWidgets.QLabel()
        lbl_high.setTextFormat(QtCore.Qt.RichText)
        lbl_high.setText("<span style='color:#48c;font-size:11px;'>{0}</span>".format(
            tr("td_hist_legend_high").replace("<", "&lt;").replace(">", "&gt;")))
        hist_info.addWidget(lbl_high)
        layout.addLayout(hist_info)
        # (drag hint rendered inside histogram paintEvent)
        # --- Filter panel ---
        flt_grp = QtWidgets.QGroupBox(tr("td_filter_header"))
        fl = QtWidgets.QVBoxLayout(flt_grp); fl.setSpacing(4); fl.setContentsMargins(8,6,8,6)
        # Max row (上限を上に配置)
        max_row = QtWidgets.QHBoxLayout()
        self._chk_max = QtWidgets.QCheckBox(tr("td_chk_max")); self._chk_max.setChecked(False)
        self._chk_max.toggled.connect(self._on_chk_max_toggled); max_row.addWidget(self._chk_max)
        self._spin_max = QtWidgets.QDoubleSpinBox()
        self._spin_max.setRange(0.0, 9999); self._spin_max.setDecimals(2)
        self._spin_max.setValue(init_max); self._spin_max.setFixedWidth(80)
        self._spin_max.setEnabled(False)
        self._spin_max.valueChanged.connect(self._on_spin_max_changed); max_row.addWidget(self._spin_max)
        self._lbl_max_source = QtWidgets.QLabel("")
        self._lbl_max_source.setStyleSheet("font-size: 10px; color: #888;"); max_row.addWidget(self._lbl_max_source)
        max_row.addStretch()
        fl.addLayout(max_row)
        # Min row (下限を下に配置)
        min_row = QtWidgets.QHBoxLayout()
        self._chk_min = QtWidgets.QCheckBox(tr("td_chk_min")); self._chk_min.setChecked(True)
        self._chk_min.toggled.connect(self._on_chk_min_toggled); min_row.addWidget(self._chk_min)
        self._spin_min = QtWidgets.QDoubleSpinBox()
        self._spin_min.setRange(0.0, 9999); self._spin_min.setDecimals(2)
        self._spin_min.setValue(init_min); self._spin_min.setFixedWidth(80)
        self._spin_min.valueChanged.connect(self._on_spin_min_changed); min_row.addWidget(self._spin_min)
        self._lbl_min_source = QtWidgets.QLabel(tr("td_set_by_threshold"))
        self._lbl_min_source.setStyleSheet("font-size: 10px; color: #888;"); min_row.addWidget(self._lbl_min_source)
        min_row.addStretch()
        fl.addLayout(min_row)
        # (Separator removed for cleaner look)
        # Target + Tolerance row
        tt_row = QtWidgets.QHBoxLayout()
        tt_row.addWidget(QtWidgets.QLabel(tr("td_target_input")))
        self._spin_target = QtWidgets.QDoubleSpinBox()
        self._spin_target.setRange(0.01, 9999); self._spin_target.setDecimals(2)
        self._spin_target.setValue(stats.get("weighted_avg", 4.5)); self._spin_target.setFixedWidth(70)
        tt_row.addWidget(self._spin_target)
        tt_row.addWidget(QtWidgets.QLabel(tr("td_tolerance_input")))
        self._spin_tol = QtWidgets.QDoubleSpinBox()
        self._spin_tol.setRange(0.001, 999); self._spin_tol.setDecimals(3)
        self._spin_tol.setValue(0.1); self._spin_tol.setFixedWidth(70)
        tt_row.addWidget(self._spin_tol)
        self._btn_apply_target = QtWidgets.QPushButton(tr("td_set_by_target"))
        self._btn_apply_target.setProperty("cssClass", "secondary")
        self._btn_apply_target.clicked.connect(self._apply_target_tolerance)
        tt_row.addWidget(self._btn_apply_target); tt_row.addStretch()
        fl.addLayout(tt_row)
        # Threshold % row
        thr_row = QtWidgets.QHBoxLayout()
        thr_row.addWidget(QtWidgets.QLabel(tr("td_threshold_input")))
        self._spin_threshold = QtWidgets.QDoubleSpinBox()
        self._spin_threshold.setRange(1.0, 100); self._spin_threshold.setDecimals(1)
        self._spin_threshold.setValue(_TD_DEFAULT_THRESHOLD_PCT); self._spin_threshold.setFixedWidth(70)
        thr_row.addWidget(self._spin_threshold)
        self._btn_apply_threshold = QtWidgets.QPushButton(tr("td_set_by_threshold"))
        self._btn_apply_threshold.setProperty("cssClass", "secondary")
        self._btn_apply_threshold.clicked.connect(self._apply_threshold)
        thr_row.addWidget(self._btn_apply_threshold); thr_row.addStretch()
        fl.addLayout(thr_row)
        layout.addWidget(flt_grp)
        # --- Filter count ---
        self._filter_count_label = QtWidgets.QLabel("")
        self._filter_count_label.setStyleSheet("font-size: 12px; color: #ccc; padding: 2px 4px;")
        layout.addWidget(self._filter_count_label)
        # --- Error count ---
        self._summary_label = QtWidgets.QLabel("")
        self._summary_label.setStyleSheet("font-size: 13px; font-weight: bold; padding: 4px;")
        layout.addWidget(self._summary_label)
        # --- Error list ---
        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.setStyleSheet("font-size: 12px;")
        self.list_widget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.list_widget)
        # --- Buttons ---
        self._build_button_row(layout, self._select_all)
        # Initial filter
        self._refilter()
    def closeEvent(self, event):
        global _td_last_stats
        _td_last_stats = {}
        super(TexelDensityResultsWindow, self).closeEvent(event)
    def _get_selection_widget(self):
        return self.list_widget
    # --- Filter logic ---
    def _refilter(self, quick=False):
        min_on = self._chk_min.isChecked(); max_on = self._chk_max.isChecked()
        lo = self._spin_min.value() if min_on else None
        hi = self._spin_max.value() if max_on else None
        new_errors = []
        for entry in self._all_entries:
            td = entry["td_value"]; is_err = False; tag = ""
            if lo is not None and td < lo: is_err = True; tag = tr("texel_too_low")
            if hi is not None and td > hi: is_err = True; tag = tr("texel_too_high")
            if is_err:
                e = dict(entry)
                base = entry.get("label", entry["component"])
                # Strip existing tags
                if " [" in base: base = base.split(" [")[0]
                e["component"] = "{0} [{1}]".format(base, tag)
                if "label" in e: e["label"] = e["component"]
                new_errors.append(e)
        new_errors.sort(key=lambda e: e["td_value"])
        self.errors = new_errors
        # Update filter count label
        total = len(self._all_entries)
        below = sum(1 for e in self._all_entries if lo is not None and e["td_value"] < lo)
        above = sum(1 for e in self._all_entries if hi is not None and e["td_value"] > hi)
        if min_on and max_on:
            self._filter_count_label.setText(
                tr("td_filter_count", below=below, above=above, total=total))
        elif min_on:
            self._filter_count_label.setText(
                tr("td_filter_count_min_only", below=below, total=total))
        elif max_on:
            self._filter_count_label.setText(
                tr("td_filter_count_max_only", above=above, total=total))
        else:
            self._filter_count_label.setText(tr("td_filter_none"))
        self._summary_label.setText(tr("error_count", count=len(new_errors)))
        if not quick:
            self._populate_list(new_errors)
    def _populate_list(self, errors):
        self.list_widget.setUpdatesEnabled(False)
        self.list_widget.clear()
        for err in errors:
            txt = err.get("label", err.get("component", ""))
            it = QtWidgets.QListWidgetItem(txt)
            td = err.get("td_value", 0)
            td_lo = self._stats.get("min", 0); td_hi = self._stats.get("max", 1)
            td_rng = td_hi - td_lo if td_hi - td_lo > 1e-6 else 1.0
            t = max(0.0, min(1.0, (td - td_lo) / td_rng))
            r_c, g_c, b_c = _td_heatmap_color(t)
            it.setForeground(QtGui.QColor(r_c, g_c, b_c))
            self.list_widget.addItem(it)
        self.list_widget.setUpdatesEnabled(True)
    # --- Checkbox handlers ---
    def _on_chk_min_toggled(self, checked):
        self._spin_min.setEnabled(checked)
        self._hist.set_min_enabled(checked)
        self._refilter()
    def _on_chk_max_toggled(self, checked):
        self._spin_max.setEnabled(checked)
        self._hist.set_max_enabled(checked)
        self._refilter()
    # --- Spin handlers (direct input) ---
    def _on_spin_min_changed(self, val):
        if self._block_signals: return
        self._min_source = self._INPUT_DIRECT
        self._lbl_min_source.setText(tr("td_set_by_direct"))
        self._hist.set_min(val); self._refilter()
    def _on_spin_max_changed(self, val):
        if self._block_signals: return
        self._lbl_max_source.setText(tr("td_set_by_direct"))
        self._hist.set_max(val); self._refilter()
    # --- Histogram drag handlers ---
    def _on_hist_min_changed(self, val):
        self._block_signals = True
        self._spin_min.setValue(round(val, 2))
        self._block_signals = False
        self._min_source = self._INPUT_DIRECT
        self._lbl_min_source.setText(tr("td_set_by_direct"))
        self._refilter(quick=True)
    def _on_hist_max_changed(self, val):
        self._block_signals = True
        self._spin_max.setValue(round(val, 2))
        self._block_signals = False
        self._lbl_max_source.setText(tr("td_set_by_direct"))
        self._refilter(quick=True)
    def _on_drag_finished(self):
        self._refilter()
    # --- Target +/- Tolerance ---
    def _apply_target_tolerance(self):
        t = self._spin_target.value(); tol = self._spin_tol.value()
        new_min = max(0.0, t - tol); new_max = t + tol
        self._block_signals = True
        self._chk_min.setChecked(True); self._spin_min.setValue(round(new_min, 2))
        self._chk_max.setChecked(True); self._spin_max.setValue(round(new_max, 2))
        self._block_signals = False
        self._hist.set_min_enabled(True); self._hist.set_max_enabled(True)
        self._hist.set_min(new_min); self._hist.set_max(new_max)
        self._spin_min.setEnabled(True); self._spin_max.setEnabled(True)
        self._min_source = self._INPUT_TARGET
        self._lbl_min_source.setText(tr("td_set_by_target"))
        self._lbl_max_source.setText(tr("td_set_by_target"))
        self._refilter()
    # --- Threshold % ---
    def _apply_threshold(self):
        pct = self._spin_threshold.value()
        avg = self._stats.get("weighted_avg", 0)
        new_min = avg * (pct / 100.0)
        self._block_signals = True
        self._chk_min.setChecked(True); self._spin_min.setValue(round(new_min, 2))
        self._block_signals = False
        self._hist.set_min_enabled(True); self._hist.set_min(new_min)
        self._spin_min.setEnabled(True)
        self._min_source = self._INPUT_THRESHOLD
        self._lbl_min_source.setText(tr("td_set_by_threshold"))
        self._chk_max.setChecked(False)
        self._spin_max.setEnabled(False)
        self._hist.set_max_enabled(False)
        self._lbl_max_source.setText("")
        self._refilter()
    # --- Selection ---
    @staticmethod
    def _collect_td_selection(errors):
        """Collect Maya face selection components from TD error entries."""
        sel = []
        for err in errors:
            mesh = err["mesh"]
            if err.get("type") == "texel_density":
                sel.extend(["{0}.f[{1}]".format(mesh, f) for f in err.get("shell_faces_a", [])])
            elif err.get("type") == "texel_density_face":
                sel.append("{0}.f[{1}]".format(err["mesh"], err["face"]))
        return sel
    def _on_selection_changed(self):
        rows = [idx.row() for idx in self.list_widget.selectedIndexes()]
        if not rows:
            cmds.select(clear=True)
            return
        selected = [self.errors[r] for r in rows if 0 <= r < len(self.errors)]
        sel = self._collect_td_selection(selected)
        if sel: cmds.select(sel, r=True)
    def _select_all(self):
        self.list_widget.blockSignals(True)
        self.list_widget.selectAll()
        self.list_widget.blockSignals(False)
        sel = self._collect_td_selection(self.errors)
        if sel: cmds.select(sel, r=True)

# --- Main UI Window ---
class UVQCToolsWindow(QtWidgets.QDialog):
    _instance = None
    @classmethod
    def show_window(cls):
        if cls._instance is not None: cls._instance.close(); cls._instance = None
        cls._instance = cls(parent=get_maya_main_window()); cls._instance.show()
    def __init__(self, parent=None):
        super(UVQCToolsWindow, self).__init__(parent)
        self.setWindowTitle("{0} {1}".format(WINDOW_TITLE, __VERSION__)); self.setMinimumWidth(340)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.Tool)
        self._help_dialog = None; self._worker = None; self._start_time = 0.0
        self._ms_cancelled = False; self._ms_settings = {}
        self._report_log = ReportLog()
        self._profiles = []
        self._stage = 0; self._orig_params = None
        self.setObjectName(WINDOW_OBJECT_NAME)
        self.setStyleSheet(_QSS)
        self._build_ui()
        self.adjustSize()
        # コンテンツ高さに基づく最小高さを動的設定（固定値だと潰れる／不足する）
        self._base_min_h = self.sizeHint().height()
        self.setMinimumHeight(self._base_min_h)
    def _build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 10); main_layout.setSpacing(8)
        self._build_top_row(main_layout)
        self._build_prep_section(main_layout)
        self._build_check_sections(main_layout)
        self._build_status_row(main_layout)
        self._sync_label_widths()
    def _build_top_row(self, main_layout):
        """Build language selector and help button row."""
        # Language / Help row
        top_row = QtWidgets.QHBoxLayout()
        self._lbl_lang = QtWidgets.QLabel(tr("lang_label")); top_row.addWidget(self._lbl_lang)
        self._combo_lang = QtWidgets.QComboBox()
        self._combo_lang.addItems(["English", "\u65e5\u672c\u8a9e"])
        self._combo_lang.setCurrentIndex(0 if _LANG == "en" else 1)
        self._combo_lang.currentIndexChanged.connect(self._on_lang_changed)
        top_row.addWidget(self._combo_lang); top_row.addStretch()
        self._btn_help = QtWidgets.QPushButton(tr("btn_how_to_use"))
        self._btn_help.setProperty("cssClass", "prep")
        self._btn_help.setMinimumWidth(100); self._btn_help.clicked.connect(self._show_help)
        top_row.addWidget(self._btn_help); main_layout.addLayout(top_row)
    def _build_prep_section(self, main_layout):
        """Build Preparation group box (UVSet, Material Separator, Texture Size)."""
        # Preparation QGroupBox (UVSet Check + Material Separator + Texture Size)
        self._grp_prep = QtWidgets.QGroupBox(tr("section_prep"))
        prep_layout = QtWidgets.QVBoxLayout(self._grp_prep)
        prep_layout.setSpacing(6); prep_layout.setContentsMargins(8, 8, 8, 8)
        # v29: UVSet Check (Preparation section)
        self._btn_uvset = QtWidgets.QPushButton(tr("btn_uvset"))
        self._btn_uvset.clicked.connect(self._run_check_uvset)
        self._btn_uvset.setProperty("cssClass", "prep")
        prep_layout.addWidget(self._btn_uvset)
        # v28: Material Separator (1 Material per Mesh)
        ms_row = QtWidgets.QHBoxLayout()
        ms_row.setSpacing(8)
        self._btn_mat_sep = QtWidgets.QPushButton(tr("mat_sep_btn"))
        self._btn_mat_sep.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self._btn_mat_sep.setFixedHeight(28)
        self._btn_mat_sep.clicked.connect(self._on_mat_sep)
        self._btn_mat_sep.setProperty("cssClass", "prep")
        ms_row.addWidget(self._btn_mat_sep)
        self._btn_ms_settings = QtWidgets.QPushButton("\u2699")
        self._btn_ms_settings.setMinimumWidth(40)
        self._btn_ms_settings.setToolTip(tr("mat_sep_settings_title"))
        self._btn_ms_settings.clicked.connect(self._on_mat_sep_settings)
        ms_row.addWidget(self._btn_ms_settings)
        prep_layout.addLayout(ms_row)
        _sizes = ["8192","4096","2048","1024","512","256","128","64","Custom"]
        self.row_square = QtWidgets.QWidget()
        sq_l = QtWidgets.QHBoxLayout(self.row_square); sq_l.setContentsMargins(0,0,0,0)
        self._lbl_res = QtWidgets.QLabel(tr("resolution")); sq_l.addWidget(self._lbl_res)
        self.combo_res = QtWidgets.QComboBox(); self.combo_res.addItems(_sizes)
        self.combo_res.setCurrentText("2048")
        self.spin_custom_res = QtWidgets.QSpinBox()
        self.spin_custom_res.setRange(1,16384); self.spin_custom_res.setValue(2048)
        self.spin_custom_res.setVisible(False)
        self.combo_res.currentTextChanged.connect(lambda t: self.spin_custom_res.setVisible(t=="Custom"))
        sq_l.addWidget(self.combo_res); sq_l.addWidget(self.spin_custom_res); sq_l.addStretch()
        prep_layout.addWidget(self.row_square)
        self.row_res_x = QtWidgets.QWidget()
        rxl = QtWidgets.QHBoxLayout(self.row_res_x); rxl.setContentsMargins(0,0,0,0)
        self._lbl_res_x = QtWidgets.QLabel(tr("res_x")); rxl.addWidget(self._lbl_res_x)
        self.combo_res_x = QtWidgets.QComboBox(); self.combo_res_x.addItems(_sizes)
        self.combo_res_x.setCurrentText("2048")
        self.spin_custom_res_x = QtWidgets.QSpinBox()
        self.spin_custom_res_x.setRange(1,16384); self.spin_custom_res_x.setValue(2048)
        self.spin_custom_res_x.setVisible(False)
        self.combo_res_x.currentTextChanged.connect(lambda t: self.spin_custom_res_x.setVisible(t=="Custom"))
        rxl.addWidget(self.combo_res_x); rxl.addWidget(self.spin_custom_res_x); rxl.addStretch()
        self.row_res_x.setVisible(False); prep_layout.addWidget(self.row_res_x)
        self.row_res_y = QtWidgets.QWidget()
        ryl = QtWidgets.QHBoxLayout(self.row_res_y); ryl.setContentsMargins(0,0,0,0)
        self._lbl_res_y = QtWidgets.QLabel(tr("res_y")); ryl.addWidget(self._lbl_res_y)
        self.combo_res_y = QtWidgets.QComboBox(); self.combo_res_y.addItems(_sizes)
        self.combo_res_y.setCurrentText("2048")
        self.spin_custom_res_y = QtWidgets.QSpinBox()
        self.spin_custom_res_y.setRange(1,16384); self.spin_custom_res_y.setValue(2048)
        self.spin_custom_res_y.setVisible(False)
        self.combo_res_y.currentTextChanged.connect(lambda t: self.spin_custom_res_y.setVisible(t=="Custom"))
        ryl.addWidget(self.combo_res_y); ryl.addWidget(self.spin_custom_res_y); ryl.addStretch()
        self.row_res_y.setVisible(False); prep_layout.addWidget(self.row_res_y)
        self._chk_nonsquare = QtWidgets.QCheckBox(tr("nonsquare"))
        self._chk_nonsquare.toggled.connect(self._toggle_nonsquare)
        prep_layout.addWidget(self._chk_nonsquare)
        self._btn_detect = QtWidgets.QPushButton(tr("btn_detect"))
        self._btn_detect.setProperty("cssClass", "prep")
        self._btn_detect.clicked.connect(self._run_detect_resolution)
        prep_layout.addWidget(self._btn_detect); main_layout.addWidget(self._grp_prep)
    def _build_check_sections(self, main_layout):
        """Dispatch to individual check section builders."""
        self._build_pixel_edge_section(main_layout)
        self._build_padding_section(main_layout)
        self._build_range_section(main_layout)
        self._build_overlap_section(main_layout)
        self._build_texel_section(main_layout)
        self._build_orientation_section(main_layout)
    def _build_pixel_edge_section(self, main_layout):
        """Build Pixel Edge Alignment group box."""
        # Pixel Edge Alignment
        self._grp_edge = QtWidgets.QGroupBox(tr("pixel_edge"))
        el = QtWidgets.QVBoxLayout(self._grp_edge)
        el.setSpacing(4); el.setContentsMargins(8, 8, 8, 8)
        edge_row = QtWidgets.QHBoxLayout()
        self._lbl_min_edge = QtWidgets.QLabel(tr("min_edge")); edge_row.addWidget(self._lbl_min_edge)
        self.spin_min_edge = QtWidgets.QDoubleSpinBox()
        self.spin_min_edge.setRange(0.1,1000.0); self.spin_min_edge.setValue(1.0)
        self.spin_min_edge.setDecimals(1); self.spin_min_edge.setFixedWidth(60)
        edge_row.addWidget(self.spin_min_edge); edge_row.addStretch()
        el.addLayout(edge_row); el.addSpacing(4)
        self._btn_pixel = QtWidgets.QPushButton(tr("btn_pixel"))
        self._btn_pixel.clicked.connect(self._run_check_edges)
        el.addWidget(self._btn_pixel); main_layout.addWidget(self._grp_edge)
    def _build_padding_section(self, main_layout):
        """Build UV Padding group box."""
        # UV Padding
        self._grp_padding = QtWidgets.QGroupBox(tr("uv_padding"))
        pad_layout = QtWidgets.QVBoxLayout(self._grp_padding)
        pad_layout.setSpacing(4); pad_layout.setContentsMargins(8, 8, 8, 8)
        ignore_row = QtWidgets.QHBoxLayout()
        self._lbl_padding_ignore = QtWidgets.QLabel(tr("ignore_under"))
        self._lbl_padding_ignore.setEnabled(False)
        ignore_row.addWidget(self._lbl_padding_ignore)
        self.spin_padding_ignore = QtWidgets.QDoubleSpinBox()
        self.spin_padding_ignore.setRange(0.01,100.0); self.spin_padding_ignore.setValue(0.05)
        self.spin_padding_ignore.setDecimals(2); self.spin_padding_ignore.setEnabled(False)
        self.spin_padding_ignore.setFixedWidth(60); ignore_row.addWidget(self.spin_padding_ignore)
        self._chk_padding_ignore_unlock = QtWidgets.QCheckBox(tr("ignore_unlock"))
        self._chk_padding_ignore_unlock.toggled.connect(self._on_padding_ignore_toggled)
        ignore_row.addWidget(self._chk_padding_ignore_unlock); ignore_row.addStretch()
        pad_layout.addLayout(ignore_row)
        shell_row = QtWidgets.QHBoxLayout()
        self._lbl_shell_padding = QtWidgets.QLabel(tr("shell_padding"))
        self._lbl_shell_padding.setStyleSheet("font-weight: bold;")
        shell_row.addWidget(self._lbl_shell_padding)
        self._lbl_shell_error = QtWidgets.QLabel(tr("error_under"))
        shell_row.addWidget(self._lbl_shell_error)
        self.spin_shell_error = QtWidgets.QSpinBox()
        self.spin_shell_error.setRange(0, 100); self.spin_shell_error.setValue(5)
        self.spin_shell_error.setFixedWidth(60)
        shell_row.addWidget(self.spin_shell_error); shell_row.addStretch()
        pad_layout.addLayout(shell_row)
        # Tile padding
        tile_row = QtWidgets.QHBoxLayout()
        self._lbl_tile_padding = QtWidgets.QLabel(tr("tile_padding"))
        self._lbl_tile_padding.setStyleSheet("font-weight: bold;")
        tile_row.addWidget(self._lbl_tile_padding)
        self._lbl_tile_error = QtWidgets.QLabel(tr("error_under"))
        tile_row.addWidget(self._lbl_tile_error)
        self.spin_tile_error = QtWidgets.QSpinBox()
        self.spin_tile_error.setRange(0, 100); self.spin_tile_error.setValue(2)
        self.spin_tile_error.setFixedWidth(60)
        tile_row.addWidget(self.spin_tile_error); tile_row.addStretch()
        pad_layout.addLayout(tile_row)
        # v46: Mode selection (radio buttons + description labels)
        normal_row = QtWidgets.QHBoxLayout()
        self._radio_normal = QtWidgets.QRadioButton(tr("mode_normal"))
        self._radio_normal.setChecked(True)
        normal_row.addWidget(self._radio_normal)
        self._lbl_normal_desc = QtWidgets.QLabel(": " + tr("normal_mode_desc"))
        self._lbl_normal_desc.setStyleSheet("color: #c90;")
        normal_row.addWidget(self._lbl_normal_desc)
        normal_row.addStretch()
        pad_layout.addLayout(normal_row)
        hp_row = QtWidgets.QHBoxLayout()
        self._radio_high_precision = QtWidgets.QRadioButton(tr("high_precision"))
        hp_row.addWidget(self._radio_high_precision)
        self._lbl_hp_desc = QtWidgets.QLabel(": " + tr("high_precision_desc"))
        self._lbl_hp_desc.setStyleSheet("")
        hp_row.addWidget(self._lbl_hp_desc)
        hp_row.addStretch()
        pad_layout.addLayout(hp_row)
        self._btn_padding = QtWidgets.QPushButton(tr("btn_padding"))
        self._btn_padding.clicked.connect(self._run_check_padding)
        pad_layout.addWidget(self._btn_padding)
        main_layout.addWidget(self._grp_padding)
    def _build_range_section(self, main_layout):
        """Build UV Range Check group box."""
        # UV Range Check
        self._grp_range = QtWidgets.QGroupBox(tr("uv_range"))
        rl = QtWidgets.QVBoxLayout(self._grp_range)
        rl.setSpacing(4); rl.setContentsMargins(8, 8, 8, 8)
        self._chk_crossing = QtWidgets.QCheckBox(tr("tile_crossing"))
        self._chk_crossing.setChecked(True); rl.addWidget(self._chk_crossing)
        self._chk_custom_range = QtWidgets.QCheckBox(tr("custom_range"))
        self._chk_custom_range.setChecked(False)
        self._chk_custom_range.toggled.connect(self._toggle_custom_range)
        rl.addWidget(self._chk_custom_range)
        self._custom_range_widget = QtWidgets.QWidget()
        _cr_layout = QtWidgets.QVBoxLayout(self._custom_range_widget)
        _cr_layout.setContentsMargins(0, 0, 0, 0); _cr_layout.setSpacing(4)
        uv_u_row = QtWidgets.QHBoxLayout()
        self._lbl_uv_u = QtWidgets.QLabel(tr("uv_u")); uv_u_row.addWidget(self._lbl_uv_u)
        self.spin_u_min = QtWidgets.QSpinBox()
        self.spin_u_min.setRange(-20, 20); self.spin_u_min.setValue(0)
        self.spin_u_min.setFixedWidth(50)
        uv_u_row.addWidget(self.spin_u_min); uv_u_row.addWidget(QtWidgets.QLabel("~"))
        self.spin_u_max = QtWidgets.QSpinBox()
        self.spin_u_max.setRange(-20, 20); self.spin_u_max.setValue(1)
        self.spin_u_max.setFixedWidth(50)
        uv_u_row.addWidget(self.spin_u_max); uv_u_row.addStretch(); _cr_layout.addLayout(uv_u_row)
        uv_v_row = QtWidgets.QHBoxLayout()
        self._lbl_uv_v = QtWidgets.QLabel(tr("uv_v")); uv_v_row.addWidget(self._lbl_uv_v)
        self.spin_v_min = QtWidgets.QSpinBox()
        self.spin_v_min.setRange(-20, 20); self.spin_v_min.setValue(0)
        self.spin_v_min.setFixedWidth(50)
        uv_v_row.addWidget(self.spin_v_min); uv_v_row.addWidget(QtWidgets.QLabel("~"))
        self.spin_v_max = QtWidgets.QSpinBox()
        self.spin_v_max.setRange(-20, 20); self.spin_v_max.setValue(1)
        self.spin_v_max.setFixedWidth(50)
        uv_v_row.addWidget(self.spin_v_max); uv_v_row.addStretch(); _cr_layout.addLayout(uv_v_row)
        self._custom_range_widget.setVisible(False)
        rl.addWidget(self._custom_range_widget)
        self._btn_range = QtWidgets.QPushButton(tr("btn_range"))
        self._btn_range.clicked.connect(self._run_check_range); rl.addWidget(self._btn_range)
        main_layout.addWidget(self._grp_range)
    def _build_overlap_section(self, main_layout):
        """Build UV Overlap group box."""
        # UV Overlap
        self._grp_ovlp = QtWidgets.QGroupBox(tr("uv_overlap"))
        ol = QtWidgets.QVBoxLayout(self._grp_ovlp)
        ol.setSpacing(4); ol.setContentsMargins(8, 8, 8, 8)
        self._chk_self_ovlp = QtWidgets.QCheckBox(tr("self_overlap")); ol.addWidget(self._chk_self_ovlp)
        self._btn_overlap = QtWidgets.QPushButton(tr("btn_overlap"))
        self._btn_overlap.clicked.connect(self._run_check_overlap); ol.addWidget(self._btn_overlap)
        main_layout.addWidget(self._grp_ovlp)
    def _build_texel_section(self, main_layout):
        """Build Texel Density group box."""
        # v56: Texel Density (measurement only — filtering moved to results window)
        self._grp_texel = QtWidgets.QGroupBox(tr("texel_density"))
        tl = QtWidgets.QVBoxLayout(self._grp_texel)
        tl.setSpacing(4); tl.setContentsMargins(8, 8, 8, 8)
        # Unit selection (vertical layout with descriptions)
        self._radio_td_shell = QtWidgets.QRadioButton(tr("td_shell"))
        self._radio_td_face = QtWidgets.QRadioButton(tr("td_face"))
        self._radio_td_shell.setChecked(True)
        self._grp_td_unit = QtWidgets.QButtonGroup(self)
        self._grp_td_unit.addButton(self._radio_td_shell, 0)
        self._grp_td_unit.addButton(self._radio_td_face, 1)
        td_shell_row = QtWidgets.QHBoxLayout()
        td_shell_row.addWidget(self._radio_td_shell)
        self._lbl_td_shell_desc = QtWidgets.QLabel(": " + tr("td_shell_desc"))
        self._lbl_td_shell_desc.setStyleSheet("")
        td_shell_row.addWidget(self._lbl_td_shell_desc)
        td_shell_row.addStretch()
        tl.addLayout(td_shell_row)
        td_face_row = QtWidgets.QHBoxLayout()
        td_face_row.addWidget(self._radio_td_face)
        self._lbl_td_face_desc = QtWidgets.QLabel(": " + tr("td_face_desc"))
        self._lbl_td_face_desc.setStyleSheet("")
        td_face_row.addWidget(self._lbl_td_face_desc)
        td_face_row.addStretch()
        tl.addLayout(td_face_row)
        self._btn_texel = QtWidgets.QPushButton(tr("btn_texel"))
        self._btn_texel.clicked.connect(self._run_check_texel); tl.addWidget(self._btn_texel)
        main_layout.addWidget(self._grp_texel)
    def _build_orientation_section(self, main_layout):
        """Build UV Orientation group box."""
        self._grp_orientation = QtWidgets.QGroupBox(tr("uv_orientation"))
        orl = QtWidgets.QVBoxLayout(self._grp_orientation)
        orl.setSpacing(4); orl.setContentsMargins(8, 8, 8, 8)
        self._btn_orientation = QtWidgets.QPushButton(tr("btn_orientation"))
        self._btn_orientation.clicked.connect(self._run_check_orientation)
        orl.addWidget(self._btn_orientation)
        main_layout.addWidget(self._grp_orientation)
    def _build_status_row(self, main_layout):
        """Build status bar, progress bar, and report button row."""
        # Status & Progress (unified row — no separate container, no height change)
        status_row = QtWidgets.QHBoxLayout()
        status_row.setContentsMargins(0, 0, 0, 0)
        self._status_bar = QtWidgets.QLabel(tr("ready"))
        # Intentional QSS override: subtle status text
        self._status_bar.setStyleSheet("font-size: 12px; color: #666; padding: 4px 8px;")
        self._status_bar.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        status_row.addWidget(self._status_bar)
        self._progress_bar = QtWidgets.QProgressBar()
        self._progress_bar.setRange(0, 100); self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self._progress_bar.setVisible(False)
        status_row.addWidget(self._progress_bar)
        self._btn_cancel = QtWidgets.QPushButton("\u2715")
        self._btn_cancel.setFixedSize(30, 22)
        self._btn_cancel.setToolTip(tr("cancel") if "cancel" in _TR.get(_LANG, {}) else "Cancel")
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
        main_layout.addLayout(status_row)
    def _sync_label_widths(self):
        _w1 = max(self._lbl_shell_padding.sizeHint().width(),
                  self._lbl_tile_padding.sizeHint().width())
        self._lbl_shell_padding.setFixedWidth(_w1)
        self._lbl_tile_padding.setFixedWidth(_w1)
        _w2 = max(self._lbl_uv_u.sizeHint().width(),
                  self._lbl_uv_v.sizeHint().width())
        self._lbl_uv_u.setFixedWidth(_w2)
        self._lbl_uv_v.setFixedWidth(_w2)
    # === Helpers ===
    def _fit_height(self):
        """Recalculate and apply optimal height, preserving current width."""
        self.layout().activate()
        QtWidgets.QApplication.processEvents()
        h = self.sizeHint().height()
        self.setFixedHeight(h)
        self.setMinimumHeight(self._base_min_h)
        self.setMaximumHeight(16777215)
    def _show_progress(self):
        """Show progress bar for a new check."""
        self._status_bar.setVisible(False)
        self._progress_bar.setFormat("%p%")
        self._progress_bar.setVisible(True)
        self._progress_bar.setValue(0)
        self._btn_cancel.setVisible(True)
    def _hide_progress(self):
        """Hide progress bar after check completes."""
        self._progress_bar.setVisible(False)
        self._progress_bar.setValue(0)
        self._btn_cancel.setVisible(False)
        self._status_bar.setVisible(True)
    def _set_status(self, text, state="ready"):
        """Set status bar text with state-based styling.
        States: ready (gray), success (green bg), error (red bg), working (accent)."""
        self._status_bar.setText(text)
        if state == "success":
            self._status_bar.setStyleSheet(
                "font-size: 12px; color: #4a4; background-color: #1a2e1a;"
                " border-radius: 3px; padding: 4px 8px;")
        elif state == "error":
            self._status_bar.setStyleSheet(
                "font-size: 12px; color: #c44; background-color: #2e1a1a;"
                " border-radius: 3px; padding: 4px 8px;")
        elif state == "working":
            self._status_bar.setStyleSheet(
                "font-size: 12px; color: #7aa2f7; padding: 4px 8px;")
        else:
            self._status_bar.setStyleSheet(
                "font-size: 12px; color: #666; padding: 4px 8px;")
    def _get_resolution(self):
        if self._chk_nonsquare.isChecked():
            rx = self.spin_custom_res_x.value() if self.combo_res_x.currentText() == "Custom" else int(self.combo_res_x.currentText())
            ry = self.spin_custom_res_y.value() if self.combo_res_y.currentText() == "Custom" else int(self.combo_res_y.currentText())
            return rx, ry
        r = self.spin_custom_res.value() if self.combo_res.currentText() == "Custom" else int(self.combo_res.currentText())
        return r, r
    def _toggle_nonsquare(self, checked):
        self.row_square.setVisible(not checked)
        self.row_res_x.setVisible(checked); self.row_res_y.setVisible(checked)
        self._fit_height()
    def _toggle_custom_range(self, checked):
        self._custom_range_widget.setVisible(checked)
        self._fit_height()
    def _on_padding_ignore_toggled(self, checked):
        self.spin_padding_ignore.setEnabled(checked)
        self._lbl_padding_ignore.setEnabled(checked)
    def _set_buttons_enabled(self, enabled):
        for b in [self._btn_pixel, self._btn_padding, self._btn_range,
                   self._btn_overlap, self._btn_texel, self._btn_uvset,
                   self._btn_mat_sep, self._btn_detect,
                   self._btn_orientation]: b.setEnabled(enabled)
    def _on_cancel(self):
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
        self._ms_cancelled = True
    # === v59: Report Log ===
    def _run_check_orientation(self):
        if self._worker and self._worker.isRunning():
            return
        self._target_label = self._get_target_label()
        meshes = get_selected_meshes()
        if not meshes:
            QtWidgets.QMessageBox.warning(self, WINDOW_TITLE, tr("no_mesh"))
            self._record_pre_fail("UV Orientation", "No mesh selected")
            return
        try:
            mesh_data = collect_orientation_data(meshes)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, WINDOW_TITLE,
                tr("check_error") + "\n({0})".format(e))
            self._record_pre_fail("UV Orientation", str(e))
            return
        if not mesh_data:
            QtWidgets.QMessageBox.warning(self, WINDOW_TITLE, tr("no_mesh"))
            self._record_pre_fail("UV Orientation", "No valid mesh data")
            return
        self._show_progress()
        self._start_time = time.time()
        self._worker = QCWorker(compute_uv_orientation, mesh_data)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_orientation_finished)
        self._worker.start()
        self._set_buttons_enabled(False)
    def _on_orientation_finished(self, results, msg):
        elapsed = time.time() - self._start_time
        self._hide_progress()
        self._set_buttons_enabled(True)
        tb = getattr(self._worker, "_traceback", None)
        # ~1.6.0-dev hotfix: Report log recording (was missing)
        _params = self._get_check_params("UV Orientation")
        _target = self._get_check_target()
        n_issues = len([r for r in results if r.get("classification") != "normal"])
        n_total = len(results)
        _worker_profile = getattr(self._worker, '_profile', {})
        self._report_log.add_entry(
            "UV Orientation", _params, _target,
            round(elapsed, 2),
            result_ok=(n_issues == 0), error_count=n_issues,
            profiles=[_worker_profile] if _worker_profile else [])
        if tb:
            self._report_log.add_error("UV Orientation", tb)
        self._worker = None
        if tb:
            self._set_status(msg, "error")
            QtWidgets.QMessageBox.warning(self, tr("uv_orientation"), msg)
            return
        self._set_status(tr("done_with_time", name=tr("uv_orientation"), time=round(elapsed, 1)), "success")
        QtCore.QTimer.singleShot(3000, lambda: self._set_status(tr("ready")))
        if results:
            w = OrientationResultsWindow(self._make_result_title(tr("uv_orientation")), results, parent=self)
            w.show()
        elif msg != tr("cancelled"):
            QtWidgets.QMessageBox.information(self, tr("uv_orientation"), tr("no_errors"))
    def _copy_report(self):
        if not self._report_log.has_entries():
            QtWidgets.QMessageBox.information(
                self, WINDOW_TITLE, tr("report_empty"))
            return
        text = self._report_log.generate()
        QtWidgets.QApplication.clipboard().setText(text)
        success, msg_key = _open_feedback_form(text)
        if not success:
            QtWidgets.QMessageBox.warning(
                self, WINDOW_TITLE, tr(msg_key))
            return
        if msg_key == "report_url_too_long":
            QtWidgets.QMessageBox.information(
                self, WINDOW_TITLE, tr("report_url_too_long"))
        self._set_status(tr("report_form_opened"), "success")
        QtCore.QTimer.singleShot(3000,
            lambda: self._set_status(tr("ready")))
    def _get_check_params(self, check_name):
        rx, ry = self._get_resolution()
        res_str = "{0}x{1}".format(rx, ry)
        if check_name == "Pixel Edge":
            return "Resolution={0}, MinEdge={1}px".format(
                res_str, self.spin_min_edge.value())
        elif check_name == "UV Padding":
            mode = "High Precision" if self._radio_high_precision.isChecked() else "Normal"
            return "Resolution={0}, Shell<{1}px, Tile<{2}px, Mode={3}".format(
                res_str, self.spin_shell_error.value(),
                self.spin_tile_error.value(), mode)
        elif check_name == "UV Range":
            if self._chk_custom_range.isChecked():
                return "Crossing={0}, CustomRange=True, U=[{1},{2}], V=[{3},{4}]".format(
                    self._chk_crossing.isChecked(),
                    self.spin_u_min.value(), self.spin_u_max.value(),
                    self.spin_v_min.value(), self.spin_v_max.value())
            return "Crossing={0}, CustomRange=False (default 0~1)".format(
                self._chk_crossing.isChecked())
        elif check_name == "UV Overlap":
            return "SelfOverlap={0}".format(self._chk_self_ovlp.isChecked())
        elif check_name == "Texel Density":
            unit = "Shell" if self._radio_td_shell.isChecked() else "Face"
            return "Resolution={0}, Unit={1}".format(res_str, unit)
        elif check_name == "UVSet Check":
            return "(none)"
        elif check_name == "UV Orientation":
            return "(none)"
        return ""
    def _get_check_target(self):
        sel = cmds.ls(sl=True, long=True, type="transform") or []
        meshes = [s for s in sel
                  if cmds.listRelatives(s, shapes=True, type="mesh")]
        count = len(meshes) if meshes else len(sel)
        return "{0} meshes".format(count)
    def _record_pre_fail(self, check_name, reason):
        params = self._get_check_params(check_name)
        self._report_log.add_entry(
            check_name, params, "0 meshes", 0,
            result_ok=False, error_count=0)
        self._report_log.add_error(check_name, reason)
    # === ~1.6.0-dev: Result window title helpers ===
    def _get_target_label(self):
        """Return a short label for the currently selected meshes."""
        sel = cmds.ls(sl=True, long=True, type="transform") or []
        meshes = [s for s in sel if cmds.listRelatives(s, shapes=True, type="mesh")]
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
            return "{0} \u2014 {1}: {2}".format(check_label, tr("results_word"), target)
        return check_label
    # === Language ===
    def _on_lang_changed(self, index):
        global _LANG
        _LANG = "en" if index == 0 else "ja"
        self._lbl_lang.setText(tr("lang_label")); self._btn_help.setText(tr("btn_how_to_use"))
        self._btn_mat_sep.setText(tr("mat_sep_btn"))
        self._btn_ms_settings.setToolTip(tr("mat_sep_settings_title"))
        self._lbl_res.setText(tr("resolution"))
        self._lbl_res_x.setText(tr("res_x")); self._lbl_res_y.setText(tr("res_y"))
        self._chk_nonsquare.setText(tr("nonsquare")); self._btn_detect.setText(tr("btn_detect"))
        self._grp_edge.setTitle(tr("pixel_edge")); self._lbl_min_edge.setText(tr("min_edge"))
        self._btn_pixel.setText(tr("btn_pixel"))
        self._grp_padding.setTitle(tr("uv_padding"))
        self._lbl_padding_ignore.setText(tr("ignore_under"))
        self._chk_padding_ignore_unlock.setText(tr("ignore_unlock"))
        self._lbl_shell_padding.setText(tr("shell_padding"))
        self._lbl_shell_error.setText(tr("error_under"))
        self._lbl_tile_padding.setText(tr("tile_padding"))
        self._lbl_tile_error.setText(tr("error_under"))
        self._btn_padding.setText(tr("btn_padding"))
        self._radio_normal.setText(tr("mode_normal"))
        self._lbl_normal_desc.setText(": " + tr("normal_mode_desc"))
        self._radio_high_precision.setText(tr("high_precision"))
        self._lbl_hp_desc.setText(": " + tr("high_precision_desc"))
        self._grp_range.setTitle(tr("uv_range")); self._chk_crossing.setText(tr("tile_crossing"))
        self._chk_custom_range.setText(tr("custom_range"))
        self._lbl_uv_u.setText(tr("uv_u")); self._lbl_uv_v.setText(tr("uv_v"))
        self._btn_range.setText(tr("btn_range"))
        self._grp_ovlp.setTitle(tr("uv_overlap")); self._chk_self_ovlp.setText(tr("self_overlap"))
        self._btn_overlap.setText(tr("btn_overlap"))
        self._grp_texel.setTitle(tr("texel_density"))
        self._radio_td_shell.setText(tr("td_shell"))
        self._radio_td_face.setText(tr("td_face"))
        self._lbl_td_shell_desc.setText(": " + tr("td_shell_desc"))
        self._lbl_td_face_desc.setText(": " + tr("td_face_desc"))
        self._btn_texel.setText(tr("btn_texel"))
        self._grp_orientation.setTitle(tr("uv_orientation"))
        self._btn_orientation.setText(tr("btn_orientation"))
        self._btn_uvset.setText(tr("btn_uvset"))
        self._grp_prep.setTitle(tr("section_prep"))
        self._set_status(tr("ready"))
        self._btn_copy_report.setText(tr("btn_copy_report"))
        if self._help_dialog: self._help_dialog.refresh_lang()
        self._sync_label_widths()
    # === Help ===
    def _show_help(self):
        if self._help_dialog is None: self._help_dialog = HelpDialog(self)
        self._help_dialog.show(); self._help_dialog.raise_()
    # === Detect Resolution ===
    def _apply_detected_resolution(self, x, y):
        """Apply detected resolution to UI controls."""
        if x == y:
            self._chk_nonsquare.setChecked(False)
            txt = str(x)
            if txt in [self.combo_res.itemText(i) for i in range(self.combo_res.count())]:
                self.combo_res.setCurrentText(txt)
            else: self.combo_res.setCurrentText("Custom"); self.spin_custom_res.setValue(x)
        else:
            self._chk_nonsquare.setChecked(True)
            for cb, sp, v in [(self.combo_res_x, self.spin_custom_res_x, x),
                               (self.combo_res_y, self.spin_custom_res_y, y)]:
                txt = str(v)
                if txt in [cb.itemText(i) for i in range(cb.count())]: cb.setCurrentText(txt)
                else: cb.setCurrentText("Custom"); sp.setValue(v)
    def _run_detect_resolution(self):
        result = _get_texture_resolution()
        if result is None:
            QtWidgets.QMessageBox.warning(self, WINDOW_TITLE, tr("detect_fail")); return
        if isinstance(result, tuple) and result[0] == "mixed":
            res_to_textures = result[1]
            dlg = ResolutionPickerDialog(res_to_textures, self)
            if dlg.exec_() != QtWidgets.QDialog.Accepted:
                return
            x, y = dlg.selected_resolution
            self._apply_detected_resolution(x, y)
            QtWidgets.QMessageBox.information(self, WINDOW_TITLE, tr("detect_result", x=x, y=y))
            return
        x, y = result
        self._apply_detected_resolution(x, y)
        QtWidgets.QMessageBox.information(self, WINDOW_TITLE, tr("detect_result", x=x, y=y))
    # === Worker callbacks ===
    def _on_progress(self, current, total, label):
        if total > 0: self._progress_bar.setValue(int(current * 100 / total))
        self._progress_bar.setFormat(label + "  %p%")
        self._set_status(label, "working")
    def _on_worker_finished(self, errors, msg):
        elapsed = time.time() - self._start_time
        self._set_buttons_enabled(True)
        self._hide_progress()
        self._set_status(tr("done_with_time", name=self._current_check, time=round(elapsed, 1)), "success")
        QtCore.QTimer.singleShot(3000, lambda: self._set_status(tr("ready")))
        # v59: Record to report log
        _params = self._get_check_params(self._current_check)
        _target = self._get_check_target()
        _worker_profile = getattr(self._worker, '_profile', {})
        if self._profiles:
            if _worker_profile:
                _p2 = dict(_worker_profile)
                _p2["label"] = "Phase 2 (Full resolution)"
                self._profiles.append(_p2)
            _all_profiles = self._profiles
        elif _worker_profile:
            _all_profiles = [_worker_profile]
        else:
            _all_profiles = []
        _log = getattr(self, '_report_log', None)
        if _log:
            _log.add_entry(
                self._current_check, _params, _target,
                round(elapsed, 2),
                result_ok=(not errors),
                error_count=(sum(len(g.get("errors", []))
                    for g in errors if not g.get("intentional", False))
                    if self._current_check == "UV Overlap" and errors
                    else len(errors)),
                profiles=_all_profiles)
        self._profiles = []
        tb = getattr(self._worker, '_traceback', None)
        if tb and _log:
            _log.add_error(self._current_check, tb)
        if not errors:
            if msg != tr("cancelled"):
                QtWidgets.QMessageBox.information(self, WINDOW_TITLE, tr("no_errors"))
            return
        if self._current_check == "Pixel Edge":
            rx, ry = self._get_resolution()
            _groups = getattr(self._worker, '_groups', None)
            win = PixelEdgeResultsWindow(self._make_result_title(tr("pixel_edge")), errors, rx, ry, groups=_groups, parent=self)
        elif self._current_check == "UV Overlap":
            win = OverlapResultsWindow(self._make_result_title(tr("uv_overlap")), errors, self)
        else:
            win = ResultsWindow(self._make_result_title(self._current_check), errors, self)
        win.show()
    # === Check: Pixel Edge ===
    def _run_check_edges(self):
        if self._worker and self._worker.isRunning(): return
        self._target_label = self._get_target_label()
        records = collect_pixel_edge_data()
        if records is None:
            self._record_pre_fail("Pixel Edge", "No mesh selected")
            QtWidgets.QMessageBox.warning(self, WINDOW_TITLE, tr("no_mesh")); return
        rx, ry = self._get_resolution()
        self._set_buttons_enabled(False); self._start_time = time.time()
        self._show_progress()
        self._status_bar.setText(tr("computing")); self._current_check = "Pixel Edge"
        self._worker = QCWorker(compute_pixel_edges, records, rx, ry, self.spin_min_edge.value())
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_worker_finished); self._worker.start()
    # === Check: UV Padding ===
    def _run_check_padding(self):
        if self._worker and self._worker.isRunning(): return
        self._target_label = self._get_target_label()
        rx, ry = self._get_resolution()
        shell_val = self.spin_shell_error.value()
        tile_val = self.spin_tile_error.value()
        self._stage = 0
        if not self._radio_high_precision.isChecked():
            # v46: Normal mode — Auto two-stage check — Phase 1 fast scan
            self._orig_params = (rx, ry, shell_val, tile_val)
            fast_rx, fast_ry, fast_shell, fast_tile, _ = calc_fast_params(rx, ry, shell_val, tile_val)
            data = collect_shell_data(fast_rx, fast_ry)
            if data is None:
                self._record_pre_fail("UV Padding", "No mesh selected")
                QtWidgets.QMessageBox.warning(self, WINDOW_TITLE, tr("no_mesh")); return
            self._stage = 1
            self._profiles = []
            self._set_buttons_enabled(False); self._start_time = time.time()
            self._show_progress()
            self._status_bar.setText(tr("phase1")); self._current_check = "UV Padding"
            # v39 fix: Dilation廃止 → エラー閾値にマージン加算で低解像度誤差を補償
            margin = 2
            phase1_shell = fast_shell + margin
            phase1_tile = fast_tile + margin
            # v40: scale_factor > 1 signals fast mode — dist=0 pairs pass to Phase 2
            ign = self.spin_padding_ignore.value()
            _sf = float(rx) / float(fast_rx)
            self._worker = QCWorker(compute_uv_padding, data, ign, phase1_shell,
                                    0, phase1_tile, fast_rx, fast_ry, False,
                                    None, None, _sf)
            self._worker.progress.connect(self._on_progress)
            self._worker.finished.connect(self._on_padding_phase1_done); self._worker.start()
        else:
            data = collect_shell_data(rx, ry)
            if data is None:
                self._record_pre_fail("UV Padding", "No mesh selected")
                QtWidgets.QMessageBox.warning(self, WINDOW_TITLE, tr("no_mesh")); return
            self._set_buttons_enabled(False); self._start_time = time.time()
            self._show_progress()
            self._status_bar.setText(tr("computing")); self._current_check = "UV Padding"
            ign = self.spin_padding_ignore.value()
            self._worker = QCWorker(compute_uv_padding, data, ign, shell_val,
                                    ign, tile_val, rx, ry, False)
            self._worker.progress.connect(self._on_progress)
            self._worker.finished.connect(self._on_worker_finished); self._worker.start()
    def _on_padding_phase1_done(self, errors, msg):
        """v58: All Phase 1 errors go to Phase 2 for full-res verification."""
        _p1 = dict(getattr(self._worker, '_profile', {}))
        if _p1:
            _p1["label"] = "Phase 1 (Fast scan)"
        self._profiles.append(_p1)
        self._worker._profile = {}
        if msg == tr("cancelled") or not errors:
            self._stage = 0
            self._on_worker_finished(errors, msg); return
        rx, ry, shell_val, tile_val = self._orig_params
        target_shell_pairs = set(); target_tile_shells = set()
        for err in errors:
            if err["type"] == "shell_distance":
                ka = (err["mesh"], err["shell_a"])
                kb = (err.get("mesh_b", err["mesh"]), err["shell_b"])
                target_shell_pairs.add((ka, kb) if ka < kb else (kb, ka))
            elif err["type"] == "tile_distance":
                target_tile_shells.add((err["mesh"], err["shell_a"]))
        if not target_shell_pairs and not target_tile_shells:
            self._stage = 0
            self._on_worker_finished([], msg); return
        n_targets = len(target_shell_pairs) + len(target_tile_shells)
        self._status_bar.setText(tr("phase2", count=n_targets))
        self._progress_bar.setValue(0)
        data = collect_shell_data(rx, ry)
        if data is None:
            self._stage = 0; self._set_buttons_enabled(True)
            self._hide_progress(); return
        self._stage = 2
        ign = self.spin_padding_ignore.value()
        self._worker = QCWorker(compute_uv_padding, data, ign, shell_val,
                                ign, tile_val, rx, ry, False,
                                target_shell_pairs, target_tile_shells)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_padding_phase2_done); self._worker.start()
    def _on_padding_phase2_done(self, errors, msg):
        """v58: Phase 2 results are final (no Phase 1 direct errors to merge)."""
        self._on_worker_finished(errors, msg)
    # === Check: UV Range ===
    def _run_check_range(self):
        if self._worker and self._worker.isRunning(): return
        self._target_label = self._get_target_label()
        data = collect_range_data()
        if data is None:
            self._record_pre_fail("UV Range", "No mesh selected")
            QtWidgets.QMessageBox.warning(self, WINDOW_TITLE, tr("no_mesh")); return
        self._set_buttons_enabled(False); self._start_time = time.time()
        self._show_progress()
        self._status_bar.setText(tr("computing")); self._current_check = "UV Range"
        if self._chk_custom_range.isChecked():
            u_min = self.spin_u_min.value(); u_max = self.spin_u_max.value() - 1
            v_min = self.spin_v_min.value(); v_max = self.spin_v_max.value() - 1
        else:
            u_min = 0; u_max = 0; v_min = 0; v_max = 0
        self._worker = QCWorker(compute_range_check, data,
            self._chk_crossing.isChecked(), True, u_min, u_max, v_min, v_max)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_worker_finished); self._worker.start()
    # === Check: UV Overlap ===
    def _run_check_overlap(self):
        if self._worker and self._worker.isRunning(): return
        self._target_label = self._get_target_label()
        data = collect_overlap_data(self._chk_self_ovlp.isChecked())
        if data is None:
            self._record_pre_fail("UV Overlap", "No mesh selected")
            QtWidgets.QMessageBox.warning(self, WINDOW_TITLE, tr("no_mesh")); return
        self._set_buttons_enabled(False); self._start_time = time.time()
        self._show_progress()
        self._status_bar.setText(tr("computing")); self._current_check = "UV Overlap"
        self._worker = QCWorker(compute_uv_overlap, data)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_worker_finished); self._worker.start()
    # === v56: Check Texel Density (measure-only) ===
    def _run_check_texel(self):
        if self._worker and self._worker.isRunning(): return
        self._target_label = self._get_target_label()
        rx, ry = self._get_resolution()
        data = collect_texel_density_data(rx, ry)
        if data is None:
            self._record_pre_fail("Texel Density", "No mesh selected")
            QtWidgets.QMessageBox.warning(self, WINDOW_TITLE, tr("no_mesh")); return
        self._set_buttons_enabled(False); self._start_time = time.time()
        self._show_progress()
        self._status_bar.setText(tr("computing")); self._current_check = "Texel Density"
        by_shell = self._radio_td_shell.isChecked()
        self._worker = QCWorker(compute_texel_density, data, by_shell)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_texel_finished); self._worker.start()
    def _on_texel_finished(self, all_entries, msg):
        """v56: Show unified TexelDensityResultsWindow."""
        elapsed = time.time() - self._start_time
        self._set_buttons_enabled(True)
        self._hide_progress()
        self._set_status(tr("done_with_time", name=self._current_check, time=round(elapsed, 1)), "success")
        QtCore.QTimer.singleShot(3000, lambda: self._set_status(tr("ready")))
        stats = _td_last_stats if _td_last_stats else {}
        # v59: Record to report log
        _params = self._get_check_params("Texel Density")
        _target = self._get_check_target()
        n_entries = len(all_entries) if all_entries else 0
        _worker_profile = getattr(self._worker, '_profile', {})
        _log = getattr(self, '_report_log', None)
        if _log:
            _log.add_entry(
                "Texel Density", _params, _target,
                round(elapsed, 2),
                result_ok=(n_entries == 0), error_count=n_entries,
                profiles=[_worker_profile] if _worker_profile else [])
        tb = getattr(self._worker, '_traceback', None)
        if tb and _log:
            _log.add_error("Texel Density", tb)
        if msg == tr("cancelled"): return
        if not all_entries and not stats:
            QtWidgets.QMessageBox.information(self, WINDOW_TITLE, tr("no_errors")); return
        win = TexelDensityResultsWindow(self._make_result_title(tr("texel_density")), all_entries or [], stats, self)
        win.show()
    # === Material Separator ===
    def _on_mat_sep(self):
        # v33: Pre-check — warn if only 1 material is assigned
        base_name, meshes, needs_separate = _ms_check_single_material()
        if not meshes:
            QtWidgets.QMessageBox.warning(self, WINDOW_TITLE, tr("mat_sep_no_mesh"))
            return
        if not needs_separate:
            QtWidgets.QMessageBox.information(
                self, tr("mat_sep_single_mat_title"),
                tr("mat_sep_single_mat_msg"))
            return
        # v33: Pre-run information (multi-material)
        QtWidgets.QMessageBox.information(
            self, tr("mat_sep_multi_mat_title"),
            tr("mat_sep_multi_mat_msg"))
        self._ms_cancelled = False; s = self._ms_settings
        self._set_buttons_enabled(False)
        self._show_progress()
        self._status_bar.setText(tr("mat_sep_progress_combine"))
        QtWidgets.QApplication.processEvents()
        # v31: Wrap in try/finally to guarantee UI recovery on error
        result = None
        try:
            result = _ms_run_separate(
                merge_uv=s.get("merge_uv", True),
                delete_history_combine=s.get("del_hist_combine", True),
                naming_index=s.get("naming_index", 0),
                do_group=s.get("do_group", True),
                group_name=s.get("group_name", ""),
                freeze_tf=s.get("freeze_tf", True),
                delete_history_separate=s.get("del_hist_separate", True),
                progress_cb=self._on_ms_progress,
                cancel_check=lambda: self._ms_cancelled)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, WINDOW_TITLE,
                "Error: {0}".format(e))
        finally:
            self._set_buttons_enabled(True)
            self._hide_progress()
            self._status_bar.setText(tr("ready"))
        if result is None: return
        if result["cancelled"]:
            msg = tr("mat_sep_summary_cancel", mesh_count=result["mesh_count"])
        else:
            mat_list = "\n".join("  - {0}".format(m) for m in result["mat_names"])
            msg = tr("mat_sep_summary_ok", mat_count=result["mat_count"],
                     mat_list=mat_list, mesh_count=result["mesh_count"], group=result["group"])
        QtWidgets.QMessageBox.information(self, tr("mat_sep_summary_title"), msg)
    def _on_ms_progress(self, current, total, label):
        if total > 0: self._progress_bar.setValue(int(current * 100 / total))
        self._progress_bar.setFormat(label + "  %p%")
        self._set_status(label, "working"); QtWidgets.QApplication.processEvents()
    def _on_mat_sep_settings(self):
        dlg = MaterialSepSettingsDialog(self._ms_settings, self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            self._ms_settings = dlg.get_settings()
    # === Check: UVSet ===
    def _run_check_uvset(self):
        self._target_label = self._get_target_label()
        entries = collect_all_uvsets()
        if entries is None:
            self._record_pre_fail("UVSet Check", "No mesh selected")
            QtWidgets.QMessageBox.warning(self, WINDOW_TITLE, tr("no_mesh")); return
        # v31: All meshes have only map1 -> show "single UVSet" message
        if all(e["is_default"] for e in entries):
            QtWidgets.QMessageBox.information(self, WINDOW_TITLE, tr("uvset_single")); return
        win = ResultsWindow(self._make_result_title(tr("uvset_check")), entries, self)
        win.show()
    def closeEvent(self, event):
        if self._worker and self._worker.isRunning():
            self._worker.cancel(); self._worker.wait()
        super(UVQCToolsWindow, self).closeEvent(event)
# --- [810] worker ---
# depends on: [000] header (QtCore)
# === QThread Worker (v21, pre-1.0: progress + cancel) ===

class QCWorker(QtCore.QThread):
    finished = QtCore.Signal(object, str)
    progress = QtCore.Signal(int, int, str)

    def __init__(self, func, *args, **kwargs):
        parent = kwargs.get('parent', None)
        super(QCWorker, self).__init__(parent)
        self._func = func; self._args = args; self._cancelled = False

    def cancel(self): self._cancelled = True

    def _is_cancelled(self): return self._cancelled

    def _report_progress(self, current, total, label):
        self.progress.emit(current, total, label)

    def run(self):
        self._traceback = None
        self._profile = {}
        self._groups = None
        try:
            result = self._func(*self._args,
                                progress_cb=self._report_progress,
                                cancel_check=self._is_cancelled)
            if isinstance(result, tuple) and len(result) >= 4:
                errors, msg, self._profile, self._groups = result[0], result[1], result[2], result[3]
            elif isinstance(result, tuple) and len(result) >= 3:
                errors, msg, self._profile = result[0], result[1], result[2]
            else:
                errors, msg = result[0], result[1]
            self.finished.emit(errors, msg)
        except Exception as e:
            import traceback
            self._traceback = traceback.format_exc()
            self.finished.emit([], str(e))
# --- [900] entry ---
# depends on: [800] ui (UVQCToolsWindow)
# === Entry Point ===

def launch():
    """Launch UV QC Tools window."""
    UVQCToolsWindow.show_window()


def add_shelf_button(shelf=None):
    """Add a UV QC Tools button to the specified (or current) Maya shelf."""
    if not _IN_MAYA:
        return
    if shelf is None:
        shelf = cmds.shelfTabLayout("ShelfLayout", q=True, st=True)
    cmds.shelfButton(
        parent=shelf,
        label="UV QC",
        annotation="UV QC Tools v{0}".format(__VERSION__),
        command="import uv_qc_tools\nuv_qc_tools.launch()",
        sourceType="python",
        image1="pythonFamily.png"
    )
