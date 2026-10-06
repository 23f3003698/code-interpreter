import os
import sys
import json
import traceback
from io import StringIO

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI


app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CodeRequest(BaseModel):
    code: str


def execute_python_code(code: str) -> dict:
    old_stdout = sys.stdout

    sys.stdout = StringIO()

    try:
        exec(code)

        output = sys.stdout.getvalue()

        return {
            "success": True,
            "output": output
        }

    except Exception:
        output = traceback.format_exc()

        return {
            "success": False,
            "output": output
        }

    finally:
        sys.stdout = old_stdout


def analyze_error_with_ai(code: str, error_traceback: str) -> list[int]:

    client = OpenAI(
        api_key=os.environ["AIPIPE_TOKEN"],
        base_url="https://aipipe.org/openai/v1"
    )

    prompt = f"""
Analyze this Python code and traceback.

Find the exact source-code line number where the error occurred.

CODE:
{code}

TRACEBACK:
{error_traceback}

Return JSON only in this format:

{{"error_lines": [3]}}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        response_format={
            "type": "json_object"
        }
    )

    result = json.loads(response.choices[0].message.content)

    return result["error_lines"]


@app.get("/")
def home():
    return {
        "message": "Code Interpreter API is running"
    }


@app.post("/code-interpreter")
def code_interpreter(request: CodeRequest):

    execution = execute_python_code(request.code)

    # Successful code → don't call AI
    if execution["success"]:
        return {
            "error": [],
            "result": execution["output"]
        }

    # Error → call AI
    error_lines = analyze_error_with_ai(
        request.code,
        execution["output"]
    )

    return {
        "error": error_lines,
        "result": execution["output"]
    }