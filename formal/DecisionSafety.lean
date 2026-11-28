import Lean
namespace LNZ
inductive Decision where
  | proven | disproven | insufficient | exhausted | unavailable
  deriving DecidableEq, Repr

-- Evidence is a proof term, not an external receipt or a Boolean assertion.
inductive Evidence (P : Prop) where
  | positive : P → Evidence P
  | negative : (¬ P) → Evidence P
  | absent : Evidence P

def decideEvidence {P : Prop} (e : Evidence P) (budget available : Bool) : Decision :=
  match e with
  | .positive _ => .proven
  | .negative _ => .disproven
  | .absent => if !available then .unavailable else if !budget then .exhausted else .insufficient

theorem proven_sound {P : Prop} (e : Evidence P) (b a : Bool)
    (h : decideEvidence e b a = .proven) : P := by
  cases e with
  | positive hp => exact hp
  | negative hn => simp [decideEvidence] at h
  | absent => cases a <;> cases b <;> simp [decideEvidence] at h

theorem disproven_sound {P : Prop} (e : Evidence P) (b a : Bool)
    (h : decideEvidence e b a = .disproven) : ¬ P := by
  cases e with
  | positive hp => simp [decideEvidence] at h
  | negative hn => exact hn
  | absent => cases a <;> cases b <;> simp [decideEvidence] at h

theorem absent_abstains {P : Prop} (b a : Bool) :
    decideEvidence (Evidence.absent : Evidence P) b a ≠ .proven ∧
    decideEvidence (Evidence.absent : Evidence P) b a ≠ .disproven := by
  cases a <;> cases b <;> simp [decideEvidence]

theorem exhausted_abstains {P : Prop} :
    decideEvidence (Evidence.absent : Evidence P) false true = .exhausted := rfl

theorem unavailable_abstains {P : Prop} (b : Bool) :
    decideEvidence (Evidence.absent : Evidence P) b false = .unavailable := rfl

theorem conflicting_evidence {P : Prop} (hp : P) (hn : ¬ P) : False := hn hp

#print axioms proven_sound
#print axioms disproven_sound
#print axioms absent_abstains
#print axioms exhausted_abstains
#print axioms unavailable_abstains
#print axioms conflicting_evidence
end LNZ
