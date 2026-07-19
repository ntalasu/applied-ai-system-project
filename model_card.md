# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name

**VibeCheck 1.0** — it checks how well each song matches your vibe.

---

## 2. Intended Use

VibeCheck suggests songs that fit a listener's taste. You give it a taste profile —
a favorite genre, a favorite mood, and target values like energy. It scores every song
in the catalog and hands back the top 5, with a short reason for each pick.

**What it's for:** classroom learning and exploration. It's a small demo of how a
recommender turns preferences into a ranked list.

**What it's *not* for:** real products or real users. The catalog is tiny, the labels
are simple, and it has no listening history or safety checks. Don't use it to make real
recommendations or any decision that matters.

**Assumptions:** it assumes the user can describe their taste as a genre, a mood, and a
few numbers, and that those numbers mean the same thing to everyone.

---

## 3. How the Model Works

Think of it as a points contest. Each song earns points for how well it matches your taste.

- If the song's **genre** matches yours, it gets **+2 points**.
- If the song's **mood** matches yours, it gets **+1 point**.
- For number features like **energy, tempo, acousticness, valence, and danceability**,
  the song earns points for being *close* to your target. A perfect match earns the most;
  the further off it is, the fewer points it gets.
- Energy, tempo, and acousticness are worth more points than valence and danceability,
  because they do the best job of telling different kinds of music apart.

The song adds up all its points into one score. Then the system sorts every song from
highest score to lowest and shows you the top 5. Genre and mood are only *bonuses* — a
song is never thrown out for missing them, so a great-sounding song from a slightly
different genre can still make the list. We started from a simple genre-only idea and
added the mood bonus and the "closeness" scoring for the number features.

---

## 4. Data

- **Size:** 18 songs. Small on purpose — it's a demo.
- **Features per song:** title, artist, genre, mood, and five numbers (energy, tempo,
  valence, danceability, acousticness).
- **Genres:** pop, lofi, rock, ambient, jazz, synthwave, indie pop, hip hop, classical,
  edm, r&b, country, metal, folk, reggae. Lofi appears 3 times; most genres appear only once.
- **Moods:** happy, chill, intense, relaxed, focused, moody, aggressive, melancholy,
  energetic, romantic, nostalgic, tense, dreamy, uplifting.
- **Limits:** the catalog is too small to give variety, most genres have just one song,
  and the energy values clump at the low and high ends with few songs in the middle.
  There are no lyrics, no language info, and no popularity data. Whole styles of music
  are simply missing.

---

## 5. Strengths

- It works well for **clear-cut tastes**. Ask for chill lofi or intense rock and the
  right songs come out on top.
- Its picks are **easy to trust because it explains them**. Every song comes with a plain
  list of the points it earned and why.
- It can **find good songs in nearby genres**. Because genre is only a bonus, a metal or
  edm track can still surface for a rock fan when the sound fits, instead of being ignored.
- The top results **matched my own musical intuition** in testing — the #1 pick for each
  well-formed profile was the song I would have chosen myself.

---

## 6. Limitations and Bias

Where the system struggles or behaves unfairly.

**Key weakness discovered — the "energy gap" penalizes moderate-energy listeners.**
The catalog is bimodal in energy: of 18 songs, 8 are high-energy (>0.70) and 7 are
low-energy (<0.45), but only 3 sit in the moderate 0.45–0.70 range. Because the energy
term scores linear closeness (`1 − |target − energy|`), a listener who wants moderate
energy (0.60) exhausts those 3 real matches and is then forced to pull from *both*
extremes at once — my test returned a loud synthwave track (0.75) and a quiet lofi track
(0.42) in the same top-5. Their scores also collapsed into a flat 4.99–5.55 band, versus
the 5.0–8.9 spread a high-energy listener enjoys, so the system can barely rank songs for
them and its recommendations are far less trustworthy. This is a genuine filter bubble:
the model quietly serves listeners at the energy extremes well while giving eclectic,
middle-of-the-road users an incoherent list drawn from opposite poles.

- **It never says "no."** For an impossible mood (`sad`), an empty profile, or an unknown
  genre (`kpop`), the recommender still returns a confident top-5 instead of signaling that
  the request couldn't be honored. Silent degradation looks like success.
- **Hidden high-energy default.** Because ties are broken on raw energy, a profile that
  expresses *no* preference (empty profile) returns the catalog's loudest songs — a bias
  the user never asked for. "Louder" quietly becomes "better" whenever the real signal runs out.
