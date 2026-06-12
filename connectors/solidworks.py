"""Open SolidWorks connector notes.

The live COM calls (pywin32) are inlined in the command scripts so they run as one
unit, but this module documents the open connector surface and centralizes the
document-type constants the commands share. Windows + a licensed SolidWorks session
are required; on other platforms the commands emit a macro instead (deck_only).
"""

DOC_PART = 1
DOC_ASSEMBLY = 2
DOC_DRAWING = 3

# Open API surface used by the community commands:
#   OpenDoc6(path, doctype, opts, cfg, errs, warns) -> model
#   model.GetComponents(topOnly) -> [component]   (assembly walk -> bom.py)
#   model.InterferenceDetectionManager -> interference check
#   model.SaveAs3(path, ...) -> STEP export
# See sw_understand.py / sw_diagnostics.py / sw_export.py for usage.
