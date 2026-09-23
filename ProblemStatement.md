# Problem Statement — AI-Powered Discovery Engine
## Google Photos Retrieval Research (NextLeap Graduation Project)

## Context
Google Photos users accumulate thousands of photos, screenshots, and videos over time.
When a user remembers a photo exists but cannot recall precise details (date, location,
album, exact keywords), retrieval becomes difficult — even though Google Photos already
has an AI-powered natural language search feature ("Ask Photos", powered by Gemini).

The strategic goal is to increase the percentage of users who successfully retrieve a
photo they vaguely remember when they start searching.

## The Problem We Are Solving (for this engine specifically)
We do not yet know, with evidence, WHERE in the retrieval journey things actually break
down for users with incomplete memory. Guessing this would produce a generic, shallow
problem definition (e.g. "search is hard") — which is explicitly the wrong framing.

We need to analyze a large volume of real, public user complaints and discussions about
Google Photos retrieval to identify recurring, evidence-backed failure patterns before
forming any problem statement or solution.

## What This Discovery Engine Must Do
1. Collect a large sample (~1200 items) of public user feedback about Google Photos
   search/retrieval, across multiple independent sources.
2. Filter this raw feedback down to items relevant to retrieval/search struggles
   (not general app complaints like bugs, storage, pricing).
3. Classify each relevant item into a fixed, structured schema using an LLM, so
   patterns can be counted and compared — not just summarized.
4. Produce a structured dataset (spreadsheet/table) that can be sliced by:
   failure type, content type, source, and outcome.

## What This Engine Must NOT Do
- It must not attempt to solve the problem or suggest features.
- It must not pre-assume a root cause (e.g. "it's an awareness problem" or
  "it's a search-quality problem"). The classification schema is intentionally
  open-ended (including an "unknown/unclear" option, and allowing more than
  one failure point per item) so the data can reveal the pattern, not confirm
  a guess.
- It is not a chatbot or RAG system. It is a one-time batch classification pipeline.
- Every classification must be traceable back to a real quote from the source
  text — no ungrounded labeling.

## Success Criteria for This Engine
- At least ~1000 usable, relevant, tagged items across 4 sources.
- Tagging accuracy validated against a manual spot-check sample (~50-100 items).
- Clear, exportable dataset that directly feeds:
  - Business metric decomposition (which failure types are most common)
  - Problem definition (root cause, backed by real user language)
  - Interview question design (what to probe deeper on with real users)

## Constraints
- Must use free/low-cost tools only (Groq for LLM classification).
- Must be reproducible and explainable in a single slide (simple pipeline,
  not a complex multi-agent system).
- Output must be usable within days, not weeks — this is one input among several
  (interviews, survey) for a larger graduation project.
