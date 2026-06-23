"""
Research & Report Agent — Flask Backend
=========================================
Wraps the ResearchAgent in a web API + serves a frontend UI.
Streams the agent's think/act steps live to the browser using
Server-Sent Events (SSE), so the user sees the agent "work" in real time.
"""

import os
import json
import time
import requests
from flask import Flask, request, Response, send_from_directory, jsonify
from flask_cors import CORS
from groq import Groq
from bs4 import BeautifulSoup

app = Flask(__name__, static_folder="static")
CORS(app)

client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
MODEL = "llama-3.3-70b-versatile"

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def llm_call(prompt, system="You are a helpful research assistant.", json_mode=False):
    messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
    kwargs = {"model": MODEL, "messages": messages, "temperature": 0.3}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content


def web_search_tool(query, max_results=3):
    try:
        resp = requests.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query}, headers=HEADERS, timeout=10
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


def sse_event(event_type, data):
    """Format a Server-Sent Event message."""
    return f"data: {json.dumps({'type': event_type, **data})}\n\n"


def run_agent_stream(topic):
    """Generator that runs the agent loop and yields SSE events at each step."""
    scratchpad = []

    yield sse_event("status", {"message": f"Agent started for topic: {topic}", "step": "start"})

    # STEP 1: THINK - plan subquestions
    yield sse_event("step", {"phase": "think", "message": "Breaking topic into research sub-questions..."})
    plan_prompt = f"""Break down this research topic into exactly 3 specific, searchable sub-questions:

Topic: {topic}

Respond ONLY with JSON: {{"subquestions": ["q1", "q2", "q3"]}}"""
    try:
        raw = llm_call(plan_prompt, json_mode=True)
        subquestions = json.loads(raw)["subquestions"]
    except Exception as e:
        yield sse_event("error", {"message": f"Planning failed: {str(e)}"})
        return

    yield sse_event("plan", {"subquestions": subquestions})

    # STEP 2-3: ACT (search) + THINK (summarize) for each subquestion
    for i, q in enumerate(subquestions):
        yield sse_event("step", {"phase": "act", "message": f"Searching: \"{q}\"", "index": i})
        results = web_search_tool(q)
        time.sleep(0.5)

        yield sse_event("step", {"phase": "think", "message": "Extracting key facts from results...", "index": i})
        context = "\n".join([f"- {r['title']}: {r['snippet']}" for r in results])
        summary_prompt = f"""Based on these search results, write 2-3 factual bullet points
answering this question: "{q}"

Search results:
{context}

If the search results don't contain enough info, say so honestly.
Respond with plain bullet points only, no preamble."""
        try:
            findings = llm_call(summary_prompt)
        except Exception as e:
            findings = f"Could not summarize: {str(e)}"

        scratchpad.append({"question": q, "findings": findings})
        yield sse_event("finding", {"question": q, "findings": findings, "index": i})

    # STEP 4: ACT - write final report
    yield sse_event("step", {"phase": "act", "message": "Writing final structured report..."})
    memory_block = "\n\n".join([f"### {item['question']}\n{item['findings']}" for item in scratchpad])
    report_prompt = f"""You are writing a short research report on: "{topic}"

Here is the research gathered so far:
{memory_block}

Write a structured report in Markdown with:
1. A title (as # heading)
2. A 2-sentence executive summary
3. Key findings (bullet points)
4. A short conclusion

Keep it concise and professional."""
    try:
        report = llm_call(report_prompt)
    except Exception as e:
        yield sse_event("error", {"message": f"Report generation failed: {str(e)}"})
        return

    yield sse_event("done", {"report": report, "scratchpad": scratchpad})


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/research")
def research():
    """SSE endpoint: streams agent progress live to the browser."""
    topic = request.args.get("topic", "").strip()
    if not topic:
        return jsonify({"error": "No topic provided"}), 400

    return Response(run_agent_stream(topic), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/api/health")
def health():
    key = os.environ.get("GROQ_API_KEY", "")
    return jsonify({"status": "ok", "api_key_set": bool(key)})


if __name__ == "__main__":
    print("\n" + "=" * 55)
    print("  Research & Report Agent — Web UI")
    print("=" * 55)
    key = os.environ.get("GROQ_API_KEY", "")
    if not key:
        print("  ⚠️  GROQ_API_KEY not set!")
        print("  Get a free key at https://console.groq.com")
        print('  Then: export GROQ_API_KEY="gsk_..." (or $env: on Windows)')
    else:
        print(f"  ✅ API Key detected: {key[:8]}...")
    print("  🌐 Open: http://localhost:5000")
    print("=" * 55 + "\n")
    app.run(debug=True, port=5000, threaded=True)
