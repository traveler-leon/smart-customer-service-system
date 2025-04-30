

agent_id = "c9aec7d023d411f09e71b6cb1ace2182"
ragflow_key = "ragflow-gyMDY3NDQwMTUwYzExZjA5MmMwYTJmMT"

from ragflow_sdk import RAGFlow, Agent

rag_object = RAGFlow(api_key=ragflow_key, base_url="http://192.168.0.200:9380")
agent = rag_object.list_agents(id = agent_id)[0]
session = agent.create_session()    

print("\n===== Miss R ====\n")
print("Hello. What can I do for you?")

while True:
    question = input("\n===== User ====\n> ")
    print("\n==== Miss R ====\n")
    
    cont = ""
    for ans in session.ask(question, stream=True):
        print(ans.content[len(cont):], end='', flush=True)
        cont = ans.content






