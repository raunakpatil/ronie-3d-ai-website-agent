/* =====================================================================================================================
   RONIE — EDIT ME. Everything specific to your website lives here.
   The example below is a made-up designer, "Alex Morgan". Replace it with your own details (a person, a studio, a
   shop, a museum, a product — Ronie can work for anyone).
   ===================================================================================================================== */
window.RONIE = {
  owner: 'Alex Morgan',          // who Ronie works for — used in buttons ("Email Alex"), drafted emails, the loading sheet
  ownerShort: 'Alex',            // how he calls them in a sentence
  exitUrl: '',                   // optional: where the Esc key takes visitors (e.g. '/'), '' = nowhere

  // Places Ronie can send people. Any of these he mentions in a reply becomes a button under it.
  links: [
    { label: 'Email', href: 'mailto:hello@example.com' },
    { label: 'LinkedIn', href: 'https://www.linkedin.com/in/example' },
    { label: 'GitHub', href: 'https://github.com/example' },
    { label: 'YouTube', href: 'https://www.youtube.com/@example' },
    { label: 'Instagram', href: 'https://www.instagram.com/example' },
  ],

  // Projects / products Ronie can show. When a reply names one he picks up its card and holds it out to the visitor,
  // and it gets a button. Images: 16:9.
  projects: [
    { title: 'Lumen', category: 'App', year: 2026, image: 'img/projects/lumen.webp', link: 'https://example.com/lumen' },
    { title: 'Northwind', category: 'Website', year: 2025, image: 'img/projects/northwind.webp', link: 'https://example.com/northwind' },
  ],

  // What Ronie knows. tools/make-facts.mjs turns this into worker/src/facts.js for the AI.
  // Write plain, true sentences — the agent will only ever say what's in here about the owner.
  knowledge: {
    summary: 'Alex Morgan is a product designer and front-end developer based in Lisbon, Portugal, working with startups on apps and websites.',
    status: 'Open to freelance projects from next month.',
    sections: {
      Experience: [
        '2023 — now: Independent product designer and developer (Lisbon).',
        '2019 — 2023: Senior designer at a fintech startup, leading the mobile app redesign.',
      ],
      Projects: [
        'Lumen (2026, App): a habit-tracking app with a calm, minimal interface; 40,000 downloads.',
        'Northwind (2025, Website): an e-commerce site for a coffee roaster; conversions up 22% after the redesign.',
      ],
      Skills: ['Product design, Figma, design systems', 'React, TypeScript, three.js', 'User research and prototyping'],
      'Fun facts': ['Alex speaks English, Portuguese and Spanish.', 'Alex built this website, and Ronie.'],
    },
  },

  assistant: {
    name: 'Ronie',
    tagline: "Alex's own neural intelligence engine",      // shown on the loading sheet
    chatUrl: '',                 // your worker's address + '/chat' (see worker/). '' = scripted lines only, no AI
    email: 'hello@example.com',  // where "Email Alex" goes
    model: {
      src: 'models/rai-robot.glb',   // any rigged glTF/GLB character — see the README ("Use your own character")
      credit: 'Sci-Fi O.B. Robot Unit TH-ICC02 (Animated)',
      creditUrl: 'https://sketchfab.com/3d-models/sci-fi-ob-robot-unit-th-icc02-animated-6c0764c2bc4c4aaa8e03ba1653f455a6',
      author: 'Jungle Jim', authorUrl: 'https://sketchfab.com/jungle_jim',
      license: 'CC BY 4.0', licenseUrl: 'http://creativecommons.org/licenses/by/4.0/',
    },
    // voice: { voice: 'am_puck', speed: 1.04 },   // optional: another Kokoro voice (af_heart, bm_george…)

    // The scripted part of the conversation. Each step: what he says (one line picked at random; {visitor}, {name},
    // {email} are filled in), his face/icon, and what comes next — `next`, `choices`, an `input`, or `chat` (the AI).
    // Steps the code needs by name: 'your-name' and 'ask' (and 'story-done' if you use `story` steps).
    start: 'intro',
    steps: {
      intro: {
        progress: 0.05, next: 'your-name', skipIfName: 'welcome-back', face: 'happy', icon: 'sparkle',
        say: [
          "Oh! A visitor. Hi {visitor}, I'm Ronie — I look after Alex's website. And I just woke up, so be gentle.",
          'Rebooting charm module… done. Hi, I\'m Ronie. I know everything about Alex. It\'s a little awkward.',
          "Hello! I'm Ronie, Alex's robot. Think of me as a tour guide, with more blinking.",
        ],
      },
      'your-name': {
        progress: 0.15, next: 'ask', skipIfName: 'welcome-back', face: 'curious', icon: 'question',
        input: { name: 'name', label: 'Your name', type: 'text' },
        say: ['Before we start — what should I call you?', "Let's do introductions properly. You know my name — what's yours?"],
      },
      'welcome-back': {
        progress: 0.3, chat: true, face: 'love', icon: 'heart',
        say: ['Wait — {name}? You came back! Ask me anything about Alex.'],
        fallback: "Sorry {name}, my chat brain is napping. Try again in a bit — or email Alex at {email}.",
        quota: "I've talked so much today that I've used up my free brain juice, {name}. Back tomorrow — or email Alex at {email}.",
        suggest: ['What has Alex built?', 'Is Alex available?', 'What does Alex do?', 'How do I contact Alex?'],
      },
      ask: {
        progress: 0.3, chat: true, face: 'happy', icon: 'speech',
        say: ["Alright {name}, I'm all yours. Ask me about Alex — work, projects, skills, anything."],
        fallback: "Sorry {name}, my chat brain is napping. Try again in a bit — or email Alex at {email}.",
        quota: "I've talked so much today that I've used up my free brain juice, {name}. Back tomorrow — or email Alex at {email}.",
        suggest: ['What has Alex built?', 'Is Alex available?', 'What does Alex do?', 'How do I contact Alex?'],
      },
    },

    // The mind-reading mini game (needs chatUrl). Remove this block to turn it off.
    game: {
      offer: { kicker: 'Mini game · 20 questions or so', title: 'Want me to read your mind?', sub: "Think of anyone, real or fictional. I'll guess who." },
      first: 'Is it a real person, not a fictional character?',
      intro: ["Okay {name}: think of a famous person, a character, an animal or a thing. Don't tell me. I'll read your mind. With questions. Ready?"],
      win: ['I knew it! I mean — I calculated it. Same thing. Another round, {name}?'],
      lose: ['Okay, you beat me, {name}. My circuits are humbled. Who was it?'],
      reveal: ['{answer}! Of course. I was one question away. Probably. Rematch?'],
      fallback: 'My guessing brain just went to sleep, {name}. Let\'s try again in a bit.',
      quota: 'I\'ve played so much today that my free brain juice ran out, {name}. Rematch tomorrow?',
    },
  },
};
