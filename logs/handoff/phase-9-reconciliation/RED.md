# Phase 9 RED Evidence

Phase 9 RED tests target current-main behaviors only. Production implementation has not yet been changed.

RED commit candidate: `f864a005fb2a0b1823c009e19a055eedc66a1324`

Expected failing contracts:

- percent-encoded, zero-width, and fullwidth secret-path disguises are not yet canonicalized;
- an allowed secret basename can authorize the same basename at a different path;
- base64 external authority claims are not decoded before policy evaluation;
- authority claims split across argument fields are not reassembled before evaluation;
- conflicting destination fields can present different hosts to different normalization layers instead of failing closed.

The decisive tests assert handler non-execution on the corrected behavior. CI on this RED candidate must fail for these contracts before any production hardening is written.