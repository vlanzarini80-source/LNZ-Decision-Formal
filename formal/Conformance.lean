import EvidenceBridge
open LNZBridge
def main : IO Unit := do
  for limit in List.range 257 do
    for used in List.range (limit + 1) do
      if h : used ≤ limit then
        let b : Budget := ⟨limit, used, h⟩
        let result := match reserve b with
          | none => "EXHAUSTED"
          | some c => toString c.used
        IO.println s!"{limit},{used},{result}"
  for (name, r) in [("ACCEPTED", Receipt.accepted), ("REJECTED", Receipt.rejected), ("UNAVAILABLE", Receipt.unavailable)] do
    let out := match classify r with
      | .unattested => "RUNNER_ACCEPTANCE_UNATTESTED"
      | .insufficient => "BUDGET_EXHAUSTED"
      | .unavailable => "VERIFIER_UNAVAILABLE"
    IO.println s!"receipt,{name},{out}"
