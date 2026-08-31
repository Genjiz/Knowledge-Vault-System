"""统一业务异常与全局错误处理器。"""
from flask import jsonify
from werkzeug.exceptions import HTTPException


class AppError(Exception):
    """业务异常：路由或服务层主动抛出，由全局处理器转成统一 JSON 响应。"""

    def __init__(self, message="操作失败", code=400):
        super().__init__(message)
        self.message = message
        self.code = code


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(e):
        return jsonify({"code": e.code, "message": e.message, "data": None}), e.code

    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        return jsonify({"code": e.code, "message": e.description, "data": None}), e.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(e):
        app.logger.exception("未处理的异常")
        return jsonify({"code": 500, "message": "服务器内部错误", "data": None}), 500
