(fn UpdateWaterPropState ()
  (Variables|Default|SetPropImmersion 0.0)
  (Variables|Default|SetWaterSurfaceZ 0.0)
  (Variables|Default|SetPropWaterVelocity (Math|Vector|MakeVector 0.0 0.0 0.0))
  (bind visual (Utilities|Casting|CastToBP_ThaiLongtailBoat
      :Object (Class|ChildActorComponent|GetChildActor (Variables|Default|GetBoatVisual)))
    (:then
      (bind propPos (Transformation|GetWorldLocation
        (Class|BPThaiLongtailBoat|GetPropellerPivot :self visual)))
      (Variables|Default|SetPropWorldPosition propPos)
      (Variables|Default|SetPropWorldZ (.z propPos))
      (bind (height flow valid) (Boat|Water|SampleWaveSurface
        :Buoyancy (Variables|Default|GetBuoyancy) :WorldLocation propPos))
      (if valid
        (Variables|Default|SetWaterSurfaceZ height)
        (Variables|Default|SetPropWaterVelocity flow)
        (bind depth (- height (.z propPos)))
        (Variables|Default|SetPropImmersion
          (select (< depth 0.0) 0.0
            (select (> depth 4.0) 1.0 (/ depth 4.0))))
        (if (!= (Variables|Default|GetThrottle) 0.0)
          (bind correction (* 0.4 (+ (- (.z propPos) height) 4.0)))
          (bind autoTarget (+ (- (Variables|Default|GetTrimDegrees) correction)
                              (Variables|Default|GetTrimTargetDegrees)))
          (Variables|Default|SetTrimTargetDegrees
            (select (< autoTarget -40.0) -40.0
              (select (> autoTarget 14.0) 14.0 autoTarget)))))
      (Variables|Default|SetDriveThrust
        (* (Variables|Default|GetDriveThrust) (Variables|Default|GetPropImmersion)))
      (CallFunction|ApplyLaunchPitch :self self
        :DeltaSeconds (Utilities|Time|GetWorldDeltaSeconds)))
    (:CastFailed
      (Variables|Default|SetDriveThrust 0.0))))
