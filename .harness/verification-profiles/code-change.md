# Verification Profile: code-change

Use this profile for feature work, bug fixes, and behavior-changing code edits.

## Checklist

- Verify the changed behavior directly, not only through static inspection.
- Run the narrowest relevant automated checks for the touched path.
- Check error handling or fallback behavior when the change affects control flow.
- Confirm the final diff stayed inside the allowed file boundary.
- Note any residual risk where the changed behavior was not exercised end-to-end.
