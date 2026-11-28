import Lean
namespace LNZTrusted
structure Evidence where
  signature : Bool
  context : Bool
  worker : Bool
  fresh : Bool
  compiled : Bool
  axioms : Bool
  attested : Bool
  sufficient : Bool
inductive Decision where
  | reject | abstain | certify
  deriving DecidableEq

def valid (e : Evidence) : Bool := e.signature && e.context && e.worker && e.fresh && e.compiled && e.axioms
def decideEvidence (e : Evidence) : Decision :=
  if valid e then
    if e.attested && e.sufficient then .certify else .abstain
  else .reject

theorem invalid_signature (e : Evidence) (h : e.signature = false) :
    decideEvidence e = .reject := by
  simp [decideEvidence, valid, h]

theorem incompatible_context (e : Evidence) (h : e.context = false) :
    decideEvidence e = .reject := by
  simp [decideEvidence, valid, h]

theorem unauthorized_worker (e : Evidence) (h : e.worker = false) :
    decideEvidence e = .reject := by
  simp [decideEvidence, valid, h]

theorem replayed_receipt (e : Evidence) (h : e.fresh = false) :
    decideEvidence e = .reject := by
  simp [decideEvidence, valid, h]

theorem failed_compilation (e : Evidence) (h : e.compiled = false) :
    decideEvidence e = .reject := by
  simp [decideEvidence, valid, h]

theorem forbidden_axioms (e : Evidence) (h : e.axioms = false) :
    decideEvidence e = .reject := by
  simp [decideEvidence, valid, h]

theorem unattested_abstains (e : Evidence) (h : e.attested = false) (hv : valid e = true) :
    decideEvidence e = .abstain := by
  simp [decideEvidence, hv, h]

theorem insufficient_abstains (e : Evidence) (h : e.sufficient = false) (hv : valid e = true) :
    decideEvidence e = .abstain := by
  simp [decideEvidence, hv, h]

theorem certify_requires_all (e : Evidence) (h : decideEvidence e = .certify) :
    valid e = true ∧ e.attested = true ∧ e.sufficient = true := by
  cases e with
  | mk a b c d f g i j =>
    cases a <;> cases b <;> cases c <;> cases d <;> cases f <;> cases g <;> cases i <;> cases j <;> simp_all [decideEvidence, valid]

#print axioms invalid_signature
#print axioms incompatible_context
#print axioms unauthorized_worker
#print axioms replayed_receipt
#print axioms failed_compilation
#print axioms forbidden_axioms
#print axioms unattested_abstains
#print axioms insufficient_abstains
#print axioms certify_requires_all
end LNZTrusted
