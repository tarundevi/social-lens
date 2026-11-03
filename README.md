# SocialLens

SocialLens is a web-first multimodal social copilot with a thin native iOS bridge for Ray-Ban Meta camera access.

## Planning docs

Full SocialLens docs: start with [docs/README.md](docs/README.md), then [TASKS/](TASKS/) for the four-computer split, [TASKS/ORCHESTRATOR.md](TASKS/ORCHESTRATOR.md), and [TASKS/PROGRESS.md](TASKS/PROGRESS.md).

## Architecture

```text
Ray-Ban Meta glasses
        |
        v
iPhone bridge (Meta Device Access Toolkit)
        |
        v
Web backend / Grok / browser dashboard
```

A browser cannot directly read the camera on displayless Ray-Ban Meta glasses. The project therefore includes Meta's official CameraAccess sample as the native bridge foundation. The web backend and dashboard can be added independently and receive sampled JPEG frames from this bridge.

## Meta bridge

The Xcode project is at `ios/CameraAccess/CameraAccess.xcodeproj`. It uses Meta Wearables Device Access Toolkit 1.0.1 and includes:

- Meta AI registration and callback handling
- Explicit device-session and camera lifecycle
- Live glasses-camera preview
- Photo and video capture
- Optional glasses microphone audio in video
- Mock Device Kit for development without glasses

The internal Xcode target remains named `CameraAccess` to keep the upstream sample easy to update. The installed app is named **SocialLens Bridge**.

### Requirements

- macOS with Xcode 26.4 or newer
- Swift 6.3 or newer
- iPhone running iOS 17.2 or newer
- Meta AI app installed on the iPhone
- Supported Ray-Ban Meta glasses paired in Meta AI
- Developer Mode enabled in Meta AI under **Settings → Your glasses → Developer Mode**

### Run with real glasses

1. Open `ios/CameraAccess/CameraAccess.xcodeproj` in Xcode.
2. Select the `CameraAccess` app target.
3. Under **Signing & Capabilities**, select your Apple development team.
4. If `com.sociallens.app` is unavailable to your team, replace it with a unique bundle identifier.
5. Select your connected iPhone and run the app.
6. In SocialLens Bridge, tap **Connect** and complete registration in Meta AI.
7. Return to the bridge, tap **Start Session**, and then **Preview**.

Developer Mode does not require `META_APP_ID` or `CLIENT_TOKEN`. Leave both unset for hackathon development. Release channels require credentials from the Wearables Developer Center; store them in local Xcode build settings and never commit them.

### Run without glasses

Build the Debug configuration and use the ladybug button to open Mock Device Kit. The included image/video resources can simulate a connected device and camera feed.

## Current scope

This repository currently establishes the Meta hardware bridge only. Frame upload, the web dashboard, backend authentication, transcription, and Grok reasoning are intentionally left for the next implementation pass.

## Upstream and terms

The bridge is based on Meta's official [`meta-wearables-dat-ios`](https://github.com/meta/meta-wearables-dat-ios) CameraAccess sample at version 1.0.1. Meta's applicable developer terms are preserved in `ios/META_WEARABLES_LICENSE.md`.
