from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class CompanyAnalysis(BaseModel):
    """
    Represents a detailed analysis of a single company.

    Attributes:
        pricing_model: The pricing model of the company (e.g., 'Subscription', 'Freemium').
        is_open_source: Whether the company's primary product is open source.
        tech_stack: A list of technologies used by the company.
        description: A brief description of the company.
        api_available: Whether the company offers a public API.
        language_support: A list of programming languages supported by their tools/API.
        integration_capabilities: A list of services or platforms it can integrate with.
    """
    pricing_model: str
    is_open_source: Optional[bool] = None 
    tech_stack: List[str] = []
    description: str = ""
    api_available: Optional[bool] = None
    language_support: List[str] = []
    integration_capabilities: List[str] = []


class CompanyInfo(BaseModel):
    """
    Represents comprehensive information about a company.

    Attributes:
        name: The name of the company.
        description: A brief description of the company.
        website: The official website of the company.
        pricing_model: The pricing model of the company (e.g., 'Subscription', 'Freemium').
        is_open_source: Whether the company's primary product is open source.
        tech_stack: A list of technologies used by the company.
        competitors: A list of known competitors.
        api_available: Whether the company offers a public API.
        language_support: A list of programming languages supported by their tools/API.
        integration_capabilities: A list of services or platforms it can integrate with.
        developer_experience_rating: A rating or description of the developer experience.
    """
    name: str
    description: str 
    website: str 
    pricing_model: Optional[str] = None 
    is_open_source: Optional[bool] = None 
    tech_stack: List[str] = []
    competitors: List[str] = []
    api_available: Optional[bool] = None 
    language_support: List[str] = []
    integration_capabilities: List[str] = []
    developer_experience_rating: Optional[str] = None


class ResearchState(BaseModel):
    """
    Represents the state of the research process in an agent or graph.

    This class holds all the information gathered and generated during a research task,
    allowing the agent to track its progress and make decisions.

    Attributes:
        query: The initial user query that started the research.
        extracted_tools: A list of tools or technologies identified from the query.
        companies: A list of `CompanyInfo` objects for companies being researched.
        search_results: A list of raw search results from search tools.
        analysis: A final analysis or summary of the research findings.
    """
    query: str 
    extracted_tools: List[str] = []
    companies: List[CompanyInfo] = []
    search_results: List[Dict[str, Any]] = []
    analysis: Optional[str] = None