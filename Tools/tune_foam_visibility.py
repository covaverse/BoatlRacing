"""Editor Python: soften the existing surface foam without rebuilding the water graph."""
from pathlib import Path
import unreal
from editor_toolset.toolsets.material import MaterialTools

path = '/Game/Water/Materials/BoatContact/M_WaterBoatContact'
material = unreal.load_asset(path)
foam = next(e for e in MaterialTools.get_expressions(material)
            if e.get_editor_property('desc') == 'BoatRippleFoam')
code = foam.get_editor_property('code')
backup = Path(unreal.Paths.project_saved_dir()) / 'Backups/2026-10-02-foam-blend/foam-before-softening.hlsl'
backup.parent.mkdir(parents=True, exist_ok=True)
if not backup.exists():
    backup.write_text(code, encoding='utf-8')
assert 'smoothstep(0.05, 1.0, amp)' in code and '* 0.88;' in code, 'Unexpected foam version; inspect before tuning'
code = '\n'.join(line for line in code.splitlines()
                 if not line.lstrip().startswith('//') or 'ponytail:' in line)
code = code.replace('smoothstep(0.05, 1.0, amp)', 'smoothstep(0.25, 1.8, amp)')
code = code.replace('* 0.88;', '* 0.30;')
foam.set_editor_property('code', code)
unreal.MaterialEditingLibrary.recompile_material(material)
assert unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False)
assert foam.get_editor_property('code') == code
print('BOAT_SOFT_FOAM_SAVED: cap=0.30, amplitude ramp=0.25..1.8 cm')
