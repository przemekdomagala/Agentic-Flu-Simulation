# Proof of Concept (PoC) Documentation: Flu Spreading Simulation

Specification and documentation for the Proof of Concept (PoC) phase of the "Spreading of Flu in a Society" project. Outline of the scope, architectural decisions, and execution flow agreed upon to transition from the conceptual framework to a practical, minimal working scenario.

## 1. Objectives of the PoC
The primary goal of this PoC is to validate the foundational mechanics of the Agent-Based Model (ABM) without the overhead of complex datasets or advanced behaviors. The PoC will prove three core aspects:
1. **Environment & Population Setup:** Ability to programmatically generate a synthetic population within a simplified spatial environment using Python and the Mesa framework.
2. **State Transitions:** Correct mapping and progression of individual agents through an epidemiological SEIR (Susceptible, Exposed, Infectious, Recovered) state model.
3. **Transmission Logic:** Successful implementation of proximity-based, probabilistic virus transmission when a susceptible agent and an infectious agent share the same spatial location.

## 2. Scope & Architectural Decisions

To ensure a tight, achievable prototype, the system scope has been restricted to the following parameter arrangements:

### 2.1 Time Scale
* **Decision:** **1 Tick = 1 Hour**
* **Rationale:** Configuring the baseline simulation step to represent a single hour ensures the time scale is natively compatible with future milestones, where structured daily schedules (e.g., an 8-hour workday followed by time spent at home) will be introduced.

### 2.2 Grid Boundary Rules
* **Decision:** **Toroidal Grid** (`toroidal=True` in Mesa's `MultiGrid`)
* **Rationale:** The simulation space wraps around seamlessly (like a donut world). If an agent exits the right boundary, they reappear on the left. This prevents artificial agent clustering along corners and walls, maintaining an even spatial distribution during random mixing.

### 2.3 Transmission Scope & Proximity
* **Decision:** **Same Cell Only**
* **Rationale:** A Susceptible agent only runs an infection check if they occupy the *exact same cell coordinates* as an Infectious agent during a given tick. This strict constraint mirrors the long-term project goal of treating cells or nodes as discrete "Spatial Agent" structures (such as a specific household or workplace).

### 2.4 Disease Progression & Timers
* **Decision:** **Fixed Constants**
* **Rationale:** Instead of using stochastic distributions for biological variance at this early stage, all transition durations will remain uniform (e.g., exactly 72 hours for the Exposed incubation phase and exactly 168 hours for the Infectious phase). This ensures predictability, making it straightforward to debug the model's numbers and state metrics.

### 2.5 Data & Population Source
* **Decision:** **Procedurally Generated (Synthetic Data)**
* **Rationale:** Complex real-world demographic datasets (such as FRED, SIPHER, or June) are omitted for this phase. The population will be fabricated completely out of thin air at startup with a hardcoded baseline (e.g., 100 total agents: 99 Susceptible, 1 Infectious).

### 2.6 Visualization Strategy
* **Decision:** **Terminal Logs + Post-Run Static Graph**
* **Rationale:** To isolate the simulation engine logic from server-side or frontend interface bugs, the PoC will output status updates directly to the console terminal during execution. Upon completion, a single static line chart will be rendered via `matplotlib` to verify the emergence of the standard epidemiological curve.

## 3. Simulation Execution Blueprint

When implemented, the script will execute sequentially according to the following pipeline:

1. **Initialization Phase:**
   * Instantiate a Mesa `Model` with a specified 2D Toroidal `MultiGrid` (e.g., 20x20).
   * Spawn a predefined number of `IndividualAgent` entities.
   * Uniformly randomize agent placement across the grid coordinates.
   * Set 99% of agents to `Susceptible` and 1% (the index case) to `Infectious`.

2. **The Hourly Simulation Loop (Each Tick):**
   * **Step 1: Random Walk Mobility:** Every individual agent randomly selects an adjacent coordinate (up, down, left, right, or diagonal) and moves there.
   * **Step 2: Proximity Check & Exposure:** If a `Susceptible` agent shares its exact cell coordinates with an `Infectious` agent, a virtual 100-sided die is rolled against a hardcoded baseline transmission probability. If successful, the agent transitions to `Exposed`.
   * **Step 3: Temporal Progression:** Internal countdown timers track how many hours an agent has spent in their current state. Once the fixed threshold is crossed, agents advance to the next clinical phase (`Exposed` $\rightarrow$ `Infectious` $\rightarrow$ `Recovered`).
   * **Step 4: Metrics Harvesting:** A Mesa `DataCollector` aggregates the total count of S, E, I, and R agents at the end of the hour and appends it to a time-series history log.

3. **Termination & Plotting Phase:**
   * The loop completes its designated run time (e.g., 500 hours).
   * The aggregated time-series data is loaded into a Pandas DataFrame.
   * `matplotlib` generates a clear plot displaying the time progression of all four SEIR compartments to visually demonstrate the epidemic outbreak curve.
