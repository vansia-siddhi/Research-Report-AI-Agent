"""
Research & Report Agent
========================
A multi-step AI agent that demonstrates the core "think -> decide -> act" loop.

Given a topic, the agent will:
  1. THINK: break the topic into 3-4 research sub-questions
  2. ACT: search the web for each sub-question (tool use)
  3. THINK: read the search results and extract key facts
  4. ACT: write a structured final report
  5. MEMORY: keep all intermediate findings in a running "scratchpad"
            so later steps can refer back to earlier ones

This uses Groq's free API (Llama 3.3) instead of a paid OpenAI key.
Get a free key at: https://console.groq.com -> API Keys
"""

import os
import json
import time
import requests
from groq import Groq
from bs4 import BeautifulSoup

# ── Setup ──────────────────────────────────────────────
client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
MODEL = "llama-3.3-70b-versatile"   # free, fast, good at structured tasks

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def llm_call(prompt, system="You are a helpful research assistant.", json_mode=False):
    """Single call to the free LLM. This is the agent's 'brain'."""
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt}
    ]
    kwargs = {"model": MODEL, "messages": messages, "temperature": 0.3}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content


# ── Tool: Web Search (free, no API key needed) ─────────
def web_search_tool(query, max_results=3):
    """
    A simple free web search tool using DuckDuckGo's HTML endpoint.
    This is the agent's 'hands' -- letting it act in the world.
    """
    try:
        resp = requests.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query},
            headers=HEADERS,
            timeout=10
        )
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for result in soup.select(".result__body")[:max_results]:
            title_el = result.select_one(".result__title")
            snippet_el = result.select_one(".result__snippet")
            title = title_el.get_text(strip=True) if title_el else ""
            snippet = snippet_el.get_text(strip=True) if snippet_el else ""
            if title or snippet:
                results.append({"title": title, "snippet": snippet})
        return results
    except Exception as e:
        return [{"title": "Search error", "snippet": str(e)}]


# ── The Agent ────────────────────────────────────────────
class ResearchAgent:
    """
    Demonstrates the core agent loop:
        THINK  -> plan what to do
        ACT    -> use a tool (web search)
        THINK  -> reason over the tool's output
        repeat -> until enough info is gathered
        ACT    -> produce final output
    """

    def __init__(self, topic):
        self.topic = topic
        self.scratchpad = []   # <-- this IS the agent's memory
        self.log = []          # for printing the agent's "thoughts" to the user

    def think_plan_subquestions(self):
        """Step 1 - THINK: break the topic into research sub-questions."""
        self._say("🧠 THINK: Breaking topic into sub-questions...")
        prompt = f"""Break down this research topic into exactly 3 specific, searchable sub-questions:

Topic: {self.topic}

Respond ONLY with JSON: {{"subquestions": ["q1", "q2", "q3"]}}"""
        raw = llm_call(prompt, json_mode=True)
        data = json.loads(raw)
        subquestions = data["subquestions"]
        self._say(f"   Plan: {subquestions}")
        return subquestions

    def act_search(self, query):
        """Step 2 - ACT: use the web search tool."""
        self._say(f"🔍 ACT: Searching for → \"{query}\"")
        results = web_search_tool(query)
        time.sleep(1)  # be polite to the free search endpoint
        return results

    def think_summarize(self, subquestion, search_results):
        """Step 3 - THINK: reason over the tool output, extract key facts."""
        self._say("🧠 THINK: Extracting key facts from search results...")
        context = "\n".join([f"- {r['title']}: {r['snippet']}" for r in search_results])
        prompt = f"""Based on these search results, write 2-3 factual bullet points
answering this question: "{subquestion}"

Search results:
{context}

If the search results don't contain enough info, say so honestly.
Respond with plain bullet points only, no preamble."""
        summary = llm_call(prompt)
        return summary

    def act_write_report(self):
        """Step 4 - ACT: produce the final structured output using all memory."""
        self._say("📝 ACT: Writing final report from gathered research...")
        memory_block = "\n\n".join(
            [f"### {item['question']}\n{item['findings']}" for item in self.scratchpad]
        )
        prompt = f"""You are writing a short research report on: "{self.topic}"

Here is the research gathered so far:
{memory_block}

Write a structured report with:
1. A title
2. A 2-sentence executive summary
3. Key findings (bullet points)
4. A short conclusion

Keep it concise and professional."""
        report = llm_call(prompt)
        return report

    def run(self):
        """The main agent loop: THINK -> ACT -> THINK -> ... -> ACT (final)."""
        self._say(f"\n{'='*60}\n🤖 AGENT STARTED — Topic: {self.topic}\n{'='*60}\n")

        subquestions = self.think_plan_subquestions()

        for q in subquestions:
            results = self.act_search(q)
            findings = self.think_summarize(q, results)
            # Save to memory -- this is what makes it an agent, not just a chatbot
            self.scratchpad.append({"question": q, "findings": findings})
            self._say(f"   ✅ Findings saved to memory.\n")

        report = self.act_write_report()

        self._say(f"\n{'='*60}\n✅ AGENT FINISHED\n{'='*60}\n")
        return report

    def _say(self, msg):
        print(msg)
        self.log.append(msg)


# ── Run it ───────────────────────────────────────────────
if __name__ == "__main__":
    if not os.environ.get("GROQ_API_KEY"):
        print("⚠️  Set your free Groq API key first:")
        print("    export GROQ_API_KEY=your_key_here   (Mac/Linux)")
        print('    $env:GROQ_API_KEY="your_key_here"    (Windows PowerShell)')
        print("\nGet a free key at: https://console.groq.com")
        exit(1)

    topic = input("Enter a research topic: ").strip() or "Benefits of remote work for small businesses"

    agent = ResearchAgent(topic)
    final_report = agent.run()

    print("\n\n" + "#" * 60)
    print("FINAL REPORT")
    print("#" * 60 + "\n")
    print(final_report)

    # Save to file
    with open("report_output.md", "w", encoding="utf-8") as f:
        f.write(f"# Research Report: {topic}\n\n{final_report}")
    print("\n💾 Report saved to report_output.md")