- **Valence is too weakly weighted to honor emotion.** At only +0.5 max, the valence term
  can never pull a genuinely sad or melancholy song above a loud one. "Loud but sad" is
  literally unreachable — conflicting emotional requests always resolve in favor of energy,
  and calm/sad tracks like *Winter Adagio* never surface for a low-energy profile.
- **Near-ties masquerade as confident rankings.** In the Chill Lofi test, *Library Rain*
  beat the near-identical *Midnight Coding* by ~0.19 points purely because its energy sat
  exactly on target. The precise-looking score hides the fact that the #1-vs-#2 order is
  effectively a coin-flip a listener wouldn't notice.
- **Exact-string matching penalizes sub-genres and synonyms.** `indie pop` earns no credit
  toward a `pop` profile, and `intense` gets nothing from the closely related `aggressive`
  or `tense`. Users are judged by the dataset's labels, not their actual taste.
- **Tiny, cold catalog.** Only 18 songs, no listening history, popularity, or feedback, so
  the same profile always yields the same list — no discovery, no diversity, and any
  labeling bias in the small catalog passes straight through. It also considers nothing
  about lyrics, language, or artist.

---

## 7. Evaluation

I evaluated the recommender by running six user profiles through `python -m src.main`
and reading the top-5 for each: **three well-formed profiles** (High-Energy Pop, Chill
Lofi, Deep Intense Rock) to confirm it ranks sensibly for normal tastes, and **three
adversarial / edge-case profiles** designed to try to "trick" the scoring logic. All
outputs below are real terminal output.

### Well-formed profiles (sanity checks)

Each of these returned the intuitively "correct" #1 — the song that matches both the
genre and mood anchor and sits near the energy target — which is what I looked for.

```
# High-Energy Pop  (genre=pop, mood=happy, target_energy=0.85)
1. Sunrise City — Neon Echo      pop / happy      score 8.76
2. Gym Hero — Max Pulse          pop / intense    score 7.54
3. Rooftop Lights — Indigo Parade indie pop/happy  score 6.47
4. Pulse Reactor — Kilo Signal   edm / energetic  score 5.50
5. Night Drive Loop — Neon Echo  synthwave/moody  score 5.25
```

```
# Chill Lofi  (genre=lofi, mood=chill, target_energy=0.35)
1. Library Rain — Paper Lanterns lofi / chill     score 8.83
2. Midnight Coding — LoRoom      lofi / chill     score 8.64
3. Focus Flow — LoRoom           lofi / focused   score 7.76
4. Spacewalk Thoughts — Orbit Bloom ambient/chill score 6.35
5. Paper Boats — Wren & Hollow   folk / dreamy    score 5.73
```

```
# Deep Intense Rock  (genre=rock, mood=intense, target_energy=0.90)
1. Storm Runner — Voltline       rock / intense   score 8.88
2. Gym Hero — Max Pulse          pop / intense    score 6.29
3. Iron Verdict — Blacktide      metal / tense    score 5.45
4. Pulse Reactor — Kilo Signal   edm / energetic  score 5.12
5. Concrete Kingdom — Vell       hip hop/aggressive score 5.03
```

### Adversarial / edge-case profiles

**1. Conflicting signals — "Loud but Sad"** (`mood=sad`, `energy=0.95`, `tempo=160`, `valence=0.10`).
The mood `sad` does not exist in the catalog, so the mood bonus can *never* fire. The
system silently ignores the impossible mood and ranks purely on the numeric targets —
returning the loudest, fastest tracks. It never warns that "sad" matched nothing, and
none of the results are actually sad; the low-valence target is too weakly weighted
(+0.5 max) to pull in genuinely melancholy songs.

```
# Adversarial: Loud but Sad  (mood=sad, target_energy=0.95)
1. Iron Verdict — Blacktide    metal / tense      score 3.74
   • energy 0.97 vs target 0.95 (+1.96)
   • tempo bpm 168 vs target 160 (+1.39)
   • valence 0.31 vs target 0.1 (+0.40)
2. Storm Runner — Voltline     rock / intense     score 3.62
3. Gym Hero — Max Pulse        pop / intense      score 3.24
4. Pulse Reactor — Kilo Signal edm / energetic    score 3.19
5. Concrete Kingdom — Vell     hip hop/aggressive score 2.80
```

**2. Empty profile** (`{}` — no preferences at all). Every song scores exactly `0.00`,
so the ranking collapses onto the energy tie-break alone: the catalog's *loudest* songs
float to the top for no reason the user expressed. This is the clearest "trick" — with
no signal, the system still confidently returns a list, defaulting to a hidden
"louder = better" bias.

