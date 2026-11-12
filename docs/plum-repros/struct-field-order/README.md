# Reordered struct literal fields can crash (Plum 0.0.41)

```
mise exec -- plum build docs/plum-repros/struct-field-order -o build/struct-order-check
build/struct-order-check
```

Type checking and building succeed, but this minimal program exits with SIGSEGV
on Linux. The literal gives `enabled` before `label`, while the declaration gives
`label` before `enabled`. Reading the label then uses a null/boolean slot as a
string pointer. Putting the literal fields in declaration order makes the same
program pass. Field names should either determine placement correctly or the
checker should reject the unsupported ordering; accepting it then crashing is
not a valid outcome.

The backup UI exposed this through Session's optional job/progress/cancellation
fields. The workaround constructs records in declaration order. Its idle-session
progress/path regression test and real-input UI test exercise that path. No
upstream issue or Plum source change has been made for this candidate.
