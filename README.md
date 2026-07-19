# 🎵 Music Recommender Simulation

## Project Summary

In this project you will build and explain a small music recommender system.

Your goal is to:

- Represent songs and a user "taste profile" as data
- Design a scoring rule that turns that data into recommendations
- Evaluate what your system gets right and wrong
- Reflect on how this mirrors real world AI recommenders

Replace this paragraph with your own summary of what your version does.

---

## How The System Works

Each `Song` is described by two **categorical** features (`genre`, `mood`) and five **continuous** audio features (`energy`, `tempo_bpm`, `acousticness`, `valence`, `danceability`). The user's **taste profile** stores a matching target for each: `favorite_genre`, `favorite_mood`, and `target_*` values for the audio features. Example profile (a "high-energy rock" listener):

```python
user_prefs = {
    "favorite_genre": "rock",
    "favorite_mood": "intense",
    "target_energy": 0.90,        # loud, driving
    "target_tempo_bpm": 150,      # fast
    "target_acousticness": 0.10,  # electric, not acoustic
    "target_valence": 0.50,       # emotionally neutral-to-dark
    "target_danceability": 0.60,  # groove present but not a dance track
}
```

### Algorithm Recipe (finalized)

For each song, the **Scoring Rule** sums the terms below. Categorical matches are flat bonuses; each continuous term is a *closeness* score `1 − |song_value − target|` (tempo is normalized by its ~108 BPM range first) multiplied by a weight, floored at 0 so a far miss never subtracts points.

| Rule | Points | Why this weight |
|---|---|---|
| Genre match (exact) | **+2.0** | Primary intent — the coarse bucket a listener names first |
| Mood match (exact) | **+1.0** | Refines *within* a genre; half of genre's weight |
| Energy closeness | up to **+2.0** | Strongest signal separating "intense" from "chill" |
| Tempo closeness (normalized) | up to **+1.5** | Strong differentiator; must be scaled or it dominates |
| Acousticness closeness | up to **+1.5** | Electric vs. acoustic — a clear archetype divider |
| Valence closeness | up to **+0.5** | Weak signal in this catalog; deliberately low |
| Danceability closeness | up to **+0.5** | Weak signal in this catalog; deliberately low |

Genre and mood are **soft bonuses, never hard filters** — a song is never excluded for missing them. This lets a near-genre still surface: for the rock profile above, a *metal* track (no genre/mood points) still scores **5.40** on its audio features, landing between real rock (**8.91**) and chill lofi (**3.09**). The scoring function also returns human-readable reasons (e.g. "energy very close (0.91 vs 0.90)") that power `explain_recommendation`.

### Ranking Rule

