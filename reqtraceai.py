import os
import re
import json
import uuid
import zipfile
import io
import csv
import json
from config.settings import settings
from utils.app_logger import logger
import requests
from fastapi import Form, UploadFile, File
from connector.lambda_handler import lambda_caller


class ReqTraceAI():
    def standardize(self, text: str):
        rows = self.parse_pipe_csv(text)
        markdown_table = self.to_markdown_table(rows)
        
        return markdown_table

    @staticmethod
    def parse_pipe_csv(text: str):
        rows = []
        reader = csv.reader(text.splitlines(), delimiter="|")
        for row in reader:
            rows.append([col.strip() for col in row])  # bersihin spasi
        return rows
    
    @staticmethod
    def rows_to_csv_string(rows):
        """Convert list of lists jadi string CSV (pakai , atau | sesuai kebutuhan)"""
        output = io.StringIO()
        writer = csv.writer(output, delimiter=",", quoting=csv.QUOTE_MINIMAL)
        writer.writerows(rows)
        return output.getvalue()

    @staticmethod
    def to_markdown_table(rows):
        if not rows:
            return ""

        # Header
        header = "| " + " | ".join(rows[0]) + " |"
        separator = "| " + " | ".join(["---"] * len(rows[0])) + " |"
        body = "\n".join("| " + " | ".join(row) + " |" for row in rows[1:])

        return "\n".join([header, separator, body])
    
    def process_reqtraceai(self, codebase_data, doc_id):
        
        # get fsd as requirements
        url_fsd = "https://c52d5fz4nrt5tfxwq4wpe7542q0cspvw.lambda-url.us-west-2.on.aws/"
        
        
        try:
            param = {"doc_id": doc_id}
            logger.info(f"Start Get FSD for {doc_id}")
            # async with httpx.AsyncClient(verify=False) as client:
            #     response_fsd = await client.post(url_fsd, json=param, timeout=timeout)
            #     result_json_fsd = response_fsd.json()
            #     requirements = result_json_fsd["result"]
            resp_reqtraceai_read_fsd = lambda_caller("arn:aws:lambda:us-west-2:761018880232:function:reqtraceai_read_fsd", param, agent=1)
            requirements = resp_reqtraceai_read_fsd['response']
        except Exception as e:
            logger.info(f"Err at Get FSD : {str(e)}")
        
        # get code flow and tree
        url_code = "https://jfwtornlyt6txwsprboiebysoi0jibhz.lambda-url.us-west-2.on.aws/"
        
        
        try:
            param_code = {"codebase_data": codebase_data}
            logger.info(f"Start FSD Code Flow {codebase_data[:10]}")
            # async with httpx.AsyncClient(verify=False) as client:
            #     response_code = await client.post(url_code, json=param_code, timeout=timeout)
            #     logger.info(f"Res Code Out : {response_code}")
            #     result_json_code = response_code.json()
            #     logger.info(f"Res Code Out JSON : {result_json_code}")
            #     result_code = result_json_code["result"]
            #     result_flow = result_code['flow']
            #     result_tree = result_code['tree']
            resp_dummy_tool_code_tree = lambda_caller("arn:aws:lambda:us-west-2:761018880232:function:dummy_tool_code_tree", param_code, agent=1)
            # result_code = resp_dummy_tool_code_tree['response']['result']
            result_flow = resp_dummy_tool_code_tree['response']['flow']
            result_tree = resp_dummy_tool_code_tree['response']['tree']
        except Exception as e:
            logger.info(f"Err at FSD Code Flow: {str(e)}")

        logger.info(f"response code: {resp_dummy_tool_code_tree}")
        
        # To compare
        url_compare = "https://uflvgh4vjea3zhgypozlvbevv40rscom.lambda-url.us-west-2.on.aws/"
        
        
        try:
            param_compare = {"requirements_text": requirements, "result_flow": result_flow, "result_tree": result_tree}
            logger.info(f"Start Comparing {result_flow[:10]}")
            # async with httpx.AsyncClient(verify=False) as client:
            #     response_compare = await client.post(url_compare, json=param_compare, timeout=timeout)
            #     result_json_compare = response_compare.json()
            #     result_compare = result_json_compare["result"]
            #     compare_flow = result_compare['flow']
            #     compare_tree = result_compare['tree']
            resp_dummy_tool_compare_fsd_and_code = lambda_caller("arn:aws:lambda:us-west-2:761018880232:function:dummy_tool_compare_fsd_and_code", param_compare, agent=1)
            # result_compare = resp_dummy_tool_compare_fsd_and_code['response']['result']
            compare_flow = resp_dummy_tool_compare_fsd_and_code['response']['flow']
            compare_tree = resp_dummy_tool_compare_fsd_and_code['response']['tree']
        except Exception as e:
            logger.info(f"Err at Comparing : {str(e)}")
        
        # Make 
        try:

            flow_result = self.standardize(compare_flow)
            tree_result = self.standardize(compare_tree)
            
            file_flow = self.rows_to_csv_string(self.parse_pipe_csv(compare_flow))
            file_tree = self.rows_to_csv_string(self.parse_pipe_csv(compare_tree))
        except Exception as e:
            logger.info(f"Err at after Comparing : {str(e)}")
        
        return {
            "flow_result":{
                "compare_markdown": flow_result,
                "filename": f"{doc_id}_checkflow.csv",
                "file_content": file_flow
            },
            "tree_result":{
                "compare_markdown": tree_result,
                "filename": f"{doc_id}_checktree.csv",
                "file_content": file_tree
            },
        }