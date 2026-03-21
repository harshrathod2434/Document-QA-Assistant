"""
Multimodal processing module: sends images to OpenAI GPT-4o-mini Vision
for detailed textual descriptions of diagrams, charts, and images.
"""

import base64
import io
import time
from typing import Dict, List

from openai import OpenAI

from config import OPENAI_API_KEY, OPENAI_VISION_MODEL, IMAGE_DESCRIPTION_PROMPT


def get_openai_client() -> OpenAI:
    """Create and return an OpenAI client."""
    if not OPENAI_API_KEY or OPENAI_API_KEY == "your_openai_api_key_here":
        raise ValueError(
            "OPENAI_API_KEY is not set. Please add your API key in Streamlit Secrets."
        )
    return OpenAI(api_key=OPENAI_API_KEY)


def describe_image(image_data: bytes, ext: str = "png", label: str = "") -> str:
    """
    Send an image to OpenAI Vision and return a detailed textual description.

    Args:
        image_data: Raw image bytes
        ext: Image file extension (png, jpg, etc.)
        label: Optional label for context

    Returns:
        Detailed text description of the image
    """
    try:
        client = get_openai_client()

        # Encode image to base64
        b64_image = base64.b64encode(image_data).decode("utf-8")

        # Map extensions to MIME types
        mime_map = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "gif": "image/gif", "webp": "image/webp"}
        mime_type = mime_map.get(ext.lower(), "image/png")

        # Build the prompt
        prompt = IMAGE_DESCRIPTION_PROMPT
        if label:
            prompt = f"Context: {label}\n\n{prompt}"

        response = client.chat.completions.create(
            model=OPENAI_VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{b64_image}",
                                "detail": "low",  # Use low detail to save costs
                            },
                        },
                    ],
                }
            ],
            max_tokens=512,
            temperature=0.3,
        )

        if response.choices and response.choices[0].message.content:
            return response.choices[0].message.content.strip()
        else:
            return f"[Could not generate description for image: {label}]"

    except Exception as e:
        return f"[Error describing image '{label}': {str(e)}]"


def process_images(images: List[Dict], rate_limit_delay: float = 0.5) -> List[str]:
    """
    Process a batch of images through OpenAI Vision.

    Args:
        images: List of image dicts with 'data', 'ext', 'label' keys
        rate_limit_delay: Seconds to wait between API calls

    Returns:
        List of text descriptions, one per image
    """
    descriptions = []

    for i, img in enumerate(images):
        description = describe_image(
            image_data=img["data"],
            ext=img.get("ext", "png"),
            label=img.get("label", f"Image {i + 1}"),
        )
        descriptions.append(description)

        # Rate limiting
        if i < len(images) - 1:
            time.sleep(rate_limit_delay)

    return descriptions
