from werkzeug.exceptions import HTTPException


class CustomBadRequestWithDetail(HTTPException):
    code = 400
    def __init__(self, detail=None):
        self.description = detail or "Wrong request"
        super().__init__()