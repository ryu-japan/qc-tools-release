# -*- coding: utf-8 -*-
"""QC Hub - QC Tool Launcher for Maya

Maya 2018 / 2023 / 2025 (Python 2.7 / 3, PySide2 / PySide6) compatible
"""
from __future__ import print_function, division, unicode_literals

from maya import cmds

try:
    from PySide6 import QtCore, QtWidgets
    from shiboken6 import wrapInstance
except ImportError:
    from PySide2 import QtCore, QtWidgets
    from shiboken2 import wrapInstance

from maya import OpenMayaUI


def get_maya_main_window():
    """Return the Maya main window as a QWidget."""
    ptr = OpenMayaUI.MQtUtil.mainWindow()
    if ptr is not None:
        return wrapInstance(int(ptr), QtWidgets.QWidget)
    return None


__VERSION__ = "0.3.3"
__RELEASE_DATE__ = "2026-04-06"

WINDOW_TITLE = "QC Hub"
WINDOW_OBJECT_NAME = "qcHubWindow"


# --- Tool definitions ---------------------------------------------------
# Each entry is a dict with keys: module, label_key, enabled,
#   version_attr, window_names.
# To add a new tool, append one dict here.
_TOOLS = [
    {"module": "model_qc_tools", "label_key": "tool_model_qc",
     "enabled": True, "version_attr": "__VERSION__",
     "window_names": ["modelQCToolsWindow", "modelQCResultsWindow", "modelQCHelpDialog"]},
    {"module": "uv_qc_tools", "label_key": "tool_uv_qc",
     "enabled": True, "version_attr": "__VERSION__",
     "window_names": ["uvQCToolsWindow", "uvQCResultsWindow", "uvQCPixelEdgeResultsWindow",
                       "uvQCOverlapResultsWindow", "uvQCOrientationResultsWindow",
                       "uvQCTexelDensityResultsWindow", "uvQCHelpDialog"]},
    {"module": "scene_cleanup_tools", "label_key": "tool_scene_cleanup",
     "enabled": True, "version_attr": "__VERSION__",
     "window_names": ["sceneCleanupToolsWindow", "sceneCleanupResultsWindow", "sceneCleanupHelpDialog"]},
]
# --- [010] strings ---------------------------------------------------------

_TR = {
    "tool_model_qc":     "Model QC Tools",
    "tool_uv_qc":        "UV QC Tools",
    "tool_scene_cleanup": "Scene Cleanup Tools",
    "coming_soon":       "* Coming Soon",
    "launch_fail":       "Failed to launch {name}. Please check the script is installed.",
    "launch_ok":         "Launched {name}.",
    "close_all":         "Close All Tools",
    "closed_all":        "All tools closed",
    "no_tools_open":     "No tools open",
}


def tr(key, **kwargs):
    """Return UI string for the given key."""
    text = _TR.get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text
# --- [800] ui -----------------------------------------------------------

# Flat-design dark theme for QC tool family UI.
_QSS = (
    "QWidget#qcHubWindow {"
    "  background-color: #2b2b2b;"
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
    "QPushButton {"
    "  background-color: #3c3c3c;"
    "  color: #e0e0e0;"
    "  border: 1px solid #555555;"
    "  border-radius: 6px;"
    "  padding: 4px 12px;"
    "  min-height: 30px;"
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
    "QStatusBar {"
    "  background: transparent;"
    "  color: #888888;"
    "  font-size: 11px;"
    "}"
    "QStatusBar::item {"
    "  border: none;"
    "}"
    "QPushButton#closeAllBtn {"
    "  background-color: transparent;"
    "  color: #e0e0e0;"
    "  border: 1px solid #555555;"
    "  border-radius: 6px;"
    "  padding: 4px 12px;"
    "  min-height: 26px;"
    "  font-size: 12px;"
    "  font-weight: normal;"
    "}"
    "QPushButton#closeAllBtn:hover {"
    "  background-color: #3c3c3c;"
    "  border: 1px solid #7aa2f7;"
    "}"
    "QPushButton#closeAllBtn:pressed {"
    "  background-color: #7aa2f7;"
    "  color: #1a1a1a;"
    "}"
)


# Label style templates (color placeholder filled at runtime).
_NAME_LBL_STYLE = (
    "font-size: 13px; font-weight: bold;"
    " color: {0}; background: transparent;")
_VER_LBL_STYLE = (
    "font-size: 10px; font-weight: normal;"
    " color: {0}; background: transparent;")
_LBL_COLOR_NORMAL = "#e0e0e0"
_LBL_COLOR_PRESSED = "#1a1a1a"


class QCHubUI(QtWidgets.QWidget):

    # ------------------------------------------------------------------
    # Init
    # ------------------------------------------------------------------
    def __init__(self, parent=None):
        super(QCHubUI, self).__init__(parent)
        self.setWindowTitle(WINDOW_TITLE)
        self.setObjectName(WINDOW_OBJECT_NAME)
        self.setMinimumWidth(240)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.Tool)
        self.setStyleSheet(_QSS)
        self._build_ui()
        self.resize(240, self.sizeHint().height())

    # ------------------------------------------------------------------
    # UI Build
    # ------------------------------------------------------------------
    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 10)
        root.setSpacing(8)

        # --- Tool buttons (grouped) ---
        grp = QtWidgets.QGroupBox("")
        grp_lay = QtWidgets.QVBoxLayout(grp)
        grp_lay.setSpacing(6)
        grp_lay.setContentsMargins(4, 4, 4, 4)

        for tool in _TOOLS:
            btn = QtWidgets.QPushButton()
            btn.setEnabled(tool["enabled"])
            if not tool["enabled"]:
                btn.setToolTip(tr("coming_soon"))
            btn.clicked.connect(
                lambda checked=False, m=tool["module"],
                       k=tool["label_key"]: self._on_launch(m, k))

            btn_lay = QtWidgets.QVBoxLayout(btn)
            btn_lay.setContentsMargins(4, 4, 4, 4)
            btn_lay.setSpacing(0)

            name_lbl = QtWidgets.QLabel(tr(tool["label_key"]))
            name_lbl.setAlignment(QtCore.Qt.AlignCenter)
            name_lbl.setStyleSheet(
                _NAME_LBL_STYLE.format(_LBL_COLOR_NORMAL))
            name_lbl.setAttribute(
                QtCore.Qt.WA_TransparentForMouseEvents)
            btn_lay.addWidget(name_lbl)

            ver_text = self._get_tool_version(
                tool["module"], tool["version_attr"])
            ver_lbl = QtWidgets.QLabel(ver_text)
            ver_lbl.setAlignment(QtCore.Qt.AlignCenter)
            ver_lbl.setStyleSheet(
                _VER_LBL_STYLE.format(_LBL_COLOR_NORMAL))
            ver_lbl.setAttribute(
                QtCore.Qt.WA_TransparentForMouseEvents)
            btn_lay.addWidget(ver_lbl)

            # Sync label color with button pressed state.
            btn.pressed.connect(
                lambda n=name_lbl, v=ver_lbl: (
                    n.setStyleSheet(
                        _NAME_LBL_STYLE.format(_LBL_COLOR_PRESSED)),
                    v.setStyleSheet(
                        _VER_LBL_STYLE.format(_LBL_COLOR_PRESSED))))
            btn.released.connect(
                lambda n=name_lbl, v=ver_lbl: (
                    n.setStyleSheet(
                        _NAME_LBL_STYLE.format(_LBL_COLOR_NORMAL)),
                    v.setStyleSheet(
                        _VER_LBL_STYLE.format(_LBL_COLOR_NORMAL))))

            grp_lay.addWidget(btn)

        root.addWidget(grp)

        # --- Close All Tools ---
        close_all_btn = QtWidgets.QPushButton(tr("close_all"))
        close_all_btn.setObjectName("closeAllBtn")
        close_all_btn.clicked.connect(self._close_all_tools)
        root.addWidget(close_all_btn)

        root.addStretch()

        # --- Status bar (version display) ---
        self._status_bar = QtWidgets.QStatusBar()
        self._status_bar.setSizeGripEnabled(False)
        self._version_label = QtWidgets.QLabel(
            "{0} {1}".format(WINDOW_TITLE, __VERSION__))
        self._version_label.setStyleSheet(
            "color: #888888; font-size: 11px;")
        self._status_bar.addPermanentWidget(self._version_label)
        root.addWidget(self._status_bar)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _get_tool_version(module_name, version_attr):
        """Return version string of the given tool module, or dash."""
        try:
            mod = __import__(module_name)
            ver = getattr(mod, version_attr, None)
            return ver if ver else "\u2014"
        except Exception:
            return "\u2014"

    # ------------------------------------------------------------------
    # Close All Tools
    # ------------------------------------------------------------------
    def _close_all_tools(self):
        """Close all open QC tool windows."""
        tool_names = set()
        for t in _TOOLS:
            tool_names.update(t["window_names"])
        closed = 0
        for w in QtWidgets.QApplication.topLevelWidgets():
            if w.objectName() in tool_names and w.isVisible():
                w.close()
                closed += 1
        if closed > 0:
            msg = tr("closed_all")
        else:
            msg = tr("no_tools_open")
        self._status_bar.showMessage(msg, 5000)

    # ------------------------------------------------------------------
    # Launch
    # ------------------------------------------------------------------
    def _on_launch(self, module_name, label_key):
        """Import and launch the target tool."""
        display_name = tr(label_key)
        try:
            mod = __import__(module_name)
            mod.launch()
            print(tr("launch_ok", name=display_name))
        except Exception as e:
            msg = tr("launch_fail", name=display_name)
            cmds.warning("{0} ({1})".format(msg, e))
# --- [900] entry --------------------------------------------------------

def launch():
    """Show QC Hub window (singleton)."""
    global _qc_hub_window

    # Close existing instance
    try:
        if _qc_hub_window is not None:
            _qc_hub_window.close()
            _qc_hub_window.deleteLater()
    except Exception:
        pass

    _qc_hub_window = QCHubUI(parent=get_maya_main_window())
    _qc_hub_window.show()
    return _qc_hub_window


_qc_hub_window = None
