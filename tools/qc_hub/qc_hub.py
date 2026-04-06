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


__VERSION__ = "0.5.0"
__RELEASE_DATE__ = "2026-04-06"

WINDOW_TITLE = "QC Hub"
WINDOW_OBJECT_NAME = "qcHubWindow"


# --- Tool definitions ---------------------------------------------------
# Each entry is a dict with keys: module, label_key, enabled,
#   version_attr, window_names, show_button (optional, default True).
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
    {"module": "qc_hub", "label_key": "tool_qc_hub",
     "enabled": True, "version_attr": "__VERSION__",
     "window_names": ["qcHubWindow"], "show_button": False},
]
# --- [010] strings ---------------------------------------------------------

_TR = {
    "tool_model_qc":     "Model QC Tools",
    "tool_uv_qc":        "UV QC Tools",
    "tool_scene_cleanup": "Scene Cleanup Tools",
    "coming_soon":       "* Coming Soon",
    "launch_fail":       "Failed to launch {name}.",
    "launch_ok":         "Launched {name}.",
    "close_all":         "Close All Tools",
    "closed_all":        "All tools closed",
    "no_tools_open":     "No tools open",
    "check_update_btn":       "Check for Updates",
    "check_update_btn_active": "Updates Available ({n})",
    "checking_updates":       "Checking for updates...",
    "no_updates":             "No updates available.",
    "update_title":           "Updates Available",
    "update_apply_btn":       "Update All",
    "update_all_done":        "All updates applied.",
    "update_partial":         "{success} of {total} updated.",
    "update_fail":            "Update failed for {name}: {error}",
    "update_check_fail":      "Update check failed: {error}",
    "tool_not_found":         "{name} is not installed. Download now?",
    "downloading":            "Downloading...",
    "not_in_manifest":        "{name} is not available for download.",
    "install_ok":             "{name} installed successfully.",
    "install_fail":           "Installation failed: {error}",
}


def tr(key, **kwargs):
    """Return UI string for the given key."""
    text = _TR.get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text
# --- [500] updater -------------------------------------------------------

import hashlib
import json
import os
import sys
import shutil
import importlib

try:
    _reload = importlib.reload
except AttributeError:
    _reload = reload  # Python 2.7 builtin

try:
    from urllib.request import urlopen, Request
    from urllib.error import URLError
except ImportError:
    from urllib2 import urlopen, Request, URLError


MANIFEST_URL = (
    "https://raw.githubusercontent.com/"
    "ryu-japan/qc-tools-release/main/manifest.json")
_BACKUP_SUFFIX = ".bak"


def _get_or_create_script_path(tool_name):
    """Return local .py path and existence flag.

    Returns:
        tuple: (path, exists) where exists is True if the file was found.
    """
    for p in sys.path:
        # Pattern 1: <base>/<tool_name>/<tool_name>.py
        candidate = os.path.join(p, tool_name, tool_name + ".py")
        if os.path.isfile(candidate):
            return candidate, True
        # Pattern 2: <base>/<tool_name>.py
        candidate = os.path.join(p, tool_name + ".py")
        if os.path.isfile(candidate):
            return candidate, True

    # New install: place alongside QC Hub
    hub_dir = os.path.dirname(os.path.abspath(__file__))
    install_path = os.path.join(hub_dir, tool_name + ".py")
    return install_path, False


def _fetch_manifest():
    """Fetch manifest.json from the release repository."""
    req = Request(MANIFEST_URL)
    resp = urlopen(req, timeout=10)
    data = resp.read()
    return json.loads(data.decode("utf-8"))


def _sha256_bytes(data):
    """Return the hex SHA256 digest of the given bytes."""
    return hashlib.sha256(data).hexdigest()


