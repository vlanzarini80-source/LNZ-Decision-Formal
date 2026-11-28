import Lean
namespace LNZTransition
inductive Phase where
  | ready | waiting | stopped
  deriving DecidableEq
inductive Event where
  | candidate | accepted | rejected | unavailable | timeout | invalid
  deriving DecidableEq
def step (p : Phase) (e : Event) (now deadline : Nat) (remaining : Bool) : Phase :=
  if p = .stopped then .stopped
  else if deadline ≤ now then .stopped
  else match p, e with
    | .ready, .candidate => if remaining then .waiting else .stopped
    | .waiting, .rejected => if remaining then .ready else .stopped
    | _, _ => .stopped

theorem terminal_absorbing (e : Event) (n d : Nat) (r : Bool) :
    step .stopped e n d r = .stopped := by simp [step]
theorem deadline_stops (p : Phase) (e : Event) (n d : Nat) (r : Bool)
    (h : d ≤ n) : step p e n d r = .stopped := by
  cases p <;> simp [step, h]
theorem accepted_stops (p : Phase) (n d : Nat) (r : Bool) :
    step p .accepted n d r = .stopped := by
  cases p <;> by_cases h : d ≤ n <;> simp [step, h]
theorem invalid_stops (p : Phase) (n d : Nat) (r : Bool) :
    step p .invalid n d r = .stopped := by
  cases p <;> by_cases h : d ≤ n <;> simp [step, h]
#print axioms terminal_absorbing
#print axioms deadline_stops
#print axioms accepted_stops
#print axioms invalid_stops
end LNZTransition
