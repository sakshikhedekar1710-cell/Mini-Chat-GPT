import random
import time
from threading import Thread
import requests

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from chatbot.models import ChatHistory, ChatSession


session_not_existing = "Session does not exist"


def datetime_to_string(datetime_obj):
    return datetime_obj.strftime('%Y-%m-%d %H:%M:%S') if datetime_obj else ""


# ✅ OpenRouter AI function
def get_ai_response(question):
    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "mistralai/mistral-7b-instruct",
        "messages": [
            {"role": "system", "content": "You are a helpful AI assistant like ChatGPT."},
            {"role": "user", "content": question}
        ]
    }

    response = requests.post(url, headers=headers, json=payload)
    data = response.json()

    if "choices" in data:
        return data["choices"][0]["message"]["content"]
    else:
        return "Sorry, something went wrong."


def get_weighted_chunk_length(remaining_length):
    possible_lengths = list(range(1, remaining_length + 1))
    weights = [1 / length for length in possible_lengths]
    normalized_weights = [weight / sum(weights) for weight in weights]
    return random.choices(possible_lengths, weights=normalized_weights, k=1)[0]


def send_websocket_messages(session_id, chat_history_info, full_response):
    channel_layer = get_channel_layer()

    if channel_layer is not None:
        start = 0

        while start < len(full_response):
            remaining_length = len(full_response) - start
            chunk_length = get_weighted_chunk_length(remaining_length)

            start += chunk_length
            chunk = full_response[:start]

            async_to_sync(channel_layer.group_send)(
                f'chat_{session_id}',
                {
                    'type': 'chat_message',
                    'message': {
                        **chat_history_info,
                        "response": chunk
                    }
                }
            )

            time.sleep(0.05)
    else:
        print("Channel layer is not configured properly.")


class CreateChatMessageView(APIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JWTAuthentication,)

    def post(self, request, *args, **kwargs):
        user = request.user
        question = request.data.get('question')
        session_id = request.data.get('session_id')
        is_first_question = False

        if not question:
            return Response({"status": "error", "response": "Question is required"}, status=400)

        session = None

        # Existing session
        if session_id:
            try:
                session = ChatSession.objects.get(id=session_id, user=user)
            except ObjectDoesNotExist:
                return Response({'status': 'error', "response": session_not_existing}, status=400)

        # New session
        else:
            session = ChatSession.objects.create(user=user, name=question[:50])
            session_id = session.id
            is_first_question = True

        # 🔥 Get AI response
        response_text = get_ai_response(question)

        # Save chat history
        chat_history = ChatHistory.objects.create(
            session_id=session_id,
            question=question,
            response=response_text
        )

        chat_history_info = {
            "id": chat_history.id,
            "session_id": session_id,
            "question": question,
            "response": response_text,
            "created_on": datetime_to_string(chat_history.created_on),
            "updated_on": datetime_to_string(chat_history.updated_on),
        }

        if is_first_question:
            chat_history_info["session"] = {
                "id": session.id,
                "user_id": session.user.id,
                "name": session.name,
                "created_on": datetime_to_string(session.created_on),
                "updated_on": datetime_to_string(session.updated_on)
            }

        # Start WebSocket streaming
        thread = Thread(
            target=send_websocket_messages,
            args=(session_id, chat_history_info, response_text)
        )
        thread.daemon = True
        thread.start()

        return JsonResponse({'status': 'success', "data": chat_history_info}, safe=False)


class GetChatSessionsView(APIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JWTAuthentication,)

    def get(self, request, *args, **kwargs):
        user = request.user
        chat_sessions = list(ChatSession.objects.filter(user=user).values())
        return JsonResponse({'status': 'success', "data": chat_sessions}, safe=False)


class ManageChatSessionView(APIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JWTAuthentication,)

    def get(self, request, *args, **kwargs):
        user = request.user
        session_id = kwargs.get('session_id')

        try:
            chat_session = ChatSession.objects.get(id=session_id, user=user)
            chat_history = list(ChatHistory.objects.filter(session_id=session_id).values())

            resp_data = {
                "name": chat_session.name,
                "chat_history": chat_history
            }

            return JsonResponse({'status': 'success', "data": resp_data}, safe=False)

        except ObjectDoesNotExist:
            return Response({'status': 'error', "response": session_not_existing}, status=400)

    def delete(self, request, *args, **kwargs):
        user = request.user
        session_id = kwargs.get('session_id')

        try:
            chat_session = ChatSession.objects.get(id=session_id, user=user)
            chat_session.delete()
            return JsonResponse({'status': 'success', "response": "Session deleted successfully"}, safe=False)

        except ObjectDoesNotExist:
            return Response({'status': 'error', "response": session_not_existing}, status=400)

    def put(self, request, *args, **kwargs):
        user = request.user
        session_id = kwargs.get('session_id')
        name = request.data.get('name')

        try:
            chat_session = ChatSession.objects.get(id=session_id, user=user)
            chat_session.name = name
            chat_session.save()
            return JsonResponse({'status': 'success', "response": "Session updated successfully"}, safe=False)

        except ObjectDoesNotExist:
            return Response({'status': 'error', "response": session_not_existing}, status=400)
