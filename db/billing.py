from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import text

from db.neon import engine

PLAN_LIMITS = {
    "FREE": {
        "documentUploads": 3,
        "chatMessages": 20,
        "portfolioSearches": 5,
        "agentRuns": 3,
    },
    "PRO": {
        "documentUploads": 30,
        "chatMessages": 200,
        "portfolioSearches": 50,
        "agentRuns": 30,
    },
    "PRO_PLUS": {
        "documentUploads": 999999,
        "chatMessages": 999999,
        "portfolioSearches": 999999,
        "agentRuns": 999999,
    },
}

FEATURE_COLUMNS = {
    "documentUploads": "documentUploads",
    "chatMessages": "chatMessages",
    "portfolioSearches": "portfolioSearches",
    "agentRuns": "agentRuns",
}

FEATURE_LABELS = {
    "documentUploads": "document uploads",
    "chatMessages": "chat messages",
    "portfolioSearches": "portfolio searches",
    "agentRuns": "agent runs",
}


def assert_usage_allowed(user_id: str, feature: str) -> None:
    if feature not in FEATURE_COLUMNS:
        raise HTTPException(status_code=400, detail="Invalid usage feature")

    now = datetime.utcnow()
    month = now.month
    year = now.year
    column = FEATURE_COLUMNS[feature]

    with engine.connect() as conn:
        user_row = conn.execute(
            text(
                'SELECT role, plan, "subscriptionStatus" FROM "User" WHERE id = :user_id LIMIT 1'
            ),
            {"user_id": user_id},
        ).mappings().first()

        if not user_row:
            raise HTTPException(status_code=404, detail="User not found")

        if user_row["role"] == "admin":
            return

        plan = user_row["plan"] or "FREE"
        if user_row["subscriptionStatus"] != "ACTIVE":
            plan = "FREE"
        limit = PLAN_LIMITS.get(plan, PLAN_LIMITS["FREE"])[feature]

        usage_row = conn.execute(
            text(
                f'''
                SELECT "{column}" AS current
                FROM "Usage"
                WHERE "userId" = :user_id AND month = :month AND year = :year
                LIMIT 1
                '''
            ),
            {"user_id": user_id, "month": month, "year": year},
        ).mappings().first()

        current = int(usage_row["current"]) if usage_row else 0
        if current >= limit:
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Monthly {FEATURE_LABELS[feature]} limit reached on your "
                    f"{plan} plan. Upgrade to continue."
                ),
            )
