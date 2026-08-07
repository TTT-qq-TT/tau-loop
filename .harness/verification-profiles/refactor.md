# Verification Profile: refactor

Use this profile when the goal is structural change with intended behavior parity.

## Checklist

- Run checks that demonstrate behavior parity for the touched path.
- Verify moved or renamed symbols still resolve from all affected call sites.
- Check imports, exports, wiring, and generated references after file movement.
- Confirm no unintended API or schema changes leaked into the diff.
- Record any parity assumptions that were not mechanically verified.
