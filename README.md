# AdaCraft: Iterative Adaptive Personalization of Educational Examples via Agentic Feedback Loops

AdaCraft is an agentic tutoring system that turns a selected concept into a personalized educational example, then improves future examples from free-form learner feedback. It consists of a Flask API, a Manifest V3 Chrome extension, and a LangGraph workflow with durable per-user JSON records.

The runnable API and browser extension are currently branded **ExaCraft**. This README uses **AdaCraft**, the name and framing used by the accompanying research paper.

## What it does

- Generates structured examples for a topic selected in the browser.
- Personalizes examples from a saved profile: name, location, education, profession, and preferred complexity.
- Accepts natural-language feedback instead of ratings.
- Uses an Adaptive Response Agent to either regenerate the current example, save a positive/neutral insight, and/or record a persistent learning pattern.
- Uses a Context Manager Agent on later sessions to retrieve relevant historical signals while guarding against unrelated-domain carryover.
- Detects the language of the topic and asks the generator to answer in that language.
- Supports OpenAI, OpenRouter, and Sarvam through LangChain's OpenAI-compatible integrations.

## Research summary

AdaCraft addresses the limitation of one-shot personalization: a profile alone cannot respond when an example is irrelevant, too difficult, or poorly framed. It combines a static profile, history-aware context retrieval, and a tool-calling feedback agent to support both in-session revision and cross-session personalization.

The accompanying study evaluates the system across a four-tier ablation, human evaluation, and multilingual scenarios. In the two automated generator runs, the complete system improved composite quality over the generic baseline by **+0.631** (DeepSeek V3.2) and **+1.269** (GPT-5-nano). The paper source is [Research_Paper/Paper.tex](Research_Paper/Paper.tex).

## Architecture

```text
Chrome extension
  selected text -> background service worker -> Flask API (:8000)
                                                   |
                                                   v
  profile JSON <--------------------------- LangGraph workflow
                                             1. load profile
                                             2. build historical context
                                             3. generate example
                                             4. save example
                                             5. interrupt for feedback
                                             6. process feedback
                                                   |
                              regenerate (up to 3 times) or finish
                                                   |
                                                   v
                         per-user JSON: examples, feedback, patterns, insights
```

The workflow is checkpointed by LangGraph. `memory` is the default checkpoint backend; SQLite and PostgreSQL are optional when their LangGraph checkpoint packages are installed.

## Feedback loop

1. The extension starts a workflow for a topic and receives an example plus a `thread_id`.
2. The workflow pauses at a LangGraph interrupt while the extension shows a feedback box.
3. On resume, the Adaptive Response Agent calls one or more tools:
   - `regenerate(instruction)` rewrites the example immediately.
   - `accept(insight)` saves a positive or neutral signal.
   - `flag_pattern(pattern_type, observation)` saves a longer-term preference or learning trait.
4. Regeneration returns to the generation node and pauses again. A thread is limited to three regeneration loops.
5. For a returning user, the Context Manager resolves topic tags and uses matching examples, linked feedback, patterns, and accepted insights to emit a focused instruction for the next generation. It is skipped when no useful history exists.

Generated examples are retained for 30 days (up to 100 entries per user). Feedback recency indexes retain 200 example IDs; accepted insights retain the latest 50 entries.

## Prerequisites

- Python 3.8 or later
- Google Chrome or another Chromium browser with extension developer mode
- An API key for one of the supported providers
  - OpenAI: `OPENAI_API_KEY`
  - OpenRouter: `OPENROUTER_API_KEY`
  - Sarvam: `SARVAM_API_KEY`

## Run locally

```powershell
git clone <repository-url>
cd MTP
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create a `.env` file in the repository root. This is the minimum configuration for the default provider:

```dotenv
DEFAULT_LLM_PROVIDER=openai
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini
```

Then start the API:

```powershell
python api_server.py
```

The development server listens at `http://localhost:8000`. The current launcher binds to port 8000 directly, so the extension and local API must use that port.

Load the browser extension:

1. Open `chrome://extensions`.
2. Enable **Developer mode**.
3. Choose **Load unpacked**.
4. Select this repository's root directory.
5. Open the extension popup, save a profile, and use the right-click menu on selected text to generate an example.

