# Ronie — template

Everything you need to put Ronie on your own website: the 3D agent, his AI brain, his voice, the mind-reading game and
the tools behind his animations — with no personal details. The example content belongs to a made-up designer,
**Alex Morgan**; replace it with yours.

**Free to run:** GitHub Pages (or any static host) + Cloudflare's free Workers tier + Google's free Gemini tier. The
voice runs in the visitor's browser.

---

## Quick start (5 minutes, no AI yet)

```bash
# from this folder
python -m http.server 5173
# open http://localhost:5173
```

Ronie loads, wakes up, asks your name and runs the scripted lines in `ronie.config.js`. Without an AI endpoint he
answers questions with a friendly "my chat brain is napping" and offers the email button.

## Make him yours — `ronie.config.js`

| Setting | What it does |
|---|---|
| `owner`, `ownerShort` | Who he works for (a person, a studio, a shop, a museum…). Used in buttons, drafted emails, the loading sheet. |
| `links` | Email, LinkedIn, GitHub, YouTube, Instagram… Any he mentions in a reply becomes a button. |
| `projects` | Things he can show. Naming one makes him pick up its card (a 16:9 image) and hold it out. |
| `knowledge` | **Everything the AI knows** — plain, true sentences. He will only ever say what's here about the owner. |
| `assistant.steps` | The scripted conversation: greeting, name, then the AI chat. Each step has lines (one picked at random), a face, an icon, and what comes next. |
| `assistant.game` | The mind-reading game's lines. Delete it to switch the game off. |
| `assistant.model` | The 3D character (see below) and its credit. |
| `assistant.voice` | Optional: another Kokoro voice (`af_heart`, `bm_george`, …) and speed. |

## Give him a brain — the AI worker (free)

The `worker/` folder is a Cloudflare Worker: persona, rules, the facts, prompt-injection guard, rate limit and a
self-healing chain of free models.

1. Set who he works for at the top of `worker/src/index.js` (`OWNER`, `OWNER_FIRST`, `SITE`, `AGENT`, `PRONOUN`).
2. Write his knowledge into `ronie.config.js`, then generate the facts: `node tools/make-facts.mjs`
3. Deploy (needs a free Cloudflare account; Node 22):
   ```bash
   cd worker
   npx wrangler deploy
   npx wrangler secret put GEMINI_API_KEY      # a free key from Google AI Studio (optional but recommended)
   ```
4. Put the worker's address + `/chat` in `ronie.config.js` → `assistant.chatUrl`.

Without a Gemini key he uses Cloudflare Workers AI's free daily allowance only. With it, he walks a list of free Gemini
models first and keeps Workers AI as the last resort; `/pick` settles on a working model once per visit.

The personality lives in `SYSTEM` in `worker/src/index.js` — "awkward but witty" by default. Change the tone, the
rules, the language; keep the three tags (`[face:…] [icon:…] [move:…]`) so his body keeps up with his words.

## Use your own character

`assistant.model.src` takes any rigged **glTF / GLB** character.

- **Character Creator / ActorCore-style rigs** (bones named `CC_Base_…`, like the included robot) get everything: head
  and eye tracking, breathing, the leap, all 23 authored moves and the project-card grip.
- **Any other rig** gets the idle pose, head-tracking (bones found by name: *head*, *neck*, *spine*, *hip*), breathing
  and the model's own animations. Re-author the moves for it with `tools/blender/ronie_anims.py` (poses are tables of
  angles per bone), then shrink them with `tools/squeeze-anims.py`.
- **The CRT face** is a shader sheet fitted to this robot's visor (`models/ronie-visor.json`). For another character,
  bake a sheet for its face the same way, or leave it out — the agent works without it.

The included robot is "Sci-Fi O.B. Robot Unit TH-ICC02" by Jungle Jim, **CC BY 4.0**: keep the credit (see
`models/rai-robot-LICENSE.txt`) if you use it.

## Change his world

- **A picture** (the default): `img/ronie-bg.webp` and `img/ronie-bg-lit.webp` — the same scene with its lights dim and
  lit. The canvas effects (water ripples, embers, stars, mist) read the difference between the two, so any pair works;
  align them pixel-for-pixel for the glow to "breathe" cleanly.
- **A 3D room**: open `?room=space` (a procedural space scene) or `?room=tubes` (a neon-tube studio) — both are built in
  code and easy to restyle.
- **Your own scene**: it's three.js — add your environment in `init3D()` in `js/ronie.js`.

## Add a game

The mind reader is a pattern you can copy: a second system prompt (`GAME_SYSTEM` in the worker), a question budget,
structured tags the page can act on (`[guess]`), and a few scripted lines in the config. Ideas: a quiz about your
product, riddles, a scavenger hunt across your site, a "which plan suits you" questionnaire.

## What's where

```
template/
├─ index.html            the page: his room and loading sheet
├─ ronie.config.js       ← everything about your site
├─ css/ronie.css         his styles
├─ js/ronie.js           the agent: 3D, face, moves, chat, voice, game (~3,700 lines)
├─ js/ronie-page.js      loading sheet, email links, voice keeping, start-up
├─ js/ronie-voice-worker.js   the neural voice (Kokoro-82M on WebGPU)
├─ sw.js                 keeps the 325 MB voice in IndexedDB after the first visit
├─ models/               the robot, his 23 moves, his face and chest emblem
├─ img/                  the backdrop pair, the loading sheet's pictures, example project cards
├─ worker/               the AI brain (Cloudflare Worker) + generated facts
└─ tools/                make-facts.mjs · blender/ronie_anims.py · squeeze-anims.py
```

No build step, no framework: plain HTML, CSS and ES modules; three.js comes from a CDN.
