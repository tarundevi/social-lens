/*
 * Every ~3s while streaming: JPEG frame → POST /api/analyze (input_kind glasses),
 * speak notified cues via AVSpeechSynthesizer. No frame persistence.
 */

import AVFoundation
import Foundation
import Observation
import UIKit

@MainActor
@Observable
final class SocialLensCueBridge {
  private let defaultsKey = "sociallens.baseURL"

  var baseURLString: String {
    didSet { UserDefaults.standard.set(baseURLString, forKey: defaultsKey) }
  }
  var isEnabled: Bool = true
  var statusText: String = "SocialLens idle"
  var lastCueText: String = ""
  var lastLatencyMs: Int?
  var isAnalyzing: Bool = false
  var captureActive: Bool = false

  private var client: SocialLensAPIClient
  private var loopTask: Task<Void, Never>?
  private let speech = AVSpeechSynthesizer()
  private var sessionStart: Date?
  private var frameProvider: (() -> UIImage?)?

  init() {
    #if targetEnvironment(simulator)
    let fallback = "http://127.0.0.1:8000"
    #else
    // Device default: Mac LAN IP from hackathon machine; edit in UI if needed.
    let fallback = "http://10.90.44.69:8000"
    #endif
    let stored = UserDefaults.standard.string(forKey: defaultsKey)
    let initial = (stored?.isEmpty == false) ? stored! : fallback
    self.baseURLString = initial
    self.client = SocialLensAPIClient(baseURLString: initial)
  }

  func start(frameProvider: @escaping () -> UIImage?) {
    guard isEnabled else { return }
    stop()
    self.frameProvider = frameProvider
    sessionStart = Date()
    captureActive = true
    statusText = "SocialLens connecting…"
    loopTask = Task { [weak self] in
      await self?.runLoop()
    }
  }

  func stop() {
    loopTask?.cancel()
    loopTask = nil
    frameProvider = nil
    captureActive = false
    isAnalyzing = false
    statusText = "SocialLens idle"
    Task { await client.deleteSession() }
  }

  func applyBaseURL() {
    Task { await client.updateBaseURL(baseURLString) }
  }

  private func runLoop() async {
    await client.updateBaseURL(baseURLString)
    do {
      let sid = try await client.ensureSession()
      statusText = "SocialLens session \(sid)"
    } catch {
      statusText = "SocialLens: \(error.localizedDescription)"
      captureActive = false
      return
    }

    while !Task.isCancelled {
      await tick()
      try? await Task.sleep(nanoseconds: 3_000_000_000)
    }
  }

  private func tick() async {
    guard let image = frameProvider?() else {
      statusText = "SocialLens waiting for frame…"
      return
    }
    guard let jpeg = SocialLensJPEG.encode(image) else { return }
    if isAnalyzing { return }
    isAnalyzing = true
    defer { isAnalyzing = false }

    let t = Date().timeIntervalSince(sessionStart ?? Date())
    do {
      let result = try await client.analyze(imageJPEG: jpeg, t: t)
      lastLatencyMs = result.latencyMs
      statusText = "\(result.source ?? "?") · \(result.latencyMs ?? 0) ms · \(result.cueType ?? "-")"
      if result.notified {
        let speak = result.hudText ?? result.cue ?? "Social cue"
        lastCueText = speak
        speakCue(speak)
      }
    } catch SocialLensAPIError.busy {
      // silent per product rules for 429
    } catch {
      statusText = "SocialLens: \(error.localizedDescription)"
    }
  }

  private func speakCue(_ text: String) {
    // Keep ≤ ~6 words when possible for glasses speakers.
    let utterance = AVSpeechUtterance(string: text)
    utterance.rate = AVSpeechUtteranceDefaultSpeechRate
    utterance.voice = AVSpeechSynthesisVoice(language: "en-US")
    speech.stopSpeaking(at: .immediate)
    speech.speak(utterance)
  }
}