The extension stores its profile and provider preference in `chrome.storage.local`; saving a profile also posts it to the local API, which writes `user_profiles/<user_id>.json`.

### Provider configuration

| Provider | Environment variables | Default model |
| --- | --- | --- |
| OpenAI | `OPENAI_API_KEY`, `OPENAI_MODEL` | `gpt-4o-mini` |
| OpenRouter | `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` | `deepseek/deepseek-v3.2` |
| Sarvam | `SARVAM_API_KEY`, `SARVAM_MODEL` | `sarvam-105b` |

Set `DEFAULT_LLM_PROVIDER` to `openai`, `openrouter`, or `sarvam`. A workflow request can override it with its `provider` field. OpenRouter reasoning is disabled by default for OpenRouter models so reasoning traces do not appear in examples.

> Current extension caveat: its provider dropdown still displays a legacy Gemini option, but the backend no longer implements Gemini. Select **OpenAI** in the popup, or call the API directly with `openai`, `openrouter`, or `sarvam`.

Other supported settings in `config/settings.py` include `ENVIRONMENT`, `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`, `CHECKPOINT_TYPE`, and `DATABASE_URL`. `CHECKPOINT_TYPE` accepts `memory`, `sqlite`, and `postgres`; unavailable optional checkpoint dependencies fall back to memory.

## API

Base URL: `http://localhost:8000`. API errors use `"success": false`; successful workflow operations use `"success": true` unless the workflow itself recorded an error.

### Start an adaptive workflow

`POST /workflows/feedback/start`

```json
{
  "user_id": "priya_sharma",
  "topic": "Newton's Second Law",
  "mode": "adaptive",
  "provider": "openai"
}
```

`user_id` must be 1–100 characters and `topic` must be 1–500 characters. `mode` accepts `adaptive` or `simple`; the workflow currently follows the same adaptive graph for both values.

```json
{
  "success": true,
  "thread_id": "thread_...",
  "generated_example": "...",
  "example_id": "ex_...",
  "status": "awaiting_feedback"
}
```

### Resume with feedback

`POST /workflows/<thread_id>/resume`

```json
{
  "user_feedback_text": "Use a hospital example and make it simpler."
}
```

`user_feedback_text` is required and may be an empty string to skip feedback. It is limited to 2,000 characters. A regeneration response has `status: "awaiting_feedback"` and includes a new `generated_example`; completion has `status: "completed"`.

### Other endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Health status and advertised endpoints |
| `GET` | `/api-info` | Workflow and agent metadata |
| `POST` | `/validate-profile` | Validate a profile object without saving it |
| `POST` | `/sync-profile` | Persist a popup profile to `user_profiles/` |
| `GET` | `/workflows/<thread_id>/state` | Inspect checkpointed thread state |
| `DELETE` | `/workflows/<thread_id>` | Remove the thread from the in-process active-thread registry |
| `GET` | `/workflows?user_id=<id>` | List active workflow records, optionally by user |

The profile payload used by the current extension is flat:

```json
{
  "profile": {
    "name": "Priya Sharma",
    "location": "Chennai, India",
    "education": "professional",
    "profession": "Nurse",
    "complexity": "simple"
  }
}
```

## Repository layout

```text
api_server.py                 Flask entry point and REST endpoints
config/settings.py            Environment, provider, path, and checkpoint settings
core/
  workflow_graphs.py          Six-node LangGraph definition and loop routing
  workflow_nodes.py           Profile, context, generation, persistence, interrupt, feedback nodes
  workflow_manager.py         Thread start/resume/state lifecycle
  context_manager_agent.py    History-aware context agent and subject-tag retrieval
  adaptive_response_agent.py  Tool-calling feedback agent
  feedback_store.py           Feedback, pattern, and insight JSON stores
  example_history.py          Generated-example history
background.js                 MV3 service worker and API bridge
content.js                    Page overlay and feedback UI
popup.html / popup.js         Profile and provider settings UI
eval/                         Ablation, multilingual, and human-evaluation tooling
Research_Paper/               Paper sources and generated research artifacts
```

Runtime-created user data is intentionally ignored by Git:

- `user_profiles/`
- `learning_contexts/`
- `data/example_history/`
- `data/feedback_history/`
- `data/learning_patterns/`
- `data/accept_insights/`

