"""Move each test Ocean's island using the live spline API, then verify and save."""
import unreal


for name in ('M_WaterPhysicsTest', 'M_WaterSmallWavesTest', 'M_WaterHighWavesTest'):
    path = '/Game/Maps/' + name
    world = unreal.EditorLoadingAndSavingUtils.load_map(path)
    assert world
    oceans = [a for a in unreal.EditorLevelLibrary.get_all_level_actors()
              if isinstance(a, unreal.WaterBodyOcean)]
    assert len(oceans) == 1
    spline = oceans[0].get_component_by_class(unreal.WaterSplineComponent)
    assert spline.get_number_of_spline_points() == 4
    for i, (x, y) in enumerate(((60250, 17750), (60250, 18250),
                              (59750, 18250), (59750, 17750))):
        spline.set_location_at_spline_point(i, unreal.Vector(x, y, oceans[0].get_actor_location().z),
                                           unreal.SplineCoordinateSpace.WORLD, False)
        spline.set_spline_point_type(i, unreal.SplinePointType.CURVE, False)
    spline.set_editor_property('spline_has_been_edited', True)
    spline.update_spline()
    for i in range(4):
        point = spline.get_location_at_spline_point(i, unreal.SplineCoordinateSpace.WORLD)
        assert point.x > 50000, (name, point)
    assert unreal.EditorLoadingAndSavingUtils.save_map(world, path)
    print('BOAT_CONTACT_SPLINE_SAVED', name)
