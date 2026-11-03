# Glasses integration (stretch track: one person, abandon at minute 30)

All names below come from github.com/facebook/meta-wearables-dat-ios v1.0.1 samples (CameraAccess, DisplayAccess, BirdSpotter). The repo README says "developer preview"; Meta's FAQ says 1.0 is stable. iOS 17.2+.

## Modules
`MWDATCore`, `MWDATCamera`, `MWDATDisplay` (Ray-Ban Display only), `MWDATMockDevice`, plus experimental `MWDATInputs`, `MWDATMotion` and `MWDATSpeech` (you can build and test them, but not publish).

## Setup
1. Meta AI app → App connections → **Developer mode** on. Then Info.plist `MWDAT` dict: `AppLinkURLScheme`, `MetaAppID`, `ClientToken`, `TeamID` (CameraAccess comments say ID and token are only needed without Developer Mode).
2. Open `samples/CameraAccess` in Xcode, set the signing team, and run on an iPhone.
3. No glasses? `MockDeviceKit.shared.enable(config: MockDeviceKitConfig(initiallyRegistered: false))`, then `MockDeviceKit.shared.pairGlasses(model: .rayBanMeta)`.
4. AI help: `claude plugin marketplace add facebook/meta-wearables-dat-ios` then `claude plugin install mwdat-ios@mwdat-ios-marketplace`; Cursor: `./install-skills.sh cursor`; docs MCP `https://mcp.developer.meta.com/wearables`.

## Camera path (as seen in the samples)
```swift
try Wearables.configure()
let wearables = Wearables.shared
wearables.startRegistration()                 // deeplinks to Meta AI; handle return with Wearables.shared.handleUrl(url)
guard try await wearables.requestPermission(.camera) == .granted else { return }
let session = try wearables.createSession(deviceSelector: AutoDeviceSelector(wearables: wearables))
let config = StreamConfiguration(videoCodec: VideoCodec.hvc1, resolution: StreamingResolution.low, frameRate: 24)
let camera = try session.addCamera(config: config)
camera?.stream.videoFramePublisher.listen { frame in /* decode → UIImage (see sample VideoFrameDecoder), every 3 s JPEG → POST /api/analyze with input_kind "glasses" */ }
camera?.stream.start()
```
UNVERIFIED: the exact frame-to-JPEG path (copy `VideoFrameDecoder.swift` from CameraAccess), and the available resolution and fps limits.

## Audio limitation
- The glasses mic over Bluetooth **HFP** (8/16 kHz mono) is beamformed to the **wearer**, so it suppresses other people's speech. For other people's words, use the **phone mic** (Web Speech / Apple speech on phone).
- In-stream camera audio (`StreamConfiguration.audioCodec`, `audioFramePublisher`) is experimental and dev/beta channels only.
- HFP and A2DP are mutually exclusive.

## Output
- **Ray-Ban Meta Wayfarer (no display):** speak the cue through the glasses speakers with iOS `AVSpeechSynthesizer` (BirdSpotter's `SystemSpokenOutput` does this). Keep it ≤ 6 words: "Question for you: dinner Friday".
- **Meta Ray-Ban Display:** `device.supportsDisplay()`, `let display = try session.addDisplay()`, `try await display.send(view)`. View:
```swift
FlexBox(direction: .column, spacing: 12) {
  Text("They asked you to dinner Friday", style: .heading)
  Text("Say: I'd love to! What time?", style: .body)
  Text("model guess", style: .meta, color: .secondary)
}
```
Verified in samples: `FlexBox(direction:spacing:alignment:crossAlignment:wrap:)`, `Text(_:style:color:)` with styles `.heading/.body/.meta`, `Button(label:style:iconName:onClick:)`. Each send replaces the whole screen. UNVERIFIED: a standalone `Icon` component's exact signature (only `iconName:` on Button was seen).
- Our `app/cues.py` `to_display_tree()` emits this same FlexBox/Text shape, so the port is mechanical.

## Privacy
The DAT docs say Meta does not access media transferred directly from the glasses to the third-party app. Our rules still apply: no frame storage, and the capture indicator is shown in the phone UI.
