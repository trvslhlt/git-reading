# Git-Reading System Architecture

## Overview

Git-reading is a tool for validating, extracting, querying, and analyzing reading notes stored in markdown files. The workflow is **validation-first**: all markdown files must pass normalization/validation checks before extraction can proceed. This ensures data quality throughout the pipeline.

## System Architecture Diagram

```mermaid
graph TB
    subgraph Input["📁 Input Sources"]
        MD[Markdown Files<br/>lastname__firstname.md]
        GIT[Git History<br/>blame data]
    end

    subgraph Normalize["✅ NORMALIZE Pipeline (REQUIRED FIRST)"]
        LEARN[Learn Patterns<br/>Statistical analysis]
        VALID[Validate<br/>Rule-based checking]
        FIX[Fix Issues<br/>Interactive repair]

        LEARN -->|patterns.json| VALID
        VALID -->|issues.json| FIX
        FIX -->|updates| MD
    end

    GATE{All Issues<br/>Fixed?}

    subgraph Extract["🔍 EXTRACT Pipeline (BLOCKED UNTIL VALID)"]
        PARSE[Parse Markdown<br/>- Extract titles & sections<br/>- Parse author from filename]
        BLAME[Git Blame<br/>Get date_read from<br/>first commit]
        PARSE --> BLAME
    end

    subgraph Storage["💾 Storage Layer"]
        JSON[JSON Index<br/>book_index.json<br/>- books<br/>- authors<br/>- sections]
        SQLITE[(SQLite DB<br/>readings.db<br/>Relational schema)]
        FAISS[FAISS Vector Store<br/>.tmp/vector_store/<br/>- embeddings<br/>- metadata lookups]
    end

    subgraph Search["🔎 SEARCH Pipeline"]
        BUILD[Build Index<br/>- Generate embeddings<br/>- Create FAISS index<br/>- Build metadata lookups]
        QUERY[Query<br/>- Encode query<br/>- Pre-filter by metadata<br/>- Semantic search]
        STATS[Statistics<br/>Index info]

        BUILD --> QUERY
        BUILD --> STATS
    end

    subgraph Output["📤 Outputs"]
        CLI[CLI Results<br/>Rich formatted]
        ISSUES[Validation Issues<br/>issues.json]
        PATTERNS[Learned Patterns<br/>patterns.json]
        RESULTS[Search Results<br/>Ranked by relevance]
    end

    MD --> LEARN
    MD --> VALID

    VALID --> ISSUES
    LEARN --> PATTERNS

    VALID -->|check status| GATE
    GATE -->|NO| FIX
    GATE -->|YES| PARSE

    PARSE --> MD
    GIT --> BLAME
    BLAME --> JSON

    JSON --> BUILD
    JSON --> SQLITE

    FAISS --> QUERY
    QUERY --> RESULTS
    VALID --> CLI
    STATS --> CLI

    classDef inputStyle fill:#e1f5ff,stroke:#0288d1,stroke-width:2px
    classDef processStyle fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef storageStyle fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef outputStyle fill:#e8f5e9,stroke:#388e3c,stroke-width:2px
    classDef blockingStyle fill:#ffebee,stroke:#c62828,stroke-width:3px

    class MD,GIT inputStyle
    class PARSE,BLAME,VALID,LEARN,FIX,BUILD,QUERY,STATS processStyle
    class JSON,SQLITE,FAISS storageStyle
    class CLI,ISSUES,PATTERNS,RESULTS outputStyle
    class GATE blockingStyle
```

## Data Flow

```mermaid
sequenceDiagram
    participant User
    participant MD as Markdown Files
    participant Normalize
    participant Extract
    participant JSON as book_index.json
    participant Search
    participant FAISS
    participant Load
    participant SQLite

    Note over User,Normalize: PHASE 1: NORMALIZE (REQUIRED FIRST)

    User->>Normalize: make run-learn-patterns
    Normalize->>MD: Analyze corpus
    Normalize->>User: Output patterns.json

    User->>Normalize: make run-validate
    Normalize->>MD: Read markdown files
    Normalize->>Normalize: Apply validators
    Normalize->>User: Output issues.json

    alt Issues Found
        Note over User,MD: BLOCKING: Must fix issues before extraction
        User->>Normalize: make run-fix
        Normalize->>Normalize: Interactive fixes
        Normalize->>MD: Update markdown files
        User->>Normalize: make run-validate
        Normalize->>User: Confirm: No issues
    end

    Note over User,Extract: PHASE 2: EXTRACT (Unblocked after validation)

    User->>Extract: make run-extract
    Extract->>MD: Parse markdown files
    Extract->>Extract: Run git blame
    Extract->>JSON: Generate index

    Note over User,SQLite: PHASE 3: QUERY & LOAD (Use extracted data)

    User->>Search: make run-search-build
    Search->>JSON: Read index
    Search->>Search: Generate embeddings
    Search->>FAISS: Create vector index

    User->>Search: make run-search-query "topic"
    Search->>FAISS: Semantic search
    FAISS->>FAISS: Pre-filter by metadata
    FAISS->>User: Return ranked results

    User->>Load: make run-migrate
    Load->>JSON: Read index
    Load->>SQLite: Create relational schema
```

