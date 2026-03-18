from dataclasses import dataclass, field
from typing import List


@dataclass
class Hypothesis:
    id: str
    description: str
    factors: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    status: str = "active"


@dataclass
class RCAReasoningScaffold:
    issue: str
    hypotheses: List[Hypothesis]

    def active_hypotheses(self) -> List[Hypothesis]:
        return [h for h in self.hypotheses if h.status == "active"]

    def reasoning_health_message(self) -> str:
        active_count = len(self.active_hypotheses())
        if active_count <= 1:
            return "Risk of premature closure: only one active explanation remains."
        return "Multiple hypotheses remain active."

    def to_summary_rows(self):
        rows = []
        for h in self.hypotheses:
            rows.append(
                {
                    "Hypothesis": h.id,
                    "Description": h.description,
                    "Status": h.status,
                    "Factors": " | ".join(h.factors),
                    "Evidence": " | ".join(h.evidence),
                }
            )
        return rows


def build_example_case() -> RCAReasoningScaffold:
    hypotheses = [
        Hypothesis(
            id="H1",
            description="Sampling procedure was not followed correctly",
            factors=[
                "Analyst may have misunderstood the sequence of sampling steps",
                "Procedure required repeated cross-checking across sections",
            ],
            evidence=[
                "Step order confusion was mentioned during retrospective questioning",
            ],
            status="active",
        ),
        Hypothesis(
            id="H2",
            description="Environmental fluctuation affected the result",
            factors=[
                "Temporary room condition shift may have influenced results",
                "Monitoring context was not stable across the whole observation period",
            ],
            evidence=[
                "Environmental log showed minor fluctuation near deviation time",
            ],
            status="narrowed",
        ),
        Hypothesis(
            id="H3",
            description="Documentation entry compressed multiple contributing factors",
            factors=[
                "Final RCA format pushed reasoning toward a single neat explanation",
                "Alternative causal paths became less visible during write-up",
            ],
            evidence=[
                "Draft notes contained broader possibilities than final narrative",
            ],
            status="active",
        ),
    ]

    return RCAReasoningScaffold(
        issue="Deviation in GMP environmental monitoring record review",
        hypotheses=hypotheses,
    )


if __name__ == "__main__":
    rca = build_example_case()
    print("RCA Reasoning Scaffold")
    print("=" * 60)
    print(f"Issue: {rca.issue}")
    print(rca.reasoning_health_message())
    for row in rca.to_summary_rows():
        print(row)