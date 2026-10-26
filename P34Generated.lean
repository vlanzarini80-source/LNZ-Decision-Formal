
import LNZCertificatePayloadP33

namespace LNZ

private def p34Cert : BoxCertificate 2 := {
  lo := fun i : Fin 2 =>
    (#[((0 : ℚ) / (1 : ℚ)),
       ((0 : ℚ) / (1 : ℚ))])[i]
  hi := fun i : Fin 2 =>
    (#[((1 : ℚ) / (1 : ℚ)),
       ((1 : ℚ) / (1 : ℚ))])[i]
  coeff := fun i : Fin 2 =>
    (#[((1 : ℚ) / (1 : ℚ)),
       ((2 : ℚ) / (1 : ℚ))])[i]
  witness := fun i : Fin 2 =>
    (#[((1 : ℚ) / (1 : ℚ)),
       ((0 : ℚ) / (1 : ℚ))])[i]
  threshold := ((1 : ℚ) / (1 : ℚ))
  objective := ((1 : ℚ) / (1 : ℚ))
}

/--
P3.4: Explicit validation of a concrete
box-simplex certificate.

No sorry.
No new axioms.
Optimality is not assumed.
-/
private theorem p34Valid :
    ValidBoxCertificate p34Cert := by
  unfold ValidBoxCertificate
  constructor
  · intro i
    fin_cases i <;>
      norm_num [p34Cert]
  constructor
  · norm_num [p34Cert, Fin.sum_univ_succ]
  constructor
  · norm_num [p34Cert, Fin.sum_univ_succ]
  constructor
  · intro i _
    fin_cases i <;>
      norm_num [p34Cert] at *
  · intro i _
    fin_cases i <;>
      norm_num [p34Cert] at *

/--
P3.4: The concrete certificate proves
global optimality for every feasible
competitor.
-/
theorem p34_instance_optimal
    (v : Fin 2 → ℚ)
    (hvlo : ∀ i, p34Cert.lo i ≤ v i)
    (hvhi : ∀ i, v i ≤ p34Cert.hi i)
    (hvsum : ∑ i, v i = 1) :
    p34Cert.objective ≤
      ∑ i, p34Cert.coeff i * v i := by
  exact valid_box_certificate_optimal
    p34Cert p34Valid v hvlo hvhi hvsum

#print axioms LNZ.p34_instance_optimal

end LNZ