def check_updates():
    """Compare local tool versions with the manifest.

    Returns a list of dicts with keys: module, local_version,
    remote_version, download_url, sha256.
    Empty list means no updates available.
    """
    manifest = _fetch_manifest()
    updates = []
    for tool in _TOOLS:
        module_name = tool["module"]
        entry = manifest.get(module_name)
        if entry is None:
            continue
        remote_ver = entry.get("version", "")
        # Get local version
        try:
            mod = __import__(module_name)
            local_ver = getattr(mod, tool["version_attr"], "")
        except Exception:
            local_ver = ""
        if remote_ver and remote_ver != local_ver:
            updates.append({
                "module": module_name,
                "local_version": local_ver,
                "remote_version": remote_ver,
                "download_url": entry.get("download_url", ""),
                "sha256": entry.get("sha256", ""),
                "is_new_install": local_ver == "",
            })
    return updates


def apply_update(update_info):
    """Download, verify, backup and overwrite a tool script.

    Args:
        update_info: dict with keys module, download_url, sha256.
    Raises:
        RuntimeError: on SHA256 mismatch or file operation failure.
    """
    module_name = update_info["module"]
    download_url = update_info["download_url"]
    expected_sha = update_info["sha256"]

    # Download
    req = Request(download_url)
    resp = urlopen(req, timeout=30)
    data = resp.read()

    # SHA256 verification
    actual_sha = _sha256_bytes(data)
    if expected_sha and actual_sha != expected_sha:
        raise RuntimeError(
            "SHA256 mismatch for {0}: expected {1}, got {2}".format(
                module_name, expected_sha, actual_sha))

    # Find local script or determine install path
    local_path, exists = _get_or_create_script_path(module_name)

    if exists:
        # Backup (1 generation, overwrite)
        bak_path = local_path + _BACKUP_SUFFIX
        try:
            shutil.copy2(local_path, bak_path)
        except Exception as e:
            raise RuntimeError(
                "Backup failed for {0}: {1}".format(module_name, e))

        # Overwrite
        try:
            with open(local_path, "wb") as f:
                f.write(data)
        except Exception as e:
            # Rollback from backup
            try:
                shutil.copy2(bak_path, local_path)
            except Exception:
                pass
            raise RuntimeError(
                "Overwrite failed for {0}: {1}".format(module_name, e))
    else:
        # New install: write directly
        try:
            with open(local_path, "wb") as f:
                f.write(data)
        except Exception as e:
            raise RuntimeError(
                "Install failed for {0}: {1}".format(module_name, e))
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
    "  padding: 2px 12px;"
    "  min-height: 22px;"
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
    "QPushButton#checkUpdateBtn {"
    "  background-color: transparent;"
    "  color: #e0e0e0;"
    "  border: 1px solid #555555;"
    "  border-radius: 6px;"
    "  padding: 2px 12px;"
    "  min-height: 22px;"
    "  font-size: 12px;"
    "  font-weight: normal;"
    "}"
    "QPushButton#checkUpdateBtn:hover {"
    "  background-color: #3c3c3c;"
    "  border: 1px solid #7aa2f7;"
    "}"
    "QPushButton#checkUpdateBtn:pressed {"
    "  background-color: #7aa2f7;"
    "  color: #1a1a1a;"
    "}"
)

