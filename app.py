import json
import os
import sys
import random
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from operator import itemgetter

from openai import AsyncOpenAI
from openai.types.beta import Thread
from openai.types.beta.threads import (
    MessageContentImageFile,
    MessageContentText,
    ThreadMessage,
)
from openai.types.beta.threads.runs import RunStep
from openai.types.beta.threads.runs.tool_calls_step_details import ToolCall

from google.cloud import vision

from chainlit.element import Element
from chainlit.types import ThreadDict
import chainlit as cl

from chromadb.config import Settings
from langchain_community.vectorstores import Chroma, OpenSearchVectorSearch
from langchain_community.document_loaders import DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import StrOutputParser
from langchain.schema.runnable import Runnable, RunnablePassthrough, RunnableLambda
from langchain.schema.runnable.config import RunnableConfig
from langchain.chains import LLMChain, RetrievalQA
from langchain.memory import ConversationBufferMemory, ChatMessageHistory
from langchain_community.embeddings import GPT4AllEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_community.embeddings.sentence_transformer import (
    SentenceTransformerEmbeddings,
)

# from knowledge.knowledge import MyKnowledgeBase, DOCUMENT_SOURCE_DIRECTORY
# db = MyKnowledgeBase(pdf_source_folder_path=DOCUMENT_SOURCE_DIRECTORY)
from knowledge.loader import load_and_process_documents

# Set up the OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
client = AsyncOpenAI(api_key=api_key)

# Define allowed MIME types
allowed_mime = [
    "image/jpeg",
    "image/png",
    "image/jpg",
    "text/plain",
]

# Check if the files uploaded are allowed
async def check_files(files: List[Element]):
    for file in files:
        if file.mime not in allowed_mime:
            return False
    return True

async def process_tool_call(
    step_references: Dict[str, cl.Step],
    step: RunStep,
    tool_call: ToolCall,
    name: str,
    input: Any,
    output: Any,
    show_input: str = None,
):
    cl_step = None
    update = False
    if not tool_call.id in step_references:
        cl_step = cl.Step(
            name=name,
            type="tool",
            parent_id=cl.context.current_step.id,
            show_input=show_input,
        )
        step_references[tool_call.id] = cl_step
    else:
        update = True
        cl_step = step_references[tool_call.id]

    if step.created_at:
        cl_step.start = datetime.fromtimestamp(step.created_at).isoformat()
    if step.completed_at:
        cl_step.end = datetime.fromtimestamp(step.completed_at).isoformat()
    cl_step.input = input
    cl_step.output = output

    if update:
        await cl_step.update()
    else:
        await cl_step.send()

class DictToObject:
    def __init__(self, dictionary):
        for key, value in dictionary.items():
            if isinstance(value, dict):
                setattr(self, key, DictToObject(value))
            else:
                setattr(self, key, value)

    def __str__(self):
        return "\n".join(f"{key}: {value}" for key, value in self.__dict__.items())

# Resume conversation
def setup_runnable():
    memory = cl.user_session.get("memory")  # type: ConversationBufferMemory
    model = ChatOpenAI(api_key=api_key, streaming=True, model_name="gpt-4")
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是一個專門為台灣中小學生解答各學科問題的AI。請通過引導性的問答來激發學生的思考，鼓勵他們自己找到答案，絕對不要直接給出答案，且回答需符合資料內容，但不要透漏有引用來源，也不能用[從你提供的資料來看]、[從您的說明中]等字句。請用繁體中文及全形標點號回答問題，保持友善支持的態度，適時加上表情符號來強調重點或情感。條列式請用阿拉伯數字或[-]符號，且標題結尾不要加其他標點符號。你的目標是刺激學生的好奇心、批判性思維和對科學主題的深入理解。"
            ),
            ("human", "{question}"),
        ]
    )

    runnable = (
        RunnablePassthrough.assign(
            history=RunnableLambda(memory.load_memory_variables) | itemgetter("history")
        )
        | prompt
        | model
        | StrOutputParser()
    )
    cl.user_session.set("runnable", runnable)

