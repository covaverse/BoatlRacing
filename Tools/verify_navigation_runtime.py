import unreal


world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert world, "Start PIE first"
controller = unreal.GameplayStatics.get_player_controller(world, 0)
widgets = unreal.WidgetLibrary.get_all_widgets_of_class(world, unreal.UserWidget, True)
navigation = [widget for widget in widgets if widget.get_class().get_name() in ("WBP_TestMenu_C", "WBP_TestDriveNavigation_C")]
assert len(navigation) == 1, "Expected one navigation overlay, got " + str(len(navigation))
print("NAV_RUNTIME", world.get_name(), navigation[0].get_class().get_name(), "camera", controller.get_view_target().get_name(), "pawn", str(controller.get_pawn()))
