from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
# If you want to run a snippet of code before or after the crew starts,
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators

@CrewBase
class DevopsAi():
    """DevopsAi crew"""

    agents: List[BaseAgent]
    tasks: List[Task]

    #****************************** Agents *****************************

    @agent
    def incident_triage_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["incident_triage_agent"],
            verbose=True,
        )

    @agent
    def log_analysis_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["log_analysis_agent"],
            verbose=True,
        )

    @agent
    def technical_research_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["technical_research_agent"],
            verbose=True,
        )

    @agent
    def root_cause_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["root_cause_agent"],
            verbose=True,
        )

    @agent
    def remediation_risk_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["remediation_risk_agent"],
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