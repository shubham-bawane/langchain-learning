import ast
import operator
from datetime import datetime, timezone
from typing import Any

import httpx
from ddgs import DDGS
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool

from main import llm

_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.USub: operator.neg,
}


def _eval(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))
    raise ValueError("unsupported expression")


@tool
def calculator(expression: str) -> str:
    """Evaluate an arithmetic expression such as '(12 + 3) * 4 / 5'."""
    try:
        return str(_eval(ast.parse(expression, mode="eval").body))
    except Exception as exc:
        return f"error: {exc}"


@tool
def current_time() -> str:
    """Get the current date and time in UTC."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


@tool
def word_count(text: str) -> int:
    """Count the words in a piece of text."""
    return len(text.split())


@tool
def web_search(query: str) -> str:
    """Search the web and return the top results (title, snippet, url)."""
    try:
        results = DDGS().text(query, max_results=4)
    except Exception as exc:
        return f"error: {exc}"
    if not results:
        return "no results"
    return "\n".join(f"- {r['title']}: {r['body']} ({r['href']})" for r in results)


_http = httpx.Client(transport=httpx.HTTPTransport(retries=3), timeout=10)

_WMO = {
    0: "clear", 1: "mostly clear", 2: "partly cloudy", 3: "overcast", 45: "fog",
    51: "light drizzle", 53: "drizzle", 55: "heavy drizzle", 61: "light rain", 63: "rain",
    65: "heavy rain", 71: "snow", 73: "moderate snow", 75: "heavy snow",
    80: "rain showers", 95: "thunderstorm",
}


@tool
def get_weather(city: str) -> str:
    """Get the current weather for a city name, e.g. 'Pune'."""
    try:
        geo = _http.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1},
        ).json()
        place = geo["results"][0]
        cur = _http.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": place["latitude"], "longitude": place["longitude"],
                "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
            },
        ).json()["current"]
    except (KeyError, IndexError):
        return f"city not found: {city}"
    except httpx.HTTPError as exc:
        return f"error: {exc}"
    sky = _WMO.get(cur["weather_code"], f"code {cur['weather_code']}")
    return (
        f"{place['name']}, {place.get('country', '')}: {cur['temperature_2m']}°C, {sky}, "
        f"humidity {cur['relative_humidity_2m']}%, wind {cur['wind_speed_10m']} km/h"
    )


TOOLS = [calculator, current_time, word_count, web_search, get_weather]

SYSTEM_PROMPT = (
    "You are a ReAct agent. Think about what is needed, call a tool when it helps, "
    "read the observation, and repeat until you can give a final answer. "
    "Use tools for math, time, counting, current weather and anything that needs fresh "
    "information from the web instead of guessing."
)


def build_agent(model: str, temperature: float):
    bound = llm.bind(model=model, temperature=temperature)
    return create_agent(bound, tools=TOOLS, system_prompt=SYSTEM_PROMPT)


def extract_steps(messages: list[Any]) -> tuple[list[dict[str, Any]], str]:
    """Turn the message history into Thinking/Action/Observation steps and the answer."""
    steps: list[dict[str, Any]] = []
    answer = ""
    for msg in messages:
        if isinstance(msg, AIMessage):
            if msg.tool_calls:
                for call in msg.tool_calls:
                    steps.append({"type": "action", "tool": call["name"], "input": call["args"]})
            else:
                answer = str(msg.content)
        elif isinstance(msg, ToolMessage):
            steps.append({"type": "observation", "tool": msg.name, "output": str(msg.content)})
    return steps, answer
