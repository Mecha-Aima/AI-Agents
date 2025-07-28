from typing import Dict, Any 
from langgraph.graph import StateGraph, END 
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from .models import ResearchState, CompanyAnalysis, CompanyInfo
from .firecrawl import FirecrawlService
from .prompts import DeveloperToolsPrompts


class Workflow:
    def __init__(self):
        self.firecrawl = FirecrawlService()
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        self.prompts = DeveloperToolsPrompts()
        self.workflow = self._build_workflow()

    def _build_workflow(self):
        graph = StateGraph(ResearchState)
        graph.add_node("extract_tools", self._extract_tools)
        graph.add_node("research", self._research)
        graph.add_node("analyze", self._analyze)

        graph.set_entry_point("extract_tools")
        graph.add_edge("extract_tools", "research")
        graph.add_edge("research", "analyze")
        graph.add_edge("analyze", END)

        return graph.compile()


    def _extract_tools(self, state: ResearchState) -> Dict[str, Any]:
        print(f"🔎 Finding Articles about {state.query}")
        article_query = f"{state.query} tools comparison best alternatives"
        search_results = self.firecrawl.search_companies(article_query, num_results=3)

        all_content = ""
        for result in search_results.data:
            url = result.get("url", "")
            scraped = self.firecrawl.scrape_company_page(url)
            if scraped:
                all_content += scraped.markdown[:2000] + "\n\n"

            messages = [
                SystemMessage(content=self.prompts.TOOL_EXTRACTION_SYSTEM),
                HumanMessage(content=self.prompts.tool_extraction_user(state.query, all_content))
            ]

            try:
                response = self.llm.invoke(messages)
                tool_names = [name.strip() for name in response.content.split("\n") if name.strip()]
                print(f"🛠️ Extracted Tools: {', '.join(tool_names[:7])}")
                return {
                    "extracted_tools": tool_names
                }
            except Exception as e:
                print(f"❌ Exception occured: {e}")
                return {"extracted_tools": []}
            

    # HELPER FUNCTION
    def _analyze_company_content(self, company_name: str, content: str) -> CompanyAnalysis:
        structured_llm = self.llm.with_structured_output(CompanyAnalysis)
        messages = [
            SystemMessage(content=self.prompts.TOOL_ANALYSIS_SYSTEM),
            HumanMessage(content=self.prompts.tool_analysis_user(company_name, content))
        ]

        try:
            analysis = structured_llm.invoke(messages)
            return analysis
        except Exception as e:
            # Prevent graph crash
            print(f"❌ Exception occured: {e}")
            return CompanyAnalysis(
                pricing_model="Unknown",
                is_open_source=None,
                tech_stack=[],
                description="Failed",
                api_available=None,
                language_support=[],
                integration_capabilities=[]
            )
        

    def _research(self, state: ResearchState) -> Dict[str, Any]:
        extracted_tools = getattr(state, "extracted_tools", [])
        if not extracted_tools:
            print(f"❗️ No extracted tools found, falling back to direct search")  
            search_results = self.firecrawl.search_companies(state.query, num_results=3)
            tool_names = [
                result.get("metadata", {}).get("title", "Unknown")
                for result in search_results.data
            ]
        else:
            tool_names = extracted_tools[:5]

        print(f"🧪 Researching specific tools: {', '.join(tool_names)}")

        companies = []
        for tool_name in tool_names:
            tool_search_results = self.firecrawl.search_companies(tool_name + " official site", num_results=1)
            if tool_search_results:
                result = tool_search_results.data[0]
                url = result.get("url", "")
                company = CompanyInfo(
                    name=tool_name,
                    description=result.get("markdown", ""),
                    website=url,
                    tech_stack=[],
                    competitors=[]
                )

                scraped = self.firecrawl.scrape_company_page(url)
                if scraped:
                    content = scraped.markdown
                    analysis = self._analyze_company_content(tool_name, content)
                    company.pricing_model = analysis.pricing_model
                    company.is_open_source = analysis.is_open_source
                    company.tech_stack = analysis.tech_stack
                    company.description = analysis.description
                    company.api_available = analysis.api_available
                    company.language_support = analysis.language_support
                    company.integration_capabilities = analysis.integration_capabilities

                companies.append(company)
            return {"companies": companies}

    
    def _analyze(self, state: ResearchState) -> Dict[str, Any]:
        print("🧩 Generating recommendations...")
        company_data = "\n".join([
            company.model_dump_json() for company in state.companies
        ])
        
        messages = [
            SystemMessage(content=self.prompts.RECOMMENDATIONS_SYSTEM),
            HumanMessage(content=self.prompts.recommendations_user(state.query, company_data))
        ]

        response = self.llm.invoke(messages)
        return {
            "analysis": response.content
        }

        

    def run(self, query: str) -> ResearchState:
        initial_state = ResearchState(query=query)
        final_state = self.workflow.invoke(initial_state)

        return ResearchState(**final_state)
 