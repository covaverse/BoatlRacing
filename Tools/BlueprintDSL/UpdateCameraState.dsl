(fn UpdateCameraState ()
  (if (Pawn|IsLocallyControlled self)
    (bind controller (Game|GetPlayerController 0))
    (bind cameraKey (Game|Player|IsInputKeyDown controller "C"))
    (if (and cameraKey (not (Variables|Default|GetCameraKeyWasDown)))
      (Variables|Default|SetCameraMode
        (select (== (Variables|Default|GetCameraMode) 3)
          0 (+ (Variables|Default|GetCameraMode) 1)))
      (if (== (Variables|Default|GetCameraMode) 3)
        (Variables|Default|SetOrbitWorldYaw
          (+ (.yaw (Transformation|GetWorldRotation (Variables|Default|GetStaticMesh))) 150.0))
        (Variables|Default|SetOrbitPitch -12.0)))
    (Variables|Default|SetCameraKeyWasDown cameraKey)
    (if (== (Variables|Default|GetCameraMode) 3)
      (bind (mouseX mouseY) (Game|Player|GetInputMouseDelta controller))
      (Variables|Default|SetOrbitWorldYaw
        (+ (Variables|Default|GetOrbitWorldYaw) (* mouseX 0.2)))
      (bind nextPitch (- (Variables|Default|GetOrbitPitch) (* mouseY 0.15)))
      (Variables|Default|SetOrbitPitch
        (select (< nextPitch -65.0) -65.0
          (select (> nextPitch 15.0) 15.0 nextPitch)))
      (bind wheel (Game|Player|GetInputAnalogKeyState controller "MouseWheelAxis"))
      (bind nextArm (- (Variables|Default|GetOrbitArmLength) (* wheel 80.0)))
      (Variables|Default|SetOrbitArmLength
        (select (< nextArm 350.0) 350.0
          (select (> nextArm 1400.0) 1400.0 nextArm)))))
  (bind mode (Variables|Default|GetCameraMode))
  (bind boom (Variables|Default|GetChaseBoom))
  (Transformation|SetRelativeLocation :self boom
    :NewLocation (Math|Vector|MakeVector
      :X (select (== mode 0) -210.0 (select (== mode 1) 10.0 35.0))
      :Y 0.0
      :Z (select (== mode 0) 105.0 (select (== mode 1) 145.0 105.0))))
  (Transformation|SetRelativeRotation :self boom
    :NewRotation (Math|Rotator|MakeRotator
      :Roll 0.0
      :Pitch (select (== mode 3) (Variables|Default|GetOrbitPitch)
               (select (== mode 0) -12.0 (select (== mode 1) -9.0 -12.0)))
      :Yaw (select (== mode 3)
             (- (Variables|Default|GetOrbitWorldYaw)
                (.yaw (Transformation|GetWorldRotation (Variables|Default|GetStaticMesh))))
             (select (< mode 2) 180.0 150.0))))
  (Class|SpringArmComponent|SetTargetArmLength :self boom
    :TargetArmLength (select (< mode 2) 0.0
      (select (== mode 3) (Variables|Default|GetOrbitArmLength) 900.0))))
