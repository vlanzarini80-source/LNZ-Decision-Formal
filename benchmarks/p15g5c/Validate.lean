import Lean
set_option autoImplicit false

namespace B01
def sumNat : Nat → Nat | 0 => 0 | n+1 => sumNat n + (n+1)
def positive (n : Nat) : Prop := 2 * sumNat n = n * (n+1)
def negative (n : Nat) : Prop := 2 * sumNat n = n * (n+1) + 1
theorem negative_counterexample : ¬ negative 0 := by
  decide
#print axioms negative_counterexample
end B01

namespace B02
def sumOdd : Nat → Nat | 0 => 0 | n+1 => sumOdd n + (2*n+1)
def positive (n : Nat) : Prop := sumOdd n = n*n
def negative (n : Nat) : Prop := sumOdd n = n*n+1
theorem negative_counterexample : ¬ negative 0 := by
  decide
#print axioms negative_counterexample
end B02

namespace B03
def sumCube : Nat → Nat | 0 => 0 | n+1 => sumCube n + (n+1)^3
def positive (n : Nat) : Prop := 4 * sumCube n = (n*(n+1))^2
def negative (n : Nat) : Prop := 4 * sumCube n = (n*(n+1))^2+1
theorem negative_counterexample : ¬ negative 0 := by
  decide
#print axioms negative_counterexample
end B03

namespace B04
def fact : Nat → Nat | 0 => 1 | n+1 => (n+1)*fact n
def positive (n : Nat) : Prop := 4 ≤ n → 2^n < fact n
def negative (n : Nat) : Prop := 3 ≤ n → 2^n < fact n
theorem negative_counterexample : ¬ negative 3 := by
  decide
#print axioms negative_counterexample
end B04

namespace B05
def revAcc : List Nat → List Nat → List Nat | [], a => a | x::xs, a => revAcc xs (x::a)
def positive (xs : List Nat) : Prop := revAcc xs [] = xs.reverse
def negative (xs : List Nat) : Prop := revAcc xs [] = xs
theorem negative_counterexample : ¬ negative [0,1] := by
  decide
#print axioms negative_counterexample
end B05

namespace B06
def fib : Nat → Nat | 0 => 0 | 1 => 1 | n+2 => fib (n+1) + fib n
def positive (n : Nat) : Prop := Nat.gcd (fib n) (fib (n+1)) = 1
def negative (n : Nat) : Prop := Nat.gcd (fib n) (fib (n+1)) = 2
theorem negative_counterexample : ¬ negative 0 := by
  decide
#print axioms negative_counterexample
end B06

namespace B07
def prime (p : Nat) : Prop := 2 ≤ p ∧ ∀ d : Nat, d ∣ p → d = 1 ∨ d = p
def positive (n : Nat) : Prop := 2 ≤ n → ∃ p : Nat, prime p ∧ p ∣ n ∧ ∀ d : Nat, 2 ≤ d → d ∣ n → p ≤ d
def negative (n : Nat) : Prop := 2 ≤ n → ∃ p : Nat, prime p ∧ p ∣ n ∧ p < n
theorem negative_counterexample : ¬ negative 2 := by
  intro h
  obtain ⟨p, hp, _, hlt⟩ := h (by decide)
  have hge : 2 ≤ p := hp.1
  omega
#print axioms negative_counterexample
end B07

namespace B08
def euclid (a b : Nat) : Nat := if h : b = 0 then a else euclid b (a % b)
termination_by b
decreasing_by exact Nat.mod_lt _ (Nat.pos_of_ne_zero h)
def positive (a b : Nat) : Prop := euclid a b ∣ a ∧ euclid a b ∣ b
def negative (a b : Nat) : Prop := euclid a b ∣ a ∧ euclid a b ∣ b ∧ euclid a b = 1
theorem negative_counterexample : ¬ negative 2 2 := by
  intro h
  have he := h.2.2
  have hn : euclid 2 2 ≠ 1 := by decide
  exact hn he
#print axioms negative_counterexample
end B08

namespace B09
def ins (x : Nat) : List Nat → List Nat | [] => [x] | y::ys => if x ≤ y then x::y::ys else y::ins x ys
def sort : List Nat → List Nat | [] => [] | x::xs => ins x (sort xs)
def positive (xs : List Nat) : Prop := (sort xs).Pairwise (· ≤ ·) ∧ List.Perm (sort xs) xs
def negative (xs : List Nat) : Prop := (sort xs).Pairwise (· < ·) ∧ List.Perm (sort xs) xs
theorem negative_counterexample : ¬ negative [1,1] := by
  intro h
  have hs := h.1
  have hn : ¬ (sort [1,1]).Pairwise (· < ·) := by decide
  exact hn hs
#print axioms negative_counterexample
end B09

namespace B10

def positive  : Prop := ¬ ∃ p q : Nat, 0 < q ∧ p*p = 2*q*q
def negative  : Prop := ¬ ∃ p q : Nat, 0 < q ∧ p*p = 4*q*q
theorem negative_counterexample : ¬ negative  := by
  intro h
  exact h ⟨2, 1, by decide, by decide⟩
#print axioms negative_counterexample
end B10
