import time
from datetime import datetime
import os
import json
import boto3
import botocore
from botocore.exceptions import ClientError
from botocore.config import Config
from config.settings import settings
from utils.app_logger import logger


class CodeFlowTree():
    def __init__(self, codebase_data):
        config = botocore.config.Config(read_timeout=900, connect_timeout=900)
        self.s3 = boto3.client("s3", region_name=settings.BUCKET_S3, config=config)
        self.codebase_data = codebase_data

    @staticmethod
    def process_response(response):
        raw = response["body"].read()
        try:
            decoded = raw.decode("utf-8")
            response_body = json.loads(decoded)
        except Exception as e:
            raise RuntimeError(f"Failed to parse response: {e}")
        content = response_body.get("content", [])
        text = content[0].get("text", "") if content else ""
        return text

    @staticmethod
    def invoke_bedrock(bedrock, model_id, request):
        try:
            if isinstance(request, dict):
                body = json.dumps(request)
            else:
                body = request

            response = bedrock.invoke_model(
                modelId=model_id,
                body=body
            )
            return response
        except ClientError as e:
            print(f"AWS ClientError invoking {model_id}: {e.response['Error']['Message']}")
            raise
        except Exception as e:
            print(f"Unexpected error invoking {model_id}: {e}")
            raise

    @staticmethod
    def prepare_message(prompt):
        native_request_tree = {
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 64000,
            "temperature": 0.1,
            "anthropic_version": "bedrock-2023-05-31"
        }
        
        request = json.dumps(native_request_tree)
        return request
    
    def return_prompt_flow(self):
        prompt_flow = '''
        You are an expert ABAP/SAP HANA code analyst. Analyze the provided ABAP codebase file, which contains the full code consolidated into one file. Each original file section is marked with its filename.
        
        Task:
        1. Identify **all flows** in the codebase. Each flow represents a distinct business process or use case.
        2. For each **flow**, build a **tree structure** with:
        - Flow name or description (what the flow does)
        - All **steps** in order
        - Class and method used for each step
        3. For each **step**, describe the **function or method**:
        - **DESCRIPTION:** What the step does
        - **PROCESS:** Step-by-step actions or sub-steps within this step
        4. For each step, identify the **inputs** and **outputs**. 
        Follow these rules strictly:
        - If a variable has nested fields (like a structure or table), list all fields.
        - If an input comes from the output of a previous step, clearly indicate it.
        When describing a step:
        - "Process" must only describe the action (e.g. SELECT ... FROM <table>).
        Do NOT list fields here.
        - "Outputs" and "Inputs" must list every field selected. 
        Always write each field in one of the following formats:
            a) field_name AS alias   (if alias exists)
            b) field_name            (if no alias)
        - Never collapse multiple fields into a single SQL line under Process. 
        Fields belong ONLY in Input and Output.
        5. The structure must support **multiple flows** and **multiple steps per flow**.
        6. Strict rules:
        - Do **not** speculate or hallucinate; describe only what is explicitly in the code
        - Do **not** add extra explanations outside the structure
        7. Output in the following **general tree structure**, fully nested:
        
        
        -----------------------------------------------------------    
        FLOW OVERVIEW:
        ⦁	[FLOW_NAME_1] and [FLOW_NAME_2] [or/and] [FLOW_NAME_N] are interconnected processes designed to accomplish [general purpose of both flows] (e.g., "data processing," "user interaction," "task execution," etc.).
        ⦁	Flow Relationships:
        1.	[FLOW_NAME_1]: Initial phase, [brief description of Flow 1]
        2.	[FLOW_NAME_1] outputs ([output_var_1], [output_var_2]) → [FLOW_NAME_2]
        3.	[FLOW_NAME_2]: Builds on [FLOW_NAME_1]'s output, performs [brief description of Flow 2]
        4.	[FLOW_NAME_2] outputs → Final results or inputs for next steps
        5.  [FLOW_NAME_N] (if applicable): Follows similar pattern
        
        Flow 1: [FLOW_NAME_1]
        ├── Objectives: [Brief description of what this flow is designed to accomplish or the intended outcome]
        ├── Step 1: [STEP_NAME_1]
        │    ├── Class/Method: [CLASS_NAME]=>[METHOD_NAME]
        │    ├── Description: [Brief description of what this step does]
        │    ├── Input:
        │    │    [input_var_1]:
        │    │        - field1
        │    │        - field2
        │    │    [input_var_2]
        │    ├── Process:
        │    │    - [Sub-step / action 1 with detailed calculation or process]
        │    │    - [Sub-step / action 2 with detailed calculation or process]
        │    │    - [Sub-step / action N with detailed calculation or process]
        │    ├── Output:
        │    │    [output_var_1]:
        │    │        - fieldA
        │    │        - fieldB
        │    │    [output_var_2]
        │    └── Scenarios:
        │         ├── Scenario A (Standard Success Path)
        │         │    ├── Condition: sy-subrc = 0
        │         │    ├── Outcome: Data retrieved successfully
        │         │    └── Next Step: Step 2
        │         └── Scenario B (Alternate Handling)
        │              ├── Condition: input optional but not provided
        │              ├── Outcome: Use default values
        │              └── Next Step: Continue with Step 2
        
        ├── Step 2: [STEP_NAME_2]
        │    ├── Class/Method: [CLASS_NAME]=>[METHOD_NAME]
        │    ├── Description: [Brief description of what this step does]
        │    ├── Input:
        │    │    [output_var_1] (from previous step)
        │    │        - fieldA 
        │    │        - fieldB
        │    │    [additional_input]
        │    ├── Process:
        │    │    - [Sub-step / action 1 with detailed calculation or process]
        │    │    - [Sub-step / action N with detailed calculation or process]
        │    ├── Output:
        │    │    [output_var_3]:
        │    │        - fieldA
        │    │        - fieldB
        │    │    [output_var_4]
        │    └── Scenarios:
        │         ├── Scenario A (Standard Success Path)
        │         │    ├── Condition: sy-subrc = 0
        │         │    ├── Outcome: Data retrieved successfully
        │         │    └── Next Step: Step 2
        │         ├── Scenario B (Validation Error)
        │         │    ├── Condition: input field missing or invalid
        │         │    ├── Outcome: Raise error message, stop flow
        │         │    └── Next Step: End process
        │         └── Scenario C (Alternate Handling)
        │              ├── Condition: input optional but not provided
        │              ├── Outcome: Use default values
        │              └── Next Step: Continue with Step 2
        
        └── Step N: [STEP_NAME_N]
            ├── Class/Method: [CLASS_NAME]=>[METHOD_NAME]
            ├── Description: [Brief description of what this step does]
            ├── Input:
            │    [output_var_3] (from previous step)
            │        - fieldX
            │        - fieldY
            │    [additional_input_N]
            ├── Process:
            │    - [Sub-step / action 1 with detailed calculation or process]
            │    - [Sub-step / action N with detailed calculation or process]
            ├── Output:
            |    [final_output]:
            |        - fieldM
            |        - fieldN
            |    [other_output]
            └── Scenarios:
                ├── Scenario A 
                │    ├── Condition:
                │    ├── Outcome: 
                │    └── Next Step: 
                └── Scenario C
                    ├── Condition:
                    ├── Outcome:
                    └── Next Step:
                
        Flow N: [FLOW_NAME_N]
        ├── Objectives: [Brief description of what this flow is designed to accomplish or the intended outcome]
        ├── Step 1: [STEP_NAME_1]
        │    ├── ...
        └── Step M: [STEP_NAME_M]
            ├── ...
        
        -----------------------------------------------------------
        
        8. Emphasize **data flow**: output of one step may feed into another step as input.
        9. Make it **as detailed as possible**, breaking down input/output fields and processes, while keeping the tree readable.
        10. For every step, explicitly describe all **Scenarios** (not only success/failure):
        - Each Scenario must specify:
        a) **Condition** (the logical check, return code, or variable state that triggers it)
        b) **Outcome** (what happens in this scenario)
        c) **Next Step / Branch** (if the process continues differently)
        11. If there are multiple scenarios (more than just success and failure), represent each scenario as a separate branch under the step.
        12. Always preserve indentation and ASCII tree formatting consistently in the output.
        13. Use the code provided below as the only source for your analysis:
        
        {codebase}

            '''.format(codebase=self.codebase_data)

        return prompt_flow

    def return_prompt_tree(self):
        prompt_tree = '''
            You are an expert ABAP/SAP HANA code analyst. Analyze the provided ABAP codebase file, which contains the full code consolidated into one file. Each original file section is marked with its filename.
            
            1. Identify all the **FILENAME** present in the codebase.
            2. For each **FILENAME**, identify all the **CLASS**.
            3. Within each **CLASS**, explain any large or small **METHODS** or **statements** present inside, including what functionality or process is being performed.
            4. For every **METHOD**, both large and small, provide the following:
            - **DESCRIPTION** of what the method does.
            - **INPUTS** accepted by the method, including the name of the variable and its data type. If none, write INPUT=None.
            - **STEPS**: Step-by-step actions within this method
            - **OUTPUTS** generated by the method, including the name of the variable and its data type. If none, write OUTPUT=None.
            5. If there are **METHODS within METHODS** (nested methods), explain all these methods as well.
            6. For every **STEPS**, provide INPUT, Detailed Process, and OUTPUT.
            7. When describing steps, if there are **Function Module calls** inside, always explicitly include the exact **Function Module name** being called, in addition to describing what it does.
            8. Do not speculate or introduce hallucinations in your explanations—only describe what is explicitly in the code.
            9. The output must strictly follow the structure and formatting shown below.
            
            **Example Structure**:
            -----------------------------------------------------------
            TREE
            ├── [FILENAME]
            │   ├── CLASS: <CLASS_Name> (file / location)
            │   │   ├── METHOD: <method_name> (visibility)
            │   │   │   ├── DESCRIPTION:
            │   │   │   │   Purpose of the method in short words.
            |   |   |   |
            │   │   │   └── STEPS:
            │   │   │       ├── STEP 1: [STEP_NAME_1]
            │   │   │       │   └── INPUT:
            │   │   │       │   |    [input_var_1]:
            │   │   │       │   |        - field1
            │   │   │       │   |        - field2
            │   │   │       │   |        - field3
            │   │   │       │   |    [input_var_2]
            │   │   │       │   └── Detailed Process: 
            │   │   │       │   |    - [Detail calculation or detail action]
            │   │   │       │   └── OUTPUT:
            │   │   │       │        [output_var_1]:
            │   │   │       │            - field1
            │   │   │       │            - field2
            │   │   │       │            - field3
            │   │   │       │        [output_var_2]
            │   │   │       │
            │   │   │       ├── STEP 2: [STEP_NAME_2]
            │   │   │       │   └── INPUT:
            │   │   │       │   |    [input_var_1] (from step 1):
            │   │   │       │   |        - field1
            │   │   │       │   |        - field2
            │   │   │       │   |        - field3
            │   │   │       │   |    [additional_input]
            │   │   │       │   └── Detailed Process: 
            │   │   │       │   |    - [Detail calculation or detail action]
            │   │   │       │   └── OUTPUT:
            │   │   │       │        [output_var_3]:
            │   │   │       │            - field1
            │   │   │       │            - field2
            │   │   │       │            - field3
            │   │   │       │        [output_var_4]
            │   │   │       │
            │   │   │       └── STEP N: [STEP_NAME_N]
            │   │   │           └── INPUT:
            │   │   │           |    [input_var_X] (from step 1):
            │   │   │           |        - fieldA
            │   │   │           |        - fieldB
            │   │   │           |        - fieldC
            │   │   │           |    [input_var_Y]
            │   │   │           └── Detailed Process: 
            │   │   │           |    - [Detail calculation or detail action]
            │   │   │           └── OUTPUT:
            │   │   │                [output_var_R]:
            │   │   │                    - fieldM
            │   │   │                    - fieldN
            │   │   │                    - fieldO
            │   │   │                [output_var_S]
            │   │   │   
            │   │   └── (next METHOD…)
            │   └── (next CLASS)
            └── [next FILENAME]
                └── (next CLASS)
                    └── (next METHOD…)
            -----------------------------------------------------------
            
            10. Emphasize **data flow**: output of one step may feed into another step as input.
            11. Make it **as detailed as possible**, breaking down input/output fields and processes, while keeping the tree readable.
            12. If there are **Function Modules** outside methods/classes, explain them in the same way as methods.
            13. If there are **FORM routines**, document them in the same way as methods.
            14. For **standalone statements** (SELECT, UPDATE, DELETE, LOOP, PERFORM, etc.), describe them as separate STEPS.
            15. Always preserve **indentation and ASCII tree formatting** consistently in the output.
            16. Use the code provided below as the only source for your analysis:
            
            {codebase}
            
            '''.format(codebase=self.codebase_data)

        return prompt_tree

    def get_flow_tree(self):

        if self.codebase_data is None:
            return {
                'status': 500,
                'response': 'Codebase Data not Found'
            }
        
        model_id = settings.MODEL_ID
        # model_id = "arn:aws:bedrock:us-west-2:761018880232:inference-profile/us.anthropic.claude-sonnet-4-20250514-v1:0"

        config = botocore.config.Config(read_timeout=1000, connect_timeout=1000)

        bedrock = boto3.client("bedrock-runtime", region_name=settings.REGION_BEDROCK, config=config)

        object_content = {}

        try:
            ### FLOW ###
            print('Start Processing Flow')
            prompt_flow = self.return_prompt_flow(self.codebase_data)
            request_flow = self.prepare_message(prompt_flow)
            response_flow = self.invoke_bedrock(bedrock, model_id, request_flow)
            flow_content = self.process_response(response_flow)
            object_content["flow"] = flow_content

            ### TREE ###
            print('Start Processing Tree')
            prompt_tree = self.return_prompt_tree(self.codebase_data)
            request_tree = self.prepare_message(prompt_tree)
            response_tree = self.invoke_bedrock(bedrock, model_id, request_tree)
            tree_content = self.process_response(response_tree)
            object_content["tree"] = tree_content

            tes = {
                'status': 200,
                "response": object_content
            }
            print(f"Status: {tes['status']}")
            print(f"Result (10 first char): {tes['response']['flow'][:10]}, {tes['response']['tree'][:10]}")


            # return {
            #     'statusCode': 200,
            #     "headers": {"Content-Type": "application/json"},
            #     "body": json.dumps({"result": object_content})
            # }
            return flow_content, tree_content
        except Exception as e:
            logger.info(f"Err : {str(e)}")
            return "", ""