```
# Edge: Empty Profile  ({})
1. Iron Verdict — Blacktide    metal / tense      score 0.00  • general fit
2. Pulse Reactor — Kilo Signal edm / energetic    score 0.00  • general fit
3. Gym Hero — Max Pulse        pop / intense      score 0.00  • general fit
4. Storm Runner — Voltline     rock / intense     score 0.00  • general fit
5. Concrete Kingdom — Vell     hip hop/aggressive score 0.00  • general fit
```

**3. Unknown genre** (`genre=kpop` — not in the catalog). The +2.0 genre bonus can never
be awarded, so the profile degrades gracefully to mood + energy. Results are reasonable
(happy, mid-energy songs), but a user asking for a genre we don't carry gets no signal
that their main request was impossible to honor.

```
# Edge: Unknown Genre (kpop)  (genre=kpop, mood=happy, target_energy=0.5)
1. Rooftop Lights — Indigo Parade indie pop/happy score 2.48  (mood +1.0, energy +1.48)
2. Sunrise City — Neon Echo    pop / happy        score 2.36  (mood +1.0, energy +1.36)
3. Velvet Hours — Sable Rose   r&b / romantic     score 1.92
4. Dust Road Home — Prairie Line country/nostalgic score 1.84
5. Midnight Coding — LoRoom    lofi / chill       score 1.84
```

### What surprised me

- **The system never says "no."** For an impossible mood, an empty profile, or an
  unknown genre, it always returns a confident top-5 rather than flagging that the
  request couldn't be satisfied. Silent degradation looks like success.
- **The empty profile exposed a hidden default bias toward high-energy songs**, purely
  because energy is the tie-break. A user who expressed nothing gets loud music.
- **"Loud but sad" is unreachable** in this catalog and weighting — valence is too
  lightly weighted to ever surface a genuinely sad song over a loud one, so conflicting
  emotional requests resolve entirely in favor of the energy signal.

### Why does "Gym Hero" keep showing up for a "Happy Pop" listener?

