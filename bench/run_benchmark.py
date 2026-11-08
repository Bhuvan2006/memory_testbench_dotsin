"""Run every configuration and write results. Example: python bench/run_benchmark.py --provider mock"""
import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))  # so `python bench/run_benchmark.py` can import src

from agno.agent import Agent  # noqa: E402
from agno.run.base import RunStatus  # noqa: E402
from agno.skills import LocalSkills, Skills  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

from bench.report import MEMORY_ORDER, SKILL_ORDER, write_report  # noqa: E402
from data.generate_scenario import build_scenario  # noqa: E402
from src.agents.members import make_model  # noqa: E402
from src.agents.team import build_team, run_turn  # noqa: E402
from src.memory.base import MemoryLLM  # noqa: E402
from src.memory.full_history import FullHistory  # noqa: E402
from src.memory.rolling_summary import RollingSummary  # noqa: E402
from src.memory.tiered.manager import TieredMemory  # noqa: E402
from src.metrics import SpendGuard, Usage, cost_usd, load_yaml, model_price, score_answer  # noqa: E402
from src.skills.loader import SkillLoader  # noqa: E402

SKILLS_DIR = ROOT / "skills"
SKILL_TASK = (
    "Use the meeting-notes skill on these jottings: met with Sam and Casey about the launch. "
    "Agreed to ship the beta on Friday. Casey will write the release post by Wednesday. Still unclear who owns support."
)
SKILL_TASK_ALL = (
    "Prepare my Monday pack from the notes below. Apply every one of these skills, each to its part of the notes: "
    "calendar-summary, task-extraction, daily-brief, meeting-notes, expense-report, goal-review, habit-check, "
    "inbox-triage, status-update, travel-plan. Notes: Monday has a 10am budget review and a 2pm design sync. "
    "Sam will send the slides by Tuesday. Met Casey about the launch and agreed on Friday. Spent 40 on a client lunch "
    "and 25 on a taxi. Goal: finish the beta this month, about half done. Walked on 4 of 7 days. Three unread emails: "
    "an invoice, a newsletter, a request from Sam. Project is on track. Flying to Lisbon on Thursday for two nights."
)
SKILL_BASE_PROMPT = "You help with work tasks. Follow the relevant skill when one applies."
COLUMNS = ["kind", "config", "rep", "provider", "model", "input_tokens", "output_tokens", "total_tokens", "cost_usd",
           "latency_s", "leader_tokens", "calendar_tokens", "writer_tokens", "memory_ops_tokens", "recall_correct", "wrong",
           "parse_failures", "starting_context_tokens", "skill_tool_calls"]


def make_strategy(name: str, llm: MemoryLLM, config: dict):
    if name == "full_history":
        return FullHistory()
    if name == "rolling_summary":
        return RollingSummary(llm, config["working_turns"], config["chunk_turns"])
    return TieredMemory(llm, config)


def base_row(kind: str, config: str, rep: int, provider: str, model_id: str, usage: Usage, price: dict, latency: float) -> dict:
    return {column: 0 for column in COLUMNS} | {
        "kind": kind, "config": config, "rep": rep, "provider": provider, "model": model_id,
        "input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens,
        "total_tokens": usage.input_tokens + usage.output_tokens, "cost_usd": round(cost_usd(usage, price), 6),
        "latency_s": round(latency, 2),
    }


def log_text(log, config: str, rep: int, kind: str, text: str, **extra) -> None:
    log.write(json.dumps({"config": config, "rep": rep, "kind": kind, "text": text, **extra}, ensure_ascii=False) + "\n")
    log.flush()  # logged text survives a later abort


