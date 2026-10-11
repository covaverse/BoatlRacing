import unreal


path = "/Game/Maps/M_WaterPhysicsTest"
world = unreal.EditorLoadingAndSavingUtils.load_map(path)
assert world is not None
oceans = [a for a in unreal.EditorLevelLibrary.get_all_level_actors()
          if a.get_class() == unreal.WaterBodyOcean.static_class()]
assert len(oceans) == 1
ocean = oceans[0]
spline = ocean.get_component_by_class(unreal.WaterSplineComponent)
component = ocean.get_editor_property("water_body_component")
print("BOAT_OCEAN_LOCATION", ocean.get_actor_location())
print("BOAT_OCEAN_COLLISION_EXTENTS", component.get_editor_property("collision_extents"))
print("BOAT_OCEAN_SPLINE_POINTS", spline.get_number_of_spline_points())
for i in range(spline.get_number_of_spline_points()):
    print("BOAT_OCEAN_SPLINE", i,
          spline.get_location_at_spline_point(i, unreal.SplineCoordinateSpace.WORLD))
for x in (6000.0, 0.0, -10000.0, -20000.0, -40000.0,
          -60000.0, -100000.0, -140000.0):
    result = component.get_water_surface_info_at_location(
        unreal.Vector(x, 1500.0, 390.0))
    print("BOAT_OCEAN_QUERY", x, result)
