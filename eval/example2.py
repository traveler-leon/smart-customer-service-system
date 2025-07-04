import os
os.environ["DEEPEVAL_RESULTS_FOLDER"] = "eval/data"

from typing import List
from openai import OpenAI
from langchain_openai import ChatOpenAI
from deepeval.models.base_model import DeepEvalBaseLLM
from deepeval.dataset import Golden
from deepeval.test_case import LLMTestCase
from deepeval.metrics import AnswerRelevancyMetric, ContextualRelevancyMetric
from deepeval import evaluate
from deepeval.tracing import observe, update_current_span


class HzOpenAI(DeepEvalBaseLLM):
    def __init__(
        self,
        model
    ):
        self.model = model

    def load_model(self):
        return self.model

    def generate(self, prompt: str) -> str:
        chat_model = self.load_model()
        return chat_model.invoke(prompt).content

    async def a_generate(self, prompt: str) -> str:
        chat_model = self.load_model()
        res = await chat_model.ainvoke(prompt)
        return res.content

    def get_model_name(self):
        return "Custom Azure OpenAI Model"

# Replace these with real values
custom_model = ChatOpenAI(
    model="glm-4-plus",
    api_key="8a70345b54344f4a8b079ea0d.4xz6BnmSdbQbNJT7",
    base_url="https://open.bigmodel.cn/api/paas/v4/",
)
chatmodel = HzOpenAI(model=custom_model)

client = OpenAI(api_key="8a70345b54344f495c9ea0d.4xz6BnmSdbQbNJT7", base_url="https://open.bigmodel.cn/api/paas/v4/")


from typing import List

from deepeval.test_case import LLMTestCase
from deepeval.tracing import (
    observe,
    update_current_span,
)

def web_search(query: str) -> str:
    return "Fake search results for: " + query


def retrieve_documents(query: str) -> List[str]:
    return ["Document 1: Hardcoded text chunks from your vector DB"]


@observe(metrics=[AnswerRelevancyMetric(model=chatmodel)])
def generate_response(input: str) -> str:
    response = "Generated response based on the prompt: " + input

    update_current_span(
        test_case=LLMTestCase(input=input, actual_output=response)
    )
    return response


@observe(name="RAG Pipeline", metrics=[ContextualRelevancyMetric(model=chatmodel)])
def rag_pipeline(query: str) -> str:
    # Calls retriever and llm
    docs = retrieve_documents(query)
    context = "\n".join(docs)
    response = generate_response(f"Context: {context}\nQuery: {query}")

    update_current_span(
        test_case=LLMTestCase(input=query, actual_output=response, retrieval_context=docs)
    )
    return response


@observe(type="agent")
def research_agent(query: str) -> str:
    # Calls RAG pipeline
    initial_response = rag_pipeline(query)

    # Use web search tool on the results
    search_results = web_search(initial_response)

    # Generate final response incorporating both RAG and search results
    final_response = generate_response(
        f"Initial response: {initial_response}\n"
        f"Additional search results: {search_results}\n"
        f"Query: {query}"
    )
    return final_response

golden = Golden(input="What's the weather like in SF?")
# Run evaluation
evaluate(goldens=[golden], observed_callback=research_agent)