def run_memory(name: str, rep: int, provider: str, model_id: str, settings: dict, guard: SpendGuard, log) -> dict:
    scenario, usage = build_scenario(), Usage()
    llm = MemoryLLM(make_model(provider, model_id, "memory", settings), usage)
    strategy = make_strategy(name, llm, settings["memory"])
    system = build_team(provider, model_id, settings)
    recall = {r["turn"]: r for r in scenario["recall"]}
    correct = wrong = 0
    started = time.perf_counter()
    for turn in scenario["turns"]:
        reply = run_turn(system, strategy, turn["index"], turn["user"], turn["tool_output"], usage)
        guard.check(usage)
        scored = {}
        if turn["index"] in recall:
            question = recall[turn["index"]]
            is_correct, is_wrong = score_answer(reply, question["expected"], question["stale"])
            correct += is_correct
            wrong += is_wrong
            scored = {"correct": is_correct, "wrong": is_wrong}
        log_text(log, name, rep, "reply", reply, turn=turn["index"], user=turn["user"], **scored)
        for summary in llm.outputs:
            log_text(log, name, rep, "summary", summary, turn=turn["index"])
        llm.outputs.clear()
        print(f"  {name} rep {rep} turn {turn['index']}/40", flush=True)
    guard.finish_run(usage)
    return base_row("memory", name, rep, provider, model_id, usage, guard.price, time.perf_counter() - started) | {
        "leader_tokens": usage.agent_total("leader"), "calendar_tokens": usage.agent_total("calendar_agent"),
        "writer_tokens": usage.agent_total("writer"), "memory_ops_tokens": usage.agent_total("memory_ops"),
        "recall_correct": correct, "wrong": wrong, "parse_failures": getattr(strategy, "parse_failures", 0),
    }


def build_skill_agent(mode: str, provider: str, model_id: str, settings: dict) -> Agent:
    loader = SkillLoader(SKILLS_DIR)
    model = make_model(provider, model_id, "skills", settings)
    if mode == "eager":
        return Agent(name="eager", model=model, instructions=f"{SKILL_BASE_PROMPT}\n\n{loader.eager_block()}", telemetry=False)
    if mode == "lazy":
        return Agent(name="lazy", model=model, instructions=f"{SKILL_BASE_PROMPT}\n\n{loader.catalog()}",
                     tools=[loader.load_skill], telemetry=False)
    return Agent(name="native", model=model, instructions=SKILL_BASE_PROMPT,
                 skills=Skills(loaders=[LocalSkills(str(SKILLS_DIR))]), telemetry=False)


def run_skill_mode(config: str, rep: int, provider: str, model_id: str, settings: dict, guard: SpendGuard, log) -> dict:
    usage = Usage()
    mode = config.removesuffix("_all")
    agent = build_skill_agent(mode, provider, model_id, settings)
    started = time.perf_counter()
    output = agent.run(SKILL_TASK_ALL if config.endswith("_all") else SKILL_TASK)
    if output.status != RunStatus.completed:
        raise RuntimeError(f"Skill run failed in {config} mode: {output.content}")
    usage.add(mode, output.metrics)
    guard.check(usage)
    guard.finish_run(usage)
    log_text(log, config, rep, "reply", str(output.content or ""))
    first_call = next(m for m in output.messages if m.role == "assistant")
    return base_row("skills", config, rep, provider, model_id, usage, guard.price, time.perf_counter() - started) | {
        "starting_context_tokens": first_call.metrics.input_tokens,
        "skill_tool_calls": sum(t.tool_name in ("load_skill", "get_skill_instructions") for t in output.tools or []),
    }


def main(argv: list[str] | None = None) -> Path:
    load_dotenv(ROOT / ".env")
    settings = load_yaml("settings.yaml")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", default=os.getenv("MODEL_PROVIDER", "mock"), choices=["mock", "anthropic", "ollama", "nvidia"])
    parser.add_argument("--model", default=os.getenv("MODEL_ID") or None)
    parser.add_argument("--reps", type=int, default=settings["repetitions"])
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    model_id = args.model or settings["default_model"][args.provider]
    # Mock output gets its own folder so it can never be mistaken for real results.
    out_dir = args.out or ROOT / ("results/mock" if args.provider == "mock" else "results")
    out_dir.mkdir(parents=True, exist_ok=True)
    guard = SpendGuard(settings["max_cost_usd"], model_price(args.provider, model_id, load_yaml("prices.yaml")))

    jobs = [(run_memory, name) for name in MEMORY_ORDER] + [(run_skill_mode, name) for name in SKILL_ORDER]
    with (out_dir / "results.csv").open("w", encoding="utf-8", newline="") as handle, \
            (out_dir / "replies.jsonl").open("w", encoding="utf-8") as log:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        for rep in range(1, args.reps + 1):
            for job, name in jobs:
                print(f"{name} rep {rep}", flush=True)
                writer.writerow(job(name, rep, args.provider, model_id, settings, guard, log))
                handle.flush()  # finished runs survive a later abort
    write_report(out_dir)
    print(f"Wrote {out_dir / 'summary.md'}. Estimated spend ${guard.finished_cost:.4f}.")
    return out_dir


if __name__ == "__main__":
    main()
