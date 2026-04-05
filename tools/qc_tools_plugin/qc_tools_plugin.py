# -*- coding: utf-8 -*-
from __future__ import print_function, division, unicode_literals
import maya.api.OpenMaya as om2
import maya.cmds as cmds

__VERSION__ = "1.0.0"

MENU_NAME = "QCToolsMenu"


def maya_useNewAPI():
    pass


def create_menu():
    if cmds.menu(MENU_NAME, exists=True):
        cmds.deleteUI(MENU_NAME, menu=True)

    cmds.menu(MENU_NAME, parent="MayaWindow", label="QC Tools", tearOff=True)
    cmds.menuItem(label="QC Hub",              command="import qc_hub; qc_hub.launch()")
    cmds.menuItem(divider=True)
    cmds.menuItem(label="Model QC Tools",      command="import model_qc_tools; model_qc_tools.launch()")
    cmds.menuItem(label="UV QC Tools",         command="import uv_qc_tools; uv_qc_tools.launch()")
    cmds.menuItem(label="Scene Cleanup Tools", command="import scene_cleanup_tools; scene_cleanup_tools.launch()")


def delete_menu():
    if cmds.menu(MENU_NAME, exists=True):
        cmds.deleteUI(MENU_NAME, menu=True)


def initializePlugin(plugin):
    om2.MFnPlugin(plugin, "Ryu", "1.0.0")
    create_menu()


def uninitializePlugin(plugin):
    delete_menu()
