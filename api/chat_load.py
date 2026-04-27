from helpers.api import ApiHandler, Input, Output, Request, Response


from helpers import persist_chat

class LoadChats(ApiHandler):
    async def process(self, input: Input, request: Request) -> Output:
        chats = input.get("chats", [])
        if not chats:
            raise Exception("No chats provided")

        # Associate imported chats with the current user
        from helpers.login import get_current_user_id
        user_id = get_current_user_id()
        ctxids = persist_chat.load_json_chats(chats, user_id=user_id)

        return {
            "message": "Chats loaded.",
            "ctxids": ctxids,
        }

