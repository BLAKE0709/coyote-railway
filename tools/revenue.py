import os
from datetime import datetime, timedelta

def get_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        return None

    from supabase import create_client
    return create_client(url, key)

def get_summary() -> dict:
    """Get revenue summary: today, MTD, MRR"""
    db = get_supabase()
    if not db:
        return {
            "today": 0,
            "mtd": 0,
            "mrr": 0,
            "subscribers": 0,
            "note": "Supabase not configured"
        }

    try:
        today = datetime.utcnow().date().isoformat()
        first_of_month = datetime.utcnow().replace(day=1).date().isoformat()

        # Today's revenue
        today_result = db.table("revenue_events")\
            .select("amount")\
            .gte("created_at", today)\
            .execute()
        today_total = sum(r["amount"] for r in today_result.data) if today_result.data else 0

        # MTD revenue
        mtd_result = db.table("revenue_events")\
            .select("amount")\
            .gte("created_at", first_of_month)\
            .execute()
        mtd_total = sum(r["amount"] for r in mtd_result.data) if mtd_result.data else 0

        # MRR (active subscribers)
        subs_result = db.table("subscribers")\
            .select("monthly_rate")\
            .eq("status", "active")\
            .execute()
        mrr = sum(r["monthly_rate"] or 0 for r in subs_result.data) if subs_result.data else 0
        sub_count = len(subs_result.data) if subs_result.data else 0

        return {
            "today": today_total,
            "mtd": mtd_total,
            "mrr": mrr,
            "subscribers": sub_count
        }
    except Exception as e:
        return {"error": str(e)}

def get_sms_formatted() -> str:
    """Return SMS-friendly revenue string"""
    data = get_summary()
    if "error" in data:
        return f"Revenue error: {data['error']}"
    return f"💰 Today: ${data['today']:.0f} | MTD: ${data['mtd']:.0f} | MRR: ${data['mrr']:.0f} | Subs: {data['subscribers']}"
