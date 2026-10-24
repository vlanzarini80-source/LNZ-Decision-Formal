
import Mathlib

namespace LNZ

/--
P3.2: Mathematical bridge between exchange conditions
and coordinatewise optimality.

The certificate must supply:
* bounds lo and hi;
* a feasible candidate w;
* a feasible competitor v;
* coefficients c and threshold lambda;
* the two exchange inequalities.

No optimality conclusion is assumed.
-/
theorem certified_coordinate_exchange
    {n : ℕ}
    (lo hi w v c : Fin n → ℚ)
    (lambda : ℚ)
    (hw_lo : ∀ i, lo i ≤ w i)
    (hw_hi : ∀ i, w i ≤ hi i)
    (hv_lo : ∀ i, lo i ≤ v i)
    (hv_hi : ∀ i, v i ≤ hi i)
    (hleft : ∀ i, lo i < w i → c i ≤ lambda)
    (hright : ∀ i, w i < hi i → lambda ≤ c i) :
    ∀ i, 0 ≤ (c i - lambda) * (v i - w i) := by
  intro i
  by_cases h : v i < w i
  · have hwl : lo i < w i := lt_of_le_of_lt (hv_lo i) h
    have hc : c i ≤ lambda := hleft i hwl
    have h1 : c i - lambda ≤ 0 := sub_nonpos.mpr hc
    have h2 : v i - w i ≤ 0 := sub_nonpos.mpr (le_of_lt h)
    exact mul_nonneg_of_nonpos_of_nonpos h1 h2
  · have hvw : w i ≤ v i := le_of_not_gt h
    by_cases heq : w i = v i
    · simp [heq]
    · have hwv : w i < v i := lt_of_le_of_ne hvw heq
      have hwh : w i < hi i := lt_of_lt_of_le hwv (hv_hi i)
      have hc : lambda ≤ c i := hright i hwh
      have h1 : 0 ≤ c i - lambda := sub_nonneg.mpr hc
      have h2 : 0 ≤ v i - w i := sub_nonneg.mpr hvw
      exact mul_nonneg h1 h2

/--
P3.2: Global optimality follows from the certified
exchange conditions and the simplex equalities.
-/
theorem certified_global_optimality
    {n : ℕ}
    (lo hi w v c : Fin n → ℚ)
    (lambda : ℚ)
    (hw_lo : ∀ i, lo i ≤ w i)
    (hw_hi : ∀ i, w i ≤ hi i)
    (hv_lo : ∀ i, lo i ≤ v i)
    (hv_hi : ∀ i, v i ≤ hi i)
    (hw_sum : ∑ i, w i = 1)
    (hv_sum : ∑ i, v i = 1)
    (hleft : ∀ i, lo i < w i → c i ≤ lambda)
    (hright : ∀ i, w i < hi i → lambda ≤ c i) :
    (∑ i, c i * w i) ≤ (∑ i, c i * v i) := by
  have hp := certified_coordinate_exchange
    lo hi w v c lambda
    hw_lo hw_hi hv_lo hv_hi hleft hright
  have hs :
      0 ≤ ∑ i, (c i - lambda) * (v i - w i) := by
    exact Finset.sum_nonneg (fun i hi => hp i)
  have hid :
      (∑ i, (c i - lambda) * (v i - w i)) =
      (∑ i, c i * v i) - (∑ i, c i * w i) := by
    simp only [sub_mul, mul_sub, Finset.sum_sub_distrib]
    simp only [← Finset.mul_sum, hv_sum, hw_sum]
    ring
  rw [hid] at hs
  exact sub_nonneg.mp hs

#print axioms LNZ.certified_coordinate_exchange
#print axioms LNZ.certified_global_optimality

end LNZ
