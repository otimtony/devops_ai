from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
from devops_ai.schemas import IncidentReport

@CrewBase
class DevopsAi():
    """DevopsAi crew"""

    agents: List[BaseAgent]
    tasks: List[Task]

    #***************** open ai model used by devopsai agents ***************
    def openai_llm(self) -> LLM:
        return LLM(
            model="openai/gpt-4o-mini",
            temperature=0.1,
            timeout=120,
            max_retries=2,
        )

    #****************************** Agents *****************************XWW
    @agent
    def incident_triage_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["incident_triage_agent"],
            llm=self.openai_llm(),
            verbose=True,
        )

    @agent
    def log_analysis_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["log_analysis_agent"],
            llm=self.openai_llm(),
            verbose=True,
        )

    @agent
    def technical_research_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["technical_research_agent"],
            llm=self.openai_llm(),
            verbose=True,
        )

    @agent
    def root_cause_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["root_cause_agent"],
            llm=self.openai_llm(),
            verbose=True,
        )

    @agent
    def remediation_risk_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["remediation_risk_agent"],
            llm=self.openai_llm(),
            verbose=True,
        )

    #********************************* Tasks **********************************

    @task
    def incident_triage_task(self) -> Task:
        return Task(
            config=self.tasks_config["incident_triage_task"],
        )

    @task
    def log_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config["log_analysis_task"],
        )

    @task
    def technical_research_task(self) -> Task:
        return Task(
            config=self.tasks_config["technical_research_task"],
        )

    @task
    def root_cause_task(self) -> Task:
        return Task(
            config=self.tasks_config["root_cause_task"],
        )

    @task
    def remediation_risk_task(self) -> Task:
        return Task(
            config=self.tasks_config["remediation_risk_task"],
            context=[
                self.incident_triage_task(),
                self.log_analysis_task(),
                self.technical_research_task(),
                self.root_cause_task(),
            ],
            # validate the final result against your existing Pydantic model.
            output_pydantic=IncidentReport,
            output_file="incident_report.md",
        )

    #****************************** Crew **************************
    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )