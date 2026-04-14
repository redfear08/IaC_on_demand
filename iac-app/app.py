import os
import subprocess
from openai import OpenAI

# 🔥 FastAPI imports
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 🔥 FastAPI app
app = FastAPI()

# Enable CORS (for GitHub frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# 🔹 Request model
class RequestModel(BaseModel):
    input: str


def generate_iac(user_input: str):
    system_prompt = """
You are a Principal Cloud Architect and DevOps expert.

Your task is to convert user requirements into:
1. AWS CloudFormation YAML
2. Terraform HCL
3. Architecture Diagram (Mermaid format)

========================
ARCHITECTURE GUIDELINES
========================
- Design a minimal but complete infrastructure
- Use AWS best practices
- Prefer managed services
- Ensure scalability, security, and cost efficiency

========================
SECURITY BEST PRACTICES
========================
- Least privilege IAM
- Avoid public exposure unless required
- Add warnings in comments for insecure configs

========================
COST OPTIMIZATION
========================
- Use cost-effective defaults
- Avoid over-provisioning

========================
COMMENTING RULES
========================
- Add inline comments explaining:
  - Purpose
  - Security implications
  - Cost considerations

========================
DIAGRAM RULES
========================
- Generate a Mermaid diagram using "graph TD"
- Show main AWS components and relationships

========================
OUTPUT FORMAT STRICTLY
========================

---CLOUDFORMATION---
<YAML WITH COMMENTS>

---TERRAFORM---
<HCL WITH COMMENTS>

---DIAGRAM---
<MERMAID CODE ONLY>
"""

    response = client.responses.create(
        model="gpt-5-mini",
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
    )

    return response.output_text.strip()


def split_output(output: str):
    cf, tf, diagram = "", "", ""

    if "---CLOUDFORMATION---" in output:
        cf = output.split("---CLOUDFORMATION---")[1].split("---TERRAFORM---")[0].strip()

    if "---TERRAFORM---" in output:
        tf = output.split("---TERRAFORM---")[1].split("---DIAGRAM---")[0].strip()

    if "---DIAGRAM---" in output:
        diagram = output.split("---DIAGRAM---")[1].strip()

    return cf, tf, diagram


def save_files(cf_code, tf_code):
    if cf_code:
        with open("template.yaml", "w") as f:
            f.write(cf_code)

    if tf_code:
        with open("main.tf", "w") as f:
            f.write(tf_code)


# 🔥 VALIDATION FUNCTIONS

def validate_cloudformation():
    try:
        result = subprocess.run(
            ["aws", "cloudformation", "validate-template", "--template-body", "file://template.yaml"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0, result.stderr
    except Exception as e:
        return False, str(e)


def validate_terraform():
    try:
        subprocess.run(["terraform", "init"], capture_output=True, text=True)

        result = subprocess.run(
            ["terraform", "validate"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0, result.stderr
    except Exception as e:
        return False, str(e)


# 🚀 FASTAPI ENDPOINT
@app.post("/generate")
def generate(request: RequestModel):
    raw = generate_iac(request.input)
    cf, tf, diagram = split_output(raw)

    save_files(cf, tf)

    cf_valid, cf_err = validate_cloudformation() if cf else (False, "")
    tf_valid, tf_err = validate_terraform() if tf else (False, "")

    return {
        "cloudformation": cf,
        "terraform": tf,
        "diagram": diagram,
        "validation": {
            "cloudformation_valid": cf_valid,
            "cloudformation_error": cf_err,
            "terraform_valid": tf_valid,
            "terraform_error": tf_err
        }
    }


# 🔹 Health check (IMPORTANT for Load Balancer)
@app.get("/")
def health():
    return {"status": "running"}


# 🔹 CLI MODE (kept from your original)
if __name__ == "__main__":
    user_input = input("Describe your infrastructure:\n")

    output = generate_iac(user_input)
    cf_code, tf_code, diagram = split_output(output)

    save_files(cf_code, tf_code)

    print("\n=== CloudFormation ===\n", cf_code)
    print("\n=== Terraform ===\n", tf_code)
    print("\n=== Diagram ===\n", diagram)

    if cf_code:
        valid, err = validate_cloudformation()
        print("\nCF VALID:", valid)
        if err:
            print(err)

    if tf_code:
        valid, err = validate_terraform()
        print("\nTF VALID:", valid)
        if err:
            print(err)