*(Plain-language walkthrough.)* Gym Hero is a pop song, but its mood is labeled *intense*,
not *happy* — yet it still lands at #2 for the Happy Pop listener. Here's why, in everyday
terms: that listener asked for three things — pop, happy, and high-energy — and Gym Hero
nails **two of them**. It really is pop (that's worth a big +2.0), and it's very loud and
punchy (energy 0.93, right up near the target), which earns almost all of the energy
points. The only box it misses is the mood — it's "intense," not "happy" — and getting
that wrong costs just **one point**. So the system sees a song that's two-thirds of exactly
what was asked for and ranks it near the top. In short, Gym Hero keeps appearing because
the recommender rewards *genre + loudness* heavily, and a single wrong label (mood) isn't
enough to outweigh two strong right ones.

### Pairwise comparisons

Each pair below contrasts two profiles' top-5 results — what differs and why it makes sense.

| Profiles compared | What changed | Why it makes sense |
|---|---|---|
| **High-Energy Pop vs Chill Lofi** | Zero overlap — pop pulls loud, upbeat radio songs; lofi pulls quiet, acoustic study tracks | Opposite energy targets (0.85 vs 0.35) and opposite acousticness send them to opposite ends of the catalog |
| **High-Energy Pop vs Deep Intense Rock** | They *share* the loud songs (Gym Hero, Pulse Reactor appear in both), but the #1 differs (Sunrise City vs Storm Runner) | Both want high energy, so loud tracks fit either; the genre/mood anchor is what picks the "flavor" at the very top |
| **High-Energy Pop vs Unknown Genre (kpop)** | Both chase "happy," but the pop list is led by *Sunrise City*; the kpop list re-ranks toward mood + moderate energy | The kpop genre matches nothing, so it loses the +2.0 genre boost and falls back on mood and a lower energy target |
| **Chill Lofi vs Deep Intense Rock** | Complete opposites, no shared songs — soft acoustic vs loud electric | Everything the profiles ask for (energy, tempo, acousticness) points in opposite directions |
| **Chill Lofi vs Unknown Genre (kpop)** | Lofi returns calm lofi tracks; kpop returns brighter, happier mid-energy songs | Different mood (chill vs happy) and energy (0.35 vs 0.5) targets, and neither shares a genre match |
| **Deep Intense Rock vs Loud but Sad** | Nearly identical lists, but rock's #1 (Storm Runner) drops to #2 while metal's Iron Verdict rises to #1 | Removing the rock genre/mood anchor lets raw loudness decide — and Iron Verdict is simply the loudest |
| **High-Energy Pop vs Loud but Sad** | Pop's happy radio songs vanish; the loud list becomes all heavy/aggressive tracks | The "sad" request matches no mood, so nothing tempers the extreme energy target — only the loudest survive |
| **Chill Lofi vs Loud but Sad** | Total inversion — quietest songs vs loudest songs | The energy targets are at opposite extremes (0.35 vs 0.95), and neither profile's mood matches the catalog well |
| **Deep Intense Rock vs Empty Profile** | Similar loud songs, but the Empty list is all tied at 0.00 and ordered only by loudness | With no preferences, the energy tie-break alone ranks songs, so it accidentally mimics a "give me loud music" request |
| **High-Energy Pop vs Empty Profile** | Pop's happy songs disappear; the empty list is the loudest songs regardless of genre/mood | Expressing nothing removes every genre/mood/closeness signal, leaving only the loudness tie-break |
| **Chill Lofi vs Empty Profile** | Complete opposites — soft songs vs the loudest songs | The empty profile's hidden loudness default is the exact opposite of a low-energy request |
| **Loud but Sad vs Empty Profile** | Almost the same list (Iron Verdict tops both) | Both end up ranking by loudness — one on purpose (energy 0.95), one by accident (tie-break) |
| **Unknown Genre (kpop) vs Empty Profile** | kpop returns happy, mid-energy songs; empty returns the loudest songs | Even one real preference (happy + moderate energy) pulls results away from the default loud cluster |
| **Deep Intense Rock vs Unknown Genre (kpop)** | Rock returns heavy loud tracks; kpop returns gentle happy ones | Opposite moods (intense vs happy) and energy targets (0.90 vs 0.50) with no shared genre match |
| **Loud but Sad vs Unknown Genre (kpop)** | Loudest heavy songs vs softer happy songs | The energy targets differ sharply (0.95 vs 0.50) and their moods point in opposite emotional directions |

---

## 8. Future Work

If I kept building this, I would:

1. **Grow the catalog.** More songs, and more songs per genre, so users get real variety
   instead of one match and a lot of near-misses.
2. **Let the system say "no."** If a mood or genre doesn't exist, or the profile is empty,
   it should tell the user instead of quietly returning the loudest songs.
3. **Match moods and genres more loosely.** Treat "intense" and "aggressive" as close, and
   give partial credit for "indie pop" toward "pop," so small label differences don't hurt.

---

## 9. Personal Reflection

I learned that a recommender is really just a scoring rule plus a sort. Turning a vague
idea like "chill lofi" into points made the whole thing feel less magical and more like a
set of choices I control. Now when I use a real music app, I think about what it's scoring,
what data it's missing, and who it might be leaving out.

**My biggest learning moment** was watching the weights decide everything. I ran an
experiment that doubled the energy weight and halved the genre weight, expecting the
results to change a lot. They barely moved — because in this dataset, loud songs and
"energetic" genres are already the same songs. That taught me that a model's behavior
comes from the *data* as much as the rules, and you can't judge a weight without looking
at what the data actually contains.

**Using an AI assistant** helped most with speed and boilerplate — reading the CSV,
setting up the scoring loop, and formatting the terminal output cleanly. It was also great
for explaining trade-offs, like how much a mood match should count versus a genre match.
But I had to **double-check the parts that involved real numbers and judgment.** At one
point the AI wrote that two songs were "~0.14 apart" when the real gap was 0.19 — a small
math slip I only caught by checking the scores myself. I also had to decide which taste
profile was really "mine," and confirm that the top picks actually matched my musical
intuition. The AI could generate and explain, but it couldn't tell me whether the output
*felt* right — that part was on me.

**What surprised me** was how a pile of plain arithmetic — add 2 here, subtract a fraction
there — could produce a list that genuinely feels like a recommendation. There's no
"understanding" of music anywhere in it, yet asking for chill lofi returns exactly the
songs I'd pick. It made me realize how much of what feels like intelligence is really just
careful scoring plus good data.

**If I extended this**, I'd grow the catalog so users get real variety, make the system
admit when it can't honor a request instead of quietly returning loud songs, and match
moods and genres more loosely so "intense" and "aggressive" count as close. I'd also want
to test it with real listeners to see where its scores and their taste disagree.
