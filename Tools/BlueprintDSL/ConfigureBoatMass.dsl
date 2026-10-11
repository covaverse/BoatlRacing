(fn ConfigureBoatMass ()
  (bind hull (Variables|Default|GetHullMassKg))
  (bind engine (Variables|Default|GetEngineMassKg))
  (bind total (+ hull engine))
  (if (> total 1.0)
    (bind mesh (Variables|Default|GetStaticMesh))
    (bind desiredCenterX (/ (+ (* hull -20.0)
                               (* engine (Variables|Default|GetEngineCenterX))) total))
    (bind offsetX (- desiredCenterX 75.7777778))
    (Physics|SetMassOverrideInKg mesh :MassInKg total :bOverrideMass true)
    (Physics|SetCenterOfMass mesh
      :CenterOfMassOffset (Math|Vector|MakeVector
        :X offsetX :Y 0.0 :Z -25.0))))
