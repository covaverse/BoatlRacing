# Unreal Skills

Source: `https://github.com/EpicGames/unreal-engine-skills-for-claude-code-plugin` (Epic Games, MIT license).

Installed for Codex at `C:\Users\LEONIDASxII\.codex\skills`:

| Skill | Use in this project |
| --- | --- |
| `unreal-mcp` | Discover live Unreal toolsets, inspect the project, import assets, and verify Editor results. Read this before the next MCP session. |
| `unreal-skill` | Create or maintain project-specific Agent Skills when a workflow is stable enough to reuse. |
| `create-toolset` | Add a custom Unreal MCP toolset only if the built-in toolsets cannot support a required workflow. |

The `unreal-mcp` skill was read and invoked after restarting Codex and Unreal. Live MCP calls now succeed. `AgentSkillToolset.ListSkills` found bundled engine/plugin skills but no project-specific import or boat-assembly skill, so no additional Agent Skill was loaded or created.

For the assembly pass, `BlueprintBasicsSkill` was read through `AgentSkillToolset` and used with live BlueprintTools discovery. Astra reviewed the assembled Blueprint and recorded its remaining mechanical caveats in `Docs/BOAT_ASSEMBLY.md`.

For the physics Pawn pass, the `unreal-mcp` workflow and `BlueprintBasicsSkill` were used to edit and compile the live Blueprint, configure Water plugin buoyancy, and run PIE tests. Astra's read-only review caught reversed A/D steering; that sign was corrected and tested again. Its remaining findings are tracked in `Docs/STATUS.md` and `Docs/WATER_PHYSICS.md`.

For future sessions, begin with `list_toolsets`, then `AgentSkillToolset.ListSkills`, and load any relevant project skill before changing assets. Save project content before and after bulk MCP edits.
