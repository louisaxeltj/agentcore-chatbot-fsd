import boto3
import time
from datetime import datetime
import os
import json
from botocore.exceptions import ClientError
from botocore.config import Config
import botocore
from config.settings import settings

class CompareFSD():
    def __init__(self, requirements, flow, tree):
        config = botocore.config.Config(read_timeout=900, connect_timeout=900)
        self.requirements_txt = requirements
        self.flow = flow
        self.tree = tree
        self.model_id = settings.MODEL_ID
        self.bedrock = boto3.client("bedrock-runtime", region_name=settings.REGION_BEDROCK, config=config)

    def compare_requirements_tree(self):
        prompt = f"""
                You are a **System Requirement and Tree Checker**.  
                Focus: **exact-name and structure matching**, with **full context**.

                GOAL
                Compare the Requirements with the provided Tree (which lists parameter names, table names, variables, data sources, UI elements, module/component names, and other named elements).  
                Verify **whether every named element and structure required is explicitly present in the tree**.  
                Nothing may be skipped: if a Requirement mentions 10 elements, the output must contain 10 rows.

                SCOPE (only check these items, if present in requirements):
                - **Data structures** (named structures, records, DTOs)
                - **Database table structure** (table names, column/field names; if types/lengths listed in requirements, mention presence/absence)
                - **User interface requirements** (element IDs, control names, labels, input fields that must exist)
                - **Element / module names** (classes, modules, services)
                - **Variable / parameter names**

                OUT OF SCOPE:
                - Business logic, workflows, test cases, error handling, or other behavioral checks.
                - Do not check semantics unless the name/structure is explicitly required.

                METHOD (strict):
                1. **Decompose** the Requirements into atomic named items. If a requirement lists multiple named elements, treat each element as a separate atomic item (one row per element).
                - Always include context in the Requirement column (e.g., "Database Table required: ZSDT_PODALL" not just "ZSDT_PODALL").  
                2. For each atomic item:  
                - Search the Tree for evidence of the element name.  
                - Matching is **case-insensitive** (e.g., `ZSDT_PODALL` matches `zsdT_podall`).  
                3. **Evidence rules**:
                - Always **quote the exact fragment** from the requirement and the Tree that you use as evidence, **with its full context**.  
                - Example: instead of only `TOR_ID`, write *"Input Data Structure in `ZSDT_PODALL` → field `TOR_ID`"* or *"Database table `CUSTOMER_MASTER` → column `CustomerID`"*.
                - Do NOT invent or infer names that are not present. If the tree is ambiguous or does not contain explicit evidence, mark **Not Implemented** and explain the reason clearly in 'Description'
                4. **Output must cover ALL requirements**: If a requirement mentions N items, the output must have N rows (no skipping).

                OUTPUT (strict):
                - Return **ONLY** a Markdown table. One row per atomic named requirement/item.
                - Columns (exact names):
                1. **Requirement** — the item as stated in the requirement **with its context**
                2. **Tree (related part)** — the exact snippet from the Tree that is relevant (quote exact text from Tree) **with context** . If not found, write "No explicit evidence in Tree".
                3. **Implemented/Partial Implemented/Not Implemented** 
                4. **Description** — full explanation:
                    - If **Implemented**: give a short, evidence-based justification (2–4 sentences) that cites the quoted Tree fragment and explains why it is match.
                    - If **Partial Implemented**: explain precisely what is present and what is missing (e.g., the name of column `X` is not exactly match but have same meaning, or name partially matches but differs in format). Recommend the exact expected name/structure that should appear additionally in the tree.
                    - If **Not Implemented**: explain precisely what is missing or mismatched (e.g., missing table, missing column `X`), and **recommend the exact expected name/structure** that should appear in the tree.

                STRICT RULES:
                - Be **objective** and factual. Do not invent or assume names not present in Tree. 
                - Always give context in both Requirement and Tree columns.  
                - Cover every single requirement item without exception.  
                - Case-insensitive match is allowed.  
                - If partially matched/implemented (e.g., table exists but some columns missing), make one row per column names and mark accordingly.

                INPUT (placeholders):
                ### Requirements:
                {self.requirements_txt}

                ### Tree:
                {self.tree}

                Return the Markdown table only — nothing else.
                """

        messages = [
            {"role": "user", "content": [{"text": prompt}]}
        ]

        response = self.bedrock.converse(
            modelId=self.model_id,
            messages=messages,
            inferenceConfig={"maxTokens": 64000, "temperature": 0}
        )

        result_text = response["output"]["message"]["content"][0]["text"]
        input_tok = response["usage"]["inputTokens"]
        output_tok = response["usage"]["outputTokens"]

        return result_text, input_tok, output_tok

    def compare_requirements_flow(self):
        prompt = f"""
                You are a **System Requirement Compliance Checker** specialized in **flow-level verification**.

                Goal:
                - Compare the **Requirements** (focus only on Business Logic, Validations, Test Cases & Validation Criteria, Error/Exception Handling, Security/Authorization, and Interface/Integration behavior) with the **actual Flow** of code execution, and judge whether the flow implements them correctly.
                - Nothing may be omitted.

                Out of scope (do NOT check):
                - DO NOT CHECK Variable/parameter/module/table names, data naming, schemas, or field mappings **unless** they directly affect control flow.
                - DO NOT CHECK Data values/contents and UI cosmetics that do not change the flow.

                Scope to check (only if present in the requirements):
                - **Functional logic / Business rules / Workflow steps** (order, branching, pre/post-conditions, idempotency).
                - **Validations** (preconditions, status checks, field/entity checks that affect control flow).
                - **Error handling & Exception handling** (detection, classification, messages/status, retry/backoff, rollback/compensation).
                - **Security & Authorization** (authN/authZ checks, permission gates, placement before sensitive actions).
                - **Test Cases & Validation Criteria** (treat each test case as an atomic requirement; verify trigger → steps → outcome).
                - **Interfaces & Integrations** (behavioral aspects only: direction inbound/outbound, sync/async, triggers/frequency, retry & status handling).
                - **Assumptions / Constraints / Risks / Rules** **sepanjang** memengaruhi alur/keputusan (control flow).

                MUST-HAVE PROCEDURE (strict — follow exactly):
                1. **Decompose** Requirements into atomic items. In particular:
                - Identify and number every Test Case present. Treat each Test Case as one atomic item (include trigger, preconditions, steps, expected result).
                - Identify each distinct validation, error-handling expectation, security/authorization check, and interface behavioral requirement as its own atomic item.
                - If a requirement lists multiple sub-requirements, split them so each atomic item is separate.
                2. **Count** the atomic items. You must ensure the output table contains **one row per atomic item**. If Requirements contain N atomic items (e.g., 9 test cases), the table must contain at least N rows corresponding to them. **Do not skip any.**
                3. For each atomic item:
                a. **Locate minimal evidence** in the Flow (exact step names/conditions/branches/error paths/retries/rollbacks/order). Quote the exact fragment(s) from Flow you rely on as evidence.
                b. **Validate** whether the Flow implements the item correctly:
                    - ordering & dependencies,
                    - branching/decisions,
                    - validations at the required points,
                    - error/exception handling (detection, messages/status, retry/rollback),
                    - security/authorization placed before sensitive actions,
                    - interface behavior (sync/async, triggers, retries/status).
                c. If evidence is explicit and complete, mark **Implemented**. If evidence is missing, partial, ambiguous, or incorrect, mark **Not Implemented**.
                4. **Evidence rules (strict)**:
                - Quote exact Flow fragment(s) used as evidence (use backticks or inline code). Example: ``Step: CALL Z_UPDATE_POD -> IF TVPOD-SUBRC <> 0``.
                - If no explicit evidence exists in Flow, put `-` or `"No explicit evidence"` in Flow column and mark **Not Implemented**.
                - Do NOT invent behavior or infer unstated logic. Only use text present in Requirements and Flow.
                5. **When marking "Implemented"**:
                - Provide a concise, evidence-based justification (3–5 sentences) that:
                    a) cites the exact Flow step(s)/condition(s) used as evidence, and
                    b) explains the logical link: *trigger → precondition → step(s) → expected outcome* showing why the Flow satisfies the atomic Requirement/Test Case.
                - Justification must be factual and cite Flow fragments (no hidden chain-of-thought).
                6. **When marking "Not Implemented"**:
                - Explain precisely what is missing, ambiguous, or incorrect (e.g., missing error path, missing retry, wrong order).
                - Give a concrete corrective description of what the Flow *should* contain to satisfy the requirement (explicit steps/conditions), again without inventing new requirements.
                7. **Completeness enforcement**:
                - If you detect the Requirements mention N test cases/items but Flow only shows evidence for M < N, you must still include rows for the missing (N−M) items with Flow = `No explicit evidence`, Implemented Status = `Not Implemented`, and Description explaining the absence.
                - If multiple Flow fragments partially satisfy an item, include them all in the Flow column (quoted) and explain which parts are missing.

                OUTPUT FORMAT (strict):
                - Return **ONLY** a Markdown table. No additional text outside the table.
                - One row per atomic requirement/test case/item.
                - Columns (exact names, in this order):
                1. **Requirement** — copy the atomic item verbatim.
                2. **Flow (related part / step)** — quote the minimal exact fragment(s) from the Flow that are relevant, with the short context (e.g., ``Step 'Process POD' -> SELECT ... FROM TVPOD``). If none, use `-` or `"No explicit evidence"`.
                3. **Implemented/Partial Implemented/Not Implemented**
                4. **Description** — 
                    - If **Implemented**: provide the 3–5 sentence evidence-based justification (cite Flow fragments). 
                    - If **Partial Implemented**: explain precisely what is present and what is missing (e.g., missing rollback, partial field validation, wrong error handling placement). Recommend what should be added/fixed.
                    - If **Not Implemented**: describe precisely what's missing/incorrect and what the correct flow should be (concrete corrective steps).

                STRICT RULES (summary):
                - The table MUST include rows for **every** atomic item discovered in Requirements. Do not omit or collapse multiple test cases into one row.
                - Do not invent or assume behavior beyond the provided documents.
                - All claims must be supported by quoted Flow fragments.
                - If ambiguous, prefer conservative judgment: mark **Not Implemented** and explain what is missing.

                Input:
                ### Requirements:
                {self.requirements_txt}

                ### Flow:
                {self.flow}
                """

        messages = [
            {"role": "user", "content": [{"text": prompt}]}
        ]

        response = self.bedrock.converse(
            modelId=self.model_id,
            messages=messages,
            inferenceConfig={"maxTokens": 8192, "temperature": 0}
        )

        result_text = response["output"]["message"]["content"][0]["text"]
        input_tok = response["usage"]["inputTokens"]
        output_tok = response["usage"]["outputTokens"]

        return result_text, input_tok, output_tok

    def do_compare_fsd(self):
        # requirements_text = event.get("requirements_text", "")
        # flow_text = event.get("result_flow", "")
        # tree_text = event.get("result_tree", "")

        try:
            
            #   model_id = "arn:aws:bedrock:us-west-2:761018880232:inference-profile/us.anthropic.claude-sonnet-4-20250514-v1:0"


            # body = json.loads(event.get("body", "{}"))
            #   requirements_text = event.get("requirements_text", "")
            #   flow_text = event.get("result_flow", "")
            #   tree_text = event.get("result_tree", "")

            print(f"Requirements (first 50 chars): {self.requirements_txt[:50]}")
            print(f"Flow (first 50 chars): {self.flow[:50]}")
            print(f"Tree (first 50 chars): {self.tree[:50]}")


            flow_comparison_table, input_token, output_token = self.compare_requirements_flow()
            tree_comparison_table, input_token, output_token = self.compare_requirements_tree()

            object_content = {}

            object_content["flow"] = flow_comparison_table
            object_content["tree"] = tree_comparison_table

            # print(f"Result: {object_content}")
            
            # return {
            #    'statusCode': 200,
            #    "headers": {"Content-Type": "application/json"},
            #    "body": json.dumps({"result": object_content})
            # }
            return {
                'status': 200,
                "response": object_content
            }
        except Exception as e:
            # return {
            #    'statusCode': 500,
            #    "headers": {"Content-Type": "application/json"},
            #    "body": json.dumps({"result": str(e)})
            # }
            return {
                'status': 500,
                "response": json.dumps(str(e))
            }