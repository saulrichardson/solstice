# Fact-Check Pipeline Architecture Analysis (OUTDATED)

**⚠️ Note: This document describes the OLD monolithic architecture. The system has been refactored to use an agent-based pipeline. See `src/fact_check/docs/ARCHITECTURE.md` for the current architecture.**

## Current Structure

```
src/fact_check/
├── agents/
│   ├── __init__.py
│   ├── base.py                 # Abstract base class
│   └── text_evidence_finder.py # Concrete agent
├── core/
│   └── responses_client.py     # LLM client
├── pipeline.py                 # Orchestrator
└── fact_checker.py            # Core logic (monolithic)
```

## Strengths ✅

### 1. **Clear Separation of Concerns**
- `BaseAgent`: Handles lifecycle, metadata, I/O
- `TextEvidenceFinder`: Focuses on evidence finding
- `FactCheckPipeline`: Orchestrates execution
- File-based communication between agents

### 2. **Good Abstractions**
```python
class BaseAgent(ABC):
    @abstractmethod
    def agent_name(self) -> str
    
    @abstractmethod
    def required_inputs(self) -> List[str]
    
    @abstractmethod
    async def process(self) -> Dict[str, Any]
```

### 3. **Stateful Pipeline Management**
- Pipeline manifest tracks execution state
- Each agent has metadata tracking
- Resumable on failure
- Clear output structure

### 4. **Configuration Flexibility**
- JSON config files
- Command-line overrides
- Per-agent configuration

## Weaknesses ❌

### 1. **Monolithic Core Logic**
`fact_checker.py` combines:
- Prompt engineering
- LLM communication
- Quote verification
- Retry logic
- Response parsing

Should be split into:
- `PromptBuilder`
- `QuoteVerifier`
- `ResponseParser`

### 2. **Tight Coupling**
```python
# TextEvidenceFinder directly imports:
from fact_check.fact_checker import FactChecker
from injestion.models.document import Document
```
Better: Use interfaces/protocols

### 3. **Limited Extensibility**
- No plugin system
- Hard-coded agent initialization
- No dependency injection

### 4. **Missing Error Recovery**
- No partial result saving
- No checkpoint/restart within agents
- Limited retry strategies

## Suggested Improvements

### 1. **Decouple Core Components**
```python
# interfaces.py
from abc import ABC, abstractmethod
from typing import Protocol

class EvidenceFinder(Protocol):
    async def find_evidence(self, claim: str, document: str) -> EvidenceResult:
        ...

class DocumentProvider(Protocol):
    def get_text(self) -> str:
        ...
```

### 2. **Plugin-Based Agent Loading**
```python
# pipeline.py
class FactCheckPipeline:
    def _load_agents(self, config: Dict) -> List[BaseAgent]:
        agents = []
        for agent_config in config.get("pipeline", []):
            agent_class = self._registry.get(agent_config["type"])
            agents.append(agent_class(**agent_config["params"]))
        return agents
```

### 3. **Event-Driven Communication**
```python
# events.py
class AgentEvent:
    agent_name: str
    event_type: str  # started, completed, failed
    data: Dict[str, Any]

# Allow agents to subscribe to events
```

### 4. **Dependency Injection**
```python
# Better initialization
class TextEvidenceFinder(BaseAgent):
    def __init__(
        self,
        evidence_finder: EvidenceFinder,
        document_provider: DocumentProvider,
        config: Dict[str, Any]
    ):
        self.evidence_finder = evidence_finder
        self.document_provider = document_provider
```

### 5. **Strategy Pattern for Variations**
```python
# strategies.py
class QuoteMatchingStrategy(ABC):
    @abstractmethod
    def match_quote(self, quote: str, document: str) -> Optional[Match]:
        pass

class ExactMatchStrategy(QuoteMatchingStrategy):
    ...

class FuzzyMatchStrategy(QuoteMatchingStrategy):
    ...
```

## Best Practices Assessment

### Following ✅
1. **Single Responsibility**: Each class has clear purpose
2. **DRY**: Good code reuse via BaseAgent
3. **Explicit Dependencies**: Clear imports
4. **Async/Await**: Proper async patterns
5. **Type Hints**: Good type annotations

### Missing ❌
1. **Dependency Inversion**: Concrete dependencies
2. **Open/Closed**: Hard to extend without modification
3. **Interface Segregation**: Large interfaces
4. **Testing**: No unit tests visible
5. **Documentation**: Limited docstrings

## Modularity Score: 7/10

### Good Modularity
- Clean agent abstraction
- Separate pipeline orchestration
- File-based decoupling

### Needs Improvement
- Core logic too monolithic
- Cross-package coupling
- Limited plugin architecture

## Recommendations

1. **Split fact_checker.py** into smaller components
2. **Add interfaces** for cross-module communication
3. **Implement plugin registry** for dynamic agent loading
4. **Add event bus** for better agent communication
5. **Create testing framework** with mocks
6. **Add configuration validation**
7. **Implement proper logging hierarchy**

## Example Refactored Structure
```
src/fact_check/
├── agents/
│   ├── base.py
│   ├── registry.py          # Agent registry
│   └── implementations/
│       └── text_evidence.py
├── core/
│   ├── interfaces.py        # Protocols/ABCs
│   ├── evidence_finder.py   # Core logic
│   ├── quote_matcher.py     # Quote verification
│   └── prompt_builder.py    # Prompt engineering
├── pipeline/
│   ├── orchestrator.py      # Main pipeline
│   ├── events.py           # Event system
│   └── config.py           # Config validation
├── strategies/
│   ├── matching.py         # Quote matching strategies
│   └── retry.py            # Retry strategies
└── utils/
    ├── logging.py
    └── validation.py
```