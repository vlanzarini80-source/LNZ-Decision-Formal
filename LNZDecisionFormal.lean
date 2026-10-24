
import Mathlib

namespace LNZ

def Feasible (n : Nat)
    (lo hi w : Fin n → ℚ) : Prop :=
  (∀ i, lo i ≤ w i ∧ w i ≤ hi i) ∧
  (∑ i, w i) = 1

def Objective (n : Nat)
    (c w : Fin n → ℚ) : ℚ :=
  ∑ i, c i * w i

end LNZ
