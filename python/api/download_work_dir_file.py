"""
TallmanZero - File Download API
Serves files from inside the Docker container to the user's browser for download.
Maps to GET /download_work_dir_file?path=<container-path>
"""
import os
import mimetypes
from flask import send_file, Request, Response
from python.helpers.api import ApiHandler
from python.helpers.file_browser import FileBrowser
from python.helpers.print_style import PrintStyle


class DownloadWorkDirFile(ApiHandler):

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET"]

    @classmethod
    def requires_csrf(cls) -> bool:
        return False  # GET requests don't need CSRF tokens

    async def process(self, input: dict, request: Request) -> dict | Response:
        file_path = request.args.get("path", "").strip()
        if not file_path:
            return Response("Missing 'path' parameter", status=400, mimetype="text/plain")

        try:
            browser = FileBrowser()
            full_path = browser.get_full_path(file_path, allow_dir=False)
        except ValueError as e:
            PrintStyle.error(f"File download error: {e}")
            return Response(str(e), status=404, mimetype="text/plain")
        except Exception as e:
            PrintStyle.error(f"File download error: {e}")
            return Response("Error locating file", status=500, mimetype="text/plain")

        if not os.path.isfile(full_path):
            return Response("Path is not a file", status=400, mimetype="text/plain")

        # Determine mime type
        mime_type, _ = mimetypes.guess_type(full_path)
        if not mime_type:
            mime_type = "application/octet-stream"

        filename = os.path.basename(full_path)

        try:
            return send_file(
                full_path,
                mimetype=mime_type,
                as_attachment=True,
                download_name=filename,
            )
        except Exception as e:
            PrintStyle.error(f"File send error: {e}")
            return Response("Error sending file", status=500, mimetype="text/plain")
