import braintrust
import pydantic
 
project = braintrust.projects.create(name="SOAP-gen-demo")
 
 
class Input(pydantic.BaseModel):
    output: str
 
 
def handler(output: str) -> int:
    # Convert output to lowercase for case-insensitive comparison
    output_lower = output.lower()
    
    # Check for required sections in lowercase
    required_sections = ["subjective", "objective", "assessment", "plan"]
    
    # Return 0 if any required section is missing
    if not all(section in output_lower for section in required_sections):
        return 0
    return 1
 
 
project.scorers.create(
    name="Not Missing Sections",
    slug="not-missing-sections",
    description="A scorer that checks if all required sections are present in the output",
    parameters=Input,
    handler=handler,
)