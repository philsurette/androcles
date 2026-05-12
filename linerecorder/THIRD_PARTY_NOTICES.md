# Third-Party Notices

Generated notices should be added before distribution.

Run:

```sh
npm run audit:licenses
```

All shipped dependencies must satisfy the LineRecorder licensing policy in `planning/linerecorder/linerecorder_design.md`.

## Release Checklist

- Run `npm run audit:licenses` from `linerecorder/`.
- Review every runtime dependency printed by the audit.
- Confirm runtime dependency licenses are MIT, BSD, ISC, Apache-2.0, or another explicitly approved permissive license.
- Reject GPL, LGPL, AGPL, SSPL, BUSL, Commons Clause, unclear-license, and unlicensed runtime packages.
- Review any dependency that touches audio capture, audio encoding, ZIP packaging, browser storage, or future native/Capacitor APIs before adopting it.
- Investigate any `missing-license-file` warning before distribution, even when the package metadata declares an allowed license.
- Update this notices file with generated third-party notices before any public or commercial distribution.
