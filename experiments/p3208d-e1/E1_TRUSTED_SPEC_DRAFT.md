
# LNZ P320.8d / E1
## Trusted Mathematical Specification — Draft

**Status:** DRAFT — NOT APPROVED  
**Experiment:** E1  
**Execution status:** NOT EXECUTED

---

## 1. Mathematical Domain

- Index set: `Fin 3`
- Coefficient field: `ℚ`
- Problem class: Box-constrained simplex linear programming

## 2. Problem Data

Let:

- `lo : Fin 3 → ℚ` be the lower bounds.
- `hi : Fin 3 → ℚ` be the upper bounds.
- `c : Fin 3 → ℚ` be the objective coefficients.
- `w : Fin 3 → ℚ` be the candidate witness.

## 3. Feasibility Conditions

A vector `v : Fin 3 → ℚ` is feasible if:

1. `lo i ≤ v i` for every `i : Fin 3`.
2. `v i ≤ hi i` for every `i : Fin 3`.
3. `∑ i, v i = 1`.

The candidate witness `w` must satisfy the same conditions.

## 4. Mathematical Objective

Define:

\[
f(v)=\sum_{i=0}^{2}c_i v_i
\]

The objective is to prove:

\[
\forall v\in\mathcal F,\quad f(w)\le f(v)
\]

where `𝓕` is the feasible set.

This is a global minimization statement.

## 5. Trust Boundary

- The mathematical specification must be independent of the candidate solution.
- The generator must not modify trusted definitions or statements.
- Concrete coefficients must be checked against the original problem source.
- The verifier must not accept candidate-supplied hashes as trusted references.
- Expected optimal values must not be inserted into the verification algorithm.
- The trusted specification requires separate review and approval.

## 6. Verification Requirements

The experiment must distinguish:

- Lean kernel verification.
- Assumption and axiom auditing.
- Mathematical specification matching.
- Original-data correspondence.
- Independent numerical or exact-arithmetic checks.

Passing one layer does not imply passing the others.

## 7. Experimental Status

**Trusted specification:** NOT APPROVED  
**Lean challenge:** NOT IMPLEMENTED  
**Baseline comparison:** NOT EXECUTED  
**LNZ evaluation:** NOT EXECUTED  

No mathematical verification result is claimed by this document.
