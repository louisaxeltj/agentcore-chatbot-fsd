def read_reqtrace_fsd(doc_id: str) -> str:
    fsd_content = ""
    # Implement lambda function of lambda_caller("arn:aws:lambda:us-west-2:761018880232:function:reqtraceai_read_fsd", param, agent=1)

    return fsd_content


def build_code_tree_and_flow(codebase_data: str) -> str:
    # Implement lambda function of lambda_caller("arn:aws:lambda:us-west-2:761018880232:function:dummy_tool_code_tree")
            # try:
            # param_code = {"codebase_data": codebase_data}
            # logger.info(f"Start FSD Code Flow {codebase_data[:10]}")
            # # async with httpx.AsyncClient(verify=False) as client:
            # #     response_code = await client.post(url_code, json=param_code, timeout=timeout)
            # #     logger.info(f"Res Code Out : {response_code}")
            # #     result_json_code = response_code.json()
            # #     logger.info(f"Res Code Out JSON : {result_json_code}")
            # #     result_code = result_json_code["result"]
            # #     result_flow = result_code['flow']
            # #     result_tree = result_code['tree']
            # resp_dummy_tool_code_tree = lambda_caller("arn:aws:lambda:us-west-2:761018880232:function:dummy_tool_code_tree", param_code, agent=1)
            # # result_code = resp_dummy_tool_code_tree['response']['result']

            # result_flow, result_tree = resp_dummy_tool_code_tree['response']['flow'],  resp_dummy_tool_code_tree['response']['tree']
    
    result_flow, result_tree = "", ""

    return result_flow, result_tree


def compare_fsd_and_code(requirements: str, code_flow: str, code_tree: str) -> str:
    #  try:
    #         param_compare = {"requirements_text": requirements, "result_flow": result_flow, "result_tree": result_tree}
    #         logger.info(f"Start Comparing {result_flow[:10]}")
    #         # async with httpx.AsyncClient(verify=False) as client:
    #         #     response_compare = await client.post(url_compare, json=param_compare, timeout=timeout)
    #         #     result_json_compare = response_compare.json()
    #         #     result_compare = result_json_compare["result"]
    #         #     compare_flow = result_compare['flow']
    #         #     compare_tree = result_compare['tree']
    #         resp_dummy_tool_compare_fsd_and_code = lambda_caller("arn:aws:lambda:us-west-2:761018880232:function:dummy_tool_compare_fsd_and_code", param_compare, agent=1)
    #         # result_compare = resp_dummy_tool_compare_fsd_and_code['response']['result']
    #         compare_flow = resp_dummy_tool_compare_fsd_and_code['response']['flow']
    #         compare_tree = resp_dummy_tool_compare_fsd_and_code['response']['tree']
    #     except Exception as e:
    #         logger.info(f"Err at Comparing : {str(e)}")

    result_comparison_flow, result_comparison_tree = "", ""

    return result_comparison_flow, result_comparison_tree


def process_reqtraceai(codebase_data: str, doc_id: str):
        
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