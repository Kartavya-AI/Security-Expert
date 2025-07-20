import os
from dotenv import load_dotenv
load_dotenv()
from src.security_expert.crew import SecurityExpertCrew

def run():
    tech_stack_input = """
    I have a Flutter mobile app for the frontend.
    The backend is a REST API built with Node.js and Express.
    We use MongoDB as our database.
    Everything is deployed on AWS EC2 instances.
    We also use S3 for file uploads from users.
    I'm not sure about our VPC or WAF setup.
    """
    crew = SecurityExpertCrew()
    result = crew.crew().kickoff(inputs={'tech_stack_description': tech_stack_input})
    print("Here is the Security Analysis Report:")
    print(result)

if __name__ == "__main__":
    run()