def extract_tasks(ai_response):
    # Pattern to match numbered (e.g., "1. Task") and bulleted (e.g., "- Task") list items
    pattern = r'^\s*(?:\d+\.\s*|-)\s*(.*)'
    # Extract matching tasks using the regular expression
    return re.findall(pattern, ai_response, re.MULTILINE)

# Start the Chainlit client
@cl.on_chat_start
async def on_chat_start():
    await cl.Avatar(
        name="BrainMate",
        path = "./public/avatar.png"
    ).send()

    cl.user_session.set("memory", ConversationBufferMemory(return_messages=True))
    setup_runnable()
    
    # Grade selection buttons
    start_action = [
        cl.Action(name="start", value="pass", label="直接開始"),
        cl.Action(name="start", value="select", label="選擇年級"),
        cl.Action(name="start", value="upload", label="閱讀PDF"),
        cl.Action(name="start", value="tasks", label="任務清單"),
    ]
    await cl.Message(content="👋 嗨！我是你的學習小助手BrainMate！\n你可以直接開始提問，或是選擇需要的服務，這有助於我提供更完整的答覆😊", actions=start_action).send()

@cl.action_callback("start")
async def on_passed(action):
    start = action.value
    cl.user_session.set("start", start)
    if start == "pass":
        await cl.Message(content=f"沒問題！可以直接拖曳圖片上傳哦~").send()

    elif start == "upload":
        files = None
        while files is None:
            files = await cl.AskFileMessage(
                content="請先上傳你要閱讀的PDF檔案😸",
                accept=["text/plain", "application/pdf"],
                max_size_mb=20,
                timeout=180,
            ).send()
        file = files[0]
        with open(file.path, "rb") as f:
            pdf_content = f.read()
            pdf_el = cl.Pdf(name="PDF閱讀器", display="side", content=pdf_content)
            await cl.Message(content="點擊連結即可開啟PDF閱讀器", elements=[pdf_el]).send()

    elif start == "tasks":
        await cl.Message(content="你今天想做什麼呢？歡迎和我討論哦！").send()

    else:
        grade_actions = [
            cl.Action(name="select_grade", value=f"{i}年級", label=f"{i}年級") for i in range(5, 10)
        ]        
        await cl.Message(content=f"你是幾年級的學生呢？", actions=grade_actions).send()

@cl.action_callback("select_grade")
async def on_select_grade(action):
    grade = action.value
    cl.user_session.set("selected_grade", grade[0])

    subject_actions = [
        cl.Action(name="select_subject", value="math", label="數學"),
        cl.Action(name="select_subject", value="chinese", label="國文"),
        cl.Action(name="select_subject", value="english", label="英語"),
        cl.Action(name="select_subject", value="science", label="自然"),
        cl.Action(name="select_subject", value="social", label="社會"),
    ]
    # print(subject_actions[0].value)
    await cl.Message(content=f"你想學習{grade}的哪個科目呢？", actions=subject_actions).send()

# Callback for subject selection
@cl.action_callback("select_subject")
async def on_select_subject(action):
    cl.user_session.set("selected_subject", action.value) 
    await cl.Message(content=f"沒問題，開始提問吧！可以直接拖曳檔案上傳哦~").send()


@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict):
    await cl.Avatar(
        name="BrainMate",
        path = "./public/avatar.png"
    ).send()
    
    memory = ConversationBufferMemory(return_messages=True)
    root_messages = [m for m in thread["steps"] if m["parentId"] == None]
    for message in root_messages:
        if message["type"] == "USER_MESSAGE":
            memory.chat_memory.add_user_message(message["output"])
        else:
            memory.chat_memory.add_ai_message(message["output"])

    cl.user_session.set("memory", memory)
    setup_runnable()

