from typing import Dict, Any 
from langgraph.graph import StateGraph, END 
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from .models import ResearchState, CompanyAnalysis, CompanyInfo
from .firecrawl import FirecrawlService
from .prompts import DeveloperToolsPrompts


class Workflow:
    def __init__(self, status_callback=None):
        self.firecrawl = FirecrawlService()
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        self.prompts = DeveloperToolsPrompts()
        self.workflow = self._build_workflow()
        self.status_callback = status_callback

    def _update_status(self, message):
        if self.status_callback:
            self.status_callback(message)

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
        self._update_status(f"🔎 Finding Articles about {state.query}...")
        article_query = f"{state.query} tools comparison best alternatives"
        search_results = self.firecrawl.search_companies(article_query, num_results=3)

        # Handle empty search results
        if not search_results.data:
            self._update_status("❌ No search results found. Please try a different query.")
            return {"extracted_tools": []}

        all_content = ""
        for i, result in enumerate(search_results.data):
            url = result.get("url", "")
            if not url:
                continue
                
            self._update_status(f"Scraping {url}... ({i+1}/{len(search_results.data)})")
            scraped = self.firecrawl.scrape_company_page(url)
            if scraped:
                all_content += scraped.markdown[:2000] + "\n\n"
            
            # Add delay to avoid rate limiting
            import time
            time.sleep(1)  # 1 second delay between requests

        if not all_content.strip():
            self._update_status("❌ No content could be scraped. Please try again later.")
            return {"extracted_tools": []}

        messages = [
            SystemMessage(content=self.prompts.TOOL_EXTRACTION_SYSTEM),
            HumanMessage(content=self.prompts.tool_extraction_user(state.query, all_content))
        ]

        try:
            response = self.llm.invoke(messages)
            tool_names = [name.strip() for name in response.content.split("\n") if name.strip()]
            self._update_status(f"🛠️ Extracted Tools: {', '.join(tool_names[:7])}")
            return {
                "extracted_tools": tool_names
            }
        except Exception as e:
            self._update_status(f"❌ Exception occurred: {e}")
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
            self._update_status(f"❌ Exception occured: {e}")
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
            self._update_status("❗️ No extracted tools found, falling back to direct search")
            search_results = self.firecrawl.search_companies(state.query, num_results=3)
            # Handle empty search results
            if not search_results.data:
                self._update_status("❌ No search results found. Please try a different query.")
                return {"companies": []}
            
            tool_names = [
                result.get("metadata", {}).get("title", "Unknown")
                for result in search_results.data
            ]
        else:
            tool_names = extracted_tools[:5]

        self._update_status(f"🧪 Researching specific tools: {', '.join(tool_names)}")

        companies = []
        for i, tool_name in enumerate(tool_names):
            self._update_status(f"🔍 Researching {tool_name} ({i+1}/{len(tool_names)})...")
            
            try:
                tool_search_results = self.firecrawl.search_companies(tool_name + " official site", num_results=1)
                
                # Handle empty search results or rate limiting
                if not tool_search_results or not tool_search_results.data:
                    self._update_status(f"⚠️ No search results found for {tool_name}, skipping...")
                    continue
                
                result = tool_search_results.data[0]
                url = result.get("url", "")
                
                if not url:
                    self._update_status(f"⚠️ No URL found for {tool_name}, skipping...")
                    continue
                
                company = CompanyInfo(
                    name=tool_name,
                    description=result.get("markdown", ""),
                    website=url,
                    tech_stack=[],
                    competitors=[]
                )

                # Add delay to avoid rate limiting
                import time
                time.sleep(1)  # 1 second delay between requests
                
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
                self._update_status(f"✅ Completed research for {tool_name}")
                
            except Exception as e:
                self._update_status(f"❌ Error researching {tool_name}: {str(e)}")
                continue
        
        if not companies:
            self._update_status("❌ No companies could be researched. Please try again later or with a different query.")
        
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
 