import logging
# from val_data import query_engine
# from app_question_intent import get_question_intent_general
# from val_dg_rag import doc_retrieval
from valorant_agent import agent_call
from connections import Connections


def get_response(user_input, session_id):
    """
    Get response RAG or Query
    """
    # logging.info("Getting response from RAG or Query or Agent Call")
    # llm_qintent = Connections.get_bedrock_llm(
    #     model_name="Claude3Haiku", max_tokens=32, cache=False
    # )

    # llm_agent = Connections.get_bedrock_llm(
    #     model_name="Claude2", max_tokens=1024, cache=False, mode="text_completion"
    # )
    # qintent = get_question_intent_general(llm=llm_qintent, query=user_input)
    # logging.debug("Question %s", user_input)
    # logging.debug("Intent: %s", qintent)
    # if qintent == "UseCase2":
    #     response = query_engine.query(user_input)
    #     logging.debug(response.response)
    #     logging.debug(response.metadata["sql_query"])
    #     output = {"source": response.metadata["sql_query"], "answer": response.response}
    # elif qintent == "UseCase1":
    #     output = doc_retrieval(user_input)
    # elif qintent == "UseCase3":
    #     output = agent_call(llm=llm_agent, query=user_input)
    # else:
    #     output = {
    #         "source": " ",
    #         "answer": "This is a malicious query. Please ask a relevant question.",
    #     }

    # logging.info(output)

    llm_agent = Connections.get_bedrock_llm(
        model_name="Claude2", max_tokens=1024, cache=False, mode="text_completion"
    )

    output = agent_call(llm=llm_agent, query=user_input)

    logging.info(output)
    return output
