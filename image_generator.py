from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import requests

def wrap_text(draw, text, x, y, max_width, font, line_height):
    words = text.split(' ')
    line = ''
    height = 0
    for word in words:
        test_line = line + word + ' '
        w, _ = draw.textsize(test_line, font=font)
        if w > max_width and line:
            draw.text((x, y + height), line.strip(), font=font, fill='black')
            line = word + ' '
            height += line_height
        else:
            line = test_line
    draw.text((x, y + height), line.strip(), font=font, fill='black')
    height += line_height
    return height

def generate_thread_image(thread):
    width = 1080  # Instagram-friendly width
    line_height = 24
    header_height = 80
    media_height = 200
    separator_height = 20
    font = ImageFont.load_default()  # Use default font; load custom if needed

    # First pass: Measure total height (rough estimate)
    total_height = 20  # Top margin
    for tweet in thread:
        text_lines = len(tweet['text'].split('\n')) * line_height + line_height
        total_height += header_height + text_lines + (media_height + 10 if tweet['media'] else 0) + separator_height
    total_height += 20  # Bottom margin

    # Create image
    img = Image.new('RGB', (width, total_height), color='white')
    draw = ImageDraw.Draw(img)

    y = 20  # Start y
    for tweet in thread:
        # Green border for each tweet section
        draw.rectangle([(10, y - 10), (width - 10, y + header_height + 100)], outline='green', width=2)

        # Avatar
        if tweet['avatar']:
            try:
                avatar_resp = requests.get(tweet['avatar'])
                avatar_img = Image.open(BytesIO(avatar_resp.content)).resize((60, 60))
                img.paste(avatar_img, (20, y))
            except Exception as e:
                print(f'Avatar load failed: {e}')

        # User and handle (green for theme)
        draw.text((90, y + 30), tweet['user'], font=font, fill='green')
        draw.text((90, y + 55), tweet['handle'], font=font, fill='gray')
        draw.text((400, y + 55), tweet['timestamp'], font=font, fill='gray')

        # Text (black, wrapped)
        text_height = wrap_text(draw, tweet['text'], 20, y + 80, width - 40, font, line_height)
        y += 80 + text_height

        # Media thumbnail (first one only)
        if tweet['media']:
            try:
                media_resp = requests.get(tweet['media'][0])
                media_img = Image.open(BytesIO(media_resp.content)).resize((300, media_height))
                img.paste(media_img, (20, y))
                y += media_height + 10
            except Exception as e:
                print(f'Media load failed: {e}')

        # Green separator line
        draw.line([(10, y + 10), (width - 10, y + 10)], fill='green', width=2)
        y += separator_height

    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer