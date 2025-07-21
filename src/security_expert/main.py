# main.py

# 1. Import your crew class from the crew.py file
from crew import SecurityExpertCrew

# This block runs when you execute `python main.py`
if __name__ == "__main__":
    print("🚀 Starting the Security Expert Crew...")

    # 2. Create an instance of your crew
    sec_crew = SecurityExpertCrew()

    # 3. Define the inputs your task needs
    #    Make sure the key (e.g., 'technology_stack') matches the variable in your tasks.yaml
    inputs = {
        "technology_stack": "Next.js, Python, and MongoDB"
    }

    # 4. Call .kickoff() with the inputs to run the crew
    result = sec_crew.kickoff(inputs=inputs)

    print("\n\n✅ Crew execution finished!")
    print("📄 Here is the final result:")
    print(result)