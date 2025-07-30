"""Central configuration for agent-specific model assignments."""

# Model assignments for each agent type
AGENT_MODELS = {
    # Evidence extraction - uses general purpose model
    "evidence_extractor": "gpt-4.1",
    
    # Evidence verification - uses general purpose model
    "evidence_verifier_v2": "gpt-4.1",
    
    # Completeness checking - uses general purpose model
    "completeness_checker": "gpt-4.1",
    
    # Image analysis - uses vision-capable model
    "image_evidence_analyzer": "o4-mini",  # o4-mini with modular capabilities support
    
    # Default fallback for any agent not explicitly configured
    "default": "gpt-4.1"
}

def get_model_for_agent(agent_name: str) -> str:
    """Get the configured model for a specific agent.
    
    Args:
        agent_name: Name of the agent (e.g., "evidence_verifier_v2")
        
    Returns:
        Model name to use for this agent
    """
    return AGENT_MODELS.get(agent_name, AGENT_MODELS["default"])