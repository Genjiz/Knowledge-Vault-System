from flask import jsonify


def success_response(data=None, message="操作成功"):
    return jsonify({
        'code': 200,
        'message': message,
        'data': data
    })


def error_response(message="操作失败", code=400):
    return jsonify({
        'code': code,
        'message': message,
        'data': None
    }), code


def paginated_response(items, total, page, per_page, message="操作成功"):
    return jsonify({
        'code': 200,
        'message': message,
        'data': {
            'items': items,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        }
    })
