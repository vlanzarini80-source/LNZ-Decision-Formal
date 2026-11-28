import Lean
namespace LNZBridge
inductive Receipt where
  | accepted | rejected | unavailable
  deriving DecidableEq
inductive Outcome where
  | unattested | insufficient | unavailable
  deriving DecidableEq

def classify : Receipt → Outcome
  | .accepted => .unattested
  | .rejected => .insufficient
  | .unavailable => .unavailable

theorem accepted_unattested : classify .accepted = .unattested := rfl
theorem rejected_insufficient : classify .rejected = .insufficient := rfl

structure Budget where
  limit : Nat
  used : Nat
  valid : used ≤ limit

def reserve (b : Budget) : Option Budget :=
  if h : b.used < b.limit then
    some ⟨b.limit, b.used + 1, h⟩
  else none

theorem reserve_bounded (b c : Budget) (_h : reserve b = some c) :
    c.used ≤ c.limit := c.valid

theorem reserve_exhausted (b : Budget) (h : b.used = b.limit) :
    reserve b = none := by
  simp [reserve, h]

theorem reserve_increments (b c : Budget) (h : reserve b = some c) :
    c.used = b.used + 1 ∧ c.limit = b.limit := by
  unfold reserve at h
  split at h
  · have he := Option.some.inj h
    subst c
    exact ⟨rfl, rfl⟩
  · contradiction

#print axioms accepted_unattested
#print axioms rejected_insufficient
#print axioms reserve_bounded
#print axioms reserve_exhausted
#print axioms reserve_increments
end LNZBridge
