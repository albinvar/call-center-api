import os
import config
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.vectorstores import FAISS
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_together import ChatTogether, TogetherEmbeddings

# Set your Together API key
os.environ["TOGETHER_API_KEY"] = config.TOGETHER_API

# Load the vector store from disk
vectorstore = FAISS.load_local(config.FAISS_KNOWLEDGE_BASE, TogetherEmbeddings(model=config.FAISS_MODEL), allow_dangerous_deserialization=True)

# Retrieve documents from the vector store
retriever = vectorstore.as_retriever()

# Initialize the Together model
model = ChatTogether(
    model=config.TOGETHER_MODEL,
    temperature=config.TOGETHER_TEMPERATURE,
    max_tokens=config.TOGETHER_MAX_TOKENS,
)

#create chain
def create_chain(type):
    prompt_template = config.prompts.get(type, config.prompts["default"])
    prompt = ChatPromptTemplate.from_template(prompt_template)

    chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | model.bind(stop=["assistant"])
        | StrOutputParser()
    )
    return chain

# Function to handle user queries
def handle_query(query, chat_history, type="default"):
    chat_history.append({"role": "user", "content": query})
    chain = create_chain(type)
    output = chain.invoke({"history": chat_history})
    chat_history.append({"role": "assistant", "content": output})
    return output, chat_history

# Example usage
if __name__ == "__main__":
    chat_history = []
    while True:
        input_query = input("\n\nYou: ")
        output, chat_history = handle_query(input_query, chat_history)
        print("\n\nAssistant: ", output)