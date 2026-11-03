# Meta SDK Base Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a buildable SocialLens iOS foundation using Meta's official CameraAccess sample and Device Access Toolkit 1.0.1.

**Architecture:** Vendor the complete official sample project under `ios/CameraAccess` so registration, camera lifecycle, media handling, mocks, and tests stay coherent. Apply only low-risk product configuration changes and keep future SocialLens/Grok work outside this setup pass.

**Tech Stack:** SwiftUI, Swift 6.3, iOS 17.2+, Xcode 26.4+, Meta Wearables Device Access Toolkit 1.0.1 via Swift Package Manager.

**Spec:** `docs/superpowers/specs/2026-11-02-meta-sdk-base-design.md`

## Global Constraints

- Keep the SDK pinned to the official 1.0.1 release.
- Do not commit credentials or developer-specific signing values.
- Preserve Meta's source headers, developer terms, mock support, and tests.
- Keep internal Xcode project and target names unchanged in this pass.

## Review Focus

- Missing transport/privacy declarations must not prevent real or mock device links.
- The callback URL scheme in the project and `Info.plist` must match.
- Developer Mode must remain usable with empty Meta credentials.
- The package reference must resolve to the official repository at exactly 1.0.1.
- The app must have a neutral placeholder bundle identifier and no developer team committed.

---

### Task 1: Import and configure the official camera sample

**Files:**
- Create: `ios/CameraAccess/**`
- Create: `ios/META_WEARABLES_LICENSE.md`
- Modify: `ios/CameraAccess/CameraAccess/Info.plist`
- Modify: `ios/CameraAccess/CameraAccess.xcodeproj/project.pbxproj`

**Interfaces:**
- Consumes: Meta's official `samples/CameraAccess` tree at release 1.0.1.
- Produces: An Xcode project with SocialLens display name, callback scheme, placeholder bundle IDs, SDK package products, camera lifecycle, and Mock Device Kit.

- [ ] Copy the complete upstream CameraAccess sample and developer terms.
- [ ] Change only product display name, callback scheme, and bundle identifiers.
- [ ] Confirm credentials and development team remain unset.
- [ ] Verify package references, entitlements, privacy strings, and background modes structurally.

### Task 2: Document setup and verify the project

**Files:**
- Modify: `README.md`
- Modify: `tasks/todo.md`

**Interfaces:**
- Consumes: The configured Xcode project from Task 1.
- Produces: Reproducible local setup, mock testing, physical-device testing, and verification instructions.

- [ ] Document prerequisites, Xcode signing, Developer Mode, mock flow, physical glasses flow, and credential handling.
- [ ] Resolve Swift packages with `xcodebuild`.
- [ ] Build and test an available simulator destination, or record the exact local toolchain blocker.
- [ ] Review the final diff for secrets and unintended upstream artifacts.

## Self-review

The plan covers the scoped design, keeps the imported project cohesive, and avoids unrequested Grok/backend behavior. Verification explicitly covers package version, callback alignment, transport declarations, credentials, signing, build, tests, and secret scanning.
