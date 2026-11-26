import Lean

set_option autoImplicit false

theorem lnz_reverse_append (α : Type) (xs ys : List α) :
    (xs ++ ys).reverse = ys.reverse ++ xs.reverse := by
  induction xs with
  | nil => simp
  | cons x xs ih => simp [List.reverse_cons, ih, List.append_assoc]

#print axioms lnz_reverse_append
