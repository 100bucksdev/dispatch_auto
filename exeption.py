from werkzeug.exceptions import HTTPException


class CustomBadRequestWithDetail(Exception):
    def __init__(self, detail: str = None):
        self.detail = detail or "Wrong request"
        super().__init__(self.detail)