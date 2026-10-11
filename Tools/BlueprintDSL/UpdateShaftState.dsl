(fn UpdateShaftState (DeltaSeconds)
  (bind targetRPM (* (* (Variables|Default|GetEngineRPM) (Variables|Default|GetClutchEngagement)) 0.25))
  (bind currentRPM (Variables|Default|GetShaftRPM))
  (Variables|Default|SetShaftRPM
    (Math|Interpolation|FInterpTo currentRPM targetRPM DeltaSeconds
      (select (< targetRPM currentRPM) 1.67 2.86)))
  (bind rpmFraction (/ (Variables|Default|GetShaftRPM) 1400.0))
  (Variables|Default|SetDriveThrust
    (* (* (Variables|Default|GetThrottle) (Variables|Default|GetClutchEngagement))
       (select (> rpmFraction 1.0) 1.0
         (select (< rpmFraction 0.0) 0.0 rpmFraction)))))
