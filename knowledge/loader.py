from langchain.text_splitter import CharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_community.embeddings.sentence_transformer import SentenceTransformerEmbeddings
from langchain_openai import OpenAIEmbeddings

FILEPATH = "./7-chinese/7-chinese.txt"
def load_and_process_documents(filepath):
    # Load the document
    loader = TextLoader(filepath, encoding='utf-8')
    documents = loader.load()

    # Split the document into chunks
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    docs = text_splitter.split_documents(documents)
 
    # Create the embedding function
    embeddings = OpenAIEmbeddings()
    return docs, embeddings

if __name__ == "__main__":
    # If you want to test loading and processing separately
    docs, embeddings = load_and_process_documents(FILEPATH)
    print("Documents loaded and processed.")