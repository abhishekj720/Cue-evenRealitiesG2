# Cue — 5-Minute Pitch Script

> Stage directions in _italics_. Spoken lines in **bold** where emphasis matters.
> Slide numbers match `docs/Cue-Pitch.pptx`.
>
> **Cast:**
> - **Javeed** — wears the G2, drives the slides, delivers the pitch.
> - **Abhishek** — live demo partner; speaks one sentence mid-pitch.

---

## 0:00 – 0:20 · Hook

**[Slide 1 — CUE title]**

_Javeed walks to center stage wearing the G2. Pauses. Looks at the audience._

> _(calm, unhurried)_  "Raise your hand if you forgot someone's name this week."

_Beat. Lets hands go up. Some nervous laughter._

> "Keep it up if you felt that little micro-panic when you saw them across the room."

_Beat._

**[Advance to Slide 2 — The Hook]**

> **"I met 40 people today. I remember maybe 6 names."**

_Let the quote breathe on screen for 2 seconds._

> **"That's not a me problem. It's an interface problem."**

---

## 0:20 – 1:00 · The wedge

**[Advance to Slide 3 — The Wedge]**

> "Meta Ray-Bans tried to solve this with a camera.
> A camera gets you thrown out of bars. Out of hospitals. Out of therapy offices. Out of the rooms where memory actually matters."

_Gesture to the G2 on your face._

> "The Even G2 has no camera. And that's not a weakness —
> **that's its unique advantage.**"

_Pause. Then deliver the line slowly:_

> **"Meta Ray-Bans remember faces.
> Cue remembers people."**

_Pause 2 seconds. Let the line land._

---

## 1:00 – 2:30 · Live demo (THE CENTERPIECE)

**[Advance to Slide 4 — LIVE DEMO]**

_Javeed steps slightly aside. Keeps the HUD mirror visible on screen so the audience can see what Javeed sees._

> "Let me show you.
> I met my co-builder Abhishek this morning at the coffee bar. He introduced himself. I tapped my right temple. Cue captured his voiceprint, his intro, and the context of our conversation."

_Turn toward the edge of the stage._

> "Abhishek — come say hi."

_Abhishek walks up from stage-left, casually, as if continuing a conversation._

**Abhishek:**
> **"Hey Javeed — about that script pairing, I pushed the fix last night. Want to walk through it?"**

_~1 second pause. The HUD flashes Abhishek's card. The mirror on the screen shows it in real time. Audience sees the card render._

_Javeed reads the HUD — doesn't glance down, just reads. Then looks at Abhishek and replies as if he totally remembered:_

**Javeed:**
> **"Abhishek — yeah, how did the script pairing work out?"**

_Abhishek smiles, walks off stage._

_Javeed turns back to camera._

> "You saw what just happened.
> Cue heard Abhishek's voice.
> Matched it against a local voiceprint I captured hours ago.
> Pulled the context from our morning conversation.
> And pushed a card onto my HUD with **what to say next** — before I even opened my mouth."

_Pause._

> "All of this happened on the phone in my pocket.
> No cloud. No camera. No face database."

---

## 2:30 – 3:00 · What lands on the HUD

**[Advance to Slide 5 — What lands on the HUD]**

> "Every card is four things. Name. What they do. The last thing they promised. And one line suggesting what to say next."

_Point at the Priya card._

> "This is Priya from Acme. She owes me a beta invite.
> So the card reminds me — _ask about onboarding friction._
> I don't have to improvise. The conversation resumes where it left off."

**[Advance to Slide 6 — End-to-end HUD states]**

> "Quiet when nothing's happening. Bright when a known voice speaks. One tap to mute when I want to be fully present."

---

## 3:00 – 3:40 · How it works

**[Advance to Slide 7 — How it works]**

_Walk the audience through the flow diagram in one breath:_

> "Mic captures speech.
> Silero VAD gates out silence.
> Resemblyzer encodes the voice as a 256-dimensional vector.
> Cosine match against a local SQLite file on my phone.
> On match, Claude Haiku writes a three-line brief.
> The brief renders as a HUD card in under 1.5 seconds."

_Beat._

> "Under 1.5 seconds. That's faster than I can formulate 'hey how's it going.'"

**[Advance to Slide 8 — What the operator sees]**

> "Everything runs on this laptop for the hackathon.
> On day two, it moves to the phone."

