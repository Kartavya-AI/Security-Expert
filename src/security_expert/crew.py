import os
from crewai import Agent, Task, Crew, Process
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool
from dotenv import load_dotenv
from crewai.memory import LongTermMemory
from langchain_google_genai import ChatGoogleGenerativeAI

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

        self.llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", verbose=True, temperature=0.5)
        self.search_tool = None
        if serper_api_key:
            try:
                self.search_tool = SerperDevTool()
            except Exception:
                self.search_tool = None
        self.memory = LongTermMemory()

    @agent
    def security_interviewer(self) -> Agent:
        return Agent(
            config=self.agents_config['security_interviewer'],
            llm=self.llm,
            verbose=True
        )

    @agent
    def security_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['security_analyst'],
            llm=self.llm,
            verbose=True,
            memory=self.memory
        )
    
    @task
    def interview_task(self) -> Task:
        return Task(
            config=self.tasks_config['interview_task'],
            agent=self.security_interviewer()
        )

    @task
    def analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config['analysis_task'],
            agent=self.security_analyst()
        )

    @crew
    def crew(self) -> Crew:
        action = getattr(self, '_current_action', 'start_interview')

        if action == 'perform_analysis':
            return Crew(
                agents=[self.security_analyst()],
                tasks=[self.analysis_task()],
                process=Process.sequential,
                verbose=True
            )
        else:
            return Crew(
                agents=[self.security_interviewer()],
                tasks=[self.interview_task()],
                process=Process.sequential,
                verbose=True
            )

    def kickoff(self, inputs):
        self._current_action = inputs.get('action', 'start_interview')
        crew_run = self.crew()
        return crew_run.kickoff(inputs=inputs)