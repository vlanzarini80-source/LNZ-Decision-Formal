import TrustedEvidencePolicy
open LNZTrusted
def main : IO Unit := do
  for n in List.range 256 do
    let b (i : Nat) := (n / 2^i) % 2 == 1
    let e : Evidence := ⟨b 0, b 1, b 2, b 3, b 4, b 5, b 6, b 7⟩
    let d := match decideEvidence e with
      | .reject => "REJECT"
      | .abstain => "ABSTAIN"
      | .certify => "CERTIFY"
    IO.println s!"{n},{d}"
