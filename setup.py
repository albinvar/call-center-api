import os
import requests
import config
from bs4 import BeautifulSoup
from langchain_community.vectorstores import FAISS
from langchain_together import TogetherEmbeddings
from concurrent.futures import ThreadPoolExecutor

# # Set your Together API key
os.environ["TOGETHER_API_KEY"] = config.TOGETHER_API

# # Load the vector store from disk

# Show message to user
print("📚 Vectorizing Information")


#read the file
with open('base_prompt.txt', 'r', encoding='utf-8') as file:
    extracted_texts = file.readlines()

# # show the number of extracted texts
# print(f"📚 Loaded {len(extracted_texts)} texts from the file")

# Create a vector store from the extracted texts
vectorstore = FAISS.from_texts(
    extracted_texts,
    TogetherEmbeddings(model=config.FAISS_MODEL)
)

# Save the vector store to disk
vectorstore.save_local(config.FAISS_KNOWLEDGE_BASE)