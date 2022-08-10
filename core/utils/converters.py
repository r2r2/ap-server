import base64


async def string_to_bytes(data: str) -> bytes:
    """Encoding string to bytes"""
    img = data.encode('utf-8')
    base64_encoded_data = base64.b64encode(img)
    return base64_encoded_data
