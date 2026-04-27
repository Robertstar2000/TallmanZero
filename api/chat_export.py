from helpers.api import ApiHandler, Input, Output, Request, Response

from helpers import persist_chat
from agent import AgentContext

class ExportChat(ApiHandler):
    async def process(self, input: Input, request: Request) -> Output:
        ctxid = input.get("ctxid", "")
        if not ctxid:
            raise Exception("No context id provided")

        # Verify ownership before exporting
        from helpers.login import get_current_user_id
        user_id = get_current_user_id()
        context = AgentContext.get(ctxid, user_id=user_id)
        if not context:
            raise Exception("Chat not found or access denied")

        content = persist_chat.export_json_chat(context)
        return {
            "message": "Chats exported.",
            "ctxid": context.id,
            "content": content,
        }

