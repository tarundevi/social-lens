# Meta SDK Base Setup

- [x] Import Meta's official CameraAccess sample at Device Access Toolkit 1.0.1.
- [x] Apply minimal SocialLens display, callback, and bundle configuration.
- [x] Preserve Meta's developer terms, Mock Device Kit, and sample tests.
- [x] Document Xcode, Developer Mode, mock-device, and physical-device setup.
- [x] Resolve packages and run the strongest build/test verification available locally.
- [x] Review the diff for secrets and unintended files.

## Review

- Meta Device Access Toolkit resolved from the official repository at exactly 1.0.1.
- `plutil` validated the app plist and entitlements.
- A Debug build for the generic iOS Simulator completed with `** BUILD SUCCEEDED **` using Xcode 26.1 and code signing disabled.
- The full UI test run and unit-only run both stalled after building while waiting on the simulator test runner, so they were stopped; no test failure was emitted.
- A secret scan found no Meta or xAI credentials.
- A fresh reviewer found no critical or important issues.
