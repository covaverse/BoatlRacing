(fn UpdateWaterPropState ()
  (Variables|Default|SetPropImmersion 0.0)
  (bind visual (Utilities|Casting|CastToBP_ThaiLongtailBoat
      :Object (Class|ChildActorComponent|GetChildActor (Variables|Default|GetBoatVisual)))
    (:then
      (bind propPos (Transformation|GetWorldLocation
        (Class|BPThaiLongtailBoat|GetPropellerPivot :self visual)))
      (Variables|Default|SetPropWorldPosition propPos)
      (Variables|Default|SetPropWorldZ (.z propPos))
      (bind waterBodies (Buoyancy|GetCurrentWaterBodyComponents
        (Variables|Default|GetBuoyancy)))
      (if (> (Utilities|Array|Length waterBodies) 0)
        (bind waterBody (Utilities|Array|Get(acopy) waterBodies 0))
        (bind (waterPos waterNormal waterVelocity waterDepth valid)
          (WaterBody|GetWaterSurfaceInfoAtLocation :self waterBody
            :InLocation propPos :bIncludeDepth false))
        (if valid
          (Variables|Default|SetWaterSurfaceZ (.z waterPos))
          (bind depth (- (.z waterPos) (.z propPos)))
          (Variables|Default|SetPropImmersion
            (select (< depth 0.0) 0.0
              (select (> depth 4.0) 1.0 (/ depth 4.0))))
          (if (!= (Variables|Default|GetThrottle) 0.0)
            (bind trimCorrection (* 0.4 (+ (- (.z propPos) (.z waterPos)) 4.0)))
            (bind requestedOffset (+ (Variables|Default|GetTrimTargetDegrees) 0.0))
            (bind autoTarget (+ (- (Variables|Default|GetTrimDegrees) trimCorrection)
                                requestedOffset))
            (Variables|Default|SetTrimTargetDegrees
              (select (< autoTarget -40.0) -40.0
                (select (> autoTarget 14.0) 14.0 autoTarget))))))
      (Variables|Default|SetDriveThrust
        (* (Variables|Default|GetDriveThrust) (Variables|Default|GetPropImmersion))))
    (:CastFailed
      (Variables|Default|SetDriveThrust 0.0))))
