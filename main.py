import mesa
import enum
import matplotlib.pyplot as plt
import pandas as pd

# ---------------------------------------------------------
# 1. State Definition
# ---------------------------------------------------------
class State(enum.IntEnum):
    """Epidemiological SEIR states for the agents."""
    SUSCEPTIBLE = 0
    EXPOSED = 1
    INFECTIOUS = 2
    RECOVERED = 3

# ---------------------------------------------------------
# 2. Agent Architecture
# ---------------------------------------------------------
class IndividualAgent(mesa.Agent):
    """An agent representing a single human in the simulation."""
    def __init__(self, model):
        super().__init__(model) 
        self.state = State.SUSCEPTIBLE
        self.timer = 0  # Tracks hours spent in current state

    def step(self):
        """The hourly execution loop for the agent."""
        self.move()
        self.interact()
        self.progress_disease()

    def move(self):
        """Step 1: Random Walk Mobility to an adjacent cell (Moore neighborhood)."""
        possible_steps = self.model.grid.get_neighborhood(
            self.pos,
            moore=True, # Includes diagonals
            include_center=False
        )
        new_position = self.random.choice(possible_steps)
        self.model.grid.move_agent(self, new_position)

    def interact(self):
        """Step 2: Proximity Check & Exposure (Same Cell Only)."""
        if self.state == State.SUSCEPTIBLE:
            # Get all agents sharing the exact same coordinate
            cellmates = self.model.grid.get_cell_list_contents([self.pos])
            for neighbor in cellmates:
                if neighbor.state == State.INFECTIOUS:
                    # Roll a virtual 100-sided die against the transmission probability
                    if self.random.random() < self.model.transmission_prob:
                        self.state = State.EXPOSED
                        self.timer = 0  # Reset timer for the new state
                        break  # Only one exposure event can happen per tick

    def progress_disease(self):
        """Step 3: Temporal Progression using Fixed Constants."""
        if self.state == State.EXPOSED:
            self.timer += 1
            if self.timer >= self.model.exposed_duration:
                self.state = State.INFECTIOUS
                self.timer = 0
        elif self.state == State.INFECTIOUS:
            self.timer += 1
            if self.timer >= self.model.infectious_duration:
                self.state = State.RECOVERED
                self.timer = 0

# ---------------------------------------------------------
# 3. Model Architecture
# ---------------------------------------------------------
# Helper functions for the DataCollector to count states
def get_susceptible(model):
    return sum(1 for a in model.agents if a.state == State.SUSCEPTIBLE)

def get_exposed(model):
    return sum(1 for a in model.agents if a.state == State.EXPOSED)

def get_infectious(model):
    return sum(1 for a in model.agents if a.state == State.INFECTIOUS)

def get_recovered(model):
    return sum(1 for a in model.agents if a.state == State.RECOVERED)

class FluModel(mesa.Model):
    """The central simulation model managing the grid, schedule, and data."""
    def __init__(self, num_agents=100, width=20, height=20, 
                 transmission_prob=0.15, exposed_duration=72, infectious_duration=168):
        super().__init__() 
        self.num_agents = num_agents
        
        # Grid Boundary Rules: Toroidal = True (using 'torus')
        self.grid = mesa.space.MultiGrid(width, height, torus=True)
        
        # Epidemic parameters
        self.transmission_prob = transmission_prob
        self.exposed_duration = exposed_duration       # Fixed Constant: 72 hours (3 days)
        self.infectious_duration = infectious_duration # Fixed Constant: 168 hours (7 days)

        # Initialization Phase: Spawn agents
        for i in range(self.num_agents):
            a = IndividualAgent(self) # Agent automatically registers itself to model.agents
            
            # Uniformly randomize agent placement
            x = self.random.randrange(self.grid.width)
            y = self.random.randrange(self.grid.height)
            self.grid.place_agent(a, (x, y))

            # Set the index case (The very first agent starts as Infectious)
            if i == 0:
                a.state = State.INFECTIOUS

        # Step 4: Metrics Harvesting setup
        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Susceptible": get_susceptible,
                "Exposed": get_exposed,
                "Infectious": get_infectious,
                "Recovered": get_recovered
            }
        )

    def step(self):
        """Advances the simulation by one hour (tick)."""
        # Collect data at the start of the tick
        self.datacollector.collect(self)
        
        self.agents.shuffle_do("step")
        
        s = get_susceptible(self)
        e = get_exposed(self)
        i = get_infectious(self)
        r = get_recovered(self)
        print(f"Tick {self.steps:03d} (Hour): S={s:03d}, E={e:03d}, I={i:03d}, R={r:03d}")

# ---------------------------------------------------------
# 4. Execution & Visualization
# ---------------------------------------------------------
if __name__ == "__main__":
    # Define runtime variables
    SIMULATION_HOURS = 500  # Total duration of the simulation loop
    
    print("Initializing PoC Simulation...")
    model = FluModel(
        num_agents=100, 
        width=20, 
        height=20, 
        transmission_prob=0.10 # 10% chance of infection when sharing a cell
    )
    
    print("Starting execution loop...")
    for _ in range(SIMULATION_HOURS):
        model.step()
        
    print("Simulation complete. Generating plot...")

    # Termination & Plotting Phase
    df = model.datacollector.get_model_vars_dataframe()
    
    # Plotting standard epidemiological curve
    fig, ax = plt.subplots(figsize=(10, 6))
    df.plot(ax=ax, color=['blue', 'orange', 'red', 'green'])
    
    ax.set_title("SEIR Epidemic Curve (PoC) - Flu Spreading Simulation")
    ax.set_xlabel("Time (Hours)")
    ax.set_ylabel("Number of Agents")
    ax.grid(True, linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    plt.show()