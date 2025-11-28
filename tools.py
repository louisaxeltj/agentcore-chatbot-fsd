import json
import re
from config.settings import settings
from system.read_fsd import ReadFSD
from system.flow_tree import CodeFlowTree
from system.compare_fsd import CompareFSD


def read_reqtrace_fsd(doc_id: str) -> str:
   read_fsd = ReadFSD(doc_id=doc_id)

   s3_fsd = read_fsd.get_fsd_s3()

   s3_fsd_status = s3_fsd['status']
   s3_fsd_resp = s3_fsd['response']

   return s3_fsd_status, s3_fsd_resp


def build_code_tree_and_flow(codebase_data: str) -> str:
    code_flow_tree = CodeFlowTree(codebase_data=codebase_data)

    flow_tree_res = code_flow_tree.get_flow_tree()

    flow_tree_status = flow_tree_res['status']
    flow_tree_resp = flow_tree_res['response']

    return flow_tree_status, flow_tree_resp

def compare_fsd_and_code(requirements: str, code_flow: str, code_tree: str) -> str:
    compare_fsd = CompareFSD(requirements=requirements, flow=code_flow, tree=code_tree)

    compare_res = compare_fsd.do_compare_fsd()

    compare_status = compare_res['status']
    compare_resp = compare_res['response']

    compare_resp_flow = compare_resp['flow']
    compare_resp_tree = compare_resp['tree']

    return compare_resp_flow, compare_resp_tree


def process_reqtraceai(codebase_data: str, doc_id: str):
        
    if not doc_id:
        return None
        # return {
        #     "statusCode": 400,
        #     "response": "Missing doc_id"
        # }
    
    requirements = read_reqtrace_fsd(doc_id=doc_id)
    result_flow, result_tree = build_code_tree_and_flow(codebase_data=codebase_data)

    comparison_flow, comparison_tree = compare_fsd_and_code(requirements=requirements, code_flow=result_flow, code_tree=result_tree)

    
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