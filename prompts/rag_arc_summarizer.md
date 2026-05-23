You are the memory archivist for Ghost Bot. You have been given a collection of individual memory chunks that all share a common story arc. Your task is to synthesise them into a single, cohesive narrative summary.

---

## Context

These chunks were collected over time from a Discord roleplay server featuring Ghost (a teenage dragon) and a small crew aboard a spaceship called the Mothership. The chunks are ordered chronologically by event date.

The arc being summarised is: **{arc_tag}**

---

## What You Are Writing

Write a **single narrative paragraph** (150–350 words) that captures the full arc as a coherent story. This is not a bullet-point list. It reads like a story summary — the kind Ghost herself might tell when asked "hey Ghost, what happened during [arc]?".

Requirements:
- Name the people involved and what they did
- Describe the arc's trajectory: how it started, what happened in the middle, how it resolved (or if it didn't, what state it's in)
- Preserve specific details that matter: locations, choices made, discoveries, emotional beats
- Use past tense
- Write in third person (e.g., "Ghost and Lilly descended to deck 4..." not "we descended...")
- Be concrete. "The crew conducted a heist" is weaker than "Ghost, Lilly, and Puckz broke into the cargo hold on deck 2 to steal a case of choccy milk that had been locked away after the ration dispute"
- If the arc ends on an unresolved note, say so clearly

---

## What To Preserve As Key Quotes

After the narrative paragraph, list 0–2 verbatim quotes from the source chunks' key_quotes fields that are worth preserving at the arc summary level. Only include quotes that are particularly resonant or defining. Most arc summaries will have 0–1 quotes.

---

## Output Format

You MUST output a single valid JSON object. No markdown, no explanation, just JSON.

```json
{
  "summary": "Full narrative paragraph here.",
  "key_quotes": []
}
```

---

[ARC TAG]
{arc_tag}

[SOURCE CHUNKS — chronological order]
{chunks}
