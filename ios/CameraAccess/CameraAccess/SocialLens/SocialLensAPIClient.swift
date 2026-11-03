/*
 * SocialLens backend client: session + analyze. Frames are never written to disk.
 */

import Foundation
import UIKit

struct SocialLensAnalyzeResult: Sendable {
  let notified: Bool
  let cue: String?
  let reply: String?
  let cueType: String?
  let source: String?
  let latencyMs: Int?
  let hudText: String?
}

enum SocialLensAPIError: LocalizedError {
  case badURL
  case http(Int)
  case decode
  case busy

  var errorDescription: String? {
    switch self {
    case .badURL: return "Invalid SocialLens server URL"
    case .http(let code): return "SocialLens HTTP \(code)"
    case .decode: return "Could not decode SocialLens response"
    case .busy: return "Analyze busy"
    }
  }
}

actor SocialLensAPIClient {
  private let session: URLSession
  private var baseURL: URL
  private var sessionId: String?

  init(baseURLString: String) {
    let trimmed = baseURLString.trimmingCharacters(in: .whitespacesAndNewlines)
      .trimmingCharacters(in: CharacterSet(charactersIn: "/"))
    self.baseURL = URL(string: trimmed) ?? URL(string: "http://127.0.0.1:8000")!
    let config = URLSessionConfiguration.ephemeral
    config.timeoutIntervalForRequest = 90
    config.timeoutIntervalForResource = 90
    self.session = URLSession(configuration: config)
  }

  func updateBaseURL(_ string: String) {
    let trimmed = string.trimmingCharacters(in: .whitespacesAndNewlines)
      .trimmingCharacters(in: CharacterSet(charactersIn: "/"))
    if let url = URL(string: trimmed) {
      baseURL = url
      sessionId = nil
    }
  }

  func ensureSession() async throws -> String {
    if let sessionId { return sessionId }
    let url = baseURL.appendingPathComponent("api/sessions")
    var req = URLRequest(url: url)
    req.httpMethod = "POST"
    let (data, resp) = try await session.data(for: req)
    guard let http = resp as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
      throw SocialLensAPIError.http((resp as? HTTPURLResponse)?.statusCode ?? -1)
    }
    guard
      let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
      let sid = json["session_id"] as? String
    else { throw SocialLensAPIError.decode }
    sessionId = sid
    return sid
  }

  func deleteSession() async {
    guard let sid = sessionId else { return }
    sessionId = nil
    let url = baseURL.appendingPathComponent("api/sessions/\(sid)")
    var req = URLRequest(url: url)
    req.httpMethod = "DELETE"
    _ = try? await session.data(for: req)
  }

  /// JPEG base64 without data: prefix. Never logs image bytes.
  func analyze(imageJPEG: Data, t: TimeInterval, transcriptWindow: String = "") async throws -> SocialLensAnalyzeResult {
    let sid = try await ensureSession()
    let b64 = imageJPEG.base64EncodedString()
    let body: [String: Any] = [
      "session_id": sid,
      "t": t,
      "transcript_window": transcriptWindow,
      "image_b64": b64,
      "input_kind": "glasses",
    ]
    let url = baseURL.appendingPathComponent("api/analyze")
    var req = URLRequest(url: url)
    req.httpMethod = "POST"
    req.setValue("application/json", forHTTPHeaderField: "Content-Type")
    req.httpBody = try JSONSerialization.data(withJSONObject: body)
    let (data, resp) = try await session.data(for: req)
    let code = (resp as? HTTPURLResponse)?.statusCode ?? -1
    if code == 429 { throw SocialLensAPIError.busy }
    guard (200..<300).contains(code) else { throw SocialLensAPIError.http(code) }
    guard let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
      throw SocialLensAPIError.decode
    }
    let event = json["event"] as? [String: Any] ?? [:]
    let hud = json["hud"] as? [String: Any]
    return SocialLensAnalyzeResult(
      notified: event["notified"] as? Bool ?? false,
      cue: event["cue"] as? String,
      reply: event["suggested_response"] as? String,
      cueType: event["cue_type"] as? String,
      source: json["source"] as? String,
      latencyMs: json["latency_ms"] as? Int,
      hudText: hud?["text"] as? String
    )
  }
}

enum SocialLensJPEG {
  /// Downscale to ≤640px wide, JPEG quality 0.7 — never write to disk.
  static func encode(_ image: UIImage, maxWidth: CGFloat = 640, quality: CGFloat = 0.7) -> Data? {
    let size = image.size
    guard size.width > 0, size.height > 0 else { return nil }
    let scale = min(1, maxWidth / size.width)
    let target = CGSize(width: size.width * scale, height: size.height * scale)
    let renderer = UIGraphicsImageRenderer(size: target)
    let scaled = renderer.image { _ in
      image.draw(in: CGRect(origin: .zero, size: target))
    }
    return scaled.jpegData(compressionQuality: quality)
  }
}
