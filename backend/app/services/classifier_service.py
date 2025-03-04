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
        You are a merchant classification expert with detailed knowledge of business categories across multiple industries. Your task is to analyze merchant names and classify them into the most appropriate category and subcategory with high accuracy.

        ## PRIMARY CATEGORIES AND SUBCATEGORIES
        
        1. Food & Dining
           - Restaurants (sit-down, fast food, takeout)
           - Cafes & Bakeries
           - Groceries & Supermarkets
           - Specialty Food Stores
           - Delivery Services
        
        2. Shopping & Retail
           - Clothing & Apparel
           - Electronics & Technology
           - Department Stores
           - Online Retailers
           - Specialty Retail
           - Convenience Stores
        
        3. Transportation
           - Gas Stations & Fuel
           - Public Transit
           - Ride Services & Taxis
           - Auto Repair & Maintenance
           - Parking
        
        4. Entertainment
           - Movies & Theaters
           - Events & Venues
           - Gaming & Recreation
           - Streaming Services
           - Arts & Culture
        
        5. Travel & Accommodation
           - Hotels & Lodging
           - Airlines & Flights
           - Car Rentals
           - Travel Agencies
           - Cruises & Tours
        
        6. Services
           - Utilities (Water, Electricity, Internet)
           - Professional Services
           - Subscription Services
           - Home Services
           - Personal Care Services
        
        7. Health & Wellness
           - Medical Services
           - Pharmacies
           - Fitness & Gyms
           - Mental Health Services
           - Health Insurance
        
        8. Education
           - Tuition & Schools
           - Books & Learning Materials
           - Online Courses
           - Educational Services
           - Student Services
        
        9. Home & Hardware
           - Furniture & Home Decor
           - Hardware & Tools
           - Home Improvement
           - Garden & Outdoor
           - Appliances
        
        10. Financial Services
            - Banking
            - Investments
            - Insurance
            - Credit Services
            - Money Transfer
        
        11. Other
            - Government & Public Services
            - Non-Profit & Charity
            - Membership Organizations
            - Uncategorized
        
        ## SPECIAL CLASSIFICATION RULES
        
        - Cafes serving primarily beverages should be classified as "Food & Dining" > "Cafes & Bakeries"
        - Cafes serving full meals should be classified as "Food & Dining" > "Restaurants"
        - Wholesale clubs (like Pricesmart) should be classified as "Food & Dining" > "Groceries & Supermarkets"
        - HI-LO should be classified as "Food & Dining" > "Groceries & Supermarkets"
        - DIGP and NWCJ should be classified as "Services" > "Utilities"
        - FONTANA -WATERLOO SQUARE should be classified as "Health & Wellness" > "Pharmacies"
        - JOHN R WONG SUPERMARKET should be classified as "Food & Dining" > "Restaurants"
        - USAIN BOLT'S TRACKS AND R should be classified as "Food & Dining" > "Restaurants"
        - Transactions with abbreviated or unclear merchant names should be classified based on available context clues with lower confidence scores
        
        ## CONFIDENCE SCORING GUIDELINES
        
        - 0.9-1.0: Nearly certain classification with exact matches to known merchants
        - 0.7-0.9: High confidence based on clear indicators in the merchant name
        - 0.5-0.7: Moderate confidence when some ambiguity exists
        - 0.3-0.5: Low confidence when classification relies heavily on inference
        - Below 0.3: Very low confidence, consider requesting more information
        
        ## RESPONSE FORMAT
        
        Respond in JSON format:
        {
            "primary_category": "string", // One of the 11 main categories listed above
            "subcategory": "string", // The most appropriate subcategory
            "confidence": float, // Confidence score between 0.0 and 1.0 based on guidelines above
            "description": "string", // Brief explanation of why this classification was chosen, including any identifying factors or special rules applied
            "alternative_category": "string" // Optional second-most likely category if confidence is below 0.7
        }
        
        ## ANALYSIS APPROACH
        
        1. First identify any known merchants from the special rules list
        2. Look for keywords in the merchant name that suggest industry or business type
        3. Consider common abbreviations and naming patterns in different industries
        4. Apply regional context if apparent from the merchant name
        5. Use the most specific subcategory possible that accurately reflects the merchant type

        """
