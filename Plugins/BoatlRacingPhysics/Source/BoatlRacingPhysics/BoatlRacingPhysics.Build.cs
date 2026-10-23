using UnrealBuildTool;

public class BoatlRacingPhysics : ModuleRules
{
    public BoatlRacingPhysics(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new[] { "Core", "CoreUObject", "Engine", "RHI", "RenderCore", "Water", "UMG", "Slate", "SlateCore", "InputCore", "DeveloperSettings" });
    }
}
