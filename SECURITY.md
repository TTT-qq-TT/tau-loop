# Security Policy

## Supported Surface

The current `main` branch and tagged releases are supported for security fixes.

## Reporting

Do not open a public issue for a suspected vulnerability, credential leak, unsafe deletion path, or command-injection risk. Contact the repository owner privately through GitHub's security advisory flow once the public repository exists. Include the affected version, reproduction steps, impact, and any suggested mitigation.

## Trust Boundary

TauLoop executes the commands declared in a run contract. Treat every contract as code: inspect its JSON `argv`, working directory, network use, paths, and declared permissions before execution. The permission fields are recorded for review; they are not an operating-system sandbox.

Never place credentials, tokens, private paths, or unredacted logs in a run contract, handoff package, issue, or pull request.
