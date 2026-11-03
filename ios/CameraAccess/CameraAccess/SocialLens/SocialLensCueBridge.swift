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
  var transcriptPreview: String = ""

  private var client: SocialLensAPIClient
  private var loopTask: Task<Void, Never>?
  private let speech = AVSpeechSynthesizer()
  private let speechCapture = SocialLensSpeechCapture()
  private var sessionStart: Date?
  private var frameProvider: (() -> UIImage?)?

  init() {
    #if targetEnvironment(simulator)
    let fallback = "http://127.0.0.1:8000"
    #else
    // Device: must set Base URL in the server settings sheet (LAN IP of the laptop).
    let fallback = "http://127.0.0.1:8000"
    #endif
    let stored = UserDefaults.standard.string(forKey: defaultsKey)
    let initial = (stored?.isEmpty == false) ? stored! : fallback
    self.baseURLString = initial
    self.client = SocialLensAPIClient(baseURLString: initial)
  }

  func start(frameProvider: @escaping () -> UIImage?) {
    guard isEnabled else { return }
    stop(clearSession: false)
    self.frameProvider = frameProvider
    let start = Date()
    sessionStart = start
    captureActive = true
    #if !targetEnvironment(simulator)
    if baseURLString.contains("127.0.0.1") || baseURLString.contains("localhost") {
      statusText = "Set SocialLens Base URL to http://<mac-lan-ip>:8000"
      captureActive = false
      return
    }
    #endif
    statusText = "SocialLens connecting…"
    Task { await speechCapture.start(sessionStart: start) }
    loopTask = Task { [weak self] in
      await self?.runLoop()
    }
  }

  /// Soft pause: keep session + last frames; hard stop tears down.
  func pauseAnalyze() {
    loopTask?.cancel()
    loopTask = nil
    isAnalyzing = false
    captureActive = false
    speechCapture.stop()
    statusText = "SocialLens paused (stream paused)"
  }

  @discardableResult
  func resumeAnalyzeIfNeeded() -> Bool {
    guard isEnabled, frameProvider != nil, loopTask == nil else { return false }
    captureActive = true
    statusText = "SocialLens resuming…"
    if let sessionStart {
      Task { await speechCapture.start(sessionStart: sessionStart, resetTranscript: false) }
    }
    loopTask = Task { [weak self] in
      await self?.runLoop()
    }
    return true
  }

  func stop(clearSession: Bool = true) {
    loopTask?.cancel()
    loopTask = nil
    frameProvider = nil
    captureActive = false
    isAnalyzing = false
    transcriptPreview = ""
    speechCapture.stop()
    statusText = "SocialLens idle"
    if clearSession {
      Task { await client.deleteSession() }
    }
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
    if isAnalyzing { return }
    isAnalyzing = true
    defer { isAnalyzing = false }

    // Encode off the main actor to avoid hitching the preview.
    let jpeg: Data? = await Task.detached(priority: .userInitiated) {
      SocialLensJPEG.encode(image)
    }.value
    guard let jpeg else { return }

    let transcript = speechCapture.transcriptWindow()
    transcriptPreview = transcript
    if let err = speechCapture.lastError, transcript.isEmpty {
      // Non-fatal: vision-only still works.
      statusText = "mic/speech: \(err)"
    }

    let t = Date().timeIntervalSince(sessionStart ?? Date())
    do {
      let result = try await client.analyze(
        imageJPEG: jpeg,
        t: t,
        transcriptWindow: transcript
      )
      lastLatencyMs = result.latencyMs
      let speechNote = transcript.isEmpty ? "vision-only" : "vision+transcript"
      statusText = "\(result.source ?? "?") · \(result.latencyMs ?? 0) ms · \(result.cueType ?? "-") · \(speechNote)"
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
    // Glasses speakers: keep it glanceable (≤ ~6 words).
    let words = text.split { $0.isWhitespace || $0.isNewline }.prefix(6)
    let spoken = words.joined(separator: " ")
    guard !spoken.isEmpty else { return }
    let utterance = AVSpeechUtterance(string: spoken)
    utterance.rate = AVSpeechUtteranceDefaultSpeechRate
    utterance.voice = AVSpeechSynthesisVoice(language: "en-US")
    speech.stopSpeaking(at: .immediate)
    speech.speak(utterance)
  }
}
