(fn UpdateEngineAudio ()
  (bind loop (Variables|Default|GetEngineLoopAudio))
  (bind rpm (Variables|Default|GetEngineRPM))
  (if (and (> rpm 100.0) (not (Variables|Default|GetEngineAudioStarted)))
    (Audio|Components|Audio|Play (Variables|Default|GetEngineStartAudio))
    (Audio|Components|Audio|Play loop)
    (Variables|Default|SetEngineAudioStarted true))
  (if (Variables|Default|GetEngineAudioStarted)
    (Class|AudioComponent|SetPitchMultiplier :self loop
      :PitchMultiplier (+ 0.75 (* (/ rpm 6500.0) 0.6)))
    (Class|AudioComponent|SetVolumeMultiplier :self loop
      :VolumeMultiplier (+ 0.15 (*
        (Math|Float|Absolute(Float) (Variables|Default|GetThrottle)) 0.3)))))
