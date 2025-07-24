from crew import SecurityExpertCrew

if __name__ == "__main__":
    print("🚀 Starting the Security Expert Crew...")
    sec_crew = SecurityExpertCrew()
    inputs = {
        "technology_stack": "Next.js, Python, and MongoDB"
    }
    result = sec_crew.kickoff(inputs=inputs)
    print("\n\n✅ Crew execution finished!")
    print("📄 Here is the final result:")
    print(result)