## Component Responsibilities

```mermaid
graph LR
    subgraph "Extract Module"
        E1[CLI Interface]
        E2[Markdown Parser]
        E3[Git Integration]
        E4[Author Extraction]
    end

    subgraph "Normalize Module"
        N1[Validation Orchestrator]
        N2[Rule Validators x5]
        N3[Pattern Learner]
        N4[Interactive Fixer]
        N5[Report Generators]
    end

    subgraph "Search Module"
        S1[Embedding Generator]
        S2[Vector Store Manager]
        S3[Metadata Filter]
        S4[Query Engine]
    end

    subgraph "Load Module"
        L1[Schema Manager]
        L2[Migration Engine]
        L3[DB Utils]
    end

    E1 --> E2 --> E3 --> E4
    N1 --> N2 & N3
    N2 --> N4 --> N5
    S1 --> S2 --> S3 --> S4
    L1 --> L2 --> L3
```

## Storage Schema

```mermaid
erDiagram
    BOOKS ||--o{ BOOK_AUTHORS : has
    AUTHORS ||--o{ BOOK_AUTHORS : writes
    BOOKS ||--o{ BOOK_GENRES : categorized
    GENRES ||--o{ BOOK_GENRES : tags
    BOOKS ||--o{ NOTES : contains
    AUTHORS ||--o{ AUTHOR_INFLUENCES : influences

    BOOKS {
        int id PK
        string title
        string isbn
        int publication_year
        string publisher
        int page_count
    }

    AUTHORS {
        int id PK
        string first_name
        string last_name
        string name
        int birth_year
        int death_year
    }

    BOOK_AUTHORS {
        int book_id FK
        int author_id FK
        string author_role
    }

    NOTES {
        int id PK
        int book_id FK
        string section
        string excerpt
        int page_number
        int faiss_index
    }

    GENRES {
        int id PK
        string name
        int parent_id FK
    }
```

## CLI Commands

```mermaid
graph TD
    START([User]) --> CMD{Command}

    CMD -->|extract| C1[readings<br/>--notes-dir DIR<br/>--output JSON]
    CMD -->|normalize| C2{Subcommand}
    CMD -->|search| C3{Subcommand}
    CMD -->|load-db| C4[migrate<br/>--input JSON<br/>--output DB]

    C2 -->|validate| C2A[Check markdown files<br/>Output: issues.json]
    C2 -->|learn| C2B[Analyze patterns<br/>Output: patterns.json]
    C2 -->|fix| C2C[Interactive fixes<br/>Updates: markdown files]

    C3 -->|build| C3A[Create FAISS index<br/>Output: vector_store/]
    C3 -->|query| C3B[Search embeddings<br/>--text QUERY<br/>--author/--section filters]
    C3 -->|stats| C3C[Show index stats<br/>Output: CLI]

    C1 --> OUT1[book_index.json]
    C2A --> OUT2[issues.json]
    C2B --> OUT3[patterns.json]
    C3A --> OUT4[.tmp/vector_store/]
    C3B --> OUT5[Search results]
    C4 --> OUT6[readings.db]

    style START fill:#e3f2fd
    style CMD fill:#fff3e0
    style C2 fill:#fff3e0
    style C3 fill:#fff3e0
    style OUT1 fill:#c8e6c9
    style OUT2 fill:#c8e6c9
    style OUT3 fill:#c8e6c9
    style OUT4 fill:#c8e6c9
    style OUT5 fill:#c8e6c9
    style OUT6 fill:#c8e6c9
```

## Key Features

### Validation-First Architecture
- **Blocking validation**: Extraction cannot proceed until all issues are fixed
- **Quality gates**: Ensures data integrity from the start
- **Pattern learning**: Adapts to your corpus's conventions

### Multi-Stage Pipeline
1. **Normalize** (REQUIRED): Validate → Learn patterns → Fix issues
2. **Extract** (BLOCKED): Parse markdown → JSON index
3. **Search**: Build embeddings → Semantic query with pre-filtering
4. **Load**: Migrate to relational database

### Dual Storage Strategy
- **JSON**: Human-readable, version-controllable
- **SQLite**: Relational queries, complex joins
- **FAISS**: High-performance semantic search

### Intelligent Validation
- **Rule-based**: 5 specialized validators
- **Pattern-based**: Learn from corpus statistics
- **Interactive fixing**: User-guided corrections

### Optimized Search
- **Pre-filtering**: Metadata lookups before vector search
- **Multi-field filtering**: Author, section, book
- **Rich metadata**: Date read, source file, chunk context
