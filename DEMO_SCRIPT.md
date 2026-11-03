# Demo script (60-90 s)

**0-10 s, Hook:** "Captions tell a Deaf user *what* was said, not that a question was aimed at them, that it was sarcasm, or that someone is waving. Graption SocialLens adds that, built on Graption, BDBI's captioning project."
**10-45 s, Live:** Open live.html ("phone/laptop camera, stand-in for glasses"; point at the red capture badge). A teammate says "Vaibhav, want to come to dinner Friday?" and the HUD shows "They asked you to dinner Friday / Say: I'd love to! What time?" Then the teammate waves, and the HUD shows "Someone is waving at you." If live fails, click Demo, then the Dinner / Sarcasm / Wave buttons (labeled DEMO INPUT).
**45-70 s, Recap:** Open recap.html?session=sample, then "Catch me up". Point out the timeline, tone chart (model guesses) and the "Addressed to you" list.
**70-90 s, Integration + Grok:** "Every cue is a Graption-schema `social_cue` event. The HUD maps 1:1 to Meta Ray-Ban Display components; on Wayfarer we speak it. Grok vision + structured outputs for cues, Grok for recap; GrokBot researched and planned this; Cursor built it."

## Show Grok tool use (screenshots ready)
GrokBot chat that produced these docs. Cursor session. Code in `app/grok.py` (Responses API, input_image, json_schema). Network tab showing calls go to our backend only (key server-side).

## Judge Q&A
- **Privacy?** No face recognition, no facial emotion, no storage, visible indicator, consent, delete session.
- **Why not emotions?** Inferring emotions from faces is unreliable and harmful, so we describe tone of voice and gestures as guesses.
- **Latency?** ~3 s cadence plus the model call; dedupe prevents spam; `none` is the default.
- **Why web?** It ships in 90 min, and the API is the same one glasses will call. The DAT camera path is documented.
- **Real Graption integration?** We use its v1.2 schema verbatim and propose v1.3 `social_cue`. The recap fills Graption's planned past-meetings dashboard.
- **Accuracy?** Evidence fields are shown with every cue, confidence is thresholded at 0.6, and the user can mute cues.
- **Cost?** One small JPEG every 3 s only while capturing; can be lowered to on-speech triggers.
