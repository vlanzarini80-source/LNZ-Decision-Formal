
import Mathlib

namespace LNZ

/--
Global optimality certificate for rational box-simplex
linear optimization.

The certificate consists of a threshold lambda and
coordinatewise saturation conditions.

No global optimality assumption is used.
-/

theorem global_optimality_box_simplex
    {n : ℕ}
    (lo hi c w v : Fin n → ℚ)
    (lambda : ℚ)
    (hw_lower : ∀ i, lo i ≤ w i)
    (hw_upper : ∀ i, w i ≤ hi i)
    (hv_lower : ∀ i, lo i ≤ v i)
    (hv_upper : ∀ i, v i ≤ hi i)
    (hw_sum : ∑ i, w i = 1)
    (hv_sum : ∑ i, v i = 1)
    (h_low :
      ∀ i, c i < lambda → w i = hi i)
    (h_high :
      ∀ i, lambda < c i → w i = lo i) :
    (∑ i, c i * w i) ≤
      (∑ i, c i * v i) := by

  have hpoint :
      ∀ i,
        0 ≤ (c i - lambda) * (v i - w i) := by
    intro i
    rcases lt_trichotomy (c i) lambda with hlt | heq | hgt
    · rw [h_low i hlt]
      apply mul_nonneg_of_nonpos_of_nonpos
      · exact sub_nonpos.mpr (le_of_lt hlt)
      · exact sub_nonpos.mpr (hv_upper i)
    · rw [heq]
      simp
    · rw [h_high i hgt]
      apply mul_nonneg
      · exact sub_nonneg.mpr (le_of_lt hgt)
      · exact sub_nonneg.mpr (hv_lower i)

  have hsum :
      0 ≤ ∑ i, (c i - lambda) * (v i - w i) := by
    exact Finset.sum_nonneg (fun i hi => hpoint i)

  have hidentity :
      (∑ i, (c i - lambda) * (v i - w i)) =
        (∑ i, c i * v i) -
        (∑ i, c i * w i) := by
    simp_rw [sub_mul, mul_sub]
    simp only [← Finset.sum_sub_distrib]
    simp only [Finset.sum_sub_distrib]
    simp only [← Finset.mul_sum]
    rw [hv_sum, hw_sum]
    ring

  rw [hidentity] at hsum
  exact sub_nonneg.mp hsum

#print axioms LNZ.global_optimality_box_simplex

end LNZ
