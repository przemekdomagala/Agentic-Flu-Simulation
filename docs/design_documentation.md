# System Architecture & Technical Specification 

---

## 1. Summary & Objective  

This document details the technical specifications for the "Spreading of Flu in a Society" project. The simulation is an Agent-Based Model (ABM) created in Python using the **Mesa** framework and **NetworkX**.  

This simulation uses a **Synthetic Population Dataset** that represents Philadelphia, Pennsylvania (FIPS 42101). The environment employs a filtered, multi-layer network topology to separate transmission vectors into distinct social layers: Household, Group Quarters, Professional, Educational, and Community. It operates on a discrete hourly clock to produce realistic epidemic curves.  

---

## 2. Core Data Sources (The Population)  

The demographic and spatial foundation of the simulation comes from the **2010 U.S. Synthesized Population Dataset** developed by the Research Triangle Institute (RTI) under the MIDAS grant.  

* **Geography Set:** 42101 (Philadelphia, Pennsylvania)  
* **Used Files:**  
  * `people.txt` (Demographics and Network IDs)  
  * `households.txt` (Household nodes)  
  * `gq.txt` & `gq_people.txt` (High-density group quarters like dorms and nursing homes)  
* **Preprocessing:** To avoid memory overload, the dataset is processed with a **Cluster Sampling Algorithm** before the simulation. This ensures that the structures of households and group quarters are intact.  

---

## 3. Epidemiological SEIR Engine (The Virus)  

Agents move through a Susceptible → Exposed → Infectious → Recovered (SEIR) state machine. The duration of clinical phases follows stochastic normal (Gaussian) distributions to ensure smooth, realistic epidemic progression curves based on official virology data.  

| Parameter | Value / Distribution | Scientific Source & Justification |  
| :--- | :--- | :--- |  
| **Incubation Phase ($D_E$)** | $\mathcal{N}(\mu=48, \sigma=12)$ hours | **[CDC: Influenza Surveillance]**. Clinical incubation ranges from 1 to 4 days, with an average of 2 days (48 hours). |  
| **Infectious Phase ($D_I$)** | $\mathcal{N}(\mu=168, \sigma=24)$ hours | **[CDC: Viral Shedding Guidelines]**. Viral shedding occurs for 5 to 7 days after symptom onset. |  
| **Elderly Vulnerability ($V_{age}$)** | $+20\%$ duration penalty if `age > 65` | **[CDC: Viral Shedding Guidelines]**. Older adults and immunocompromised individuals shed the virus for longer periods. |  
| **Asymptomatic Rate** | $35\%$ of infections | **[NIH/PMC: Asymptomatic Influenza Infections]**. Large-scale meta-analyses indicate a subclinical prevalence between 30% and 50%. |  

---

## 4. Transmission Mechanics (The Environment)  

Transmission happens randomly when a `Susceptible` agent and an `Infectious` agent share an active network edge during the same hourly tick. The probability of exposure $P(\text{inf})$ is defined as:  

$P(\text{inf}) = β * M_{\text{location}}$  

Here, β is the baseline transmissibility constant (calibrated through simulation testing to achieve an $R_0$ between 1.3 and 1.8). $M_{\text{location}}$ adjusts the risk based on the environment:  

| Network Layer | Multiplier ($M$) | Source / Structural Rationale |  
| :--- | :--- | :--- |  
| **Group Quarters** | $3.5$ | **Assumed maximum.** Nursing homes and dorms represent the highest density transmission environments. |  
| **Household** | $2.5$ | **[NIH/PMC: Transmissibility & Control]**. Secondary Attack Rate (SAR) is around 27.3%, which is the main driver of transmission. |  
| **School** | $1.8$ | **[NIH/PMC: Transmissibility & Control]**. High contact density; infected children spread to an average of 2.4 peers. |  
| **Workplace** | $1.0$ | **Baseline.** Represents standard adult-to-adult contact indoors. |  
| **Community** | $0.4$ | **Assumed abstract layer.** Low risk, brief contact for evening errands or transit. |  

---

## 5. Behavioral Routing & The Simulation Clock  

The temporal resolution is **1 Tick = 1 Hour**. To improve performance, the global NetworkX graph is divided into time-filtered sub-graphs.  

### Hourly Matrix Distribution  
* **00:00 - 08:00 (Night):** Only `G_home` and `G_gq` sub-graphs are active.  
* **08:00 - 16:00 (Day):** `G_work` and `G_school` sub-graphs activate. `G_home` deactivates for employed or student agents but stays active for retirees and homebound individuals.  
* **16:00 - 24:00 (Evening):** `G_home` reactivates. A randomized 10% of agents activate `G_community` edges to simulate public errands.  

### Symptom-Driven Absenteeism  
At 07:00 daily, all `Infectious` agents undergo a behavioral compliance check:  
* **Compliance Rate:** $70\%$ of symptomatic agents will successfully quarantine. This means they will suspend their `G_work` and `G_school` routing and stay locked to `G_home` for the day.  
* **Presenteeism:** The remaining $30\%$ of symptomatic agents (along with $100\%$ of asymptomatic agents) will stick to their normal routing, acting as vectors in the wider community.  

---

## 6. Telemetry, Analytics, and UI Dashboard  

User interface focuses strictly on telemetry.  

### 6.1 Real-Time Macro Dashboard  
The simulation uses Mesa's visualization modules to show live telemetry:  
1. **The SEIR Epidemic Curve:** A live line chart tracking the total counts of `Count_S`, `Count_E`, `Count_I`, and `Count_R` over time.  
2. **Transmission Vector Hotspots:** A live bar chart showing where infections occur (Home vs. School vs. Work vs. Group Quarters) to validate the impacts of network multipliers.  