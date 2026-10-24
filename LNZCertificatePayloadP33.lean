
import LNZCertificateBridge

namespace LNZ

/-!
P3.3: Mathematical interpretation of a validated
box-simplex certificate.

This file does not prove correctness of the Python
JSON parser, SHA-256 hashing or digital signatures.

Requires LNZCertificateBridge.lean and its
certified_global_optimality theorem.
-/

/--
Exact mathematical representation of a
box-simplex optimization certificate.
-/
structure BoxCertificate (n : ℕ) where
  lo : Fin n → ℚ
  hi : Fin n → ℚ
  coeff : Fin n → ℚ
  witness : Fin n → ℚ
  threshold : ℚ
  objective : ℚ

/--
Conditions that an independent certificate
verifier is intended to check.

The optimality conclusion is not included
among these assumptions.
-/
def ValidBoxCertificate {n : ℕ}
    (cert : BoxCertificate n) : Prop :=
  (∀ i,
    0 ≤ cert.lo i ∧
    cert.lo i ≤ cert.witness i ∧
    cert.witness i ≤ cert.hi i ∧
    cert.hi i ≤ 1) ∧
  (∑ i, cert.witness i) = 1 ∧
  cert.objective =
    (∑ i, cert.coeff i * cert.witness i) ∧
  (∀ i,
    cert.lo i < cert.witness i →
      cert.coeff i ≤ cert.threshold) ∧
  (∀ i,
    cert.witness i < cert.hi i →
      cert.threshold ≤ cert.coeff i)

/--
P3.3: A valid mathematical certificate
establishes global optimality against
every feasible competitor.

No sorry.
No new axioms.
No assumption of the desired conclusion.
-/
theorem valid_box_certificate_optimal
    {n : ℕ}
    (cert : BoxCertificate n)
    (hcert : ValidBoxCertificate cert)
    (v : Fin n → ℚ)
    (hvlo : ∀ i, cert.lo i ≤ v i)
    (hvhi : ∀ i, v i ≤ cert.hi i)
    (hvsum : ∑ i, v i = 1) :
    cert.objective ≤
      ∑ i, cert.coeff i * v i := by

  rcases hcert with
    ⟨hb, hsum, hobj, hleft, hright⟩

  have hwlo :
      ∀ i, cert.lo i ≤ cert.witness i := by
    intro i
    exact (hb i).2.1

  have hwhi :
      ∀ i, cert.witness i ≤ cert.hi i := by
    intro i
    exact (hb i).2.2.1

  rw [hobj]

  exact certified_global_optimality
    cert.lo
    cert.hi
    cert.witness
    v
    cert.coeff
    cert.threshold
    hwlo
    hwhi
    hvlo
    hvhi
    hsum
    hvsum
    hleft
    hright

#print axioms LNZ.valid_box_certificate_optimal

end LNZ
