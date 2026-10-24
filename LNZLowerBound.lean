
import Mathlib

namespace LNZ

theorem objective_lower_bound
    {n : ℕ}
    (c v : Fin n → ℚ)
    (lambda : ℚ)
    (hv_nonneg : ∀ i, 0 ≤ v i)
    (hv_sum : ∑ i, v i = 1)
    (hc : ∀ i, lambda ≤ c i) :
    lambda ≤ ∑ i, c i * v i := by
  have hpoint :
      ∀ i, lambda * v i ≤ c i * v i := by
    intro i
    exact mul_le_mul_of_nonneg_right (hc i) (hv_nonneg i)
  have hsum :
      ∑ i, lambda * v i ≤ ∑ i, c i * v i := by
    exact Finset.sum_le_sum (fun i hi => hpoint i)
  have hfactor :
      (∑ i, lambda * v i) = lambda := by
    rw [← Finset.mul_sum, hv_sum]
    ring
  rw [hfactor] at hsum
  exact hsum

#print axioms LNZ.objective_lower_bound

end LNZ
