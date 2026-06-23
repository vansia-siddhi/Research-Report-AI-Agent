# Research & Report Agent (Free, No Paid API)

A beginner-friendly AI agent project that demonstrates the **think → decide → act**
loop your curriculum mentions, plus tool use and memory — without spending any money.

## What makes this an "agent" and not just a chatbot?

| Chatbot | Agent (this project) |
|---|---|
| One prompt → one reply | Plans multiple steps on its own |
| No tools | Calls a real tool (web search) |
| No memory between turns | Keeps a "scratchpad" of findings across steps |
| You drive every step | It drives itself once you give it a topic |

## How it works (the loop)

```
   ┌─────────────┐
   │   THINK     │  Break topic into 3 sub-questions
   └──────┬──────┘
          ▼
   ┌─────────────┐
   │    ACT      │  Search the web for sub-question #1
   └──────┬──────┘
          ▼
   ┌─────────────┐
   │   THINK     │  Read results, extract key facts → save to memory
   └──────┬──────┘
          │  (repeat for sub-question #2, #3...)
          ▼
   ┌─────────────┐
   │    ACT      │  Write final report using ALL memory gathered
   └─────────────┘
```

## Setup

1. Get a **free** Groq API key (no credit card needed):
    - Go to https://console.groq.com
    - Sign up → API Keys → Create API Key
    - Copy it

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set your key:

   **Windows PowerShell:**
   ```
   $env:GROQ_API_KEY="gsk_your_key_here"
   ```
   **Mac/Linux:**
   ```
   export GROQ_API_KEY="gsk_your_key_here"
   ```

4. Run it:
   ```
   python agent.py
   ```

5. Type a topic when prompted, e.g.:
   ```
   Enter a research topic: AI tools for small restaurants
   ```

6. Watch the agent think and act in real time in your terminal, then check
   `report_output.md` for the final saved report.

## Why Groq instead of OpenAI?

Groq's free tier runs open models (Llama 3.3) at no cost with generous daily
limits — perfect for learning. The code is written so swapping to OpenAI later
is a 5-minute change (just swap the `llm_call` function to use `openai.chat.completions.create`
instead of `client.chat.completions.create`, since both SDKs use a near-identical interface).

## Exercises to extend this (recommended next steps for your learning plan)

1. **Add a tool**: give the agent a calculator tool, or a "save to file" tool it can call mid-run.
2. **Add a loop limit**: make the agent decide *itself* whether it has enough info,
   instead of always doing exactly 3 sub-questions (true dynamic decision-making).
3. **Add memory persistence**: save `scratchpad` to a JSON file so the agent can
   resume research on the same topic later without starting over.
4. **Turn it into a Flask API**: wrap `ResearchAgent.run()` in a `/api/research` endpoint
   (you already know how to do this from the BizFind project) so it has a web UI.
5. **Multi-agent**: create a second agent ("Critic Agent") that reviews the first
   agent's report and asks for revisions — this is the core idea behind more
   advanced agent frameworks like AutoGen/CrewAI.
