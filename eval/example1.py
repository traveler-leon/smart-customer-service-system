import os
os.environ["DEEPEVAL_RESULTS_FOLDER"] = "eval/data"

from typing import List
from openai import OpenAI
from langchain_openai import ChatOpenAI
from deepeval.models.base_model import DeepEvalBaseLLM
from deepeval.dataset import Golden
from deepeval.test_case import LLMTestCase
from deepeval.metrics import AnswerRelevancyMetric
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
    api_key="8a70345b54344f4a8b07659e95c9ea0d.4xz6BnmSdbQbNJT7",
    base_url="https://open.bigmodel.cn/api/paas/v4/",
)
chatmodel = HzOpenAI(model=custom_model)

client = OpenAI(api_key="8a70345b54344f4a8b07659e95c9ea0d.4xz6BnmSdbQbNJT7", base_url="https://open.bigmodel.cn/api/paas/v4/")

@observe(name="all pipeline")
def your_llm_app(input: str):
    def retriever(input: str):
        return ["Hardcoded text chunks from your vector database"]
    
    @observe(name="generator", metrics=[AnswerRelevancyMetric(model=chatmodel)])
    def generator(input: str, retrieved_chunks: List[str]):
        res = client.chat.completions.create(
            model="glm-4-plus",
            messages=[
                {"role": "system", "content": "Use the provided context to answer the question."},
                {"role": "user", "content": "\n\n".join(retrieved_chunks) + "\n\nQuestion: " + input}
            ]
        ).choices[0].message.content
        update_current_span(
            test_case=LLMTestCase(input=input, actual_output=res)
        )
        return res

    retrieval_context = retriever(input)
    return generator(input, retrieval_context), retrieval_context


print(your_llm_app("How are you?"))





goldens = [Golden(input="How are you?")]


# Create test cases from goldens
# test_cases = []
# for golden in goldens:
#     res, text_chunks = your_llm_app(golden.input)
#     test_case = LLMTestCase(input=golden.input, actual_output=res, retrieval_context=text_chunks)
#     test_cases.append(test_case)


# # Evaluate end-to-end
# evaluate(test_cases=test_cases, metrics=[AnswerRelevancyMetric(model=chatmodel)])

evaluate(goldens=goldens, observed_callback=your_llm_app)