import asyncio
import json

import openai
from cachetools import TTLCache

from app.config import get_settings
from app.core.exceptions import ClassificationError
from app.core.logger import logger
from app.models.schemas import MerchantCategory

settings = get_settings()


class MerchantClassifier:
    def __init__(self):
        self.client = openai.Client(api_key=settings.OPENAI_API_KEY)
        self.cache = TTLCache(
            maxsize=settings.CACHE_MAX_SIZE,
            ttl=settings.CACHE_TTL
        )

    async def classify_merchant(self, merchant_name: str) -> MerchantCategory:
        cache_key = merchant_name.lower()

        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            response = await self._get_classification(merchant_name)
            result = self._parse_response(response)
            self.cache[cache_key] = result
            return result

        except Exception as e:
            logger.error(f"Classification failed for {merchant_name}: {str(e)}")
            raise ClassificationError(f"Failed to classify merchant: {str(e)}")

    async def _get_classification(self, merchant_name: str) -> str:
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": self._get_classification_prompt()
                    },
                    {
                        "role": "user",
                        "content": f"Classify this merchant: {merchant_name}"
                    }
                ],
                temperature=0.1
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"OpenAI API call failed: {str(e)}")
            raise ClassificationError(f"OpenAI API error: {str(e)}")

    def _parse_response(self, response: str) -> MerchantCategory:
        try:
            data = json.loads(response)
            return MerchantCategory(**data)
        except Exception as e:
            logger.error(f"Failed to parse classification response: {str(e)}")
            raise ClassificationError(f"Invalid classification format: {str(e)}")

    def _get_classification_prompt(self) -> str:
        return """
        You are a merchant classification expert. Analyze the merchant name and classify it into the most appropriate category.

        Primary categories:
        - Food & Dining (restaurants or groceries)
        - Shopping & Retail (clothing, electronics, etc.)
        - Transportation (gas, public transit, etc.)
        - Entertainment (movies, events, etc.)
        - Travel & Accommodation (hotels, flights, etc.)
        - Services (utilities, insurance, etc.)
        - Health & Wellness (medical, fitness, etc.)
        - Education (tuition, books, etc.)
        - Home & Hardware (furniture, repairs, etc.)
        - Financial Services (banking, investments, etc.)
        - Other
        
        Cafes and other food establishments should as either Groceries or Restaurants.
        Pricesmart should be classified as "Groceries".
        HI-LO should be classified as "Groceries".
        DIGP should be classified as "Utilities".
        NWCJ should be classified as "Utilities"
        FONTANA -WATERLOO SQUARE should be classified as "Pharmacy".
        JOHN R WONG SUPERMARKET should be classified as "Restaurants".

        Respond in JSON format:
        {
            "primary_category": "string",
            "subcategory": "string",
            "confidence": float,
            "description": "string"
        }
        """
