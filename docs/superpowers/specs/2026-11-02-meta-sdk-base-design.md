# Meta SDK Base Design

## Intent

Give SocialLens a working native iOS foundation for Ray-Ban Meta camera access without spending hackathon time recreating Meta's device registration, camera lifecycle, or mock-device support.

## Scope

- Base the iOS app on Meta's official `CameraAccess` sample from Device Access Toolkit 1.0.1.
- Keep registration, the explicit session/camera lifecycle, live preview, capture support, Mock Device Kit, tests, and licensing.
- Brand the visible app and URL callback as SocialLens while keeping internal Xcode target names unchanged to minimize fragile project-file edits.
- Use Developer Mode without credentials by default and document local release-channel credential configuration without committing secrets.
- Document physical-device and mock-device startup.

## Non-goals

- xAI/Grok API integration.
- Backend services, transcription, social-cue analysis, or the final dashboard.
- Publishing or release-channel enrollment.
- Renaming every imported Swift type and Xcode target.

## Constraints

- Xcode 26.4+, Swift 6.3+, and iOS 17.2+.
- Pin the SDK to Meta's official 1.0.1 package release.
- Do not commit Meta or xAI secrets.
- Preserve capture indicators, runtime permission descriptions, and Meta's upstream developer terms.

## Implementation call

Copy the complete official `samples/CameraAccess` project into `ios/CameraAccess`. Set the display name to `SocialLens`, use `sociallens` as the callback scheme, and change bundle identifiers to placeholder `com.sociallens.app` identifiers that can be replaced before device signing.
