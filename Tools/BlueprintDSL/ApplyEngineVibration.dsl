(fn ApplyEngineVibration (DeltaSeconds)
  (bind visualActor
    (Class|ChildActorComponent|GetChildActor (Variables|Default|GetBoatVisual)))
  (bind boat (Utilities|Casting|CastToBP_ThaiLongtailBoat visualActor))
  (bind speed (Variables|Default|GetBoatSpeed))
  (bind underLoad (> (Math|Float|Absolute(Float)
      (Variables|Default|GetDriveThrust)) 0.25))
  (bind launchOrTopSpeed (or (< speed 400.0) (> speed 900.0)))
  (bind targetEnvelope (select (and underLoad launchOrTopSpeed) 1.0 0.0))
  (Variables|Default|SetEngineVibrationEnvelope
    (Math|Interpolation|FInterpTo
      (Variables|Default|GetEngineVibrationEnvelope)
      targetEnvelope DeltaSeconds 8.0))
  (bind vibrationRPM (* (Variables|Default|GetEngineRPM)
      (Variables|Default|GetEngineVibrationEnvelope)))
  (Class|BPThaiLongtailBoat|SetEngineVibration :self boat
    :RPM vibrationRPM
    :Load (Variables|Default|GetThrottle)
    :DeltaSeconds DeltaSeconds))
