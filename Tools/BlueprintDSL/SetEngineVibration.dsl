(fn SetEngineVibration (RPM Load DeltaSeconds)
  (bind rpmAlpha (select (> RPM 6500.0) 1.0
                   (select (< RPM 0.0) 0.0 (/ RPM 6500.0))))
  (bind loadAlpha (Math|Float|Absolute(Float) Load))
  (bind intensity (* rpmAlpha (+ 0.35 (* loadAlpha 0.65))))
  (bind phase (+ (Variables|Default|GetEngineVibrationPhase)
                 (* DeltaSeconds (+ 600.0 (* rpmAlpha 3000.0)))))
  (Variables|Default|SetEngineVibrationPhase phase)
  (bind shakeA (Math|Trig|Sin(Degrees) phase))
  (bind shakeB (Math|Trig|Sin(Degrees) (* phase 1.31)))
  (bind engine (Variables|Default|GetEngineAssembly))
  (Transformation|SetRelativeLocation :self engine
    :NewLocation (Math|Vector|MakeVector
      :X 0.0 :Y (* intensity (* 0.35 shakeB))
      :Z (* intensity (* 0.8 shakeA))))
  (Transformation|SetRelativeRotation :self engine
    :NewRotation (Math|Rotator|MakeRotator
      :Roll (* intensity (* 0.25 shakeA))
      :Pitch (* intensity (* 0.6 shakeB))
      :Yaw 0.0)))
