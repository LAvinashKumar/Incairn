# Incairn — A Daily Numerical Logic Puzzle

Incairn is a daily puzzle game built around pattern recognition, logical deduction, and hidden arithmetic relationships.

Players are given ten numbered stones and an empty four-level pyramid. Their challenge is to arrange every stone correctly by discovering the hidden mathematical rule that connects each parent stone to the two stones beneath it.

Unlike traditional arithmetic puzzles, Incairn does not reveal the rule. Success comes from identifying patterns, testing hypotheses, and uncovering the logic that governs the entire structure.

---

## Core Gameplay

Every puzzle consists of:

* 10 numbered stones
* A 4-level pyramid structure
* One hidden arithmetic relationship
* A single valid solution (plus its mirror equivalent)

Players must:

1. Analyze the available numbers.
2. Infer the hidden arithmetic rule.
3. Arrange all stones into the pyramid.
4. Validate the completed structure.

The challenge is not heavy calculation, but discovering the underlying relationship that makes the entire pyramid consistent.

---

## Key Features

### Daily Puzzle Experience

A new puzzle can be generated every day, encouraging repeat engagement and long-term retention.

### Multiple Difficulty Levels

**Easy**

* Addition-based relationships
* Clear and intuitive patterns
* Designed for onboarding and quick wins

**Medium**

* Multiplication and hybrid arithmetic relationships
* Requires experimentation and logical deduction

**Hard**

* Complex arithmetic relationships
* Greater ambiguity and deeper reasoning
* Designed for experienced puzzle players

### Hint System

Players can use limited hints when stuck, allowing progress without completely revealing the solution.

### Feedback Collection

Integrated feedback system allows collection of player observations, difficulty ratings, and gameplay impressions for continuous puzzle refinement.

---

## Product Design Goals

Incairn was designed around three core principles:

### Challenge Without Frustration

The puzzle should not be immediately obvious, but it should never feel impossible.

### Discovery-Driven Gameplay

Players should experience moments of insight as they uncover the hidden rule.

### Daily Replayability

A successful puzzle should encourage players to return day after day while maintaining novelty and challenge.

---

## Technical Architecture

```text
Incairn/
├── app.py
├── generator.py
├── feedback.py
├── review.py
├── incairn_boards.json
└── incairn_feedback.json
```

### app.py

Main Streamlit application containing the complete player experience, navigation flow, gameplay mechanics, and puzzle validation.

### generator.py

Board generation engine responsible for creating valid Incairn puzzles across multiple difficulty levels while maintaining puzzle quality constraints.

### feedback.py

Feedback collection and storage system used for playtesting and puzzle evaluation.

### review.py

Internal review tool used to evaluate generated boards, identify weak puzzles, and refine generation logic.

### incairn_boards.json

Generated puzzle library used by the application.

### incairn_feedback.json

Stores player feedback and playtesting observations.

---

## Board Generation Framework

Incairn uses a rule-based generation framework.

Each puzzle is generated using a predefined arithmetic relationship.

Example rule families include:

### Easy

* x + y
* x + y + 1
* 2x + y
* |x − y|

### Medium

* x × y
* x × y + 1
* x × y + y

### Hard

* x × y − x
* x × y − y
* x × y + x + y

The selected rule remains hidden from the player throughout gameplay.

---

## Generation Process

1. Select arithmetic rule.
2. Generate a valid pyramid.
3. Extract all 10 values.
4. Shuffle values.
5. Validate puzzle constraints.
6. Verify solution uniqueness.
7. Publish puzzle.

This approach ensures that every puzzle is solvable, logically consistent, and aligned with its intended difficulty level.

---

## Playtesting & Evaluation

To improve puzzle quality, generated boards are continuously evaluated through playtesting.

Evaluation focuses on:

* Rule discoverability
* Perceived difficulty
* Completion time
* Player satisfaction
* Hint usage
* Overall engagement

The goal is to create puzzles that are challenging enough to be rewarding, but intuitive enough to remain enjoyable.

---

## Future Enhancements

* Daily challenge system
* Global leaderboard
* User accounts and streak tracking
* Advanced analytics dashboard
* Community-created puzzles
* Additional rule families
* Adaptive difficulty generation

---

## Built With

* Python
* Streamlit
* JSON-based board storage

---

## Vision

Incairn aims to combine the accessibility of daily puzzle games like Wordle and Connections with the satisfaction of mathematical discovery.

Every puzzle is designed to create a moment of insight—where a collection of disconnected numbers suddenly reveals a hidden structure.
