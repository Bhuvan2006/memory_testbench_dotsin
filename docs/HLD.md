# High-level design

```mermaid
flowchart TD
    U[User message] --> R[run_turn]
    R -->|build_context| MM
    MM -->|additional_input| L[Team leader]
    MM -->|additional_input| W[writer]
    R --> L
    L -->|delegate_task_to_member| C[calendar_agent]
    L -->|delegate_task_to_member| W
    C --> T[read_calendar tool]
    T -->|large synthetic dump| C
    C -->|short summary| L
    W -->|reply| L
    L -->|final reply| R
    R -->|update: reply and tool output| MM
    L --> M[(Model: mock, Ollama or Anthropic)]
    C --> M
    W --> M

    subgraph MM[MemoryStrategy: one of three]
        FH[FullHistory]
        RS[RollingSummary]
        subgraph TM[TieredMemory]
            WM[Working: last N turns, trimmed tool output]
            SM[Semantic: key-value facts, profile block]
            EM[(Episodic: SQLite FTS5, decay and eviction)]
        end
    end
    RS -->|memory_ops| M
    TM -->|memory_ops| M

    subgraph SK[Skill path, compared on one Agent]
        F[skills folder: 10 SKILL.md files] --> LD[loader.py]
        LD -->|names and descriptions| P[System prompt]
        P --> A[Skill agent]
        A -->|load_skill name| LD
        LD -->|full body| A
    end
    A --> M

    R --> X[metrics.py: tokens per agent, cost, spend guard]
```

**Reading the diagram.** Each turn, `run_turn` asks the memory strategy for context. It gives that context to the leader and `writer` through Agno's `additional_input`, then runs the team. `calendar_agent` gets only its task. After the run, `run_turn` adds up tokens per agent and hands the reply and tool output back to the memory strategy. Model calls made by memory are counted separately as `memory_ops`.
