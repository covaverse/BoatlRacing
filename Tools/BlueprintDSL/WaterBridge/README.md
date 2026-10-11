# Applied Native Water Bridge Sources

Applied and compiled through live MCP: `UpdateWaterPropState.dsl`, `ApplyTailWaterSteering.dsl`, `ConfigureBoatMass.dsl`, `LoadHandlingProfile.dsl`.

`UpdateDriveState_0.dsl` is an unapplied QA-timer candidate. Auto-review rejected its graph replacement. Do not bulk-import it or use another route to apply the rejected change. Existing tests use world age and require a fresh Simulate session.

`Tools/integrate_boat_water_bridge.py` is editor-only, not a verified complete reproduction of the live integration. Commandlet editing does not expose the required Blueprint-local actions. See `Docs/HANDOFF.md` and the execution ledger for verified results and backups.
