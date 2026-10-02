from typing import Dict
from backend.app.schemas.decision import RiskLevel

# ---------------------------------------------------------------------------
# Centralized Action Risk Classification Model
# ---------------------------------------------------------------------------

TOOL_RISK_MAP: Dict[str, RiskLevel] = {
    # LOW risk actions
    "web.search": RiskLevel.LOW,
    "web.read": RiskLevel.LOW,
    "plan.create": RiskLevel.LOW,
    "plan.declare": RiskLevel.LOW,
    "objective.decompose": RiskLevel.LOW,
    # MEDIUM risk actions
    "research_db.read": RiskLevel.MEDIUM,
    "database.read": RiskLevel.MEDIUM,
    "report.generate": RiskLevel.MEDIUM,
    "task.delegate": RiskLevel.MEDIUM,
    "fs.read": RiskLevel.MEDIUM,
    # HIGH risk actions
    "database.export": RiskLevel.HIGH,
    "external.post": RiskLevel.HIGH,
    "fs.write": RiskLevel.HIGH,
    "shell.exec": RiskLevel.HIGH,
    "secret.read": RiskLevel.HIGH,
}


def classify_action_risk(action: str) -> RiskLevel:
    """
    Centralized deterministic risk classification for tools and actions.
    Extensible mapping with safe prefix fallbacks.
    """
    if action in TOOL_RISK_MAP:
        return TOOL_RISK_MAP[action]

    if (
        action.startswith("database.export")
        or action.startswith("secret.")
        or action.startswith("shell.")
        or action.startswith("external.")
    ):
        return RiskLevel.HIGH

    if action.startswith("database."):
        return RiskLevel.MEDIUM

    if action.startswith("fs."):
        return RiskLevel.MEDIUM

    # Default to LOW for benign reads/declarations unless classified
    return RiskLevel.LOW