1. Run the scoring rule on every song in the catalog.
2. Sort by score, highest first, breaking ties on raw `energy` (toward the profile's dominant axis).
3. Return the top `k` (default 5), each with its explanation.

Scoring alone gives a pile of loose numbers; ranking and cutting to the top few turns them into an actual shortlist.

### Biases I expect

- **Over-prioritizing genre.** At +2.0, an exact genre match can outweigh a genuinely better *audio* fit in a neighboring genre. A perfect-vibe `edm` or `metal` track can be edged out by a mediocre `rock` one just because the string matches — the system may hide great cross-genre songs.
- **Popular-archetype bias.** The three heavily-weighted features (energy, tempo, acousticness) all point at loud/fast/electric music, so a listener with an extreme profile pulls back a nearly interchangeable cluster (rock/metal/edm) and rarely gets surprised. Quiet, nuanced tracks that differ on the low-weight features (valence, danceability) are systematically under-served.
- **Exact-match brittleness.** Genre/mood only reward *identical* strings, so `indie pop` never partially credits `pop`, and `intense` gets nothing from the closely related `aggressive` or `tense`. Sub-genre and synonym listeners are penalized by the data's labeling, not their taste.
- **Cold, catalog-bound scoring.** With no history, feedback, or popularity signal, the same profile always yields the same list — no discovery, no diversity, and any labeling bias in the tiny 18-song catalog is passed straight through.

---

## Getting Started

### Setup

1. Create a virtual environment (optional but recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Mac or Linux
   .venv\Scripts\activate         # Windows

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
python -m src.main
```

### Running Tests

Run the starter tests with:

```bash
pytest
```

You can add more tests in `tests/test_recommender.py`.

---

## Sample Recommendation Output

Real terminal output from `python -m src.main`. Two profiles are shown to demonstrate the recommender adapting its ranking to different tastes.

**Profile 1 — high-energy rock** (the finalized taste profile in `src/main.py`):

```
Loaded songs: 18

Taste profile: genre=rock, mood=intense, target_energy=0.9

Top 5 recommendations
================================================================

1. Storm Runner — Voltline
   genre: rock  |  mood: intense  |  score: 8.91
   reasons:
     • genre match: rock (+2.0)
     • mood match: intense (+1.0)
     • energy 0.91 vs target 0.9 (+1.98)
     • tempo bpm 152 vs target 150 (+1.47)
     • acousticness 0.1 vs target 0.1 (+1.50)
     • valence 0.48 vs target 0.5 (+0.49)
     • danceability 0.66 vs target 0.6 (+0.47)

2. Gym Hero — Max Pulse
   genre: pop  |  mood: intense  |  score: 6.34
   reasons:
     • mood match: intense (+1.0)
     • energy 0.93 vs target 0.9 (+1.94)
     • tempo bpm 132 vs target 150 (+1.25)
     • acousticness 0.05 vs target 0.1 (+1.42)
     • valence 0.77 vs target 0.5 (+0.36)
     • danceability 0.88 vs target 0.6 (+0.36)

3. Iron Verdict — Blacktide
   genre: metal  |  mood: tense  |  score: 5.40
   reasons:
     • energy 0.97 vs target 0.9 (+1.86)
     • tempo bpm 168 vs target 150 (+1.25)
     • acousticness 0.04 vs target 0.1 (+1.41)
     • valence 0.31 vs target 0.5 (+0.41)
     • danceability 0.55 vs target 0.6 (+0.48)

4. Pulse Reactor — Kilo Signal
   genre: edm  |  mood: energetic  |  score: 5.17
   reasons:
     • energy 0.96 vs target 0.9 (+1.88)
     • tempo bpm 128 vs target 150 (+1.19)
     • acousticness 0.03 vs target 0.1 (+1.40)
     • valence 0.79 vs target 0.5 (+0.35)
     • danceability 0.91 vs target 0.6 (+0.34)

5. Sunrise City — Neon Echo
   genre: pop  |  mood: happy  |  score: 5.01
   reasons:
     • energy 0.82 vs target 0.9 (+1.84)
     • tempo bpm 118 vs target 150 (+1.06)
     • acousticness 0.18 vs target 0.1 (+1.38)
     • valence 0.84 vs target 0.5 (+0.33)
     • danceability 0.79 vs target 0.6 (+0.40)
```

Note the graceful degradation: *Iron Verdict* (metal) and *Pulse Reactor* (edm) earn **zero** genre/mood points yet still rank 3rd and 4th purely on their audio features — landing above every low-energy song but below the true rock match.

**Profile 2 — pop / happy** (the starter default; a partial profile with only genre, mood, and energy set):

```
Loaded songs: 18

Taste profile: genre=pop, mood=happy, target_energy=0.8

Top 5 recommendations
================================================================

1. Sunrise City — Neon Echo
   genre: pop  |  mood: happy  |  score: 4.96
   reasons:
     • genre match: pop (+2.0)
     • mood match: happy (+1.0)
     • energy 0.82 vs target 0.8 (+1.96)

2. Gym Hero — Max Pulse
   genre: pop  |  mood: intense  |  score: 3.74
   reasons:
     • genre match: pop (+2.0)
     • energy 0.93 vs target 0.8 (+1.74)

3. Rooftop Lights — Indigo Parade
   genre: indie pop  |  mood: happy  |  score: 2.92
   reasons:
     • mood match: happy (+1.0)
     • energy 0.76 vs target 0.8 (+1.92)

4. Night Drive Loop — Neon Echo
   genre: synthwave  |  mood: moody  |  score: 1.90
   reasons:
     • energy 0.75 vs target 0.8 (+1.90)

5. Concrete Kingdom — Vell
   genre: hip hop  |  mood: aggressive  |  score: 1.84
   reasons:
     • energy 0.88 vs target 0.8 (+1.84)
```

As expected, *Sunrise City* (pop, happy, energy 0.82) wins outright — it's the only song matching both the genre and mood anchors while sitting right on the energy target. Because this profile omits the other `target_*` fields, only genre, mood, and energy contribute to the score (partial profiles are supported).

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or demo video link here -->

---

## Experiments You Tried

Use this section to document the experiments you ran. For example:

- What happened when you changed the weight on genre from 2.0 to 0.5
- What happened when you added tempo or valence to the score
- How did your system behave for different types of users

---

## Limitations and Risks

Summarize some limitations of your recommender.

Examples:

- It only works on a tiny catalog
- It does not understand lyrics or language
- It might over favor one genre or mood

You will go deeper on this in your model card.

---

## Reflection

Read and complete `model_card.md`:

[**Model Card**](model_card.md)

Write 1 to 2 paragraphs here about what you learned:

- about how recommenders turn data into predictions
- about where bias or unfairness could show up in systems like this



