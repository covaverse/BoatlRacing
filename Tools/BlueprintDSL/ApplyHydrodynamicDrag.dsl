(fn ApplyHydrodynamicDrag ()
  (if (Buoyancy|IsInWaterBody (Variables|Default|GetBuoyancy))
    (bind mesh (Variables|Default|GetStaticMesh))
    (bind velocity (Transformation|GetComponentVelocity mesh))
    (bind horizontal (Math|Vector|MakeVector
      :X (.x velocity) :Y (.y velocity) :Z 0.0))
    (bind speed (Math|Vector|VectorLength horizontal))
    (Physics|AddForce mesh (* horizontal (* speed -0.055)))))