@cl.on_message
async def on_message(message: cl.Message):
    
    start = cl.user_session.get("start")
    
    memory = cl.user_session.get("memory")
    runnable = cl.user_session.get("runnable")

    grade = cl.user_session.get("selected_grade")
    subject = cl.user_session.get("selected_subject")

    memory_variables = memory.load_memory_variables({})
    conversation_history = memory_variables.get('history', [])
    conversation_history_str_list = [msg.content for msg in conversation_history if hasattr(msg, 'content')]
    conversation_history_str = "\n".join(conversation_history_str_list)
    all_messages = conversation_history_str + " " + message.content

    #response = cl.Message(content="正在處理您的問題⏳，請稍候...\n\n")
    #await response.send()

    if message.elements:
        files = [file for file in message.elements if file.mime in allowed_mime]

        if not files:
            await cl.Message(content="No files of allowed type attached or file(s) not provided.").send()
            return

        for file in files:
            if file.mime in ["image/jpeg", "image/png", "image/jpg"]:
                client = vision.ImageAnnotatorClient()
                with open(file.path, "rb") as image_file:
                    content = image_file.read()
                image = vision.Image(content=content)
                # print('path' + file.path)
                ocr = client.text_detection(image=image)
                texts = ocr.text_annotations
                print(texts)
                if texts:
                    all_messages += " " + texts[0].description

    print(all_messages)

    if start == "tasks":

        res = cl.Message(content="")
        async for chunk in runnable.astream(
            {"question": all_messages},
            config=RunnableConfig(callbacks=[cl.LangchainCallbackHandler()]),
        ):
            await res.stream_token(chunk)
        await res.update()

        tasks_to_add = extract_tasks(res.content)
        # print(tasks_to_add)
        task_list = cl.TaskList()
        task_list.status = "Running..."
        for task_description in tasks_to_add:
            task = cl.Task(title=task_description, status=cl.TaskStatus.READY)
            await task_list.add_task(task)
            await task_list.send()

            message_id = await cl.Message(content=task_description).send()
            ans = cl.Message(content="")
            async for chunk in runnable.astream(
                {"question": task_description},
                config=RunnableConfig(callbacks=[cl.LangchainCallbackHandler()]),
            ):
                await ans.stream_token(chunk)
            await ans.send()

            task.forId = message_id
            task.status = cl.TaskStatus.DONE
            await task_list.send()

    else:

        if start == "select":
            doc_path = f"./knowledge/{grade}-{subject}/{grade}-{subject}.txt"
            docs, embeddings = load_and_process_documents(doc_path)
            db = Chroma.from_documents(docs, embeddings)
            docs = db.similarity_search(all_messages)
            if(docs):
                print("search_results: " + docs[0].page_content)    
                all_messages += docs[0].page_content

        response = cl.Message(content="")
        async for chunk in runnable.astream(
            {"question": all_messages},
            config=RunnableConfig(callbacks=[cl.LangchainCallbackHandler()]),
        ):
            await response.stream_token(chunk)
        await response.send()
        # print(response.content)

        memory.chat_memory.add_user_message(all_messages)
        memory.chat_memory.add_ai_message(response.content)
        memory.load_memory_variables({})


    '''
    loading_messages = [
        "正在處理您的問題⏳，請稍候...",
        "讓我想想...🤔"
    ]
    random_loading_message = random.choice(loading_messages)
    msg = cl.Message(content=random_loading_message)
    await msg.send()
    '''

#Authentication
@cl.password_auth_callback
def auth_callback(username: str, password: str):
    valid_users = {
        "gov": "2024",
        "winnie": "1122",
    }
    if username in valid_users and valid_users[username] == password:
        return cl.User(
            identifier=username, metadata={"role": "user", "provider": "credentials"}
        )
    # You can add more specific roles or metadata based on your application's needs
    elif username == "admin" and password == "admin":
        return cl.User(
            identifier="admin", metadata={"role": "admin", "provider": "credentials"}
        )
    else:
        return None