---

## 3:40 – 4:10 · Privacy — earn the trust

**[Advance to Slide 9 — Privacy]**

_Slow down. Make eye contact with the audience. This is the trust beat._

> "A product that remembers people lives or dies on whether it feels like a gift or surveillance.
> Three promises make it a gift."

_Beat on each:_

> "**One** — explicit enrollment only. No voiceprint is stored without a deliberate temple tap. We do not accumulate strangers."

> "**Two** — local-first. The database lives on my phone. No cloud sync. One tap deletes any row."

> "**Three** — cameraless by physics. The G2 has no lens. No face database exists. Never could."

_Pause._

> **"Cue only remembers the people you chose to remember."**

---

## 4:10 – 4:30 · Why this resonates

**[Advance to Slide 10 — Why this resonates]**

_Lift the energy back up._

> "Everyone in this room forgot someone's name this week.
> You walked into 40 intros today. You'll forget 34.
> Meta tried cameras — they got thrown out of the room.
> **G2 stays in. And Cue is Even Realities' brand as a product — Quiet Tech, made real.**"

---

## 4:30 – 4:50 · What's next

**[Advance to Slide 11 — What's Next]**

> "From hackathon to daily wear, we're building:
> Group-conversation diarization. Proactive recall — _you promised Priya a beta invite 21 days ago._
> Calendar hydration. Two-way consent between G2 wearers. On-device Claude.
> The same 1.5-second magic — on the phone you already carry."

---

## 4:50 – 5:00 · Close

**[Advance to Slide 12 — Close]**

_Breathe. Lower your voice. Deliver slowly._

> **"Faces are data.
> People are memory.
> The G2 is the first wearable quiet enough to hold the second one."**

_Pause 2 seconds._

> "I'm Javeed. That was Cue.
> Thank you."

_Small bow. Don't move until the clap breaks. Hand the mic to the next team._

---

## Stage setup & safety

### Pre-pitch checklist (run T-15 min)

- [ ] 3 terminals open on the laptop
- [ ] Terminal A running `cue.app run --echo`, showing `bridge client connected (1 total)`
- [ ] Terminal B running `npm run dev`, Vite on `0.0.0.0:5173`
- [ ] G2 connected via QR, HUD shows `Cue / Listening…`
- [ ] Rehearse the Abhishek walk-up once. Card lands on HUD.
- [ ] Laptop battery ≥ 60% OR plugged in
- [ ] Phone battery ≥ 60% OR plugged in
- [ ] Wi-Fi is the same on laptop + phone

### If the live demo breaks

**Card doesn't appear within 3 seconds:**
> "Cue doesn't always fire on the first word — it waits for a full phrase. Abhishek, give it one more line."

(Buys 3 more seconds. Usually works.)

**Complete failure (no card at all):**
> "This is the demo gods reminding us we built this in a day. Here's the pre-recorded clip."

_Hit a backup video on the laptop. Keep going._

### Pacing

| Segment | Target time | Cumulative |
|---|---|---|
| Hook | 0:20 | 0:20 |
| Wedge | 0:40 | 1:00 |
| Live demo | 1:30 | 2:30 |
| What lands | 0:30 | 3:00 |
| How it works | 0:40 | 3:40 |
| Privacy | 0:30 | 4:10 |
| Why this resonates | 0:20 | 4:30 |
| What's next | 0:20 | 4:50 |
| Close | 0:10 | 5:00 |

If you're running long, cut in this order:
1. First — trim the how-it-works technical walkthrough
2. Then — cut the "What's next" slide
3. Never — cut the live demo or the close

---

## Delivery notes

- **Speak 15% slower than feels natural.** Nerves will accelerate you.
- **Pause after every tagline.** "Meta Ray-Bans remember faces. Cue remembers people." — hold for 2 seconds.
- **Let the HUD card land without narration.** The audience should _see_ the magic before you explain it.
- **Eye contact on privacy.** That's the trust beat — don't read off the slide.
- **Final line — deliver it like a closing line of a poem.** Short words, held pauses.

---

## One-line elevator version

_For hallway conversations after the pitch:_

> "Cue is ambient social memory for the Even G2. You tap once when someone introduces themselves. When their voice speaks again, their name and a suggested follow-up fade onto your HUD. Cameraless, local, and quiet enough to use in the rooms where memory actually matters."
