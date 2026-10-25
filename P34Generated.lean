import LNZCertificatePayloadP33

namespace LNZ

private def p34Cert : BoxCertificate 2 := {
  lo := (fun i : Fin 2 =>
    (#[((0 : ℚ) / (1 : ℚ)),
       ((0 : ℚ) / (1 : ℚ))])[i]),
  hi := (fun i : Fin 2 =>
    (#[((1 : ℚ) / (1 : ℚ)),
       ((1 : ℚ) / (1 : ℚ))])[i]),
  coeff := (fun i : Fin 2 =>
    (#[((1 : ℚ) / (1 : ℚ)),
       ((2 : ℚ) / (1 : ℚ))])[i]),
  witness := (fun i : Fin 2 =>
    (#[((1 : ℚ) / (1 : ℚ)),
       ((0 : ℚ) / (1 : ℚ))])[i]),
  threshold := ((1 : ℚ) / (1 : ℚ)),
  objective := ((1 : ℚ) / (1 : ℚ))
}

-- Candidate requiring Lean 4.24.0 verification.
private theorem p34Valid :
    ValidBoxCertificate p34Cert := by
  decide

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
