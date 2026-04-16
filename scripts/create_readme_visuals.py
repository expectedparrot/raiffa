from __future__ import annotations

from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).resolve().parents[1]
VISUALS = ROOT / "docs" / "visuals"


DIAGRAMS = {
    "workflow.mmd": """
        flowchart LR
          init[raiffa init] --> build[Build tree]
          build --> validate[Validate assumptions]
          validate --> solve[Rollback solve]
          solve --> stress[Stress test]
          stress --> report[Snapshots and exports]

          build --> tree[(.raiffa trees and nodes)]
          solve --> analyses[(.raiffa analyses)]
          stress --> analyses
          report --> mermaid[Mermaid diagrams]
          report --> json[JSON output]

          classDef command fill:#e8f1ff,stroke:#2f5f9f,color:#10233f
          classDef store fill:#edf7ed,stroke:#39733b,color:#173817
          classDef output fill:#fff4d6,stroke:#9f7b18,color:#3d3005
          class init,build,validate,solve,stress command
          class tree,analyses store
          class mermaid,json output
    """,
    "node_types.mmd": """
        flowchart TD
          decision{Decision node}
          chance((Chance node))
          terminal[Terminal node]

          decision -->|controlled choice| action_a[Child branch A]
          decision -->|controlled choice| action_b[Child branch B]
          chance -->|p=0.30| state_a[State A]
          chance -->|p=0.70| state_b[State B]
          terminal --> utility[Scalar vNM utility]

          classDef decision fill:#e8f1ff,stroke:#2f5f9f,color:#10233f
          classDef chance fill:#fff4d6,stroke:#9f7b18,color:#3d3005
          classDef terminal fill:#edf7ed,stroke:#39733b,color:#173817
          class decision decision
          class chance chance
          class terminal terminal
    """,
    "lawsuit_tree.mmd": """
        flowchart TD
          root{Choose action}
          root -->|settle| settle_outcome[Accept settlement<br/>U=42]
          root -->|litigate| trial_result((Trial result))
          trial_result -->|p=0.25| win_big[Win big<br/>U=90]
          trial_result -->|p=0.35| partial_win[Partial win<br/>U=45]
          trial_result -->|p=0.40| lose[Lose<br/>U=-40]

          classDef decision fill:#e8f1ff,stroke:#2f5f9f,color:#10233f
          classDef chance fill:#fff4d6,stroke:#9f7b18,color:#3d3005
          classDef terminal fill:#edf7ed,stroke:#39733b,color:#173817
          class root decision
          class trial_result chance
          class settle_outcome,win_big,partial_win,lose terminal
    """,
    "lawsuit_rollback.mmd": """
        flowchart BT
          win_big[Win big<br/>90]
          partial_win[Partial win<br/>45]
          lose[Lose<br/>-40]
          trial_result((Trial result<br/>0.25*90 + 0.35*45 + 0.40*-40 = 22.25))
          settle_outcome[Settle<br/>42]
          root{Choose action<br/>max 42 vs 22.25 = 42}

          win_big --> trial_result
          partial_win --> trial_result
          lose --> trial_result
          trial_result --> root
          settle_outcome --> root

          classDef best fill:#dff5e1,stroke:#257a35,color:#123d1a
          classDef rejected fill:#f8e1df,stroke:#994038,color:#421411
          classDef chance fill:#fff4d6,stroke:#9f7b18,color:#3d3005
          class settle_outcome,root best
          class trial_result chance
          class win_big,partial_win,lose rejected
    """,
    "scenario_flip.mmd": """
        flowchart LR
          base[Base scenario<br/>P major win = 0.25<br/>litigate value = 22.25] --> base_choice[Choose settle<br/>EU=42]
          optimistic[Optimistic scenario<br/>P major win = 0.65<br/>litigate value = 65.75] --> opt_choice[Choose litigate<br/>EU=65.75]

          classDef scenario fill:#e8f1ff,stroke:#2f5f9f,color:#10233f
          classDef settle fill:#edf7ed,stroke:#39733b,color:#173817
          classDef litigate fill:#fff4d6,stroke:#9f7b18,color:#3d3005
          class base,optimistic scenario
          class base_choice settle
          class opt_choice litigate
    """,
    "sensitivity_flip.mmd": """
        flowchart LR
          p10["P(major win)=0.10<br/>settle"] --> p20["0.20<br/>settle"]
          p20 --> p30["0.30<br/>settle"]
          p30 --> p40["0.40<br/>settle"]
          p40 --> threshold{{flip between<br/>0.40 and 0.50}}
          threshold --> p50["0.50<br/>litigate"]
          p50 --> p60["0.60<br/>litigate"]

          classDef settle fill:#edf7ed,stroke:#39733b,color:#173817
          classDef litigate fill:#fff4d6,stroke:#9f7b18,color:#3d3005
          classDef threshold fill:#f8e1df,stroke:#994038,color:#421411
          class p10,p20,p30,p40 settle
          class p50,p60 litigate
          class threshold threshold
    """,
    "voi_states.mmd": """
        flowchart TD
          info[Observe trial result perfectly] --> win[Major win<br/>choose litigate<br/>value 90]
          info --> partial[Partial win<br/>choose litigate<br/>value 45]
          info --> loss[Lose<br/>choose settle<br/>value 42]
          win --> ev[Value with information<br/>55.05]
          partial --> ev
          loss --> ev
          ev --> gain[EVPPI<br/>55.05 - 42 = 13.05]

          classDef info fill:#e8f1ff,stroke:#2f5f9f,color:#10233f
          classDef action fill:#fff4d6,stroke:#9f7b18,color:#3d3005
          classDef result fill:#edf7ed,stroke:#39733b,color:#173817
          class info info
          class win,partial,loss action
          class ev,gain result
    """,
    "product_launch_tree.mmd": """
        flowchart TD
          launch_root{Launch decision}
          launch_root -->|no_launch| no_launch[Do not launch<br/>U=0]
          launch_root -->|launch| demand((Demand))
          demand -->|p=0.30| high_demand[High demand<br/>U=120]
          demand -->|p=0.70| low_demand[Low demand<br/>U=-20]

          classDef decision fill:#e8f1ff,stroke:#2f5f9f,color:#10233f
          classDef chance fill:#fff4d6,stroke:#9f7b18,color:#3d3005
          classDef terminal fill:#edf7ed,stroke:#39733b,color:#173817
          class launch_root decision
          class demand chance
          class no_launch,high_demand,low_demand terminal
    """,
    "validation_flow.mmd": """
        flowchart TD
          validate[raiffa tree validate] --> structure{Structure ok?}
          structure -->|no| structural_error[structured validation_error]
          structure -->|yes| probabilities{Probabilities sum to 1?}
          probabilities -->|no| probability_error[probability_sum error]
          probabilities -->|yes| utilities{Terminal utilities numeric?}
          utilities -->|no| utility_error[missing_utility error]
          utilities -->|yes| valid[tree is valid]

          classDef command fill:#e8f1ff,stroke:#2f5f9f,color:#10233f
          classDef check fill:#fff4d6,stroke:#9f7b18,color:#3d3005
          classDef error fill:#f8e1df,stroke:#994038,color:#421411
          classDef ok fill:#edf7ed,stroke:#39733b,color:#173817
          class validate command
          class structure,probabilities,utilities check
          class structural_error,probability_error,utility_error error
          class valid ok
    """,
}


def main() -> None:
    VISUALS.mkdir(parents=True, exist_ok=True)
    for filename, diagram in DIAGRAMS.items():
        text = dedent(diagram).strip() + "\n"
        (VISUALS / filename).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
