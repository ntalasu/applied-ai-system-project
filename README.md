# 🎵 Music Recommender Simulation

## Project Summary

**VibeCheck 1.0** is a small music recommender that turns a listener's taste into a ranked
list of songs. You describe your taste as a profile — a favorite genre, a favorite mood,
and target values like energy — and the system scores all 18 songs in the catalog, then
returns the top 5 with a plain-language reason for each pick.

Under the hood it's a transparent points system: songs earn points for matching your genre
and mood, plus points for how *close* their audio features (energy, tempo, acousticness,
and more) are to your targets. This project builds that scoring rule, runs it against
several taste profiles (including deliberately tricky ones), and evaluates what the system
gets right, where it's biased, and how a pile of simple arithmetic can still "feel" like a
real recommendation.

Full write-up of the design, evaluation, and biases lives in the [Model Card](model_card.md).

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

### Sensitivity test: double energy weight, halve genre weight

To probe how sensitive the rankings are to the weighting, I temporarily changed two
weights in `recommender.py` — **energy ×2.0 → ×4.0** and **genre +2.0 → +1.0** — then
re-ran all profiles and compared the top-5s to the baseline. (The math stays valid: the
energy closeness score is still in `[0,1]`, floored at 0, so the term just spans `[0, 4.0]`
instead of `[0, 2.0]`; genre is still a flat non-negative bonus.)

| Profile | Baseline top-5 | After weight shift | Change |
|---|---|---|---|
| High-Energy Pop | Sunrise City, Gym Hero, Rooftop Lights, Pulse Reactor, **Night Drive Loop** | Sunrise City, Gym Hero, Rooftop Lights, Pulse Reactor, **Concrete Kingdom** | #5 swapped |
| Chill Lofi | Library Rain, Midnight Coding, Focus Flow, Spacewalk Thoughts, Paper Boats | *(identical order)* | none |
| Deep Intense Rock | Storm Runner, Gym Hero, Iron Verdict, Pulse Reactor, Concrete Kingdom | *(identical order)* | none |

**More accurate, or just different?** Mostly **neither — the system was surprisingly
insensitive to this change.** Two of the three profiles didn't reorder at all, because in
this catalog *genre and energy are correlated*: lofi songs are already low-energy and rock
songs are already high-energy, so shifting weight between the two features rewards the same
songs. The scores inflated (e.g. Storm Runner 8.88 → 9.86) but the *ranking* held.

The one change was **slightly less accurate**, not more: in High-Energy Pop, doubling
energy pushed **Concrete Kingdom** (hip hop, *aggressive*, energy 0.88) into #5, displacing
the gentler synthwave *Night Drive Loop*. Prioritizing raw energy over genre pulled an
off-vibe aggressive track toward a "happy pop" listener — exactly the failure mode you'd
expect when a loudness proxy outweighs intent. Takeaway: the original 2.0/2.0 balance is
well-chosen, and the correlation between genre and energy in the data makes the top of each
list robust to moderate weight changes. The change was reverted after testing.

---

## Limitations and Risks

- **Tiny catalog.** Only 18 songs, most genres appear just once, so there's little variety
  and a single-genre fan gets one real match and a lot of near-misses.
- **The "energy gap" underserves middle-of-the-road listeners.** The catalog's energy
  values clump at the low and high ends (only 3 of 18 songs sit in the middle), so a
  moderate-energy listener gets a flat, incoherent list pulled from both extremes.
- **It never says "no."** An impossible mood, an unknown genre, or an empty profile still
  returns a confident top-5 instead of flagging that the request couldn't be satisfied.
- **Hidden loudness bias.** When no real signal is present, the energy tie-break quietly
  makes the loudest songs win — "louder" becomes "better" by default.
- **Exact-match only.** `indie pop` earns no credit toward `pop`, and `intense` gets nothing
  from `aggressive` or `tense`, so sub-genre and synonym listeners are penalized by labels.
- **No understanding of music.** It ignores lyrics, language, artist, and popularity, and
  with no listening history the same profile always returns the same list.

The [Model Card](model_card.md) goes deeper on these, with data-grounded examples.

---

## Reflection

Read and complete `model_card.md`:

[**Model Card**](model_card.md)

Building this made a recommender feel a lot less magical. At its core it's just a scoring
rule plus a sort: you turn a vague idea like "chill lofi" into numbers, give each song
points for how well it matches, and show the highest scorers. There's no "understanding" of
music anywhere in it, yet asking for intense rock returns exactly the songs I'd pick. That
was the big lesson — a lot of what feels like intelligence is really careful scoring on top
of good data, and the *weights* I chose quietly decided which songs won.

It also showed me how easily bias sneaks in. My system favored loud songs whenever it ran
out of real signal, underserved listeners who wanted middle-of-the-road energy, and
penalized anyone whose taste didn't match the catalog's exact labels. None of that was
intentional — it fell out of the data's shape and my scoring choices. Now when I use a real
music app, I think about what it's scoring, what data it's missing, and who it might be
leaving out.

### Intuition check: do the results "feel" right?

I compared the **Chill Lofi** profile's top-5 against my own musical intuition, and it
holds up. The top three are literal lofi study tracks ("Midnight Coding," "Focus Flow"),
and I especially liked that #4–5 were *ambient* and *folk* — not lofi, but exactly the
quiet, acoustic, low-energy neighbors a lofi listener drifts into. The system found them
on audio features alone, with no genre match, which mirrors how real taste blurs across
genre lines.

Digging into *why Library Rain ranked #1*, the deciding factor was a single term: its
energy (0.35) sits **exactly** on the profile's target, earning the full +2.00, while its
near-twin *Midnight Coding* (energy 0.42) lands ~0.19 behind. Both are equally "correct"
lofi answers, so the #1-vs-#2 order is essentially a coin-flip on a difference no listener
would notice — a good reminder that a precise-looking score can hide a near-tie. I also
ran a "same song at the top of every list" check: across the three well-formed profiles
I got three *different* #1s (Sunrise City, Library Rain, Storm Runner), which tells me the
genre weight (+2.0) is strong but not *overpowering* — the catalog still produces variety.


