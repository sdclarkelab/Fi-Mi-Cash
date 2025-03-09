import asyncio
import json
import os
from pathlib import Path
from typing import List, Dict, Optional

import openai
from cachetools import TTLCache

from app.config import get_settings
from app.core.exceptions import ClassificationError
from app.core.logger import logger
from app.models.schemas import MerchantCategory

settings = get_settings()


class SpecialClassificationRuleManager:
    """Manager for merchant classification rules with JSON persistence."""

    def __init__(self, rules_file_path: Optional[str] = None):
        self.rules_file = Path(rules_file_path or os.path.join(
            os.path.dirname(__file__), "../data/classification_rules.json"))
        self._rules = []
        self._load_rules()

    def _load_rules(self) -> None:
        """Load rules from the JSON file."""
        try:
            if self.rules_file.exists():
                with open(self.rules_file, 'r') as f:
                    data = json.load(f)
                    self._rules = data.get("special_rules", [])
            else:
                # Create file with default rules if it doesn't exist
                self._rules = self._get_default_rules()
                self._save_rules()
        except Exception as e:
            logger.error(f"Failed to load classification rules: {str(e)}")
            self._rules = self._get_default_rules()

    def _save_rules(self) -> None:
        """Save rules to the JSON file."""
        try:
            # Ensure directory exists
            self.rules_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.rules_file, 'w') as f:
                json.dump({"special_rules": self._rules}, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save classification rules: {str(e)}")

    def _get_default_rules(self) -> List[Dict[str, str]]:
        """Return default classification rules."""
        return [
            {"merchant": "Cafes serving primarily beverages", "category": "Food & Dining",
             "subcategory": "Restaurants"},
            {"merchant": "Cafes serving full meals", "category": "Food & Dining", "subcategory": "Restaurants"},
            {"merchant": "Wholesale clubs (like Pricesmart)", "category": "Food & Dining",
             "subcategory": "Groceries & Supermarkets"},
            {"merchant": "HI-LO", "category": "Food & Dining", "subcategory": "Groceries & Supermarkets"},
            {"merchant": "DIGP", "category": "Services", "subcategory": "Utilities"},
            {"merchant": "NWCJ", "category": "Services", "subcategory": "Utilities"},
            {"merchant": "FONTANA -WATERLOO SQUARE", "category": "Health & Wellness", "subcategory": "Pharmacies"},
            {"merchant": "JOHN R WONG SUPERMARKET", "category": "Food & Dining", "subcategory": "Restaurants"},
            {"merchant": "USAIN BOLT'S TRACKS AND R", "category": "Food & Dining", "subcategory": "Restaurants"}
        ]

    def get_all_rules(self) -> List[Dict[str, str]]:
        """Return all special classification rules."""
        return self._rules.copy()

    def add_rule(self, merchant: str, category: str, subcategory: str) -> bool:
        """Add a new special classification rule."""
        # Check if rule already exists
        for rule in self._rules:
            if rule["merchant"].lower() == merchant.lower():
                return False

        self._rules.append({
            "merchant": merchant,
            "category": category,
            "subcategory": subcategory
        })
        self._save_rules()
        return True

    def edit_rule(self, merchant: str, category: str, subcategory: str) -> bool:
        """Edit an existing special classification rule."""
        for i, rule in enumerate(self._rules):
            if rule["merchant"].lower() == merchant.lower():
                self._rules[i] = {
                    "merchant": merchant,
                    "category": category,
                    "subcategory": subcategory
                }
                self._save_rules()
                return True
        return False

    def delete_rule(self, merchant: str) -> bool:
        """Delete a special classification rule."""
        for i, rule in enumerate(self._rules):
            if rule["merchant"].lower() == merchant.lower():
                self._rules.pop(i)
                self._save_rules()
                return True
        return False

    def format_rules_for_prompt(self) -> str:
        """Format rules for inclusion in the classification prompt."""
        rules_text = "\n\n## SPECIAL CLASSIFICATION RULES\n\n"
        for rule in self._rules:
            rules_text += f"- {rule['merchant']} should be classified as \"{rule['category']}\" > \"{rule['subcategory']}\"\n"

        # Add the special rule about unclear merchant names
        rules_text += "- Transactions with abbreviated or unclear merchant names should be classified based on available context clues with lower confidence scores\n"

        return rules_text


class MerchantClassifier:
    def __init__(self):
        self.client = openai.Client(api_key=settings.OPENAI_API_KEY)
        self.cache = TTLCache(
            maxsize=settings.CACHE_MAX_SIZE,
            ttl=settings.CACHE_TTL
        )
        self.rule_manager = SpecialClassificationRuleManager()

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
        base_prompt = """
        You are a merchant classification expert with detailed knowledge of business categories across multiple industries. Your task is to analyze merchant names and classify them into the most appropriate category and subcategory with high accuracy.

        ## PRIMARY CATEGORIES AND SUBCATEGORIES
        
        1. Food & Dining
           - Restaurants (sit-down, fast food, takeout)
           - Groceries & Supermarkets
        
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

        return base_prompt + self.rule_manager.format_rules_for_prompt()
