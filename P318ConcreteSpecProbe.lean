
import P34Generated

namespace LNZ

/-!
P3.18 candidate: independently written concrete specification.
Checks definitional equality of the fields exposed by the theorem.
Does NOT check private witness/threshold or arbitrary JSON input.
-/

private def p318Spec : BoxCertificate 2 := {
  lo := fun i : Fin 2 =>
    (#[((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))])[i]
  hi := fun i : Fin 2 =>
    (#[((1 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (1 : ℚ))])[i]
  coeff := fun i : Fin 2 =>
    (#[((1 : ℚ) / (1 : ℚ)), ((2 : ℚ) / (1 : ℚ))])[i]
  witness := fun i : Fin 2 =>
    (#[((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))])[i]
  threshold := ((1 : ℚ) / (1 : ℚ))
  objective := ((1 : ℚ) / (1 : ℚ))
}

/-- Kernel-checked definitional-equality bridge for the public theorem. -/
theorem p318_concrete_spec_bound
    (v : Fin 2 → ℚ)
    (hvlo : ∀ i, p318Spec.lo i ≤ v i)
    (hvhi : ∀ i, v i ≤ p318Spec.hi i)
    (hvsum : ∑ i, v i = 1) :
    p318Spec.objective ≤
      ∑ i, p318Spec.coeff i * v i := by
  exact p34_instance_optimal v hvlo hvhi hvsum

#print axioms LNZ.p318_concrete_spec_bound

end LNZ
