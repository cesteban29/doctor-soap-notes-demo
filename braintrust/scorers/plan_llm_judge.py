import braintrust
 
project = braintrust.projects.create(name="SOAP-gen-demo")
 
project.scorers.create(
    name="Plan LLM Judge",
    slug="plan-llm-judge",
    description="A LLM scorer for the Plan section of a SOAP note",
    messages=[
        {
        "role": "system",
        "content": """
        
        You are a medical documentation expert evaluating SOAP notes. 
        You are focusing on the Plan section of a SOAP note.

        Your criteria are as follows:
        1. The plan is clear and concise.
        2. The plan is clinically appropriate.
        3. The plan is complete.
        4. The plan is consistent with the patient's history and physical examination.
        5. The plan is written in a professional and appropriate tone.
        
        Please evaluate the plan and return a score that matches the criteria.
        
        """
        },
        {
            "role": "user",
            "content":
            """
            Transcript:
            {{input}}

            Plan:
            {{output}}
            """
            ,
        },
    ],
    model="gpt-4o",
    use_cot=True,
    choice_scores=
    {
        "perfect": 1, 
        "good": 0.75,
        "fair": 0.5,
        "poor": 0.25,
        "bad": 0
    },
)