Do not commit `.env` or user-generated JSON data.

## Evaluation

The ablation suite evaluates four configurations:

| Tier | Profile | Context manager | Feedback agent |
| --- | --- | --- | --- |
| T0 | No | No | No |
| T1 | Yes | No | No |
| T2 | Yes | Yes | No |
| T3 | Yes | Yes | Yes |

### Automated results

The study evaluates 8 synthetic users (four cross-cultural profiles, each in cold- and warm-start conditions) across four topics, for 32 user-topic cells per tier and 128 cells per generator run. The primary judge is GPT-4.1-nano; Llama 3.3 70B scores a 20% subsample to assess inter-judge reliability.

| Generator | T0 | T1 | T2 | T3 | T0 → T3 |
| --- | ---: | ---: | ---: | ---: | ---: |
| DeepSeek V3.2 | 4.257 | 4.809 | 4.859 | 4.888 | +0.631 |
| GPT-5-nano | 3.712 | 4.388 | 4.791 | 4.981 | +1.269 |

All six pairwise tier comparisons are significant after Holm-Bonferroni correction (`p < 0.001`) in both runs. The reported rank-biserial effect size is 1.000 for each comparison; secondary-judge agreement is Cohen's kappa ≥ 0.607.

The composite is a weighted five-axis score: Personalization Fidelity (0.20), Complexity Calibration (0.20), Conceptual Accuracy (0.30), Pedagogical Clarity (0.20), and Domain Appropriateness (0.10).

### Feedback-loop results

| Metric | DeepSeek V3.2 | GPT-5-nano | Meaning |
| --- | ---: | ---: | --- |
| FCR@3 | 1.000 | 0.945 | Regenerations that address the critique at ≥3/5 |
| FCR@4 | 0.902 | 0.891 | Regenerations that address the critique at ≥4/5 |
| LUR | 0.938 | 0.969 | T3 sessions that trigger at least one regeneration |
| PPU delta PF | +0.312 | +1.938 | Warm-start T3 versus warm-start T1 first-generation personalization |

### Human and multilingual evaluation

- **Study A:** 10 learners evaluated 20 examples on their own topics. T3 was preferred over T0 in 18/20 cases (90%).
- **Study B:** the same 10 participants independently annotated 30 ablation examples. T3 was preferred in 26/30 cases (86.7%); composite human–LLM agreement was `r = 0.629`.
- **Multilingual robustness:** DeepSeek V3.2 and GPT-5-nano were tested in Hindi, Tamil, Bengali, German, Arabic, and Mandarin Chinese; Sarvam 105B was tested on the Indic subset. The study reports no statistically significant generation-quality degradation relative to English for any provider.

These results are evaluation findings, not a guarantee of performance on arbitrary learners or topics. The paper notes that the 8 automated users are synthetic and that seeded warm-start patterns do not replace a longitudinal real-user study.

Run a fresh ablation evaluation with a new tag only; completed results are immutable source-of-truth artifacts:

```powershell
python eval/ablation/seed_warm_start.py
python eval/ablation/run_evaluation.py --run-tag <new-tag> --provider openai
python eval/ablation/analysis_minimal.py --results-dir eval/ablation/results/<new-tag> --provider openai
```

The evaluator uses five 1–5 axes—personalization fidelity, complexity calibration, conceptual accuracy, pedagogical clarity, and domain appropriateness—and reports feedback compliance, loop utilization, and pattern-persistence utilization. Existing aggregate results are documented in [eval/ablation/results/results.md](eval/ablation/results/results.md), with statistical tests in [eval/ablation/Sig.md](eval/ablation/Sig.md). The repository also contains multilingual evaluation tools in `eval/multilingual/` and two human-evaluation studies in `eval/human_eval/`.

## Development notes

- There is no separate automated unit-test suite. For code changes, exercise the relevant API endpoint locally; for workflow changes, use the appropriate evaluation script.
- The extension requires the local server because its host permission is restricted to `http://localhost:*/*`.
- `GET /workflows` is an in-process registry. With the default memory checkpointer, restarting the API clears workflow state.
- Keep provider credentials in `.env`. Never enable OpenRouter reasoning unless a task explicitly requires it.

## License

No license file is currently present in this repository. Add an explicit license before redistributing the project.
