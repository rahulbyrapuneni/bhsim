
from bhsim import BHSimulator

# ---CREATE SIMULATOR---
sim = BHSimulator(
    clients=1000,
    employees=100,
    history_months=12,
    seed=42
)

# ---GENERATE DATA---
sim.generate("behavioral_health.db")

# ---VALIDATE DATA---
print(sim.validate())

# ---EXPORT CSV---
sim.to_csv("output")
