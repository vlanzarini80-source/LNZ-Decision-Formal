
import Mathlib

namespace LNZ

/--
Exact change in a two-coordinate linear objective
when epsilon is transferred from i to j.

No feasibility or optimality assumption is used.
-/
theorem exchange_objective_delta
    (ci cj epsilon : ℚ) :
    ci * (-epsilon) + cj * epsilon =
      epsilon * (cj - ci) := by
  ring

/--
If ci ≤ cj and epsilon ≥ 0, transferring epsilon
from coordinate i to coordinate j cannot
decrease the linear objective.
-/
theorem exchange_nonimproving
    (ci cj epsilon : ℚ)
    (hcost : ci ≤ cj)
    (heps : 0 ≤ epsilon) :
    0 ≤ ci * (-epsilon) + cj * epsilon := by
  rw [exchange_objective_delta]
  exact mul_nonneg heps (sub_nonneg.mpr hcost)

#print axioms LNZ.exchange_objective_delta
#print axioms LNZ.exchange_nonimproving

end LNZ
