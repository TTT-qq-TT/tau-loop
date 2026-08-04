## Summary

Describe the user-visible behavior and why it belongs in the portable core.

## Verification

- [ ] `python3 -m unittest discover -s tests -v`
- [ ] `bash -n bin/tau`
- [ ] Fresh install or target-project lifecycle check when packaging changed

## Boundaries

- [ ] No user state, credentials, machine paths, or unreviewed run logs were added.
- [ ] Documentation does not overstate supervisor, GPU, or Desktop behavior.
