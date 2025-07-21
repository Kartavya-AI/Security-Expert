import os
from crewai import Agent, Task, Crew, Process, LLM
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool
from dotenv import load_dotenv
from crewai.memory import LongTermMemory

load_dotenv()

@CrewBase
class SecurityExpertCrew:
    """
    The SecurityExpertCrew class orchestrates AI agents loaded from YAML files
    to perform security analysis on a given technology stack.
    """
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    def __init__(self, api_key: str = None, serper_key: str = None):
        gemini_key = api_key or os.getenv("GEMINI_API_KEY")
        serper_api_key = serper_key or os.getenv("SERPER_API_KEY")
        if not gemini_key:
            raise ValueError("No Gemini API Key found")

        self.llm = LLM(model="gemini/gemini-2.0-flash-exp", api_key = api_key)
        self.search_tool = None
        if serper_api_key:
            try:
                self.search_tool = SerperDevTool()
            except Exception:
                self.search_tool = None

        # Initialize LocalAgentMemory for the agent
        # This will store memories in a local file (`agent_memory.json` by default)
        self.memory = LongTermMemory()

    @agent
    def security_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['security_analyst'],
            llm=self.llm,
            verbose=True,
            # Assign memory to the agent
            memory=self.memory
        )

    @task
    def analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config['analysis_task'],
            agent=self.security_analyst()
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=[self.security_analyst()],
            tasks=[self.analysis_task()],
            process=Process.sequential,
            verbose=True
        )