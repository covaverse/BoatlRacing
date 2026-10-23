"""Give the Thai UI font a Latin fallback.

NotoSansThai has no Latin digits or letters, so "V4", "150cc", "<" and "%" rendered as boxes.
Run from a live editor:  python Tools/run_editor_script.py Tools/showroom_fix_thai_font.py
"""
import json

import unreal
from editor_toolset.toolsets.object import ObjectTools

FONT = "/Game/UI/Prototype/Fonts/NotoSansThai_Font"
LATIN_FACE = "/Engine/EngineFonts/Faces/RobotoRegular.RobotoRegular"

font = unreal.load_asset(FONT)
composite = json.loads(ObjectTools.get_properties(font, ["CompositeFont"]))["CompositeFont"]
composite["fallbackTypeface"] = {"typeface": {"fonts": [{"name": "Regular", "font": {
    "fontFilename": "", "hinting": "Default", "loadingPolicy": "LazyLoad", "subFaceIndex": 0,
    "fontFaceAsset": {"refPath": LATIN_FACE}}}]}, "scalingFactor": 1}
assert ObjectTools.set_properties(font, json.dumps({"CompositeFont": composite})), "set CompositeFont failed"
check = json.loads(ObjectTools.get_properties(font, ["CompositeFont"]))["CompositeFont"]["fallbackTypeface"]["typeface"]["fonts"]
assert check and LATIN_FACE in json.dumps(check), check
unreal.EditorAssetLibrary.save_loaded_asset(font, only_if_is_dirty=False)
print("THAI_FONT_FALLBACK_READY")
