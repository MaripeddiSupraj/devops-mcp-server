from app.utils.logger import logger
from app.config import settings
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
        # Default to configured rolling window
        start_date = (datetime.now() - timedelta(days=settings.aws_default_cost_days)).strftime("%Y-%m-%d")
        
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

def list_aws_ec2_instances(region: str) -> dict:
    """
    List EC2 instances in a specific AWS region.
    """
    logger.info(f"Listing EC2 instances in region: {region}")
    try:
        ec2 = boto3.client("ec2", region_name=region)
        instances = []
        paginator = ec2.get_paginator("describe_instances")
        page_count = 0
        for page in paginator.paginate():
            page_count += 1
            if page_count > settings.aws_max_pages:
                break
            for reservation in page.get("Reservations", []):
                for inst in reservation.get("Instances", []):
                    name = "Unknown"
                    for tag in inst.get("Tags", []):
                        if tag["Key"] == "Name":
                            name = tag["Value"]
                            break

                    instances.append({
                        "id": inst.get("InstanceId"),
                        "name": name,
                        "type": inst.get("InstanceType"),
                        "state": inst.get("State", {}).get("Name"),
                        "private_ip": inst.get("PrivateIpAddress"),
                        "public_ip": inst.get("PublicIpAddress")
                    })
                
        return {"status": "success", "region": region, "instances": instances, "pages_scanned": page_count}
    except Exception as e:
        logger.error(f"Failed to list EC2 instances: {e}")
        return {"status": "error", "message": str(e)}

def list_aws_s3_buckets() -> dict:
    """
    List all S3 buckets in the AWS account.
    """
    logger.info("Listing S3 buckets")
    try:
        s3 = boto3.client("s3")
        response = s3.list_buckets()
        
        buckets = []
        for bucket in response.get("Buckets", []):
            buckets.append({
                "name": bucket.get("Name"),
                "creation_date": str(bucket.get("CreationDate"))
            })
                
        return {"status": "success", "buckets": buckets}
    except Exception as e:
        logger.error(f"Failed to list S3 buckets: {e}")
        return {"status": "error", "message": str(e)}

def list_aws_ecs_clusters(region: str) -> dict:
    """
    List ECS clusters in a specific AWS region.
    """
    logger.info(f"Listing ECS clusters in region: {region}")
    try:
        ecs = boto3.client("ecs", region_name=region)
        paginator = ecs.get_paginator("list_clusters")
        cluster_arns = []
        page_count = 0
        for page in paginator.paginate():
            page_count += 1
            if page_count > settings.aws_max_pages:
                break
            cluster_arns.extend(page.get("clusterArns", []))

        if not cluster_arns:
            return {"status": "success", "region": region, "clusters": [], "pages_scanned": page_count}

        # describe_clusters accepts up to 100 clusters per call
        desc_clusters = []
        for i in range(0, len(cluster_arns), 100):
            desc_response = ecs.describe_clusters(clusters=cluster_arns[i:i + 100])
            desc_clusters.extend(desc_response.get("clusters", []))
        
        clusters = []
        for cluster in desc_clusters:
            clusters.append({
                "name": cluster.get("clusterName"),
                "arn": cluster.get("clusterArn"),
                "status": cluster.get("status"),
                "running_tasks": cluster.get("runningTasksCount"),
                "pending_tasks": cluster.get("pendingTasksCount"),
                "active_services": cluster.get("activeServicesCount")
            })
                
        return {"status": "success", "region": region, "clusters": clusters, "pages_scanned": page_count}
    except Exception as e:
        logger.error(f"Failed to list ECS clusters: {e}")
        return {"status": "error", "message": str(e)}
