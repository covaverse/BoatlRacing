import unreal


def describe(name, selected):
    cls = getattr(unreal, name, None)
    if cls is None:
        print("UE_PROBE_MISSING", name)
        return
    print("UE_PROBE_CLASS", name)
    for method in selected:
        member = getattr(cls, method, None)
        print("UE_PROBE_METHOD", name, method, (member.__doc__ or "")[:1200] if member else "MISSING")


describe("InterchangeManager", ("get_interchange_manager_scripted", "import_asset", "import_scene"))
describe("AssetTools", ("import_asset_tasks",))
describe("AssetImportTask", ())
describe("InterchangeSourceData", ())
describe("ImportAssetParameters", ())
describe("ImportSceneParameters", ())
print("UE_PROBE_PROJECT", unreal.Paths.project_dir())
