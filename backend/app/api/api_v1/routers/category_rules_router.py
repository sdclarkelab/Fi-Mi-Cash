from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException, Path

from app.api.api_v1.dependencies import get_classifier
from app.models.schemas import ClassificationRule, ClassificationRuleResponse, ClassificationRulesResponse
from app.services.classifier_service import MerchantClassifier

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("", response_model=ClassificationRulesResponse)
async def get_all_rules(classifier: MerchantClassifier = Depends(get_classifier)):
    """Get all special classification rules."""
    rules = classifier.rule_manager.get_all_rules()
    return ClassificationRulesResponse(rules=rules)


@router.post("", response_model=ClassificationRuleResponse)
async def add_rule(rule: ClassificationRule, classifier: MerchantClassifier = Depends(get_classifier)):
    """Add a new special classification rule."""
    success = classifier.rule_manager.add_rule(
        merchant=rule.merchant,
        category=rule.category,
        subcategory=rule.subcategory
    )
    if not success:
        raise HTTPException(status_code=409, detail=f"Rule for '{rule.merchant}' already exists")

    return ClassificationRuleResponse(
        merchant=rule.merchant,
        category=rule.category,
        subcategory=rule.subcategory,
        success=True
    )


@router.put("", response_model=ClassificationRuleResponse)
async def update_rule(rule: ClassificationRule, classifier: MerchantClassifier = Depends(get_classifier)):
    """Update an existing special classification rule."""
    success = classifier.rule_manager.edit_rule(
        merchant=rule.merchant,
        category=rule.category,
        subcategory=rule.subcategory
    )
    if not success:
        raise HTTPException(status_code=404, detail=f"Rule for '{rule.merchant}' not found")

    return ClassificationRuleResponse(
        merchant=rule.merchant,
        category=rule.category,
        subcategory=rule.subcategory,
        success=True
    )


@router.delete("/{merchant}", response_model=ClassificationRuleResponse)
async def delete_rule(
        merchant: str = Path(..., description="The merchant name of the rule to delete"),
        classifier: MerchantClassifier = Depends(get_classifier)
):
    """Delete a special classification rule."""
    # URL decode the merchant name
    merchant = unquote(merchant)
    success = classifier.rule_manager.delete_rule(merchant)
    if not success:
        raise HTTPException(status_code=404, detail=f"Rule for '{merchant}' not found")

    return ClassificationRuleResponse(
        merchant=merchant,
        category="",
        subcategory="",
        success=True
    )
