from app.ai.agents.base import BaseAgent
from app.ai.agents.claims_agent import ClaimsAgent
from app.ai.agents.health_agents import MedicalInsuranceAgent, ProviderNetworkAgent
from app.ai.agents.policy_agents import (
    BillingAgent,
    CoverageAgent,
    DocumentIntelligenceAgent,
    PolicyIntelligenceAgent,
    RenewalAgent,
    RiskAgent,
    ShoppingAgent,
)
from app.ai.agents.support_agents import CommunicationAgent, FraudSignalAgent, HumanEscalationAgent

AGENT_CLASSES: list[type[BaseAgent]] = [
    PolicyIntelligenceAgent, ClaimsAgent, CoverageAgent, BillingAgent, RenewalAgent, ShoppingAgent, RiskAgent,
    DocumentIntelligenceAgent, MedicalInsuranceAgent, ProviderNetworkAgent, CommunicationAgent, FraudSignalAgent,
    HumanEscalationAgent,
]


def get_agent(name: str) -> BaseAgent:
    for cls in AGENT_CLASSES:
        if cls.name == name:
            return cls()
    return PolicyIntelligenceAgent()


def describe_agents() -> list[dict]:
    return [{"name": c.name, "description": c.description, "tools": list(c.tools), "permissions": list(c.permissions),
             "escalation_rules": list(c.escalation_rules)} for c in AGENT_CLASSES]
