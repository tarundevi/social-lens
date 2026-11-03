# Privacy and ethics

## Hard rules (enforced in code review)
1. **No face recognition or identity.** Never ask the model who someone is, and never store face embeddings. Speaker names come only from a user-made local mapping (speakers.json).
2. **No emotion inference from faces.** Prompts forbid it. UI says "tone of voice" and "model guess". Graption tone tags are shown as "sounded X?".
3. **No retention.** Frames and audio are never written to disk or logs. The event log is in memory and deletable (DELETE session). Sample data is synthetic.
4. **Visible capture indicator** whenever camera or mic is live, plus a one-tap Stop.
5. **Consent:** a start screen explains what is sent (frame + transcript to xAI) and asks for consent. Tell people nearby you're using it.
6. **Key server-side only** (`XAI_API_KEY`). Set `store: false` on image requests (UNVERIFIED param, per xAI's image advice).
7. **Demo honesty:** canned outputs and placeholder images are labeled.

## Ethics framing
- It's assistive, not corrective. Cues are suggestions; the user decides. Neurodivergent mode is opt-in and never "scores" the user.
- Restraint: default to `none`. Interruptions cost attention.
- Third-party data: frames go to xAI (a third party) during live mode, so say so in the consent text. Browser Web Speech in Chrome also sends audio to Google (UNVERIFIED for current Chrome versions; state it as possible).
- Bias: sarcasm and gesture norms vary by culture, so show evidence and confidence.
- Graption repo has no LICENSE file. Ask the BDBI lead before reusing its code beyond the schema.
