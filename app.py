import json
import os
import sys
import random
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI
from openai.types.beta import Thread
from openai.types.beta.threads import (
    MessageContentImageFile,
    MessageContentText,
    ThreadMessage,
)

from openai.types.beta.threads.runs import RunStep
from openai.types.beta.threads.runs.tool_calls_step_details import ToolCall

from chainlit.element import Element
import chainlit as cl

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser
from langchain.schema.runnable import Runnable
from langchain.schema.runnable.config import RunnableConfig
from langchain.chains import LLMChain

from google.cloud import vision

# Set up the OpenAI client
api_key = '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'
client = AsyncOpenAI(api_key=api_key)

# Define allowed MIME types
allowed_mime = [
    "application/pdf",
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

# Start the Chainlit client
@cl.on_chat_start
async def on_chat_start():
    await cl.Avatar(
        name="BrainMate",
        path = "./public/avatar.png"
    ).send()

    model = ChatOpenAI(api_key='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', streaming=True, model_name="gpt-4")
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是一個專門為台灣的國中生解答自然科學問題的AI。你的主要方法是通過引導性的問答來激發學生的思考，而不是直接給出答案。你的回答應該引導學生思考，鼓勵他們自己找到答案，並且讓回答符合上傳檔案中的知識。請用繁體中文及全形標點號回答問題，若條列式或表格能幫助理解也可以適時使用。保持友善支持的態度，適當使用表情符號來強調重點或情感。你的目標是刺激學生的好奇心、批判性思維和對科學主題的深入理解。"
            ),
            ("human", "{question}"),
        ]
    )
    chain = LLMChain(llm=model, prompt=prompt, output_parser=StrOutputParser())
    cl.user_session.set("chain", chain)

    # Grade selection buttons
    grade_actions = [
        cl.Action(name="select_grade", value=f"{i}年級", label=f"{i}年級") for i in range(1, 7)
    ]
    await cl.Message(content="👋 嗨！我是你的學習小助手BrainMate！\n提問前請先選擇你的年級，這有助於我提供更完整的答覆😊", actions=grade_actions).send()

@cl.action_callback("select_grade")
async def on_select_grade(action):
    grade = action.value
    # After selecting a grade, show subjects
    subject_actions = [
        cl.Action(name="select_subject", value="math", label="數學"),
        cl.Action(name="select_subject", value="chinese", label="國文"),
        cl.Action(name="select_subject", value="science", label="自然"),
        cl.Action(name="select_subject", value="social", label="社會"),
    ]
    await cl.Message(content=f"你想學習{grade}的哪個科目呢？", actions=subject_actions).send()

# Callback for subject selection
@cl.action_callback("select_subject")
async def on_select_subject(action):
    subject = action.value
    # Handle subject selection here
    await cl.Message(content=f"沒問題，開始提問吧！可以直接拖曳圖片上傳哦~").send()


@cl.on_message
async def on_message(message: cl.Message):
    all_messages = message.content
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
                response = client.text_detection(image=image)
                texts = response.text_annotations
                print(texts)
                if texts:
                    all_messages += " " + texts[0].description
                    print(all_messages)
        

    # Assuming this is an instance of LLMChain
    chain = cl.user_session.get("chain") 
    if not chain:
        await cl.Message(content="⚠️ 系統尚未初始化，請稍後再試。").send()
        return

    # Select a random message from the list
    loading_messages = [
        "正在處理您的問題⏳，請稍候...",
        "讓我想想...🤔"
    ]
    random_loading_message = random.choice(loading_messages)
    msg = cl.Message(content=random_loading_message)
    await msg.send()

    # Process the text request
    print("訊息：" + all_messages)
    response = await chain.arun(question=all_messages)

    # Update the message content after processing
    if response:
        msg.content = response
    else:
        msg.content = "很抱歉，我無法處理您的問題。請再試一次。"

    await msg.update()


#Authentication
@cl.password_auth_callback
def auth_callback(username: str, password: str):
    # Fetch the user matching username from your database
    # and compare the hashed password with the value stored in the database
    if (username, password) == ("admin", "admin"):
        return cl.User(
            identifier="admin", metadata={"role": "admin", "provider": "credentials"}
        )
    else:
        return None