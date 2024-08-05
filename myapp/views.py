from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from linebot import LineBotApi, WebhookParser, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextMessage
from linebot.models import TextSendMessage
from langchain.chat_models import ChatOpenAI
from langchain.document_loaders import TextLoader
from langchain.document_loaders import PyPDFLoader
from langchain.document_loaders import Docx2txtLoader
from langchain.document_loaders import CSVLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.chains import ConversationalRetrievalChain
import openai, os
from dotenv import load_dotenv, find_dotenv

_ = load_dotenv(find_dotenv())


openai.api_key = os.getenv("OPENAI_API_KEY")
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
parser = WebhookParser(os.getenv("LINE_CHANNEL_SECRET"))

	
chat_language = os.getenv("INIT_LANGUAGE", default = "zh")
	

	
conversation = []
documents =[]
for file in os.listdir("Docs"):
    if file.endswith(".pdf"):
        pdf_path = "./Docs/" + file
        loader = PyPDFLoader(pdf_path)
        documents.extend(loader.load())
    elif file.endswith('.docx') or file.endswith('.doc'):
        doc_path = "./Docs/" + file
        loader = Docx2txtLoader(doc_path)
        documents.extend(loader.load())
    elif file.endswith('.txt'):
        text_path = "./Docs/" + file
        loader = TextLoader(text_path, encoding ="utf-8") #在這裡加上encoding參數否則python會報錯 目前只有txt有這個問題
        documents.extend(loader.load())


text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000 , chunk_overlap=10)
documents = text_splitter.split_documents(documents)
vectordb = Chroma.from_documents(documents, embedding=OpenAIEmbeddings())
#create the index in retriever interface
retriever = vectordb.as_retriever(search_type="similarity",search_kwargs={"k":3})




qa = ConversationalRetrievalChain.from_llm(ChatOpenAI(temperature=0.5), retriever=retriever , verbose=False , chain_type="stuff")
chat_history= []

@csrf_exempt
def callback(request):
    if request.method == 'POST':
        signature = request.META['HTTP_X_LINE_SIGNATURE']
        body = request.body.decode('utf-8')
        try:
            events = parser.parse(body, signature)
        except InvalidSignatureError:
            return HttpResponseForbidden()
        except LineBotApiError:
            return HttpResponseBadRequest()

        for event in events:
            if isinstance(event, MessageEvent):
                if isinstance(event.message, TextMessage):
            ##############
                    user_message = event.message.text

                    result = qa({"question": user_message + '(用繁體中文回答)', "chat_history": chat_history})
                    #reply_msg = chatgpt.get_response(user_message).replace("AI:", "", 1)
                    reply_msg = result['answer'].replace("AI:","",1)

                    chat_history.append((user_message, result['answer']))
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=reply_msg)
                        )
            ##########################

                     
                                              
                
        return HttpResponse()

    else:
        return HttpResponseBadRequest()


