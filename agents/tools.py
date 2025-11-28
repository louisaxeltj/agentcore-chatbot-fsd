import json
import re
from config.settings import settings
from agents.read_fsd import ReadFSD
from agents.flow_tree import CodeFlowTree
from agents.compare_fsd import CompareFSD
from utils.app_logger import logger
from utils.helpers import standardize, rows_to_csv_string, parse_pipe_csv


def process_reqtraceai(codebase_data: str, doc_id: str):
    if not doc_id:
        return None
    
    read_fsd = ReadFSD(doc_id=doc_id)

    s3_fsd = read_fsd.get_fsd_s3()

    code_flow_tree = CodeFlowTree(codebase_data=codebase_data)

    flow_res, tree_res = code_flow_tree.get_flow_tree()

    compare_fsd = CompareFSD(requirements=s3_fsd, flow=flow_res, tree=tree_res)

    comparison_flow, comparison_tree = compare_fsd.do_compare_fsd()

    try:
        flow_result = standardize(comparison_flow)
        tree_result = standardize(comparison_tree)

        file_flow = rows_to_csv_string(parse_pipe_csv(comparison_flow))
        file_tree = rows_to_csv_string(parse_pipe_csv(comparison_tree))

    except Exception as e:
        logger.info(f"Err at Output Processing: {str(e)}")

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