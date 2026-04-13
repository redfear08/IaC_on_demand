import os
import subprocess
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


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
- Keep it clean and readable
- Use labels like:
  User --> API Gateway --> Lambda --> EC2

========================
OUTPUT FORMAT STRICTLY
========================

---CLOUDFORMATION---
<YAML WITH COMMENTS>

---TERRAFORM---
<HCL WITH COMMENTS>

---DIAGRAM---
<MERMAID CODE ONLY>

IMPORTANT:
- No explanations outside sections
- No markdown formatting
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
    cf, tf = "", ""

    if "---CLOUDFORMATION---" in output:
        cf = output.split("---CLOUDFORMATION---")[1].split("---TERRAFORM---")[0].strip()

    if "---TERRAFORM---" in output:
        tf = output.split("---TERRAFORM---")[1].strip()

    return cf, tf


def save_files(cf_code, tf_code):
    if cf_code:
        with open("template.yaml", "w") as f:
            f.write(cf_code)

    if tf_code:
        with open("main.tf", "w") as f:
            f.write(tf_code)


# 🔥 VALIDATION FUNCTIONS

def validate_cloudformation():
    print("\n🔍 Validating CloudFormation...")

    try:
        result = subprocess.run(
            ["aws", "cloudformation", "validate-template", "--template-body", "file://template.yaml"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print("✅ CloudFormation is VALID")
        else:
            print("❌ CloudFormation INVALID")
            print(result.stderr)

    except Exception as e:
        print("Error:", str(e))


def validate_terraform():
    print("\n🔍 Validating Terraform...")

    try:
        subprocess.run(["terraform", "init"], capture_output=True, text=True)

        result = subprocess.run(
            ["terraform", "validate"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print("✅ Terraform is VALID")
        else:
            print("❌ Terraform INVALID")
            print(result.stderr)

    except Exception as e:
        print("Error:", str(e))


if __name__ == "__main__":
    user_input = input("Describe your infrastructure:\n")

    output = generate_iac(user_input)

    cf_code, tf_code = split_output(output)

    save_files(cf_code, tf_code)

    print("\n=== CloudFormation ===\n", cf_code)
    print("\n=== Terraform ===\n", tf_code)

    # 🔥 Run validations automatically
    if cf_code:
        validate_cloudformation()

    if tf_code:
        validate_terraform()
