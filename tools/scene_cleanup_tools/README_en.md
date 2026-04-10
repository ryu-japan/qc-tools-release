# Scene Cleanup Tools

A scene cleanup tool for Maya. Check geometry, unnecessary nodes, and scene environment settings in one pass, then interactively review and fix detected issues.

## Basic Workflow

1. Open a scene and launch the tool
2. Review check items (each can be toggled ON/OFF)
3. Click **Check** to run
4. Review detected issues in the results window
5. Use **Fix Selected** to fix as needed

Checks run asynchronously. Track progress with the progress bar, and cancel anytime with the × button.

---

## Check Items

### Geometry

Remaining History, Unfreezed Transforms, Vertex Tweaks, Remaining Instances, Smooth Mesh Preview

### Unused

Intermediate Objects, Empty Groups / Empty Shapes, Unused Materials / Textures, Unused Layers, Empty Object Sets, Empty Namespaces

### Scene Environment

Unknown Nodes, Referenced Nodes, Scene Units / Up-Axis, File Paths

---

## Results Window

- Switch check items in the left panel, review detected nodes in the right panel
- Click a node to select it in the Maya viewport
- Risky nodes are highlighted with a ⚠ icon and color coding
- Use **Fix Selected** to batch-fix selected nodes (with risk-based confirmation)

---

## Send Report

Use the **Send Report** button to submit bug reports or feature requests.