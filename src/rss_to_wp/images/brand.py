"""A factual-neutral featured graphic when a feed supplies no usable image."""

from io import BytesIO

from PIL import Image, ImageDraw, ImageFont


def create_brand_image():
    image = Image.new("RGB", (1200, 630), "#10283f")
    draw = ImageDraw.Draw(image)
    draw.rectangle((64, 90, 72, 500), fill="#e6ae53")
    draw.line((112, 135, 1090, 135), fill="#4e6478", width=2)
    font = ImageFont.load_default(size=72)
    small = ImageFont.load_default(size=30)
    draw.text((110, 225), "DeSoto County", fill="white", font=font)
    draw.text((110, 310), "NEWS", fill="#e6ae53", font=font)
    draw.text((112, 455), "DESOTOCOUNTYNEWS.COM", fill="white", font=small)
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue(), "desoto-county-news.png", "image/png"