# Style applied dynamically when updates are available.
_ACTIVE_UPDATE_BTN_STYLE = (
    "QPushButton {"
    "  background-color: #4D6594;"
    "  color: #e0e0e0;"
    "  border: 1px solid #5B75AB;"
    "  border-radius: 6px;"
    "  padding: 2px 12px;"
    "  min-height: 22px;"
    "  font-size: 12px;"
    "  font-weight: bold;"
    "}"
    "QPushButton:hover {"
    "  background-color: #5A77B0;"
    "  border: 1px solid #7aa2f7;"
    "}"
    "QPushButton:pressed {"
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


class UpdateDialog(QtWidgets.QDialog):
    """Dialog for reviewing and applying tool updates (C-plan)."""

    def __init__(self, updates, parent=None):
        super(UpdateDialog, self).__init__(parent)
        self.setWindowTitle(tr("update_title"))
        self.setMinimumWidth(320)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.Tool)
        self._updates = updates
        self._parent_hub = parent
        self._layout = QtWidgets.QVBoxLayout(self)
        self._layout.setContentsMargins(16, 16, 16, 16)
        self._layout.setSpacing(10)
        self._build_confirm_ui()

    def _build_confirm_ui(self):
        """Build the confirmation screen (step 1)."""
        for upd in self._updates:
            if upd.get("is_new_install"):
                row = QtWidgets.QLabel(
                    "{0}\n  New install \u2192 {1}".format(
                        upd["module"],
                        upd["remote_version"]))
            else:
                row = QtWidgets.QLabel(
                    "{0}\n  {1} \u2192 {2}".format(
                        upd["module"],
                        upd["local_version"] or "\u2014",
                        upd["remote_version"]))
            row.setStyleSheet(
                "color: #e0e0e0; font-size: 12px;"
                " background: transparent;")
            self._layout.addWidget(row)

        self._layout.addSpacing(8)

        btn_lay = QtWidgets.QHBoxLayout()
        apply_btn = QtWidgets.QPushButton(tr("update_apply_btn"))
        apply_btn.clicked.connect(self._apply_all)
        cancel_btn = QtWidgets.QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_lay.addWidget(apply_btn)
        btn_lay.addWidget(cancel_btn)
        self._layout.addLayout(btn_lay)

    def _clear_layout(self):
        """Remove all widgets and sub-layouts from the layout."""
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            sub = item.layout()
            if sub:
                while sub.count():
                    child = sub.takeAt(0)
                    w = child.widget()
                    if w:
                        w.deleteLater()

    def _apply_all(self):
        """Apply all updates and switch to the result screen."""
        results = []
        success_count = 0
        for upd in self._updates:
            try:
                apply_update(upd)
                results.append({
                    "module": upd["module"],
                    "version": upd["remote_version"],
                    "ok": True, "error": ""})
                success_count += 1
            except Exception as e:
                results.append({
                    "module": upd["module"],
                    "version": upd["remote_version"],
                    "ok": False, "error": str(e)})

        # Switch to result screen
        self._clear_layout()

        for res in results:
            if res["ok"]:
                text = "\u2713 {0}  \u2192 {1}".format(
                    res["module"], res["version"])
                color = "#a9dc76"
            else:
                text = "\u2717 {0} \u2014 {1}".format(
                    res["module"], res["error"])
                color = "#ff6188"
            lbl = QtWidgets.QLabel(text)
            lbl.setStyleSheet(
                "color: {0}; font-size: 12px;"
                " background: transparent;".format(color))
            lbl.setWordWrap(True)
            self._layout.addWidget(lbl)

        self._layout.addSpacing(4)
        total = len(self._updates)
        if success_count == total:
            msg_lbl = QtWidgets.QLabel(tr("update_all_done"))
        else:
            msg_lbl = QtWidgets.QLabel(
                tr("update_partial",
                   success=success_count, total=total))
        msg_lbl.setStyleSheet(
            "color: #e0e0e0; font-size: 12px;"
            " background: transparent; font-weight: bold;")
        self._layout.addWidget(msg_lbl)

        self._layout.addSpacing(8)
        close_btn = QtWidgets.QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        self._layout.addWidget(close_btn)

        # Reload updated modules
        self._reload_modules(results)

    def _reload_modules(self, results):
        """Reload updated tool modules and refresh QC Hub."""
        hub_updated = False
        for res in results:
            if not res["ok"]:
                continue
            module_name = res["module"]
            # Close open windows for this tool
            for tool in _TOOLS:
                if tool["module"] == module_name:
                    for wn in tool["window_names"]:
                        for w in QtWidgets.QApplication.topLevelWidgets():
                            if w.objectName() == wn and w.isVisible():
                                w.close()
                    break
            # Reload module
            if module_name in sys.modules:
                try:
                    _reload(sys.modules[module_name])
                except Exception:
                    pass
            if module_name == "qc_hub":
                hub_updated = True

        if hub_updated and self._parent_hub is not None:
            self.close()
            cmds.evalDeferred(
                "import sys; "
                "m = sys.modules.get('qc_hub') or __import__('qc_hub'); "
                "getattr(__import__('importlib'), 'reload', reload)(m); "
                "m.launch()")


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
        self._pending_updates = []
        self._build_ui()
        self.resize(240, self.sizeHint().height())
        # Auto-check for updates on startup
        try:
            self._pending_updates = check_updates()
            if self._pending_updates:
                n = len(self._pending_updates)
                self._update_btn.setText(
                    tr("check_update_btn_active", n=n))
                self._update_btn.setStyleSheet(
                    _ACTIVE_UPDATE_BTN_STYLE)
        except Exception:
            pass

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
            if not tool.get("show_button", True):
                continue
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

        # --- Check for Updates ---
        self._update_btn = QtWidgets.QPushButton(
            tr("check_update_btn"))
        self._update_btn.setObjectName("checkUpdateBtn")
        self._update_btn.clicked.connect(self._check_updates_ui)
        root.addWidget(self._update_btn)

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
    # Check for Updates
    # ------------------------------------------------------------------
    def _check_updates_ui(self):
        """Handle the Check for Updates button click."""
        self._status_bar.showMessage(tr("checking_updates"), 0)
        QtWidgets.QApplication.processEvents()
        try:
            updates = check_updates()
        except Exception as e:
            self._status_bar.showMessage(
                tr("update_check_fail", error=str(e)), 7000)
            return
        finally:
            self._status_bar.clearMessage()

        if not updates:
            self._status_bar.showMessage(tr("no_updates"), 5000)
            # Reset button to default state
            self._update_btn.setText(tr("check_update_btn"))
            self._update_btn.setStyleSheet("")
            self._pending_updates = []
            return

        self._pending_updates = updates
        dlg = UpdateDialog(updates, parent=self)
        dlg.setStyleSheet(_QSS)
        result = dlg.exec_()

        # After dialog closes, refresh version labels
        self._refresh_version_labels()
        if result == QtWidgets.QDialog.Accepted:
            # Updates applied — reset button
            self._update_btn.setText(tr("check_update_btn"))
            self._update_btn.setStyleSheet("")
            self._pending_updates = []
        else:
            # Cancelled — restore active state
            n = len(self._pending_updates)
            self._update_btn.setText(
                tr("check_update_btn_active", n=n))
            self._update_btn.setStyleSheet(
                _ACTIVE_UPDATE_BTN_STYLE)

    def _refresh_version_labels(self):
        """Refresh version labels on tool buttons after updates."""
        grp = self.findChild(QtWidgets.QGroupBox)
        if grp is None:
            return
        grp_lay = grp.layout()
        for i, tool in enumerate(_TOOLS):
            if i >= grp_lay.count():
                break
            btn = grp_lay.itemAt(i).widget()
            if btn is None:
                continue
            btn_lay = btn.layout()
            if btn_lay is None or btn_lay.count() < 2:
                continue
            ver_lbl = btn_lay.itemAt(1).widget()
            if ver_lbl is not None:
                ver_text = self._get_tool_version(
                    tool["module"], tool["version_attr"])
                ver_lbl.setText(ver_text)

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
        except ImportError:
            result = QtWidgets.QMessageBox.question(
                self, WINDOW_TITLE,
                tr("tool_not_found", name=display_name),
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            if result == QtWidgets.QMessageBox.Yes:
                self._download_tool(module_name, label_key)
        except Exception as e:
            msg = tr("launch_fail", name=display_name)
            cmds.warning("{0} ({1})".format(msg, e))

    def _download_tool(self, module_name, label_key):
        """Download a tool that is not installed locally."""
        display_name = tr(label_key)
        self._status_bar.showMessage(tr("downloading"), 0)
        QtWidgets.QApplication.processEvents()
        try:
            manifest = _fetch_manifest()
            entry = manifest.get(module_name)
            if entry is None:
                self._status_bar.showMessage(
                    tr("not_in_manifest", name=display_name), 5000)
                return
            update_info = {
                "module": module_name,
                "download_url": entry.get("download_url", ""),
                "sha256": entry.get("sha256", ""),
                "remote_version": entry.get("version", ""),
            }
            apply_update(update_info)
            __import__(module_name)
            self._refresh_version_labels()
            self._status_bar.showMessage(
                tr("install_ok", name=display_name), 5000)
        except Exception as e:
            self._status_bar.showMessage(
                tr("install_fail", error=str(e)), 7000)
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
