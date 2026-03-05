from app.utils.logger import logger
import boto3
from datetime import datetime, timedelta

def estimate_aws_cost(service: str = None, start_date: str = None, end_date: str = None) -> dict:
    """
    Query AWS Cost Explorer for billing estimates.
    If dates are not provided, defaults to the last 30 days.
    """
    logger.info(f"Estimating AWS cost for service={service}, start={start_date}, end={end_date}")
    
    # Calculate dates if not provided
    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")
    
    if not start_date:
        # Default to 30 days ago
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        
    try:
        # This requires standard AWS credentials in the environment
        ce = boto3.client("ce")
        
        # Base query
        query = {
            "TimePeriod": {
                'Start': start_date,
                'End': end_date
            },
            "Granularity": 'MONTHLY',
            "Metrics": ['UnblendedCost']
        }
        
        # Add filter if a specific service was requested
        if service and service.lower() != "all":
            query["Filter"] = {
                "Dimensions": {
                    "Key": "SERVICE",
                    "Values": [service]
                }
            }
            
        response = ce.get_cost_and_usage(**query)
        
        # Extract the results cleanly
        results = []
        for result in response.get("ResultsByTime", []):
            cost_info = result.get("Total", {}).get("UnblendedCost", {})
            amount = cost_info.get("Amount", "0")
            unit = cost_info.get("Unit", "USD")
            
            results.append({
                "period_start": result.get("TimePeriod", {}).get("Start"),
                "period_end": result.get("TimePeriod", {}).get("End"),
                "cost": f"{float(amount):.2f} {unit}"
            })
            
        return {
            "query_period": f"{start_date} to {end_date}",
            "service": service or "All Services",
            "results": results,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch AWS costs: {e}")
        return {
            "status": "error",
            "error_message": str(e),
            "hint": "Ensure the application has AWS credentials with Cost Explorer (ce:GetCostAndUsage) permissions."
        }
