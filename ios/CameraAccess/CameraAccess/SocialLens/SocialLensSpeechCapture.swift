/*
 * Phone-mic speech → rolling transcript window for /api/analyze.
 * Glasses HFP mic is wearer-beamformed; use the phone mic for others' speech.
 * Transcripts are kept in memory only (never written to disk/logs).
 */

import AVFoundation
import Foundation
import Speech

@MainActor
final class SocialLensSpeechCapture {
  private let recognizer = SFSpeechRecognizer(locale: Locale(identifier: "en-US"))
  private var audioEngine: AVAudioEngine?
  private var request: SFSpeechAudioBufferRecognitionRequest?
  private var task: SFSpeechRecognitionTask?

  private var finals: [(t: TimeInterval, text: String)] = []
  private var sessionStart: Date?
  private var generation = 0
  private(set) var lastError: String?

  var isAvailable: Bool { recognizer?.isAvailable == true }

  func start(sessionStart: Date, resetTranscript: Bool = true) async {
    stop()
    let startGeneration = generation
    self.sessionStart = sessionStart
    if resetTranscript { finals = [] }
    lastError = nil

    let speechStatus = await withCheckedContinuation { (cont: CheckedContinuation<SFSpeechRecognizerAuthorizationStatus, Never>) in
      SFSpeechRecognizer.requestAuthorization { cont.resume(returning: $0) }
    }
    guard generation == startGeneration else { return }
    guard speechStatus == .authorized else {
      lastError = "Speech recognition not authorized"
      return
    }

    let micStatus = await AVAudioApplication.requestRecordPermission()
    guard generation == startGeneration else { return }
    guard micStatus else {
      lastError = "Microphone not authorized"
      return
    }

    let session = AVAudioSession.sharedInstance()
    do {
      try session.setCategory(.playAndRecord, mode: .measurement, options: [.defaultToSpeaker, .allowBluetoothHFP])
      try session.setActive(true, options: .notifyOthersOnDeactivation)
    } catch {
      lastError = error.localizedDescription
      return
    }

    let engine = AVAudioEngine()
    let req = SFSpeechAudioBufferRecognitionRequest()
    req.shouldReportPartialResults = true
    req.addsPunctuation = true

    let input = engine.inputNode
    let format = input.outputFormat(forBus: 0)
    input.removeTap(onBus: 0)
    input.installTap(onBus: 0, bufferSize: 1024, format: format) { buffer, _ in
      req.append(buffer)
    }

    guard let recognizer, recognizer.isAvailable else {
      lastError = "Speech recognizer unavailable"
      return
    }

    task = recognizer.recognitionTask(with: req) { [weak self] result, error in
      Task { @MainActor in
        guard let self, self.generation == startGeneration else { return }
        if let result {
          let text = result.bestTranscription.formattedString.trimmingCharacters(in: .whitespacesAndNewlines)
          if result.isFinal, !text.isEmpty {
            let t = Date().timeIntervalSince(self.sessionStart ?? Date())
            self.finals.append((t, text))
            // Keep ~2 minutes of finals in memory max.
            if self.finals.count > 40 {
              self.finals.removeFirst(self.finals.count - 40)
            }
          }
        }
        if let error {
          self.lastError = error.localizedDescription
        }
      }
    }

    engine.prepare()
    do {
      try engine.start()
      self.audioEngine = engine
      self.request = req
    } catch {
      lastError = error.localizedDescription
      stop()
    }
  }

  func stop() {
    generation += 1
    request?.endAudio()
    task?.cancel()
    task = nil
    request = nil
    if let engine = audioEngine {
      engine.inputNode.removeTap(onBus: 0)
      engine.stop()
    }
    audioEngine = nil
  }

  /// Last ~30s of finals as `[m:ss] Someone: text` lines (PROMPTS.md shape).
  func transcriptWindow(now: Date = Date()) -> String {
    let start = sessionStart ?? now
    let cutoff = now.timeIntervalSince(start) - 30
    let lines = finals.filter { $0.t >= cutoff }.map { item in
      let m = Int(item.t) / 60
      let s = Int(item.t) % 60
      return String(format: "[%d:%02d] Someone: %@", m, s, item.text)
    }
    return lines.joined(separator: "\n")
  }
}
